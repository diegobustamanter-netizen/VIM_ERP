"""Estado de Resultados: que la utilidad refleje lo que realmente pasó.

Cada prueba de acá corresponde a un error que el sistema tuvo y que se corrigió.
Si alguna falla, ese error volvió.
"""

from base import PruebaVIM


class PruebaEstadoResultados(PruebaVIM):

    def setUp(self):
        super().setUp()
        self.caja_id = self.abrir_caja()
        # Sin IVA: estas pruebas miden cómo se clasifican gastos e ingresos,
        # no el cálculo del impuesto (que se prueba en PruebaCalculoIVA).
        self.configurar_iva(0)

    # ------------------------------------------------------------------
    # Doble conteo de mercadería
    # ------------------------------------------------------------------

    def test_compra_de_mercaderia_no_es_gasto(self):
        """La mercadería se reconoce como costo al VENDER, no al comprar.

        Contarla en ambos lados hacía aparecer pérdidas inexistentes.
        """
        self.crear_compra(100000, "compra_inventario",
                          cuenta_contable_id=self.cuenta_contable("Mercaderías"))

        datos = self.pnl()

        self.assertNotIn("Mercaderías", self.nombres_de_gastos(datos),
                         "La compra de mercadería volvió a contarse como gasto")
        self.assertEqual(datos["total_gastos"], 0)

    def test_gasto_operativo_real_si_es_gasto(self):
        """Contracara del anterior: un arriendo SÍ es gasto del período."""
        self.crear_compra(20000, "gasto_operativo",
                          cuenta_contable_id=self.cuenta_contable("Arriendo"))

        datos = self.pnl()

        self.assertIn("Arriendo", self.nombres_de_gastos(datos))
        self.assertEqual(datos["total_gastos"], 20000)

    # ------------------------------------------------------------------
    # Activos fijos
    # ------------------------------------------------------------------

    def test_activo_fijo_no_es_gasto(self):
        """Comprar una máquina es inversión que se deprecia, no gasto del mes."""
        self.crear_compra(50000, "activo_fijo",
                          cuenta_contable_id=self.cuenta_contable("Maquinaria y Equipo"))

        datos = self.pnl()

        for nombre in self.nombres_de_gastos(datos):
            self.assertNotIn("Maquinaria", nombre)
            self.assertNotIn("Activos Fijos", nombre)
        self.assertEqual(datos["total_gastos"], 0)

    # ------------------------------------------------------------------
    # Movimientos de caja ad-hoc
    # ------------------------------------------------------------------

    def test_aporte_de_capital_no_infla_la_utilidad(self):
        """Meter plata a la caja no es ganar plata.

        Antes los ingresos ad-hoc se restaban de los gastos, así que un aporte
        del dueño hacía subir la utilidad sin haber vendido nada.
        """
        self.movimiento_caja(self.caja_id, "egreso", 5000)
        self.movimiento_caja(self.caja_id, "ingreso", 200000, categoria="aporte")

        datos = self.pnl()

        self.assertEqual(datos["total_gastos"], 5000,
                         "El aporte de capital volvió a netearse contra los gastos")
        self.assertEqual(datos["otros_ingresos_caja"], 200000,
                         "El aporte debe informarse aparte")
        self.assertLess(datos["utilidad_neta"], 0,
                        "Sin ventas y con gastos, la utilidad tiene que ser negativa")

    # ------------------------------------------------------------------
    # Escenario completo
    # ------------------------------------------------------------------

    def test_escenario_completo_da_la_utilidad_correcta(self):
        """Compro, vendo parte, invierto y recibo un aporte: la utilidad es una sola."""
        from database.ventas import confirmar_venta

        pid = self.crear_producto(precio_venta=2000, precio_compra=1000, stock=100)

        self.crear_compra(100000, "compra_inventario",
                          cuenta_contable_id=self.cuenta_contable("Mercaderías"))
        self.crear_compra(50000, "activo_fijo",
                          cuenta_contable_id=self.cuenta_contable("Maquinaria y Equipo"))
        self.crear_compra(20000, "gasto_operativo",
                          cuenta_contable_id=self.cuenta_contable("Arriendo"))
        self.movimiento_caja(self.caja_id, "egreso", 5000)
        self.movimiento_caja(self.caja_id, "ingreso", 200000, categoria="aporte")

        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=40, precio_unitario=2000)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        datos = self.pnl()

        self.assertEqual(datos["ingresos_ventas"], 80000)
        self.assertEqual(datos["costo_ventas"], 40000)   # 40 unidades x costo 1000
        self.assertEqual(datos["utilidad_bruta"], 40000)
        self.assertEqual(datos["total_gastos"], 25000)   # arriendo + caja ad-hoc
        self.assertEqual(datos["utilidad_neta"], 15000)

    # ------------------------------------------------------------------
    # IVA
    # ------------------------------------------------------------------

    def test_iva_coincide_entre_los_dos_reportes(self):
        """El mismo impuesto no puede dar distinto según dónde se lo mire."""
        from database.reportes_financieros import obtener_reporte_iva
        from database.utils import ahora

        self.crear_compra(50000, "gasto_operativo", impuesto=9500,
                          cuenta_contable_id=self.cuenta_contable("Arriendo"))

        hoy = ahora("%Y-%m-%d")
        datos = self.pnl()
        iva = obtener_reporte_iva(hoy, hoy)

        self.assertEqual(datos["impuestos_estimados"], iva["iva_a_pagar"])
        self.assertEqual(iva["iva_credito"], 9500)

    def test_boleta_no_da_credito_de_iva(self):
        """Solo las facturas dan derecho a crédito fiscal."""
        from database.reportes_financieros import obtener_reporte_iva
        from database.utils import ahora

        self.crear_compra(50000, "gasto_operativo", impuesto=9500,
                          tipo_documento="boleta",
                          cuenta_contable_id=self.cuenta_contable("Arriendo"))

        hoy = ahora("%Y-%m-%d")
        self.assertEqual(obtener_reporte_iva(hoy, hoy)["iva_credito"], 0)

    # ------------------------------------------------------------------
    # Ventas anuladas
    # ------------------------------------------------------------------

    def test_venta_anulada_no_suma_a_los_ingresos(self):
        """Una venta anulada no facturó: no puede aparecer en el resultado."""
        from database.ventas import confirmar_venta, anular_venta

        pid = self.crear_producto(precio_venta=2000, precio_compra=1000, stock=100)
        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(pid, cantidad=10, precio_unitario=2000)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)
        self.assertEqual(self.pnl()["ingresos_ventas"], 20000)

        anulada, mensaje = anular_venta(venta_id, usuario_id=1, motivo="Prueba")
        self.assertTrue(anulada, mensaje)

        datos = self.pnl()
        self.assertEqual(datos["ingresos_ventas"], 0,
                         "La venta anulada sigue sumando a los ingresos")
        self.assertEqual(datos["costo_ventas"], 0,
                         "La venta anulada sigue sumando al costo de ventas")

    # ------------------------------------------------------------------
    # Robustez
    # ------------------------------------------------------------------

    def test_periodo_sin_movimientos_no_rompe(self):
        """Un período vacío debe dar ceros, no una excepción."""
        datos = self.pnl("2020-01-01", "2020-01-31")

        self.assertEqual(datos["ingresos_ventas"], 0)
        self.assertEqual(datos["total_gastos"], 0)
        self.assertEqual(datos["utilidad_neta"], 0)
        self.assertEqual(datos["margen_bruto_pct"], 0)
        self.assertEqual(datos["punto_equilibrio"], 0)


