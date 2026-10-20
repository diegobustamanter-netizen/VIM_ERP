"""Copias de seguridad: que guarden todo y que restaurar devuelva todo.

Lo que más importa comprobar acá es el stock: si un backup se hace con la
base en uso, los últimos movimientos viven en el archivo -wal de SQLite.
Copiar solo el .db dejaría afuera las ventas recientes y el backup mostraría
un stock que ya no es el real.
"""

import os

from base import PruebaVIM


class PruebaBackup(PruebaVIM):

    def setUp(self):
        super().setUp()
        import database.backup as backup

        # backup.py toma las rutas de config al importarse, no de connection:
        # hay que redirigirlas o trabajaría sobre la base y carpeta reales.
        self.backup = backup
        self._db_orig = backup.DB_NAME
        self._dir_orig = backup.BACKUP_DIR
        backup.DB_NAME = self.ruta_db
        backup.BACKUP_DIR = os.path.join(self.carpeta_tmp, "backups")

        self.abrir_caja()
        self.configurar_iva(0)

    def tearDown(self):
        self.backup.DB_NAME = self._db_orig
        self.backup.BACKUP_DIR = self._dir_orig
        super().tearDown()

    # ------------------------------------------------------------------
    # Ayudantes
    # ------------------------------------------------------------------

    def _stock(self, pid):
        with self.conectar() as con:
            return con.execute(
                "SELECT stock FROM productos WHERE id = ?", (pid,)
            ).fetchone()["stock"]

    def _stock_en(self, ruta_db, pid):
        """Lee el stock directamente de un archivo de backup."""
        import sqlite3
        con = sqlite3.connect(ruta_db)
        try:
            return con.execute(
                "SELECT stock FROM productos WHERE id = ?", (pid,)
            ).fetchone()[0]
        finally:
            con.close()

    def _vender(self, pid, cantidad, precio=1000):
        from database.ventas import confirmar_venta
        ok, msg, _ = confirmar_venta(
            [self.linea_ticket(pid, cantidad=cantidad, precio_unitario=precio)],
            9999999, "efectivo", usuario_id=1)
        self.assertTrue(ok, msg)

    # ------------------------------------------------------------------
    # Qué guarda el backup
    # ------------------------------------------------------------------

    def test_el_backup_guarda_los_productos(self):
        self.crear_producto(nombre="Café molido", precio_venta=3500, stock=40)
        self.crear_producto(nombre="Azúcar 1kg", precio_venta=1200, stock=25)

        ruta = self.backup.crear_backup()

        import sqlite3
        con = sqlite3.connect(ruta)
        try:
            nombres = [r[0] for r in con.execute("SELECT nombre FROM productos")]
        finally:
            con.close()

        self.assertIn("Café molido", nombres)
        self.assertIn("Azúcar 1kg", nombres)

    def test_el_backup_guarda_el_stock_actual(self):
        """El stock que quede en el backup tiene que ser el del momento."""
        pid = self.crear_producto(precio_venta=1000, stock=100)
        self._vender(pid, cantidad=30)
        self.assertEqual(self._stock(pid), 70)

        ruta = self.backup.crear_backup()

        self.assertEqual(self._stock_en(ruta, pid), 70,
                         "El backup no refleja el stock del momento en que se hizo")

    def test_el_backup_incluye_ventas_recientes_sin_checkpoint(self):
        """El caso peligroso: datos que todavía viven en el archivo -wal.

        Con journal_mode=WAL una venta recién hecha puede no estar aún en el
        .db principal. Copiar el archivo a mano la perdería; la API de SQLite
        que usa el sistema la incluye.
        """
        pid = self.crear_producto(precio_venta=1000, stock=50)
        self._vender(pid, cantidad=10)          # queda en el -wal
        self._vender(pid, cantidad=5)

        ruta = self.backup.crear_backup()

        import sqlite3
        con = sqlite3.connect(ruta)
        try:
            ventas = con.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
        finally:
            con.close()

        self.assertEqual(ventas, 2, "El backup perdió ventas que estaban en el WAL")
        self.assertEqual(self._stock_en(ruta, pid), 35)

    def test_el_camino_de_emergencia_no_pierde_ventas(self):
        """Si la API de SQLite falla, se copia a mano el .db MÁS sus auxiliares.

        Copiar solo el .db en modo WAL dejaría afuera las últimas ventas y el
        backup parecería válido igual, que es la peor forma de fallar.
        """
        import sqlite3

        pid = self.crear_producto(precio_venta=1000, stock=50)
        self._vender(pid, cantidad=10)
        self._vender(pid, cantidad=5)

        # sqlite3.Connection es un tipo inmutable de C, así que no se le puede
        # parchear .backup(). Se sustituye el módulo sqlite3 que ve backup.py
        # por un envoltorio que delega todo salvo backup(), que falla.
        class ConexionSinBackup:
            def __init__(self, real):
                self._real = real

            def backup(self, *a, **kw):
                raise sqlite3.OperationalError("falla simulada")

            def __getattr__(self, nombre):
                return getattr(self._real, nombre)

        class SqliteConBackupRoto:
            OperationalError = sqlite3.OperationalError
            DatabaseError = sqlite3.DatabaseError

            @staticmethod
            def connect(*a, **kw):
                return ConexionSinBackup(sqlite3.connect(*a, **kw))

        original = self.backup.sqlite3
        self.backup.sqlite3 = SqliteConBackupRoto
        try:
            ruta = self.backup.crear_backup()
        finally:
            self.backup.sqlite3 = original

        con = sqlite3.connect(ruta)
        try:
            ventas = con.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]
            stock = con.execute(
                "SELECT stock FROM productos WHERE id = ?", (pid,)).fetchone()[0]
        finally:
            con.close()

        self.assertEqual(ventas, 2, "El camino de emergencia perdió ventas")
        self.assertEqual(stock, 35, "El camino de emergencia guardó un stock viejo")

    def test_el_backup_guarda_todas_las_tablas(self):
        """No sirve guardar productos si se pierde caja o configuración."""
        import sqlite3

        ruta = self.backup.crear_backup()
        con = sqlite3.connect(ruta)
        try:
            tablas = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            con.close()

        for esperada in ("productos", "ventas", "detalle_ventas", "usuarios",
                         "cajas_sesiones", "movimientos_caja", "movimientos_inventario",
                         "compras", "configuracion", "plan_cuentas", "historial"):
            self.assertIn(esperada, tablas, f"El backup no incluye la tabla {esperada}")

    # ------------------------------------------------------------------
    # Restaurar
    # ------------------------------------------------------------------

    def test_restaurar_devuelve_el_stock_del_backup(self):
        pid = self.crear_producto(precio_venta=1000, stock=100)
        ruta = self.backup.crear_backup()          # stock 100

        self._vender(pid, cantidad=40)             # stock 60
        self.assertEqual(self._stock(pid), 60)

        self.backup.restaurar_backup(ruta)

        self.assertEqual(self._stock(pid), 100,
                         "Restaurar no devolvió el stock que tenía el backup")

    def test_restaurar_borra_lo_posterior_al_backup(self):
        """Restaurar es volver atrás: lo hecho después no debe sobrevivir."""
        pid = self.crear_producto(precio_venta=1000, stock=100)
        ruta = self.backup.crear_backup()

        self._vender(pid, cantidad=5)
        self.crear_producto(nombre="Producto nuevo", stock=10)

        self.backup.restaurar_backup(ruta)

        with self.conectar() as con:
            ventas = con.execute("SELECT COUNT(*) c FROM ventas").fetchone()["c"]
            nuevo = con.execute(
                "SELECT COUNT(*) c FROM productos WHERE nombre = 'Producto nuevo'"
            ).fetchone()["c"]

        self.assertEqual(ventas, 0)
        self.assertEqual(nuevo, 0)

    def test_restaurar_deja_una_copia_de_lo_que_habia(self):
        """Por si restaurar fue un error: tiene que haber a dónde volver."""
        pid = self.crear_producto(precio_venta=1000, stock=100)
        ruta = self.backup.crear_backup()
        self._vender(pid, cantidad=40)             # stock 60

        self.backup.restaurar_backup(ruta)

        previas = [a for a in os.listdir(self.backup.BACKUP_DIR)
                   if a.startswith("pre_restauracion_")]
        self.assertTrue(previas, "No se guardó copia del estado previo")

        ruta_previa = os.path.join(self.backup.BACKUP_DIR, previas[0])
        self.assertEqual(self._stock_en(ruta_previa, pid), 60,
                         "La copia previa no refleja el estado que se reemplazó")

    def test_un_archivo_que_no_es_base_se_rechaza(self):
        falso = os.path.join(self.carpeta_tmp, "no_es_una_base.db")
        with open(falso, "w", encoding="utf-8") as f:
            f.write("esto es texto, no una base de datos")

        with self.assertRaises(ValueError):
            self.backup.restaurar_backup(falso)

    def test_restaurar_algo_inexistente_avisa(self):
        with self.assertRaises(FileNotFoundError):
            self.backup.restaurar_backup(
                os.path.join(self.carpeta_tmp, "no_existe.db"))

    # ------------------------------------------------------------------
    # Listado y borrado
    # ------------------------------------------------------------------

    def test_los_backups_se_listan_del_mas_nuevo_al_mas_viejo(self):
        import time

        self.crear_producto(nombre="Uno")
        primero = self.backup.crear_backup()
        time.sleep(1.1)                      # el nombre lleva hora con segundos
        self.crear_producto(nombre="Dos")
        segundo = self.backup.crear_backup()

        listado = self.backup.listar_backups()
        nombres = [b["nombre"] for b in listado]

        self.assertEqual(len(listado), 2)
        self.assertEqual(nombres[0], os.path.basename(segundo))
        self.assertEqual(nombres[1], os.path.basename(primero))

    def test_el_listado_informa_tamano_y_fecha(self):
        self.backup.crear_backup()
        info = self.backup.listar_backups()[0]

        self.assertGreater(info["tamaño_mb"], 0, "El backup figura vacío")
        self.assertTrue(info["fecha"])
        self.assertTrue(os.path.exists(info["ruta"]))

    def test_eliminar_backup(self):
        ruta = self.backup.crear_backup()
        self.assertTrue(self.backup.eliminar_backup(ruta))
        self.assertFalse(os.path.exists(ruta))
        self.assertFalse(self.backup.eliminar_backup(ruta))

    def test_la_copia_previa_no_aparece_como_backup_normal(self):
        """pre_restauracion_* no debe mezclarse con los backups del usuario."""
        ruta = self.backup.crear_backup()
        self.backup.restaurar_backup(ruta)

        nombres = [b["nombre"] for b in self.backup.listar_backups()]
        self.assertTrue(all(not n.startswith("pre_restauracion_") for n in nombres))
