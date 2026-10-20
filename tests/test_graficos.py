"""Pruebas de los gráficos del Análisis Visual (cálculos y que se generen sin error)."""
import os
import sys
import unittest

from base import PruebaVIM

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import matplotlib
    matplotlib.use("Agg")
    from modulos.ventas_reportes import graficos as g
except ImportError:  # sin matplotlib no hay panel visual que probar
    g = None


@unittest.skipIf(g is None, "matplotlib no está instalado")
class TestCalculos(unittest.TestCase):
    def test_periodo_anterior_mismo_largo(self):
        self.assertEqual(g.periodo_anterior("2026-10-08", "2026-10-14"), ("2026-10-01", "2026-10-07"))
        self.assertEqual(g.periodo_anterior("2026-10-20", "2026-10-20"), ("2026-10-19", "2026-10-19"))

    def test_mes_en_curso_se_compara_con_los_mismos_dias_del_mes_anterior(self):
        self.assertEqual(g.periodo_anterior("2026-10-01", "2026-10-20"), ("2026-09-01", "2026-09-20"))
        self.assertEqual(g.periodo_anterior("2026-03-01", "2026-03-30"), ("2026-02-01", "2026-02-28"))

    def test_mes_completo_se_compara_con_el_mes_anterior_completo(self):
        self.assertEqual(g.periodo_anterior("2026-03-01", "2026-03-31"), ("2026-02-01", "2026-02-28"))
        self.assertEqual(g.periodo_anterior("2026-09-01", "2026-09-30"), ("2026-08-01", "2026-08-31"))
        self.assertEqual(g.periodo_anterior("2026-01-01", "2026-01-31"), ("2025-12-01", "2025-12-31"))

    def test_anio_en_curso_se_compara_con_los_mismos_dias_del_anio_anterior(self):
        self.assertEqual(g.periodo_anterior("2026-01-01", "2026-10-20"), ("2025-01-01", "2025-10-20"))
        self.assertEqual(g.periodo_anterior("2028-01-01", "2028-02-29"), ("2027-01-01", "2027-02-28"))

    def test_periodo_anterior_fechas_invalidas(self):
        self.assertIsNone(g.periodo_anterior("", ""))
        self.assertIsNone(g.periodo_anterior("2026-10-14", "2026-10-08"))

    def test_variacion(self):
        self.assertAlmostEqual(g.variacion(120, 100), 20.0)
        self.assertAlmostEqual(g.variacion(50, 100), -50.0)
        self.assertIsNone(g.variacion(100, 0))      # sin período anterior no se compara
        self.assertIsNone(g.variacion(100, None))

    def test_completar_dias_rellena_con_cero(self):
        filas = [{"dia": "2026-10-01", "tickets": 2, "ingresos_totales": 1000},
                 {"dia": "2026-10-03", "tickets": 1, "ingresos_totales": 500}]
        dias = g.completar_dias(filas, "2026-10-01", "2026-10-04")
        self.assertEqual([d["ingresos"] for d in dias], [1000, 0, 500, 0])

    def test_formatos_de_monto(self):
        self.assertEqual(g.monto(1234567), "$1.234.567")
        self.assertEqual(g.monto_corto(1250000), "$1,2M")
        self.assertEqual(g.monto_corto(2000000), "$2M")
        self.assertEqual(g.monto_corto(350400), "$350 mil")
        self.assertEqual(g.monto_corto(900), "$900")


@unittest.skipIf(g is None, "matplotlib no está instalado")
class TestFiguras(unittest.TestCase):
    def _dibujar(self, fig):
        fig.canvas.draw()  # falla si algo del gráfico está mal armado
        self.assertGreater(len(fig.axes), 0)

    def test_figuras_con_datos(self):
        self._dibujar(g.grafico_ventas_por_dia(
            [{"dia": "2026-10-01", "tickets": 3, "ingresos_totales": 15000}], "2026-10-01", "2026-10-07"))
        self._dibujar(g.grafico_ventas_por_hora([{"hora": "09:00", "tickets": 2}, {"hora": "13:00", "tickets": 7}]))
        self._dibujar(g.grafico_medios_de_pago(1000, 500, 0))
        self._dibujar(g.grafico_ranking(["A", "B"], [300, 100]))

    def test_figuras_sin_datos_no_fallan(self):
        self._dibujar(g.grafico_ventas_por_dia([], "2026-10-01", "2026-10-07"))
        self._dibujar(g.grafico_ventas_por_hora([]))
        self._dibujar(g.grafico_medios_de_pago(0, 0, 0))
        self._dibujar(g.grafico_ranking([], []))

    def test_ranking_muestra_maximo_cinco(self):
        fig = g.grafico_ranking([f"P{i}" for i in range(8)], [100 * (i + 1) for i in range(8)])
        self.assertEqual(len(fig.axes[0].get_yticks()), 5)

    def test_hora_incluye_horas_sin_ventas(self):
        fig = g.grafico_ventas_por_hora([{"hora": "09:00", "tickets": 2}, {"hora": "12:00", "tickets": 4}])
        self.assertEqual(len(fig.axes[0].patches), 4)  # 9, 10, 11 y 12


class PruebaVentasPorDia(PruebaVIM):
    """Los datos del gráfico "Ventas por día" salen de la base, agrupados por fecha."""

    def test_agrupa_las_ventas_del_dia(self):
        from database.ventas import confirmar_venta, obtener_reportes_avanzados

        self.abrir_caja()
        self.configurar_iva(0)
        pid = self.crear_producto(precio_venta=1000, stock=100)
        for _ in range(2):
            ok, msg, _vid = confirmar_venta([self.linea_ticket(pid)], 1000, "efectivo", usuario_id=1)
            self.assertTrue(ok, msg)

        hoy = self.ahora_local()[:10]
        dias = obtener_reportes_avanzados(hoy, hoy)["ventas_por_dia"]

        self.assertEqual(len(dias), 1)
        self.assertEqual(dias[0]["dia"], hoy)
        self.assertEqual(dias[0]["tickets"], 2)
        self.assertEqual(dias[0]["ingresos_totales"], 2000)


if __name__ == "__main__":
    unittest.main()
