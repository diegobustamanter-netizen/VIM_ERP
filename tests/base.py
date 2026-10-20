"""Infraestructura común para las pruebas de VIM ERP.

REGLA DE ORO: las pruebas NUNCA tocan la base de datos real.

Cada prueba arma una base nueva y vacía en una carpeta temporal del sistema,
la puebla con el esquema y los datos semilla reales, y la borra al terminar.
Para lograrlo se redirige `database.connection.DB_NAME`, que es de donde sale
la ruta que usa todo el sistema para conectarse.

Se usa unittest (viene con Python) en vez de pytest para no agregar
dependencias: las pruebas corren en cualquier máquina donde corra el programa.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

# Permitir ejecutar las pruebas desde cualquier carpeta
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from database import connection as _conexion  # noqa: E402


class PruebaVIM(unittest.TestCase):
    """Base con una base de datos limpia y aislada por cada prueba."""

    # ------------------------------------------------------------------
    # Preparación y limpieza
    # ------------------------------------------------------------------

    def setUp(self):
        self.carpeta_tmp = tempfile.mkdtemp(prefix="vimerp_test_")
        self.ruta_db = os.path.join(self.carpeta_tmp, "prueba.db")

        # Redirigir toda la capa de datos a la base temporal
        self._db_original = _conexion.DB_NAME
        _conexion.DB_NAME = self.ruta_db

        self._verificar_aislamiento()

        from database.schema import inicializar_db
        inicializar_db()

        # El modo de negocio se cachea en memoria: limpiarlo entre pruebas
        # para que una no herede el estado de otra.
        from database import negocio
        negocio.invalidar_cache()

        # Lo mismo con las autorizaciones de administrador
        from modulos.seguridad.sesion import Sesion
        Sesion.limpiar_autorizaciones()

        self._aislar_log()

    def _aislar_log(self):
        """Desvía el log a la carpeta temporal.

        Las pruebas provocan errores a propósito: si escribieran en el log
        real, ensuciarían el archivo que sirve para diagnosticar problemas
        de verdad.
        """
        import logging
        from vim_logger import logger, _FORMAT, _DATE_FORMAT

        self._handlers_originales = list(logger.handlers)
        for h in self._handlers_originales:
            logger.removeHandler(h)

        self._handler_tmp = logging.FileHandler(
            os.path.join(self.carpeta_tmp, "prueba.log"), encoding="utf-8"
        )
        self._handler_tmp.setFormatter(logging.Formatter(_FORMAT, datefmt=_DATE_FORMAT))
        logger.addHandler(self._handler_tmp)

    def _restaurar_log(self):
        from vim_logger import logger

        logger.removeHandler(self._handler_tmp)
        self._handler_tmp.close()
        for h in self._handlers_originales:
            logger.addHandler(h)

    def tearDown(self):
        self._restaurar_log()
        _conexion.DB_NAME = self._db_original
        from database import negocio
        negocio.invalidar_cache()
        shutil.rmtree(self.carpeta_tmp, ignore_errors=True)

    def _verificar_aislamiento(self):
        """Cinturón de seguridad: abortar si apuntamos a una base real."""
        ruta = os.path.abspath(_conexion.DB_NAME)
        if "vimerp_test_" not in ruta:
            raise RuntimeError(
                f"ABORTADO: las pruebas apuntan a una base que no es temporal:\n  {ruta}"
            )

    # ------------------------------------------------------------------
    # Utilidades para armar escenarios
    # ------------------------------------------------------------------

    def conectar(self):
        con = sqlite3.connect(self.ruta_db)
        con.row_factory = sqlite3.Row
        return con

    @staticmethod
    def ahora_local():
        """Fecha y hora como las guarda la app (hora local).

        OJO: no usar datetime('now') de SQLite en las pruebas. Devuelve UTC,
        así que en Chile (UTC-4) a partir de las 20:00 cae en el día
        siguiente y los registros quedan fuera del período que consultan los
        reportes. Las pruebas pasaban de día y fallaban de noche.
        """
        from database.utils import ahora
        return ahora()

    def abrir_caja(self, usuario_id=1, monto=0):
        """Sin caja abierta no se puede vender: casi toda prueba la necesita."""
        with self.conectar() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO cajas_sesiones (fecha_apertura, monto_inicial, usuario_id, estado)
                VALUES (?, ?, ?, 'abierta')
                """,
                (self.ahora_local(), monto, usuario_id),
            )
            con.commit()
            return cur.lastrowid

    def crear_producto(self, nombre="Producto de prueba", precio_venta=1000,
                       precio_compra=400, stock=100, tipo_item="producto"):
        with self.conectar() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO productos
                    (nombre, tipo_item, precio_compra, precio_venta, precio_por_kilo,
                     stock, stock_minimo, tipo_venta, activo, fecha_creacion)
                VALUES (?, ?, ?, ?, 0, ?, 0, 'unidad', 1, ?)
                """,
                (nombre, tipo_item, precio_compra, precio_venta, stock,
                 self.ahora_local()),
            )
            con.commit()
            return cur.lastrowid

    def crear_compra(self, subtotal, tipo_operacion, cuenta_contable_id=None,
                     fecha=None, tipo_documento="factura", impuesto=0):
        with self.conectar() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO compras
                    (numero_documento, tipo_documento, fecha, proveedor_id, usuario_id,
                     subtotal, descuento, impuesto, total, tipo_operacion,
                     estado_pago, saldo_pendiente, cuenta_contable_id, estado)
                VALUES (?, ?, COALESCE(?, ?), NULL, 1,
                        ?, 0, ?, ?, ?, 'pagado', 0, ?, 'recibida')
                """,
                (f"C-{subtotal}-{tipo_operacion}", tipo_documento, fecha, self.ahora_local(),
                 subtotal, impuesto, subtotal + impuesto, tipo_operacion,
                 cuenta_contable_id),
            )
            con.commit()
            return cur.lastrowid

    def movimiento_caja(self, caja_id, tipo, monto, categoria="varios"):
        with self.conectar() as con:
            con.execute(
                """
                INSERT INTO movimientos_caja
                    (caja_sesion_id, fecha, tipo, categoria, monto, descripcion, usuario_id)
                VALUES (?, ?, ?, ?, ?, 'Movimiento de prueba', 1)
                """,
                (caja_id, self.ahora_local(), tipo, categoria, monto),
            )
            con.commit()

    def configurar_iva(self, porcentaje=0, incluido=False):
        """Fija el IVA del sistema.

        Las pruebas que miden clasificación de gastos lo ponen en 0 para que
        los números sean redondos y el resultado no dependa de la
        configuración tributaria. El cálculo del IVA en sí se prueba aparte.
        """
        with self.conectar() as con:
            con.execute("UPDATE configuracion SET valor = ? WHERE clave = 'iva_porcentaje'",
                        (str(porcentaje),))
            con.execute("UPDATE configuracion SET valor = ? WHERE clave = 'iva_incluido'",
                        ("1" if incluido else "0",))
            con.commit()

    def linea_ticket(self, producto_id, nombre="Producto de prueba", cantidad=1,
                     precio_unitario=1000, **extra):
        """Arma una línea con la forma que usa el ticket del POS."""
        linea = {
            "producto_id": producto_id,
            "nombre": nombre,
            "tipo_venta": "unidad",
            "tipo_item": "producto",
            "cantidad": cantidad,
            "peso": 0,
            "precio_unitario": precio_unitario,
            "precio_por_kilo": 0,
            "subtotal": cantidad * precio_unitario,
        }
        linea.update(extra)
        return linea

    def cuenta_contable(self, nombre):
        """Id de una cuenta del plan de cuentas semilla, por nombre."""
        with self.conectar() as con:
            fila = con.execute(
                "SELECT id FROM plan_cuentas WHERE nombre = ?", (nombre,)
            ).fetchone()
            self.assertIsNotNone(fila, f"No existe la cuenta contable '{nombre}'")
            return fila["id"]

    def pnl(self, desde=None, hasta=None):
        """Estado de resultados del día de hoy (o del rango indicado)."""
        from database.reportes_financieros import obtener_estado_resultados
        from database.utils import ahora
        hoy = ahora("%Y-%m-%d")
        return obtener_estado_resultados(desde or hoy, hasta or hoy)

    def nombres_de_gastos(self, pnl=None):
        datos = pnl if pnl is not None else self.pnl()
        return [g["cuenta"] for g in datos["gastos_detallados"]]
