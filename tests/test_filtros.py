"""Filtros de Reportes: fechas, método de pago y folio.

Todas las consultas del panel (historial, conteo, tarjetas, rankings,
gráficos) deben ver exactamente las mismas ventas para los mismos filtros.
"""
from datetime import date

from base import PruebaVIM
from stub_tk import modulo_reportes


class _ConVentas(PruebaVIM):
    """Ventas en fechas conocidas, incluidos los bordes del día."""

    VENTAS = [
        # (fecha y hora, método, cantidad)
        ("2026-05-09 23:59:59", "efectivo", 1),       # el día anterior, al límite
        ("2026-05-10 00:00:00", "efectivo", 2),       # primer segundo del período
        ("2026-05-10 13:30:00", "tarjeta", 3),
        ("2026-05-11 23:59:59", "transferencia", 4),  # último segundo del período
        ("2026-05-12 00:00:00", "efectivo", 5),       # el día siguiente
    ]

    def setUp(self):
        super().setUp()
        from database.ventas import anular_venta, confirmar_venta
        self.abrir_caja()
        self.configurar_iva(0)
        pid = self.crear_producto(precio_venta=1000, stock=100)
        self.ids = {}
        for fecha, metodo, cantidad in self.VENTAS:
            ok, msg, vid = confirmar_venta([self.linea_ticket(pid, cantidad=cantidad)],
                                           cantidad * 1000, metodo, usuario_id=1)
            self.assertTrue(ok, msg)
            with self.conectar() as con:
                con.execute("UPDATE ventas SET fecha = ? WHERE id = ?", (fecha, vid))
                con.commit()
            self.ids[fecha] = vid
        # Una venta anulada dentro del período
        ok, msg, self.anulada = confirmar_venta([self.linea_ticket(pid, cantidad=9)], 9000, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)
        with self.conectar() as con:
            con.execute("UPDATE ventas SET fecha = '2026-05-10 10:00:00' WHERE id = ?", (self.anulada,))
            con.commit()
        self.assertTrue(anular_venta(self.anulada, 1, "prueba")[0])

    def folio(self, fecha):
        with self.conectar() as con:
            return con.execute("SELECT folio FROM ventas WHERE id = ?", (self.ids[fecha],)).fetchone()[0]


class PruebaFiltroDeFechas(_ConVentas):
    def test_incluye_los_bordes_del_periodo_y_nada_mas(self):
        from database.ventas import buscar_ventas_filtradas
        ventas = buscar_ventas_filtradas("2026-05-10", "2026-05-11", "Todos", "")
        fechas = sorted(v["fecha"] for v in ventas if v["estado"] == "completada")
        self.assertEqual(fechas, ["2026-05-10 00:00:00", "2026-05-10 13:30:00", "2026-05-11 23:59:59"])

    def test_todas_las_consultas_ven_las_mismas_ventas(self):
        from database.ventas import (buscar_ventas_filtradas, contar_ventas_filtradas,
                                     obtener_kpis_ventas, obtener_reportes_avanzados)
        args = ("2026-05-10", "2026-05-11", "Todos", "")
        kpis = obtener_kpis_ventas(*args)
        rep = obtener_reportes_avanzados(*args)

        # El historial muestra también la anulada (marcada); el resto no la cuenta
        self.assertEqual(contar_ventas_filtradas(*args), 4)
        self.assertEqual(len(buscar_ventas_filtradas(*args)), 4)
        self.assertEqual(kpis["cantidad_ventas"], 3)
        self.assertEqual(kpis["ventas_totales"], 9000)
        self.assertEqual(sum(h["ingresos_totales"] for h in rep["ventas_por_hora"]), 9000)
        self.assertEqual(sum(d["ingresos_totales"] for d in rep["ventas_por_dia"]), 9000)
        self.assertEqual(sum(p["ingresos_totales"] for p in rep["top_productos"]), 9000)
        self.assertEqual(sum(c["ingresos_totales"] for c in rep["top_categorias"]), 9000)

    def test_ventas_por_dia_y_por_hora(self):
        from database.ventas import obtener_reportes_avanzados
        rep = obtener_reportes_avanzados("2026-05-10", "2026-05-11")
        self.assertEqual([(d["dia"], d["ingresos_totales"]) for d in rep["ventas_por_dia"]],
                         [("2026-05-10", 5000), ("2026-05-11", 4000)])
        self.assertEqual([(h["hora"], h["tickets"]) for h in rep["ventas_por_hora"]],
                         [("00:00", 1), ("13:00", 1), ("23:00", 1)])


class PruebaFiltroDeMetodo(_ConVentas):
    def test_cada_metodo_trae_solo_lo_suyo(self):
        from database.ventas import buscar_ventas_filtradas, obtener_kpis_ventas
        for metodo, total in (("Efectivo", 2000), ("Tarjeta", 3000), ("Transferencia", 4000)):
            with self.subTest(metodo=metodo):
                kpis = obtener_kpis_ventas("2026-05-10", "2026-05-11", metodo, "")
                self.assertEqual(kpis["ventas_totales"], total)
                ventas = buscar_ventas_filtradas("2026-05-10", "2026-05-11", metodo, "")
                self.assertTrue(all(v["metodo_pago"] == metodo.lower() for v in ventas))

    def test_todos_no_filtra(self):
        from database.ventas import obtener_kpis_ventas
        self.assertEqual(obtener_kpis_ventas("2026-05-10", "2026-05-11", "Todos", "")["ventas_totales"], 9000)


class PruebaFiltroDeFolio(_ConVentas):
    def test_folio_exacto_encuentra_una_sola_venta(self):
        from database.ventas import buscar_ventas_filtradas, obtener_kpis_ventas
        folio = self.folio("2026-05-10 13:30:00")
        ventas = buscar_ventas_filtradas("2026-05-10", "2026-05-11", "Todos", folio)
        self.assertEqual([v["folio"] for v in ventas], [folio])
        self.assertEqual(obtener_kpis_ventas("2026-05-10", "2026-05-11", "Todos", folio)["ventas_totales"], 3000)

    def test_folio_fuera_del_periodo_no_aparece(self):
        from database.ventas import buscar_ventas_filtradas
        folio = self.folio("2026-05-12 00:00:00")
        self.assertEqual(buscar_ventas_filtradas("2026-05-10", "2026-05-11", "Todos", folio), [])


class PruebaBotonesRapidos(PruebaVIM):
    """Hoy / Semana / Mes / Año terminan hoy: sin días futuros vacíos."""

    def _rango(self, tipo, hoy):
        return modulo_reportes().rango_rapido(tipo, hoy)

    def test_hoy(self):
        self.assertEqual(self._rango("hoy", date(2026, 10, 20)), (date(2026, 10, 20), date(2026, 10, 20)))

    def test_semana_desde_el_lunes_hasta_hoy(self):
        self.assertEqual(self._rango("semana", date(2026, 10, 22)), (date(2026, 10, 19), date(2026, 10, 22)))

    def test_mes_desde_el_dia_uno_hasta_hoy(self):
        self.assertEqual(self._rango("mes", date(2026, 10, 20)), (date(2026, 10, 1), date(2026, 10, 20)))

    def test_anio_desde_el_uno_de_enero_hasta_hoy(self):
        self.assertEqual(self._rango("anio", date(2026, 10, 20)), (date(2026, 1, 1), date(2026, 10, 20)))
