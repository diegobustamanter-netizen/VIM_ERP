"""Códigos de producto: un código identifica a un solo producto.

Si dos productos comparten código, al escanear el POS no sabe cuál vender.
"""

from base import PruebaVIM


class PruebaCodigosUnicos(PruebaVIM):

    def _crear(self, nombre, barras=None, plu=None, activo=1):
        with self.conectar() as con:
            cur = con.execute(
                """
                INSERT INTO productos (nombre, codigo_barras, codigo_pos, precio_venta,
                                       stock, tipo_venta, activo, fecha_creacion)
                VALUES (?, ?, ?, 1000, 10, 'unidad', ?, ?)
                """, (nombre, barras, plu, activo, self.ahora_local()))
            con.commit()
            return cur.lastrowid

    def _conflicto(self, codigos, excluir_id=None):
        from database.productos import buscar_conflicto_de_codigo
        with self.conectar() as con:
            return buscar_conflicto_de_codigo(con, codigos, excluir_id)

    def test_detecta_codigo_de_barras_repetido(self):
        self._crear("Gaseosa", barras="7801234567890")

        conflicto = self._conflicto(["7801234567890"])

        self.assertIsNotNone(conflicto)
        self.assertEqual(conflicto["nombre"], "Gaseosa",
                         "El aviso tiene que decir qué producto ya usa el código")

    def test_un_plu_no_puede_coincidir_con_el_codigo_de_barras_de_otro(self):
        """La base solo impedía repetir dentro de la misma columna."""
        self._crear("Pan", plu="501")

        self.assertIsNotNone(self._conflicto(["501", None]),
                             "Se permitió un código de barras igual al PLU de otro producto")

    def test_editar_un_producto_no_choca_consigo_mismo(self):
        pid = self._crear("Pan", plu="501")

        self.assertIsNone(self._conflicto(["501"], excluir_id=pid))

    def test_codigos_vacios_no_son_conflicto(self):
        self._crear("Sin código de barras", plu="10")

        self.assertIsNone(self._conflicto([None, "", "  "]))

    def test_el_codigo_de_un_producto_eliminado_se_puede_reutilizar(self):
        """Eliminar es una baja lógica: el código quedaba tomado para siempre."""
        from database.productos import liberar_codigos_de_eliminados

        viejo = self._crear("Producto borrado", barras="111", activo=0)
        conflicto = self._conflicto(["111"])
        self.assertFalse(conflicto["activo"], "El conflicto debe venir marcado como eliminado")

        with self.conectar() as con:
            liberar_codigos_de_eliminados(con, ["111"])
            con.commit()
            fila = con.execute("SELECT codigo_barras FROM productos WHERE id = ?",
                               (viejo,)).fetchone()

        self.assertIsNone(fila[0])
        self.assertIsNone(self._conflicto(["111"]))
        self._crear("Producto nuevo", barras="111")   # ya no revienta por UNIQUE

    def test_liberar_no_toca_productos_activos(self):
        from database.productos import liberar_codigos_de_eliminados

        activo = self._crear("Activo", barras="222")
        with self.conectar() as con:
            liberar_codigos_de_eliminados(con, ["222"])
            con.commit()
            fila = con.execute("SELECT codigo_barras FROM productos WHERE id = ?",
                               (activo,)).fetchone()

        self.assertEqual(fila[0], "222")
