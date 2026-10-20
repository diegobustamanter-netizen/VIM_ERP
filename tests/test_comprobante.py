"""Comprobante de venta: lo que se entrega al cliente.

VIM ERP no emite boletas del SII. Lo que imprime (o guarda en PDF) es un
comprobante interno, y tiene que decirlo siempre.
"""

from base import PruebaVIM

CONFIG = {
    "ticket_tamano": "58mm",
    "nombre_negocio": "Almacén Ñuñoa",
    "rut_empresa": "76.123.456-7",
    "ticket_mensaje_pie": "¡Gracias por su compra!",
    "ticket_desglose_iva": "1",
    "iva_porcentaje": "19",
}


class PruebaComprobantePDF(PruebaVIM):

    def _pdf(self, **cambios):
        from modulos.impresion.impresora_termica import generar_ticket_pdf, datos_de_ejemplo
        config = dict(CONFIG, **cambios)
        return generar_ticket_pdf(datos_de_ejemplo(), config)

    def _lineas(self, **cambios):
        from modulos.impresion.impresora_termica import _lineas_del_ticket, datos_de_ejemplo
        return _lineas_del_ticket(datos_de_ejemplo(), dict(CONFIG, **cambios))[0]

    def test_es_un_pdf_completo(self):
        pdf = self._pdf()

        self.assertTrue(pdf.startswith(b"%PDF-1.4"))
        self.assertTrue(pdf.rstrip().endswith(b"%%EOF"))
        self.assertIn(b"/Count 1", pdf, "El comprobante debe ocupar una sola página")

    def test_dice_que_no_es_boleta(self):
        """Lo más importante: nadie puede confundirlo con una boleta del SII."""
        texto = "\n".join(self._lineas())

        self.assertIn("Comprobante interno de venta", texto)
        self.assertIn("No valido como boleta", texto)

    def test_trae_lo_mismo_que_el_papel(self):
        texto = "\n".join(self._lineas())

        for esperado in ("ALMACÉN ÑUÑOA", "RUT: 76.123.456-7", "Folio: PRUEBA-001",
                         "$6.990", "IVA (19%)", "Vuelto:"):
            with self.subTest(esperado=esperado):
                self.assertIn(esperado, texto)

    def test_no_quedan_comandos_de_impresora_en_el_texto(self):
        for linea in self._lineas():
            with self.subTest(linea=linea):
                self.assertFalse(any(ord(c) < 32 for c in linea),
                                 f"Quedó un comando ESC/POS en el PDF: {linea!r}")

    def test_respeta_el_ancho_del_papel(self):
        for tamano, ancho in (("58mm", 32), ("80mm", 48)):
            with self.subTest(tamano=tamano):
                for linea in self._lineas(ticket_tamano=tamano):
                    self.assertLessEqual(len(linea), ancho, f"Línea más ancha que el papel: {linea!r}")

    def test_los_acentos_y_parentesis_no_rompen_el_pdf(self):
        pdf = self._pdf(nombre_negocio="Panadería (La Ñ)")

        self.assertIn(b"\\(LA \xd1\\)", pdf,
                      "Los paréntesis deben ir escapados y la Ñ en WinAnsi")


class PruebaTipoDeDocumento(PruebaVIM):

    def test_una_venta_nueva_es_comprobante_no_boleta(self):
        from database.ventas import confirmar_venta

        self.abrir_caja()
        self.configurar_iva(0)
        pid = self.crear_producto(precio_venta=1000, stock=10)
        ok, msg, venta_id = confirmar_venta(
            [self.linea_ticket(pid, cantidad=1, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

        with self.conectar() as con:
            tipo = con.execute("SELECT tipo_documento FROM ventas WHERE id = ?",
                               (venta_id,)).fetchone()[0]
        self.assertEqual(tipo, "comprobante",
                         "VIM ERP no emite boletas: la venta no puede quedar como 'boleta'")

    def test_las_ventas_viejas_marcadas_como_boleta_se_corrigen(self):
        from database.schema import inicializar_db

        with self.conectar() as con:
            con.execute(
                """
                INSERT INTO ventas (folio,tipo_documento,fecha,usuario_id,caja_sesion_id,
                                    subtotal,descuento,impuesto,total,monto_pagado,vuelto,
                                    metodo_pago,estado)
                VALUES ('VTA-VIEJA','boleta',?,1,1,100,0,0,100,100,0,'efectivo','completada')
                """, (self.ahora_local(),))
            con.commit()

        inicializar_db()

        with self.conectar() as con:
            tipo = con.execute(
                "SELECT tipo_documento FROM ventas WHERE folio = 'VTA-VIEJA'").fetchone()[0]
        self.assertEqual(tipo, "comprobante")
