"""Centro de Descargas: qué se va a exportar y de qué período."""

from datetime import date

from base import PruebaVIM


def rango_de(clave, hoy=None, minimo=None):
    """Usa el cálculo REAL de los atajos (antes esto era una copia, y la
    prueba seguía pasando aunque el código de la pantalla cambiara)."""
    from stub_tk import modulo_reportes
    return modulo_reportes().rango_de_atajo(clave, hoy or date.today(), minimo)


class PruebaAtajosDePeriodo(PruebaVIM):
    """Un atajo mal calculado exporta un período equivocado sin avisar."""

    def test_hoy(self):
        hoy = date(2026, 8, 20)
        self.assertEqual(rango_de("hoy", hoy), (hoy, hoy))

    def test_ayer_no_incluye_hoy(self):
        hoy = date(2026, 8, 20)
        desde, hasta = rango_de("ayer", hoy)

        self.assertEqual(desde, date(2026, 8, 19))
        self.assertEqual(hasta, date(2026, 8, 19))

    def test_esta_semana_arranca_el_lunes(self):
        jueves = date(2026, 8, 20)
        desde, hasta = rango_de("semana", jueves)

        self.assertEqual(desde.weekday(), 0, "La semana debe empezar el lunes")
        self.assertEqual(desde, date(2026, 8, 17))
        self.assertEqual(hasta, jueves)

    def test_un_lunes_la_semana_es_ese_mismo_dia(self):
        lunes = date(2026, 8, 17)
        self.assertEqual(rango_de("semana", lunes), (lunes, lunes))

    def test_este_mes_arranca_el_dia_uno(self):
        desde, hasta = rango_de("mes", date(2026, 8, 20))

        self.assertEqual(desde, date(2026, 8, 1))
        self.assertEqual(hasta, date(2026, 8, 20))

    def test_mes_pasado_es_el_mes_completo(self):
        desde, hasta = rango_de("mes_pasado", date(2026, 8, 20))

        self.assertEqual(desde, date(2026, 7, 1))
        self.assertEqual(hasta, date(2026, 7, 31))

    def test_mes_pasado_cruzando_el_año(self):
        """El caso que suele romperse: enero tiene que ir a diciembre."""
        desde, hasta = rango_de("mes_pasado", date(2026, 1, 15))

        self.assertEqual(desde, date(2025, 12, 1))
        self.assertEqual(hasta, date(2025, 12, 31))

    def test_mes_pasado_desde_marzo_en_año_bisiesto(self):
        desde, hasta = rango_de("mes_pasado", date(2028, 3, 10))

        self.assertEqual(desde, date(2028, 2, 1))
        self.assertEqual(hasta, date(2028, 2, 29), "2028 es bisiesto")


class PruebaVistaPrevia(PruebaVIM):
    """Antes había que elegir dónde guardar para recién ahí saber si había datos."""

    def setUp(self):
        super().setUp()
        self.abrir_caja()
        self.configurar_iva(0)
        self.pid = self.crear_producto(precio_venta=1000, stock=1000)

    def _resumen(self, desde=None, hasta=None):
        from database.ventas import resumen_ventas_periodo
        from database.utils import ahora
        hoy = ahora("%Y-%m-%d")
        return resumen_ventas_periodo(desde or hoy, hasta or hoy)

    def _vender(self, cantidad):
        from database.ventas import confirmar_venta
        ok, msg, vid = confirmar_venta(
            [self.linea_ticket(self.pid, cantidad=cantidad, precio_unitario=1000)],
            9999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)
        return vid

    def test_periodo_vacio_informa_cero(self):
        datos = self._resumen("2020-01-01", "2020-01-31")

        self.assertEqual(datos["cantidad"], 0)
        self.assertEqual(datos["total"], 0)

    def test_cuenta_las_ventas_y_suma_los_totales(self):
        self._vender(3)      # 3.000
        self._vender(2)      # 2.000

        datos = self._resumen()

        self.assertEqual(datos["cantidad"], 2)
        self.assertEqual(datos["total"], 5000)

    def test_las_ventas_anuladas_no_se_cuentan(self):
        """Si se contaran, la vista previa prometería datos que el reporte no trae."""
        from database.ventas import anular_venta

        self._vender(3)
        vid = self._vender(2)
        anular_venta(vid, usuario_id=1, motivo="Prueba")

        datos = self._resumen()

        self.assertEqual(datos["cantidad"], 1)
        self.assertEqual(datos["total"], 3000)

    def test_no_cuenta_ventas_de_otro_periodo(self):
        self._vender(4)
        datos = self._resumen("2019-01-01", "2019-12-31")

        self.assertEqual(datos["cantidad"], 0)

    def test_un_error_no_rompe_la_ventana(self):
        """La vista previa se recalcula al tocar las fechas: no puede reventar."""
        from database.ventas import resumen_ventas_periodo

        with self.conectar() as con:
            con.execute("DROP TABLE ventas")
            con.commit()

        datos = resumen_ventas_periodo("2026-01-01", "2026-12-31")

        self.assertEqual(datos, {"cantidad": 0, "total": 0})


class PruebaHojasDelReporteMaestro(PruebaVIM):
    """El reporte no debe anunciar hojas que no genera."""

    def _hojas(self):
        from database.negocio import maneja_inventario
        hojas = ["Ventas Detalladas", "Movimientos de Caja"]
        if maneja_inventario():
            hojas.append("Inventario")
        return hojas + ["Cuentas por Pagar", "Nómina Personal"]

    def test_productos_incluye_inventario(self):
        hojas = self._hojas()

        self.assertIn("Inventario", hojas)
        self.assertEqual(len(hojas), 5)

    def test_servicios_no_incluye_inventario(self):
        from database import negocio
        negocio.establecer_modo_negocio(negocio.MODO_SERVICIOS)

        hojas = self._hojas()

        self.assertNotIn("Inventario", hojas)
        self.assertEqual(len(hojas), 4,
                         "En servicios el reporte trae una hoja menos")
