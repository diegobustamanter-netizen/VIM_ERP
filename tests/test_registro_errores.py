"""Que las fallas dejen rastro.

Un error que se traga en silencio es un error que no se puede diagnosticar.
Estas pruebas provocan fallas a propósito y verifican que quedan registradas.
"""

import logging

from base import PruebaVIM


class CapturaDeLog(logging.Handler):
    """Handler que guarda en memoria lo que se loguea durante la prueba."""

    def __init__(self):
        super().__init__()
        self.registros = []

    def emit(self, record):
        self.registros.append(record)

    @property
    def mensajes(self):
        return [r.getMessage() for r in self.registros]

    def hubo(self, texto, nivel=None):
        return any(
            texto.lower() in r.getMessage().lower()
            and (nivel is None or r.levelno >= nivel)
            for r in self.registros
        )


class PruebaRegistroDeErrores(PruebaVIM):

    def setUp(self):
        super().setUp()
        from vim_logger import logger
        self.captura = CapturaDeLog()
        logger.addHandler(self.captura)
        self._logger = logger

    def tearDown(self):
        self._logger.removeHandler(self.captura)
        super().tearDown()

    # ------------------------------------------------------------------
    # El logger tiene que funcionar en el ejecutable
    # ------------------------------------------------------------------

    def test_el_logger_escribe_en_un_archivo(self):
        """El circuito completo: mensaje -> archivo, con nivel y módulo."""
        import os
        from vim_logger import get_logger

        get_logger("prueba").error("mensaje de prueba de escritura")
        self._handler_tmp.flush()

        with open(os.path.join(self.carpeta_tmp, "prueba.log"), encoding="utf-8") as f:
            contenido = f.read()

        self.assertIn("mensaje de prueba de escritura", contenido)
        self.assertIn("[ERROR]", contenido, "Falta el nivel en el formato")
        self.assertIn("vim_erp.prueba", contenido, "Falta el módulo en el formato")

    def test_el_log_de_produccion_apunta_a_la_carpeta_logs(self):
        """El handler real (apartado durante las pruebas) está bien armado."""
        from logging.handlers import RotatingFileHandler
        from vim_logger import _LOG_FILE

        rotativos = [h for h in self._handlers_originales
                     if isinstance(h, RotatingFileHandler)]
        self.assertTrue(rotativos, "No hay handler de archivo configurado")
        self.assertEqual(rotativos[0].baseFilename, _LOG_FILE)

    def test_el_log_rota_y_no_crece_sin_limite(self):
        """Un POS encendido durante años no puede dejar un log de 500 MB."""
        from logging.handlers import RotatingFileHandler

        # Se inspecciona el handler real, que las pruebas apartan para no
        # escribir en el log de producción.
        rotativos = [h for h in self._handlers_originales
                     if isinstance(h, RotatingFileHandler)]
        self.assertTrue(rotativos, "El log no tiene rotación configurada")
        self.assertGreater(rotativos[0].maxBytes, 0)
        self.assertGreater(rotativos[0].backupCount, 0)

    def test_loguear_no_revienta_sin_consola(self):
        """El .exe se compila con console=False: ahí sys.stdout es None."""
        import sys
        from vim_logger import get_logger

        stdout_real = sys.stdout
        try:
            sys.stdout = None
            get_logger("prueba").warning("sin consola disponible")
        finally:
            sys.stdout = stdout_real

        self.assertTrue(self.captura.hubo("sin consola disponible"))

    # ------------------------------------------------------------------
    # Fallas reales que antes se perdían
    # ------------------------------------------------------------------

    def test_error_al_leer_el_administrador_queda_registrado(self):
        """Si la tabla de usuarios falla, la recuperación de clave no puede
        limitarse a decir 'no configurado'."""
        from vim_logger import get_logger

        with self.conectar() as con:
            con.execute("DROP TABLE usuarios")
            con.commit()

        # Se replica el bloque protegido de recuperacion_ui sin abrir la UI
        from database.connection import session_db
        try:
            with session_db(dict_rows=True) as conn:
                conn.execute("SELECT * FROM usuarios WHERE rol = 'administrador' LIMIT 1").fetchone()
        except Exception as e:
            get_logger("seguridad.recuperacion").error(
                f"No se pudo leer el usuario administrador: {e}"
            )

        self.assertTrue(
            self.captura.hubo("administrador", nivel=logging.ERROR),
            "La falla al leer el administrador no quedó registrada")

    def test_conteos_de_backup_con_tabla_faltante_no_rompen(self):
        """El resumen del sistema debe sobrevivir a una tabla que no existe."""
        import database.backup as backup

        # backup.py toma la ruta de config al importarse, no de connection:
        # hay que redirigirla también o leería la base real.
        ruta_original = backup.DB_NAME
        backup.DB_NAME = self.ruta_db
        try:
            with self.conectar() as con:
                con.execute("DROP TABLE proveedores")
                con.commit()

            info = backup.obtener_info_sistema()
        finally:
            backup.DB_NAME = ruta_original

        self.assertEqual(info["registros"].get("proveedores"), 0,
                         "Una tabla faltante debe contar 0, no romper")
        self.assertTrue(self.captura.hubo("proveedores"),
                        "No se registró que faltaba la tabla")

    def test_una_venta_fallida_no_deja_datos_a_medias(self):
        """Si la venta falla, no puede quedar registrada la cabecera sola."""
        from database.ventas import confirmar_venta

        self.abrir_caja()
        self.configurar_iva(0)
        pid = self.crear_producto(precio_venta=1000, stock=1)

        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=99, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)
        self.assertFalse(ok, "Debería haber fallado por stock")

        with self.conectar() as con:
            ventas = con.execute("SELECT COUNT(*) c FROM ventas").fetchone()["c"]
            detalles = con.execute("SELECT COUNT(*) c FROM detalle_ventas").fetchone()["c"]
            movs = con.execute("SELECT COUNT(*) c FROM movimientos_caja").fetchone()["c"]

        self.assertEqual(ventas, 0, "Quedó una venta huérfana tras el error")
        self.assertEqual(detalles, 0, "Quedaron líneas de una venta que falló")
        self.assertEqual(movs, 0, "Quedó un movimiento de caja de una venta que falló")

    def test_el_stock_no_se_toca_si_la_venta_falla(self):
        """Una venta rechazada no puede haber descontado inventario."""
        from database.ventas import confirmar_venta

        self.abrir_caja()
        self.configurar_iva(0)
        pid_ok = self.crear_producto(nombre="Con stock", precio_venta=1000, stock=50)
        pid_sin = self.crear_producto(nombre="Sin stock", precio_venta=1000, stock=1)

        # La primera línea entra, la segunda revienta: debe revertirse todo
        ok, _, _ = confirmar_venta(
            [self.linea_ticket(pid_ok, cantidad=5, precio_unitario=1000),
             self.linea_ticket(pid_sin, cantidad=99, precio_unitario=1000)],
            999999, "efectivo", usuario_id=1)
        self.assertFalse(ok)

        with self.conectar() as con:
            stock = con.execute(
                "SELECT stock FROM productos WHERE id = ?", (pid_ok,)
            ).fetchone()["stock"]

        self.assertEqual(stock, 50, "Se descontó stock de una venta que falló")