class PruebaCalculoIVA(PruebaVIM):
    """El impuesto en sí: separar bien neto de bruto."""

    def setUp(self):
        super().setUp()
        self.caja_id = self.abrir_caja()

    def _vender(self, precio, cantidad=1):
        from database.ventas import confirmar_venta
        pid = self.crear_producto(precio_venta=precio, precio_compra=0, stock=1000)
        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(pid, cantidad=cantidad, precio_unitario=precio)],
            9999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)
        with self.conectar() as con:
            return dict(con.execute(
                "SELECT total, impuesto FROM ventas WHERE id = ?", (venta_id,)
            ).fetchone())

    def test_precios_con_iva_incluido(self):
        """Si el precio ya trae IVA, el total es el precio y el neto se despeja."""
        self.configurar_iva(19, incluido=True)
        venta = self._vender(11900)

        self.assertAlmostEqual(venta["total"], 11900, places=2)
        self.assertAlmostEqual(venta["impuesto"], 1900, places=2)
        self.assertAlmostEqual(self.pnl()["ingresos_ventas"], 10000, places=2)

    def test_precios_sin_iva_incluido(self):
        """Si el precio es neto, el IVA se suma encima."""
        self.configurar_iva(19, incluido=False)
        venta = self._vender(10000)

        self.assertAlmostEqual(venta["total"], 11900, places=2)
        self.assertAlmostEqual(venta["impuesto"], 1900, places=2)
        self.assertAlmostEqual(self.pnl()["ingresos_ventas"], 10000, places=2)

    def test_iva_en_cero_deja_el_precio_tal_cual(self):
        """Negocio sin IVA: lo que se carga es lo que se cobra."""
        for incluido in (True, False):
            with self.subTest(iva_incluido=incluido):
                self.configurar_iva(0, incluido=incluido)
                venta = self._vender(10000)
                self.assertAlmostEqual(venta["total"], 10000, places=2)
                self.assertAlmostEqual(venta["impuesto"], 0, places=2)
