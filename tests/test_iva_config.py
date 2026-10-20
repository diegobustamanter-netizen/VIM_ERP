"""IVA según la configuración: lo que ve el cajero es lo que se cobra.

Antes, con "los precios ya incluyen IVA" desactivado, el POS mostraba $1.000
y el sistema cobraba $1.190: el pago justo se rechazaba y toda venta con
tarjeta fallaba con "Pago insuficiente".
"""

from base import PruebaVIM


class PruebaTotalesSegunConfiguracion(PruebaVIM):

    def setUp(self):
        super().setUp()
        self.abrir_caja()

    def _config(self, pct=19, incluido=True, redondeo=False):
        self.configurar_iva(pct, incluido=incluido)
        with self.conectar() as con:
            con.execute("UPDATE configuracion SET valor = ? WHERE clave = 'redondeo_automatico'",
                        ("1" if redondeo else "0",))
            con.commit()

    def _montos(self, subtotal, metodo="efectivo"):
        from database.finanzas_utils import calcular_totales_venta
        return calcular_totales_venta(subtotal, metodo_pago=metodo)

    def _vender(self, precio, metodo, pago):
        from database.ventas import confirmar_venta
        pid = self.crear_producto(precio_venta=precio, stock=100)
        return confirmar_venta([self.linea_ticket(pid, cantidad=1, precio_unitario=precio)],
                               pago, metodo, usuario_id=1)

    def _guardado(self, venta_id):
        with self.conectar() as con:
            return dict(con.execute("SELECT total, impuesto, vuelto FROM ventas WHERE id = ?",
                                    (venta_id,)).fetchone())

    # ------------------------------------------------------------------

    def test_sin_iva_incluido_la_tarjeta_cobra_lo_que_muestra_el_pos(self):
        """El POS manda pago = total para tarjeta. Antes ese total no incluía el IVA."""
        self._config(19, incluido=False)
        a_cobrar = self._montos(1000, "tarjeta")["total"]
        self.assertEqual(a_cobrar, 1190, "El POS tiene que mostrar el precio + IVA")

        ok, msg, vid = self._vender(1000, "tarjeta", a_cobrar)

        self.assertTrue(ok, f"La venta con tarjeta falló: {msg}")
        self.assertEqual(self._guardado(vid)["total"], 1190)

    def test_sin_iva_incluido_el_pago_justo_en_efectivo_alcanza(self):
        self._config(19, incluido=False)
        a_cobrar = self._montos(1000)["total"]

        ok, msg, vid = self._vender(1000, "efectivo", a_cobrar)

        self.assertTrue(ok, msg)
        self.assertEqual(self._guardado(vid)["vuelto"], 0)

    def test_con_iva_incluido_se_cobra_el_precio(self):
        self._config(19, incluido=True)
        montos = self._montos(1000)

        self.assertEqual((montos["total"], montos["impuesto"], montos["neto"]), (1000, 160, 840))

    def test_iva_cero_no_cobra_impuesto_marque_lo_que_marque(self):
        for incluido in (True, False):
            with self.subTest(incluido=incluido):
                self._config(0, incluido=incluido)
                montos = self._montos(1000)
                self.assertEqual((montos["total"], montos["impuesto"]), (1000, 0))

    # ------------------------------------------------------------------
    # Redondeo
    # ------------------------------------------------------------------

    def test_el_redondeo_es_solo_para_efectivo(self):
        """Con tarjeta se cobra exacto; el redondeo existe porque faltan monedas."""
        self._config(0, redondeo=True)

        self.assertEqual(self._montos(1234, "efectivo")["total"], 1230)
        self.assertEqual(self._montos(1234, "tarjeta")["total"], 1234)

    def test_el_redondeo_sube_desde_5(self):
        self._config(0, redondeo=True)
        for subtotal, esperado in [(1221, 1220), (1224, 1220), (1225, 1230), (1235, 1240), (1239, 1240)]:
            with self.subTest(subtotal=subtotal):
                self.assertEqual(self._montos(subtotal)["total"], esperado)

    def test_redondeo_y_venta_guardada_coinciden(self):
        self._config(0, redondeo=True)
        a_cobrar = self._montos(1235)["total"]

        ok, msg, vid = self._vender(1235, "efectivo", a_cobrar)

        self.assertTrue(ok, msg)
        self.assertEqual(self._guardado(vid)["total"], 1240)

    def test_el_redondeo_no_cambia_el_iva(self):
        self._config(19, incluido=True, redondeo=True)
        efectivo = self._montos(1234, "efectivo")
        tarjeta = self._montos(1234, "tarjeta")

        self.assertEqual(efectivo["impuesto"], tarjeta["impuesto"])
        self.assertEqual(efectivo["ajuste_redondeo"], -4)

    # ------------------------------------------------------------------
    # Configuración incompleta
    # ------------------------------------------------------------------

    def test_sin_la_clave_iva_incluido_se_asume_incluido(self):
        """Una base vieja sin esa clave no puede empezar a sumar IVA encima."""
        from database.finanzas_utils import obtener_config_finanzas
        with self.conectar() as con:
            con.execute("DELETE FROM configuracion WHERE clave = 'iva_incluido'")
            con.commit()

        self.assertTrue(obtener_config_finanzas()["iva_incluido"])

    def test_un_iva_mal_escrito_no_rompe_las_ventas(self):
        from database.finanzas_utils import obtener_config_finanzas
        with self.conectar() as con:
            con.execute("UPDATE configuracion SET valor = 'diecinueve' WHERE clave = 'iva_porcentaje'")
            con.commit()

        self.assertEqual(obtener_config_finanzas()["iva_porcentaje"], 19.0)
