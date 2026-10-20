import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import subprocess

from config import (
    COLOR_PRIMARIO, COLOR_BLANCO,
    COLOR_GRIS, COLOR_PELIGRO, FUENTE_BOTON, FUENTE_MODULO
)
from database.backup import (
    crear_backup, listar_backups, restaurar_backup,
    eliminar_backup, obtener_info_sistema, BACKUP_DIR
)
from modulos.seguridad.autorizacion_ui import solicitar_autorizacion_admin
from ui_scale import escalar, escalar_fuente
from vim_logger import get_logger


class ModuloBackup:
    def __init__(self, root, frame_contenido, volver_menu=None, embebido=False):
        """
        Módulo de Copias de Seguridad.

        Args:
            root: Ventana raíz de Tkinter.
            frame_contenido: Frame donde se renderiza el contenido.
            volver_menu: Callback para volver al menú principal (None si embebido).
            embebido: Si True, omite el header (útil para embeberse en Configuración).
        """
        self.root = root
        self.frame_contenido = frame_contenido
        self.volver_menu = volver_menu
        self.embebido = embebido

        self._construir_ui()
        self.refrescar_historial()

    def _construir_ui(self):
        for w in self.frame_contenido.winfo_children():
            w.destroy()

        parent = self.frame_contenido

        # ---- HEADER (solo en modo standalone) ----
        if not self.embebido:
            header = tk.Frame(parent, bg=COLOR_PRIMARIO, height=escalar(70))
            header.pack(fill="x")
            header.pack_propagate(False)

            tk.Label(
                header, text="COPIAS DE SEGURIDAD",
                font=FUENTE_MODULO, fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
            ).pack(side="left", padx=escalar(20), pady=escalar(18))

            if self.volver_menu:
                tk.Button(
                    header, text="\u2190 Volver al Men\u00fa", bg=COLOR_PELIGRO, fg=COLOR_BLANCO,
                    relief="flat", font=FUENTE_BOTON, cursor="hand2", command=self.volver_menu
                ).pack(side="right", padx=escalar(20), pady=escalar(18))

        # ---- CUERPO ----
        cuerpo = tk.Frame(parent, bg=COLOR_GRIS)
        cuerpo.pack(fill="both", expand=True, padx=escalar(15), pady=escalar(15))

        # ---- INFO SISTEMA ----
        card_info = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        card_info.pack(fill="x", pady=(0, escalar(12)))

        tk.Label(card_info, text="Estado del Sistema", font=("Segoe UI", escalar_fuente(12), "bold"),
                 bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(anchor="w", padx=escalar(20), pady=(escalar(12), escalar(5)))

        self.info_grid = tk.Frame(card_info, bg=COLOR_BLANCO)
        self.info_grid.pack(fill="x", padx=escalar(20), pady=(0, escalar(12)))

        self.labels_status = {}
        self._crear_labels_status()
        self.actualizar_info_sistema()

        # ---- ACCIONES (2 tarjetas lado a lado) ----
        acciones = tk.Frame(cuerpo, bg=COLOR_GRIS)
        acciones.pack(fill="x", pady=(0, escalar(12)))
        acciones.grid_columnconfigure(0, weight=1, uniform="acc")
        acciones.grid_columnconfigure(1, weight=1, uniform="acc")

        # Tarjeta Crear
        card_crear = tk.Frame(acciones, bg=COLOR_BLANCO, bd=1, relief="solid")
        card_crear.grid(row=0, column=0, sticky="nsew", padx=(0, escalar(6)))

        tk.Label(card_crear, text="\U0001f4e6  Crear Copia de Seguridad", font=("Segoe UI", escalar_fuente(12), "bold"),
                 bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(anchor="w", padx=escalar(20), pady=(escalar(15), escalar(5)))
        tk.Label(card_crear, text="Genera un respaldo completo de todas tus ventas,\nproductos y configuraciones actuales.",
                 bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9)), fg="#666", justify="left").pack(anchor="w", padx=escalar(20), pady=(0, escalar(12)))
        tk.Button(
            card_crear, text="\U0001f4be  Generar Copia Ahora", bg="#28a745", fg="white",
            relief="flat", font=("Segoe UI", escalar_fuente(11), "bold"), cursor="hand2",
            command=self.hacer_backup
        ).pack(fill="x", padx=escalar(20), pady=(0, escalar(15)), ipady=escalar(6))

        # Tarjeta Restaurar
        card_rest = tk.Frame(acciones, bg=COLOR_BLANCO, bd=1, relief="solid")
        card_rest.grid(row=0, column=1, sticky="nsew", padx=(escalar(6), 0))

        tk.Label(card_rest, text="\U0001f4e5  Restaurar desde Archivo Externo", font=("Segoe UI", escalar_fuente(12), "bold"),
                 bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(anchor="w", padx=escalar(20), pady=(escalar(15), escalar(5)))
        tk.Label(card_rest, text="Selecciona un archivo .db externo para restaurar.\nSe creará un backup de seguridad automáticamente.",
                 bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9)), fg="#666", justify="left").pack(anchor="w", padx=escalar(20), pady=(0, escalar(5)))
        tk.Label(card_rest, text="\u26a0\ufe0f  Esta acci\u00f3n es irreversible",
                 bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "bold"), fg=COLOR_PELIGRO).pack(anchor="w", padx=escalar(20), pady=(0, escalar(8)))
        tk.Button(
            card_rest, text="\U0001f4c2  Seleccionar y Restaurar", bg="#ffc107", fg="black",
            relief="flat", font=("Segoe UI", escalar_fuente(11), "bold"), cursor="hand2",
            command=self.restaurar_externo
        ).pack(fill="x", padx=escalar(20), pady=(0, escalar(15)), ipady=escalar(6))

        # ---- HISTORIAL DE BACKUPS ----
        card_hist = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        card_hist.pack(fill="both", expand=True)

        header_hist = tk.Frame(card_hist, bg=COLOR_BLANCO)
        header_hist.pack(fill="x", padx=escalar(20), pady=(escalar(12), escalar(8)))

        tk.Label(header_hist, text="\U0001f4cb  Historial de Copias de Seguridad",
                 font=("Segoe UI", escalar_fuente(12), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO).pack(side="left")

        btn_frame = tk.Frame(header_hist, bg=COLOR_BLANCO)
        btn_frame.pack(side="right")

        tk.Button(btn_frame, text="\U0001f504 Refrescar", bg="#e9ecef", fg="#333", relief="flat",
                  font=("Segoe UI", escalar_fuente(9)), cursor="hand2",
                  command=self._refresh_all).pack(side="left", padx=(0, escalar(5)))
        tk.Button(btn_frame, text="\U0001f4c2 Abrir carpeta", bg="#e9ecef", fg="#333", relief="flat",
                  font=("Segoe UI", escalar_fuente(9)), cursor="hand2",
                  command=self.abrir_carpeta_backups).pack(side="left", padx=(0, escalar(5)))
        self.btn_restaurar_sel = tk.Button(
            btn_frame, text="\U0001f4e5 Restaurar", bg="#17a2b8", fg="white", relief="flat",
            font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled",
            command=self.restaurar_seleccionado
        )
        self.btn_restaurar_sel.pack(side="left", padx=(0, escalar(5)))
        self.btn_eliminar_sel = tk.Button(
            btn_frame, text="\U0001f5d1\ufe0f Eliminar", bg=COLOR_PELIGRO, fg="white", relief="flat",
            font=("Segoe UI", escalar_fuente(9), "bold"), cursor="hand2", state="disabled",
            command=self.eliminar_seleccionado
        )
        self.btn_eliminar_sel.pack(side="left")

        # ---- DÓNDE QUEDAN GUARDADAS ----
        # La carpeta cambia según se ejecute desde el código o desde el .exe
        # (ver config.py). Mostrarla evita que haya que adivinarla, y va en
        # un campo de solo lectura para poder copiarla y pegarla.
        fila_ruta = tk.Frame(card_hist, bg=COLOR_BLANCO)
        fila_ruta.pack(fill="x", padx=escalar(20), pady=(0, escalar(8)))

        tk.Label(fila_ruta, text="Se guardan en:", bg=COLOR_BLANCO, fg="#64748b",
                 font=("Segoe UI", escalar_fuente(9), "bold")).pack(side="left")

        self.ent_ruta_backups = tk.Entry(
            fila_ruta, font=("Consolas", escalar_fuente(9)),
            bd=0, bg="#f1f5f9", fg="#334155", readonlybackground="#f1f5f9"
        )
        self.ent_ruta_backups.pack(side="left", fill="x", expand=True,
                                   padx=(escalar(8), escalar(8)), ipady=escalar(3))
        self.ent_ruta_backups.insert(0, BACKUP_DIR)
        self.ent_ruta_backups.config(state="readonly")

        tk.Button(fila_ruta, text="Copiar ruta", bg="#e9ecef", fg="#333", relief="flat",
                  font=("Segoe UI", escalar_fuente(8)), cursor="hand2",
                  command=self.copiar_ruta_backups).pack(side="left")

        # Tabla de backups
        tabla_frame = tk.Frame(card_hist, bg=COLOR_BLANCO)
        tabla_frame.pack(fill="both", expand=True, padx=escalar(20), pady=(0, escalar(15)))

        style = ttk.Style()
        style.configure("Backup.Treeview", rowheight=escalar(32), font=("Segoe UI", escalar_fuente(10)))
        style.configure("Backup.Treeview.Heading", font=("Segoe UI", escalar_fuente(10), "bold"),
                        background="#e2e8f0", foreground="#333333", relief="flat")

        cols = ("nombre", "fecha", "tamaño")
        self.tree = ttk.Treeview(tabla_frame, columns=cols, show="headings", style="Backup.Treeview")

        self.tree.heading("nombre", text="Archivo")
        self.tree.heading("fecha", text="Fecha de Creación")
        self.tree.heading("tamaño", text="Tamaño")

        self.tree.column("nombre", width=escalar(350), anchor="w")
        self.tree.column("fecha", width=escalar(180), anchor="center")
        self.tree.column("tamaño", width=escalar(100), anchor="center")

        self.tree.tag_configure("impar", background="#edf2f7")
        self.tree.tag_configure("par", background="#ffffff")

        vsb = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self._on_select_backup)

    def _crear_labels_status(self):
        positions = [
            ("db_nombre", 0, 0), ("db_tamaño_mb", 0, 1),
            ("ultimo_backup", 0, 2), ("total_backups", 0, 3),
            ("productos", 1, 0), ("ventas", 1, 1),
            ("usuarios", 1, 2), ("proveedores", 1, 3)
        ]
        for key, row, col in positions:
            lbl = tk.Label(self.info_grid, text="...", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9)), anchor="w")
            lbl.grid(row=row, column=col, sticky="w", padx=escalar(15), pady=escalar(2))
            self.labels_status[key] = lbl
            self.info_grid.grid_columnconfigure(col, weight=1)

    def actualizar_info_sistema(self):
        info = obtener_info_sistema()
        registros = info.get("registros", {})

        mapping = {
            "db_nombre": f"\U0001f4c1  Base de datos: {info['db_nombre']}",
            "db_tamaño_mb": f"\U0001f4be  Tama\u00f1o: {info['db_tamaño_mb']} MB",
            "ultimo_backup": f"\U0001f550  Último backup: {info['ultimo_backup']}",
            "total_backups": f"\U0001f4e6  Backups guardados: {info['total_backups']}",
            "productos": f"\U0001f3f7\ufe0f  Productos: {registros.get('productos', 0)}",
            "ventas": f"\U0001f9fe  Ventas: {registros.get('ventas', 0)}",
            "usuarios": f"\U0001f464  Usuarios: {registros.get('usuarios', 0)}",
            "proveedores": f"\U0001f6cd\ufe0f  Proveedores: {registros.get('proveedores', 0)}"
        }

        for key, text in mapping.items():
            if key in self.labels_status:
                self.labels_status[key].config(text=text)

    def _refresh_all(self, event=None):
        self.refrescar_historial()
        self.actualizar_info_sistema()

    def _on_select_backup(self, event=None):
        sel = self.tree.selection()
        state = "normal" if sel else "disabled"
        self.btn_restaurar_sel.config(state=state)
        self.btn_eliminar_sel.config(state=state)

    def refrescar_historial(self):
        self.tree.delete(*self.tree.get_children())
        backups = listar_backups()

        if not backups:
            self.tree.insert("", "end", values=("Sin backups disponibles", "\u2014", "\u2014"))
            return

        for i, b in enumerate(backups):
            tag = "impar" if i % 2 else "par"
            self.tree.insert(
                "", "end", iid=b["ruta"],
                values=(b["nombre"], b["fecha"], f"{b['tamaño_mb']} MB"),
                tags=(tag,)
            )

    def hacer_backup(self):
        try:
            ruta = crear_backup()
            self._refresh_all()

            # Antes solo se mostraba el nombre del archivo y el usuario no
            # ten\u00eda forma de saber d\u00f3nde hab\u00eda quedado.
            abrir = messagebox.askyesno(
                "Copia de seguridad creada",
                f"Archivo:\n{os.path.basename(ruta)}\n\n"
                f"Guardado en:\n{BACKUP_DIR}\n\n"
                "\u00bfQuer\u00e9s abrir la carpeta ahora?",
                parent=self.root
            )
            if abrir:
                self.abrir_carpeta_backups(resaltar=ruta)
        except Exception as e:
            get_logger("backup").exception("Falló la creación del backup")
            messagebox.showerror("Error", f"No se pudo crear el backup:\n{e}", parent=self.root)

    def copiar_ruta_backups(self):
        """Deja la carpeta de backups en el portapapeles."""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(BACKUP_DIR)
            self.root.update()          # necesario para que persista al cerrar
            messagebox.showinfo(
                "Ruta copiada",
                f"Se copi\u00f3 al portapapeles:\n\n{BACKUP_DIR}\n\n"
                "Pegala en el explorador de archivos para llegar ah\u00ed.",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo copiar la ruta:\n{e}", parent=self.root)

    def restaurar_externo(self):
        filepath = filedialog.askopenfilename(
            parent=self.root, title="Seleccionar Backup de VIM ERP",
            filetypes=[("Base de datos SQLite", "*.db"), ("Todos los archivos", "*.*")]
        )
        if not filepath:
            return

        self._ejecutar_restauracion(filepath)

    def restaurar_seleccionado(self):
        sel = self.tree.selection()
        if not sel:
            return
        ruta = sel[0]
        self._ejecutar_restauracion(ruta)

    def _ejecutar_restauracion(self, ruta):
        if not solicitar_autorizacion_admin(self.root, "RESTAURAR BASE DE DATOS"):
            return

        warning = (
            "\u26a0\ufe0f \u00bfEST\u00c1 COMPLETAMENTE SEGURO?\n\n"
            "Restaurar un backup REEMPLAZAR\u00c1 y ELIMINAR\u00c1 todas las ventas, "
            "productos y configuraciones realizadas despu\u00e9s de que dicho "
            "backup fue creado.\n\n"
            "Antes de restaurar se guarda una copia del estado actual, por si\n"
            "esto fue un error. Queda como 'pre_restauracion_...' en:\n"
            f"{BACKUP_DIR}\n\n"
            "IMPORTANTE: Aseg\u00farese de cerrar el PUNTO DE VENTA y cualquier otra\n"
            "ventana abierta antes de continuar.\n\n"
            "Esta acci\u00f3n requiere reiniciar la aplicaci\u00f3n."
        )
        if not messagebox.askyesno("Peligro de P\u00e9rdida de Datos", warning,
                                    icon="warning", parent=self.root):
            return

        try:
            restaurar_backup(ruta)
            messagebox.showinfo(
                "Restauraci\u00f3n Completada",
                "La base de datos fue reemplazada correctamente.\n\n"
                "Para GARANTIZAR que los cambios se apliquen y evitar errores,\n"
                "la aplicaci\u00f3n SE CERRAR\u00c1 AHORA.\n\n"
                "Por favor, \u00e1brala nuevamente para continuar.",
                parent=self.root
            )
            self.root.quit()
            os._exit(0)
        except Exception as e:
            get_logger("backup").exception("Falló la restauración del backup")
            messagebox.showerror("Error", f"No se pudo restaurar:\n{e}", parent=self.root)

    def eliminar_seleccionado(self):
        sel = self.tree.selection()
        if not sel:
            return

        ruta = sel[0]
        nombre = os.path.basename(ruta)

        if not messagebox.askyesno("Confirmar", f"\u00bfEliminar el backup?\n\n{nombre}",
                                    parent=self.root):
            return

        try:
            eliminar_backup(ruta)
            self._refresh_all()
            messagebox.showinfo("\u00c9xito", "Backup eliminado.", parent=self.root)
        except Exception as e:
            get_logger("backup").exception("Falló una operación de backup")
            messagebox.showerror("Error", str(e), parent=self.root)

    def abrir_carpeta_backups(self, resaltar=None):
        """Abre la carpeta de backups en el explorador.

        Si se indica `resaltar`, abre la carpeta con ese archivo ya
        seleccionado, para que no haya que buscarlo entre los demás.
        """
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)

            if resaltar and os.path.exists(resaltar):
                # /select, deja el archivo marcado dentro de la carpeta
                subprocess.Popen(["explorer", "/select,", os.path.normpath(resaltar)])
            else:
                os.startfile(BACKUP_DIR)
        except Exception as e:
            from vim_logger import get_logger
            get_logger("backup.ui").warning(f"No se pudo abrir la carpeta de backups: {e}")
            messagebox.showerror(
                "Error",
                f"No se pudo abrir la carpeta.\n\n"
                f"Está acá:\n{BACKUP_DIR}\n\nDetalle: {e}",
                parent=self.root
            )


def abrir_modulo_backup(root, frame_contenido, volver_menu):
    return ModuloBackup(root, frame_contenido, volver_menu, embebido=False)
