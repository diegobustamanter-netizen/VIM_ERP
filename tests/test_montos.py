"""Los montos son pesos enteros y la suma cuadra siempre.

El peso chileno no tiene decimales, y el SII valida que
    neto + impuesto = total
de forma exacta. Cualquier diferencia de un peso hace que rechace el documento.

Antes una venta de $1.000 con IVA incluido guardaba neto 840,3361 e IVA
159,6639: centavos que no existen y una suma que no cierra en enteros.
"""

from base import PruebaVIM


class PruebaMontosEnteros(PruebaVIM):

    def _calcular(self, monto, pct=19, incluido=True):
        from database.finanzas_utils import calcular_total_con_iva
        return calcular_total_con_iva(monto, pct, incluye_iva=incluido)

    # ------------------------------------------------------------------
    # Enteros
    # ------------------------------------------------------------------

    def test_no_quedan_decimales_con_iva_incluido(self):
        for monto in (1, 7, 13, 1000, 1990, 3333, 7777, 12345, 99999, 123456):
            with self.subTest(monto=monto):
                total, iva = self._calcular(monto, incluido=True)
                neto = total - iva

                self.assertEqual(total, int(total), f"total con decimales: {total}")
                self.assertEqual(iva, int(iva), f"IVA con decimales: {iva}")
                self.assertEqual(neto, int(neto), f"neto con decimales: {neto}")

    def test_no_quedan_decimales_sin_iva_incluido(self):
        for monto in (1, 7, 13, 1000, 1990, 3333, 7777, 12345, 99999, 123456):
            with self.subTest(monto=monto):
                total, iva = self._calcular(monto, incluido=False)
                neto = total - iva

                self.assertEqual(total, int(total))
                self.assertEqual(iva, int(iva))
                self.assertEqual(neto, int(neto))

    # ------------------------------------------------------------------
    # La suma cuadra (lo que valida el SII)
    # ------------------------------------------------------------------

    def test_el_iva_es_el_que_corresponde_al_neto(self):
        """Neto e IVA se calculan de verdad, no por resta de sí mismos.

        Antes esta prueba calculaba neto = total - iva y comprobaba que
        neto + iva == total: siempre era verdad, así que no cuidaba nada.
        """
        from decimal import Decimal, ROUND_HALF_UP

        def a_peso(x):
            return int(Decimal(x).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

        for monto in range(1, 3000, 7):          # ~430 montos distintos
            with self.subTest(monto=monto, incluido=False):
                total, iva = self._calcular(monto, incluido=False)
                self.assertEqual(iva, a_peso(Decimal(monto) * Decimal("0.19")))
                self.assertEqual(total, monto + iva)

            with self.subTest(monto=monto, incluido=True):
                total, iva = self._calcular(monto, incluido=True)
                self.assertEqual(total, monto)
                self.assertEqual(total - iva, a_peso(Decimal(monto) / Decimal("1.19")))

    def test_el_medio_peso_redondea_hacia_arriba(self):
        """round() de Python deja 28,5 en 28 (redondeo al par). El SII y
        cualquier calculadora dan 29."""
        for neto, iva_esperado in [(150, 29), (350, 67), (550, 105), (50, 10)]:
            with self.subTest(neto=neto):
                total, iva = self._calcular(neto, incluido=False)
                self.assertEqual(iva, iva_esperado,
                                 "El IVA volvió a redondear el ,5 hacia abajo")
                self.assertEqual(total, neto + iva_esperado)

    def test_valores_conocidos_con_iva_incluido(self):
        """$1.000 con IVA incluido son $840 netos + $160 de IVA."""
        total, iva = self._calcular(1000, incluido=True)
        self.assertEqual((total, iva), (1000, 160))

    def test_con_iva_incluido_el_total_es_el_precio_de_etiqueta(self):
        """El cliente paga lo que dice el precio, sin sorpresas."""
        for monto in (990, 1000, 2500, 9990):
            with self.subTest(monto=monto):
                total, _ = self._calcular(monto, incluido=True)
                self.assertEqual(total, monto)

    def test_sin_iva_incluido_el_iva_se_suma_encima(self):
        total, iva = self._calcular(10000, pct=19, incluido=False)

        self.assertEqual(iva, 1900)
        self.assertEqual(total, 11900)

    # ------------------------------------------------------------------
    # Casos límite
    # ------------------------------------------------------------------

    def test_iva_cero_deja_el_monto_intacto(self):
        for incluido in (True, False):
            with self.subTest(incluido=incluido):
                total, iva = self._calcular(10000, pct=0, incluido=incluido)

                self.assertEqual(total, 10000)
                self.assertEqual(iva, 0)

    def test_monto_cero(self):
        for incluido in (True, False):
            with self.subTest(incluido=incluido):
                total, iva = self._calcular(0, incluido=incluido)
                self.assertEqual(total, 0)
                self.assertEqual(iva, 0)

    def test_un_peso_no_rompe(self):
        for incluido in (True, False):
            with self.subTest(incluido=incluido):
                total, iva = self._calcular(1, incluido=incluido)
                self.assertEqual(total, 1, "Un peso no puede cambiar de valor")
                self.assertEqual(iva, 0, "El IVA de $1 redondea a $0")

    # ------------------------------------------------------------------
    # De punta a punta: lo que queda guardado en la base
    # ------------------------------------------------------------------

    def test_la_venta_guarda_montos_enteros(self):
        from database.ventas import confirmar_venta

        self.abrir_caja()
        with self.conectar() as con:
            con.execute("UPDATE configuracion SET valor='19' WHERE clave='iva_porcentaje'")
            con.execute("UPDATE configuracion SET valor='1' WHERE clave='iva_incluido'")
            con.commit()

        pid = self.crear_producto(precio_venta=1000, precio_compra=400, stock=100)
        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(pid, cantidad=3, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        with self.conectar() as con:
            v = dict(con.execute(
                "SELECT total, impuesto FROM ventas WHERE id = ?", (venta_id,)
            ).fetchone())

        self.assertEqual(v["total"], int(v["total"]), "El total quedó con decimales")
        self.assertEqual(v["impuesto"], int(v["impuesto"]), "El IVA quedó con decimales")

        neto = v["total"] - v["impuesto"]
        self.assertEqual(neto + v["impuesto"], v["total"])
        self.assertEqual(v["total"], 3000, "Con IVA incluido, 3 x $1.000 son $3.000")

    def test_el_estado_de_resultados_no_muestra_centavos(self):
        from database.ventas import confirmar_venta

        self.abrir_caja()
        with self.conectar() as con:
            con.execute("UPDATE configuracion SET valor='19' WHERE clave='iva_porcentaje'")
            con.execute("UPDATE configuracion SET valor='1' WHERE clave='iva_incluido'")
            con.commit()

        pid = self.crear_producto(precio_venta=1990, precio_compra=800, stock=100)
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=1, precio_unitario=1990)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        datos = self.pnl()

        self.assertEqual(datos["ingresos_ventas"], int(datos["ingresos_ventas"]),
                         "Los ingresos del reporte traen centavos")
        self.assertEqual(datos["recaudacion_impuestos"],
                         int(datos["recaudacion_impuestos"]),
                         "El IVA del reporte trae centavos")
