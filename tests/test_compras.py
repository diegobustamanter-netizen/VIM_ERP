"""Compras: qué se puede registrar según el tipo de negocio."""

from base import PruebaVIM


class PruebaOpcionesDeCompra(PruebaVIM):

    def _tipos(self):
        from database.negocio import tipos_de_operacion_disponibles
        return tipos_de_operacion_disponibles()

    def _cuentas(self):
        from database.negocio import cuentas_aplicables
        from database.plan_cuentas import obtener_plan_cuentas
        return cuentas_aplicables(obtener_plan_cuentas())

    def _a_servicios(self):
        from database import negocio
        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS, convertir=True)

    # ------------------------------------------------------------------
    # Modo productos: todo disponible
    # ------------------------------------------------------------------

    def test_productos_ofrece_compra_de_inventario(self):
        tipos = self._tipos()

        self.assertIn("compra_inventario", tipos)
        self.assertEqual(tipos[0], "compra_inventario",
                         "En un negocio de productos debería venir preseleccionada")

    def test_productos_ofrece_la_cuenta_mercaderias(self):
        nombres = [c["nombre"] for c in self._cuentas()]
        self.assertIn("Mercaderías", nombres)

    # ------------------------------------------------------------------
    # Modo servicios: sin inventario
    # ------------------------------------------------------------------

    def test_servicios_no_ofrece_compra_de_inventario(self):
        """Sin inventario que reponer, esa opción solo lleva a clasificar mal."""
        self._a_servicios()
        tipos = self._tipos()

        self.assertNotIn("compra_inventario", tipos)
        self.assertEqual(tipos[0], "gasto_operativo",
                         "Debería preseleccionar un gasto operativo")

    def test_servicios_no_ofrece_cuentas_inventariables(self):
        self._a_servicios()

        for cuenta in self._cuentas():
            self.assertFalse(cuenta.get("es_inventariable"),
                             f"Se ofreció la cuenta inventariable '{cuenta['nombre']}'")

    def test_servicios_conserva_las_cuentas_de_gasto(self):
        """Una peluquería igual paga arriendo, luz y sueldos."""
        self._a_servicios()
        nombres = [c["nombre"] for c in self._cuentas()]

        for esperada in ("Arriendo", "Luz", "Sueldos y Salarios"):
            self.assertIn(esperada, nombres)

    def test_la_cuenta_preseleccionada_existe_en_la_lista(self):
        """Evita que el combo arranque con un valor que ya no está.

        Antes quedaba fijo en 'Mercaderías', que en modo servicios ya no
        aparece entre las opciones.
        """
        self._a_servicios()
        cuentas = self._cuentas()
        opciones = [f"{c['codigo']} - {c['nombre']}" for c in cuentas]

        self.assertTrue(opciones, "No quedó ninguna cuenta para elegir")
        preferida = "1.1 - Mercaderías"
        elegida = preferida if preferida in opciones else opciones[0]

        self.assertIn(elegida, opciones)
        self.assertNotEqual(elegida, preferida)

    # ------------------------------------------------------------------
    # Efecto en el resultado
    # ------------------------------------------------------------------

    def test_todos_los_tipos_ofrecidos_son_gasto_o_inversion(self):
        """Lo que se ofrece en servicios va a gastos o a activos, nunca a stock."""
        self._a_servicios()
        self.assertEqual(set(self._tipos()),
                         {"gasto_operativo", "sueldos", "activo_fijo"})

    def test_un_gasto_de_servicios_llega_al_estado_de_resultados(self):
        """Registrar el arriendo de la peluquería tiene que verse en el P&L."""
        self._a_servicios()
        self.configurar_iva(0)
        self.crear_compra(30000, "gasto_operativo",
                          cuenta_contable_id=self.cuenta_contable("Arriendo"))

        datos = self.pnl()

        self.assertIn("Arriendo", self.nombres_de_gastos(datos))
        self.assertEqual(datos["total_gastos"], 30000)

    def test_un_activo_fijo_de_servicios_sigue_sin_ser_gasto(self):
        """Comprar sillones es inversión, también en una peluquería."""
        self._a_servicios()
        self.configurar_iva(0)
        self.crear_compra(80000, "activo_fijo",
                          cuenta_contable_id=self.cuenta_contable("Instalaciones / Mobiliario"))

        self.assertEqual(self.pnl()["total_gastos"], 0)
