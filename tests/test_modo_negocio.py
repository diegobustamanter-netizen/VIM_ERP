"""Modo de negocio: productos o servicios, nunca los dos mezclados."""

from base import PruebaVIM


class PruebaModoNegocio(PruebaVIM):

    def setUp(self):
        super().setUp()
        self.abrir_caja()
        self.configurar_iva(0)

    # ------------------------------------------------------------------
    # Configuración
    # ------------------------------------------------------------------

    def test_por_defecto_arranca_sin_configurar(self):
        """Instalación nueva: hay que preguntarle al dueño qué tipo de negocio es."""
        from database import negocio

        self.assertFalse(negocio.modo_configurado())
        self.assertEqual(negocio.obtener_modo_negocio(), negocio.MODO_PRODUCTOS,
                         "Sin configurar debe comportarse como siempre (productos)")

    def test_cambiar_de_modo_invalida_la_cache(self):
        """El modo se cachea en memoria: si no se limpia, la UI queda desfasada."""
        from database import negocio

        self.assertFalse(negocio.es_negocio_de_servicios())
        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS)
        self.assertTrue(negocio.es_negocio_de_servicios(),
                        "La caché quedó con el modo anterior")

    def test_modo_invalido_se_rechaza(self):
        from database import negocio

        with self.assertRaises(ValueError):
            negocio.establecer_modo_negocio("cualquier_cosa")

    # ------------------------------------------------------------------
    # Conversión de ítems
    # ------------------------------------------------------------------

    def test_pasar_a_servicios_convierte_y_anula_el_stock(self):
        from database import negocio

        self.crear_producto(nombre="Shampoo", stock=50)
        self.crear_producto(nombre="Tijera", stock=10)

        convertidos = negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS,
                                                      convertir=True)
        self.assertGreaterEqual(convertidos, 2)

        with self.conectar() as con:
            filas = con.execute(
                "SELECT tipo_item, stock FROM productos WHERE activo = 1"
            ).fetchall()

        self.assertTrue(all(f["tipo_item"] == "servicio" for f in filas),
                        "Quedaron ítems sin convertir")
        self.assertTrue(all(f["stock"] == 0 for f in filas),
                        "Un servicio no puede tener stock")

    def test_convertir_no_toca_las_ventas_historicas(self):
        """Cambiar el modo no puede reescribir lo que ya pasó."""
        from database.ventas import confirmar_venta
        from database import negocio

        pid = self.crear_producto(precio_venta=1000, precio_compra=400, stock=100)
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=5, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        antes = self.pnl()["ingresos_ventas"]
        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS, convertir=True)
        despues = self.pnl()["ingresos_ventas"]

        self.assertEqual(antes, despues, "Cambiar de modo alteró ventas ya registradas")

    def test_contar_antes_de_convertir_no_modifica_nada(self):
        """El conteo que se le muestra al usuario debe ser solo lectura."""
        from database import negocio

        self.crear_producto(nombre="Algo", stock=7)
        negocio.contar_items_a_convertir(negocio.MODO_SERVICIOS)

        with self.conectar() as con:
            fila = con.execute(
                "SELECT tipo_item, stock FROM productos WHERE nombre = 'Algo'"
            ).fetchone()

        self.assertEqual(fila["tipo_item"], "producto")
        self.assertEqual(fila["stock"], 7)

    # ------------------------------------------------------------------
    # Reflejo en los reportes
    # ------------------------------------------------------------------

    def test_servicios_no_valoriza_inventario(self):
        from database.reportes_financieros import obtener_resumen_balance_general
        from database import negocio

        self.crear_producto(precio_compra=500, stock=100)

        self.assertTrue(obtener_resumen_balance_general()["mostrar_inventario"])

        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS, convertir=True)
        balance = obtener_resumen_balance_general()

        self.assertFalse(balance["mostrar_inventario"])
        self.assertEqual(balance["activos"]["inventario"], 0)

    def test_servicios_sin_costo_oculta_costo_y_margen(self):
        """Mostrar 'costo 0 / margen 100%' es ruido: se omite."""
        from database.ventas import confirmar_venta
        from database import negocio

        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS)
        pid = self.crear_producto(precio_venta=8000, precio_compra=0,
                                  stock=0, tipo_item="servicio")
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=2, precio_unitario=8000,
                               tipo_item="servicio")],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        datos = self.pnl()
        self.assertEqual(datos["modo_negocio"], "servicios")
        self.assertEqual(datos["costo_ventas"], 0)
        self.assertFalse(datos["mostrar_costo"])
        self.assertFalse(datos["mostrar_margen_bruto"])
        self.assertEqual(datos["etiqueta_ingresos"], "Ingresos por servicios")

    def test_servicios_con_costo_si_muestra_el_margen(self):
        """Si cargan costo directo, el margen sí aporta y debe verse."""
        from database.ventas import confirmar_venta
        from database import negocio

        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS)
        pid = self.crear_producto(precio_venta=8000, precio_compra=2000,
                                  stock=0, tipo_item="servicio")
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=2, precio_unitario=8000,
                               tipo_item="servicio")],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        datos = self.pnl()
        self.assertEqual(datos["costo_ventas"], 4000)
        self.assertTrue(datos["mostrar_costo"])
        self.assertTrue(datos["mostrar_margen_bruto"])
        self.assertEqual(datos["utilidad_bruta"], 12000)

    def test_la_utilidad_no_depende_del_modo(self):
        """El modo cambia cómo se presenta, no cuánto se ganó."""
        from database.ventas import confirmar_venta
        from database import negocio

        pid = self.crear_producto(precio_venta=1000, precio_compra=400, stock=100)
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=10, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        utilidad_productos = self.pnl()["utilidad_neta"]
        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS, convertir=True)
        utilidad_servicios = self.pnl()["utilidad_neta"]

        self.assertEqual(utilidad_productos, utilidad_servicios)
