import tkinter as tk
from tkinter import ttk, messagebox

from ui_scale import escalar, escalar_fuente

from config import COLOR_PRIMARIO, COLOR_BLANCO, COLOR_GRIS, COLOR_PELIGRO, FUENTE_BOTON, FUENTE_MODULO
from database.usuarios import (
    MODULOS_DISPONIBLES, obtener_usuarios, obtener_permisos_usuario,
    guardar_permisos_usuario, crear_usuario, actualizar_usuario,
    desactivar_usuario, activar_usuario, eliminar_usuario
)
from modulos.seguridad.auth import hash_password
from modulos.utils_globales import crear_frame_scrollable
from vim_logger import get_logger


# ============================================================
# ETIQUETAS AMIGABLES PARA MÓDULOS
# ============================================================

MODULOS_LABELS = {
    "pos": "🛒  Punto de Venta (POS)",
    "inventario": "📦  Inventario",
    "productos": "🏷️  Productos",
    "reportes": "📊  Ventas / Reportes",
    "compras": "🛍️  Administración",
    "caja": "💰  Caja",
    "usuarios": "👨‍💼  Gestión de Usuarios",
    "configuracion": "⚙️  Configuración",
    "backup": "💾  Copias de Seguridad",
}


class ModuloUsuarios:
    def __init__(self, root, frame_contenido, volver_menu):
        self.root = root
        self.frame_contenido = frame_contenido
        self.volver_menu = volver_menu
        self.usuario_id_sel = None
        self.perm_vars = {}  # {modulo: tk.BooleanVar}

        self._construir_ui()
        self.cargar_usuarios()

    # ============================================================
    # LAYOUT PRINCIPAL
    # ============================================================

    def _construir_ui(self):

        parent = self.frame_contenido

        # ---- HEADER ----
        header = tk.Frame(parent, bg=COLOR_PRIMARIO, height=escalar(70))
        header.pack(fill="x")
        header.pack_propagate(False)

        tk.Label(
            header, text="👨‍💼  USUARIOS",
            font=FUENTE_MODULO, fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
        ).pack(side="left", padx=escalar(20), pady=escalar(18))

        tk.Button(
            header, text="← Volver al Menú", bg=COLOR_PELIGRO, fg=COLOR_BLANCO,
            relief="flat", font=FUENTE_BOTON, cursor="hand2", command=self.volver_menu
        ).pack(side="right", padx=escalar(20), pady=escalar(18))

        # ---- CUERPO ----
        cuerpo = tk.Frame(parent, bg=COLOR_GRIS)
        cuerpo.pack(fill="both", expand=True, padx=escalar(15), pady=escalar(15))

        # Panel izquierdo: Lista de usuarios
        izq = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid")
        izq.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(
            izq, text="Usuarios del Sistema",
            font=("Segoe UI", escalar_fuente(13), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # Tabla usuarios
        tabla_frame = tk.Frame(izq, bg=COLOR_BLANCO)
        tabla_frame.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        style = ttk.Style()
        style.configure("Usuarios.Treeview", rowheight=escalar(34), font=("Segoe UI", escalar_fuente(10)))
        style.configure("Usuarios.Treeview.Heading", font=("Segoe UI", escalar_fuente(10), "bold"),
                        background="#e2e8f0", foreground="#333333", relief="flat")

        cols = ("id", "usuario", "nombre", "rol", "estado", "ultimo_acceso")
        self.tree = ttk.Treeview(tabla_frame, columns=cols, show="headings", style="Usuarios.Treeview")

        self.tree.heading("id", text="ID")
        self.tree.heading("usuario", text="Usuario")
        self.tree.heading("nombre", text="Nombre")
        self.tree.heading("rol", text="Rol")
        self.tree.heading("estado", text="Estado")
        self.tree.heading("ultimo_acceso", text="Último Acceso")

        self.tree.column("id", width=escalar(40), anchor="center")
        self.tree.column("usuario", width=escalar(100), anchor="w")
        self.tree.column("nombre", width=escalar(150), anchor="w")
        self.tree.column("rol", width=escalar(100), anchor="center")
        self.tree.column("estado", width=escalar(70), anchor="center")
        self.tree.column("ultimo_acceso", width=escalar(130), anchor="center")

        self.tree.tag_configure("impar", background="#edf2f7")
        self.tree.tag_configure("par", background="#ffffff")
        self.tree.tag_configure("inactivo", foreground="#999")

        vsb = ttk.Scrollbar(tabla_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        # Botones bajo tabla
        btn_bar = tk.Frame(izq, bg=COLOR_BLANCO)
        btn_bar.pack(fill="x", padx=15, pady=(0, 15))

        tk.Button(btn_bar, text="➕ Nuevo Usuario", bg="#28a745", fg="white",
                  relief="flat", font=FUENTE_BOTON, cursor="hand2",
                  command=self.limpiar_form).pack(side="left", padx=(0, 5))

        self.btn_toggle_estado = tk.Button(
            btn_bar, text="Desactivar", bg="#6c757d", fg="white",
            relief="flat", font=FUENTE_BOTON, cursor="hand2", state="disabled",
            command=self.toggle_estado_usuario
        )
        self.btn_toggle_estado.pack(side="left", padx=(0, 5))

        self.btn_eliminar_usuario = tk.Button(
            btn_bar, text="🗑️ Eliminar", bg=COLOR_PELIGRO, fg="white",
            relief="flat", font=FUENTE_BOTON, cursor="hand2", state="disabled",
            command=self.eliminar_usuario_seleccionado
        )
        self.btn_eliminar_usuario.pack(side="left", padx=(0, 5))

        # Panel derecho: Formulario + Permisos
        der_shell = tk.Frame(cuerpo, bg=COLOR_BLANCO, bd=1, relief="solid", width=max(310, escalar(380)))
        der_shell.pack(side="right", fill="y", padx=(8, 0))
        der_shell.pack_propagate(False)

        scroll_der, der = crear_frame_scrollable(der_shell, bg=COLOR_BLANCO)
        scroll_der.pack(fill="both", expand=True)

        # --- Formulario ---
        tk.Label(
            der, text="Datos del Usuario",
            font=("Segoe UI", escalar_fuente(13), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(anchor="w", padx=20, pady=(15, 5))

        tk.Frame(der, height=1, bg="#eee").pack(fill="x", padx=20, pady=(0, 10))

        form = tk.Frame(der, bg=COLOR_BLANCO)
        form.pack(fill="x", padx=20)

        tk.Label(form, text="Usuario (Login):", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9))).pack(anchor="w")
        self.ent_user = tk.Entry(form, font=("Segoe UI", escalar_fuente(10)))
        self.ent_user.pack(fill="x", pady=(2, 8))

        tk.Label(form, text="Nombre Completo:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9))).pack(anchor="w")
        self.ent_nombre = tk.Entry(form, font=("Segoe UI", escalar_fuente(10)))
        self.ent_nombre.pack(fill="x", pady=(2, 8))

        tk.Label(form, text="Contraseña:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9))).pack(anchor="w")
        self.ent_pass = tk.Entry(form, font=("Segoe UI", escalar_fuente(10)), show="*")
        self.ent_pass.pack(fill="x", pady=(2, 8))

        tk.Label(form, text="Rol del Sistema:", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9))).pack(anchor="w")
        self.cmb_rol = ttk.Combobox(
            form, values=["cajero", "supervisor", "administrador"],
            state="readonly", font=("Segoe UI", escalar_fuente(10))
        )
        self.cmb_rol.pack(fill="x", pady=(2, 12))
        self.cmb_rol.set("cajero")

        # --- Panel de Permisos ---
        tk.Label(
            der, text="Permisos por Módulo",
            font=("Segoe UI", escalar_fuente(11), "bold"), bg=COLOR_BLANCO, fg=COLOR_PRIMARIO
        ).pack(anchor="w", padx=20, pady=(5, 3))

        tk.Frame(der, height=1, bg="#eee").pack(fill="x", padx=20, pady=(0, 8))

        perm_frame = tk.Frame(der, bg=COLOR_BLANCO)
        perm_frame.pack(fill="x", padx=20)

        self.perm_vars = {}
        for modulo in MODULOS_DISPONIBLES:
            var = tk.BooleanVar(value=False)
            label = MODULOS_LABELS.get(modulo, modulo)
            cb = tk.Checkbutton(
                perm_frame, text=label, variable=var, bg=COLOR_BLANCO,
                font=("Segoe UI", escalar_fuente(9)), anchor="w", cursor="hand2",
                activebackground=COLOR_BLANCO
            )
            cb.pack(fill="x", pady=1)
            self.perm_vars[modulo] = var

        # Botones selección rápida de permisos
        perm_btns = tk.Frame(der, bg=COLOR_BLANCO)
        perm_btns.pack(fill="x", padx=20, pady=(5, 5))

        tk.Button(perm_btns, text="✅ Todos", bg="#e9ecef", fg="#333", relief="flat",
                  font=("Segoe UI", escalar_fuente(8)), cursor="hand2",
                  command=lambda: self._set_all_perms(True)).pack(side="left", padx=(0, 5))
        tk.Button(perm_btns, text="❌ Ninguno", bg="#e9ecef", fg="#333", relief="flat",
                  font=("Segoe UI", escalar_fuente(8)), cursor="hand2",
                  command=lambda: self._set_all_perms(False)).pack(side="left")

        # Botón guardar
        tk.Button(
            der, text="💾 Guardar Cambios", bg="#28a745", fg="white",
            relief="flat", font=("Segoe UI", escalar_fuente(11), "bold"), cursor="hand2",
            command=self.guardar
        ).pack(fill="x", padx=20, pady=(15, 15), ipady=6)

    # ============================================================
    # LÓGICA
    # ============================================================

    def cargar_usuarios(self):
        self.tree.delete(*self.tree.get_children())
        try:
            usuarios = obtener_usuarios()
            for i, u in enumerate(usuarios):
                estado = "Activo" if u["activo"] else "Inactivo"
                acceso = u.get("ultimo_acceso") or "Nunca"
                if acceso != "Nunca":
                    try:
                        p = acceso.replace("T", " ").split(" ")
                        y, m, d = p[0].split("-")
                        acceso = f"{d}-{m}-{y}"
                        if len(p) > 1:
                            acceso += f" {p[1][:5]}"
                    except Exception:
                        acceso = acceso[:16]

                tag = "inactivo" if not u["activo"] else ("impar" if i % 2 else "par")
                self.tree.insert(
                    "", "end", iid=str(u["id"]),
                    values=(u["id"], u["username"], u["nombre"], u["rol"].capitalize(), estado, acceso),
                    tags=(tag,)
                )
        except Exception as e:
            print(f"Error cargando usuarios: {e}")

    def on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return

        item = self.tree.item(sel[0])
        v = item["values"]
        self.usuario_id_sel = v[0]

        # Llenar formulario
        self.ent_user.delete(0, tk.END)
        self.ent_user.insert(0, v[1])
        self.ent_nombre.delete(0, tk.END)
        self.ent_nombre.insert(0, v[2])
        self.ent_pass.delete(0, tk.END)
        self.cmb_rol.set(str(v[3]).lower())

        # Cargar permisos
        permisos = obtener_permisos_usuario(self.usuario_id_sel)
        for modulo, var in self.perm_vars.items():
            var.set(permisos.get(modulo, False))

        # Actualizar botón estado
        estado = str(v[4])
        if estado == "Activo":
            self.btn_toggle_estado.config(text="🚫 Desactivar", bg=COLOR_PELIGRO, state="normal")
        else:
            self.btn_toggle_estado.config(text="✅ Reactivar", bg="#28a745", state="normal")

        self.btn_eliminar_usuario.config(state="normal")

        # Proteger admin principal
        if self.usuario_id_sel == 1:
            self.btn_toggle_estado.config(state="disabled")
            self.btn_eliminar_usuario.config(state="disabled")

    def limpiar_form(self):
        self.usuario_id_sel = None
        self.ent_user.delete(0, tk.END)
        self.ent_nombre.delete(0, tk.END)
        self.ent_pass.delete(0, tk.END)
        self.ent_pass.insert(0, "1234")
        self.cmb_rol.set("cajero")
        self.btn_toggle_estado.config(state="disabled")
        self.btn_eliminar_usuario.config(state="disabled")

        # Permisos default cajero
        from database.usuarios import _permisos_default_por_rol
        defaults = _permisos_default_por_rol("cajero")
        for modulo, var in self.perm_vars.items():
            var.set(defaults.get(modulo, False))

        self.ent_user.focus_set()

    def _set_all_perms(self, value: bool):
        for var in self.perm_vars.values():
            var.set(value)

    def guardar(self):
        username = self.ent_user.get().strip()
        nombre = self.ent_nombre.get().strip()
        pwd = self.ent_pass.get().strip()
        rol = self.cmb_rol.get()

        if not username or not nombre:
            messagebox.showwarning("Campos requeridos", "Usuario y nombre son obligatorios.", parent=self.root)
            return

        # Recopilar permisos
        permisos = {m: v.get() for m, v in self.perm_vars.items()}

        try:
            if self.usuario_id_sel:
                # Actualizar existente
                from modulos.seguridad.sesion import Sesion
                admin_id = Sesion.get_usuario_id()
                
                pwd_hash = hash_password(pwd) if pwd else None
                actualizar_usuario(self.usuario_id_sel, username, nombre, rol, pwd_hash, responsable_id=admin_id)
                guardar_permisos_usuario(self.usuario_id_sel, permisos, responsable_id=admin_id)
                messagebox.showinfo("Éxito", f"Usuario '{username}' actualizado correctamente.", parent=self.root)
            else:
                # Crear nuevo
                if not pwd:
                    messagebox.showwarning("Contraseña requerida",
                                           "La contraseña es obligatoria para nuevos usuarios.", parent=self.root)
                    return
                if len(pwd) < 4:
                    messagebox.showwarning("Contraseña débil",
                                           "La contraseña debe tener al menos 4 caracteres.", parent=self.root)
                    return
                from modulos.seguridad.sesion import Sesion
                admin_id = Sesion.get_usuario_id()
                
                pwd_hash = hash_password(pwd)
                nuevo_id = crear_usuario(username, pwd_hash, nombre, rol, responsable_id=admin_id)
                guardar_permisos_usuario(nuevo_id, permisos, responsable_id=admin_id)
                messagebox.showinfo("Éxito", f"Usuario '{username}' creado exitosamente.", parent=self.root)

            self.limpiar_form()
            self.cargar_usuarios()

            # Recargar permisos de sesión si se editó el usuario actual
            from modulos.seguridad.sesion import Sesion
            if self.usuario_id_sel == Sesion.get_usuario_id():
                Sesion.recargar_permisos()

        except Exception as e:
            if "UNIQUE" in str(e):
                messagebox.showerror("Error", "El nombre de usuario ya existe.", parent=self.root)
            else:
                messagebox.showerror("Error", f"Error al guardar: {e}", parent=self.root)

    def toggle_estado_usuario(self):
        if not self.usuario_id_sel:
            return

        if self.usuario_id_sel == 1:
            messagebox.showwarning("Prohibido", "No puedes desactivar al administrador principal.", parent=self.root)
            return

        item = self.tree.item(str(self.usuario_id_sel))
        estado_actual = item["values"][4]

        try:
            from modulos.seguridad.sesion import Sesion
            admin_id = Sesion.get_usuario_id()
            
            if estado_actual == "Activo":
                if messagebox.askyesno("Confirmar", "¿Desactivar este usuario? No podrá iniciar sesión.",
                                        parent=self.root):
                    desactivar_usuario(self.usuario_id_sel, responsable_id=admin_id)
                    messagebox.showinfo("Éxito", "Usuario desactivado.", parent=self.root)
            else:
                if messagebox.askyesno("Confirmar", "¿Reactivar este usuario?", parent=self.root):
                    activar_usuario(self.usuario_id_sel, responsable_id=admin_id)
                    messagebox.showinfo("Éxito", "Usuario reactivado.", parent=self.root)

            self.limpiar_form()
            self.cargar_usuarios()
        except Exception as e:
            get_logger("usuarios").exception("Falló una operación de usuarios")
            messagebox.showerror("Error", str(e), parent=self.root)

    def eliminar_usuario_seleccionado(self):
        if not self.usuario_id_sel:
            return

        if self.usuario_id_sel == 1:
            messagebox.showwarning("Prohibido", "No puedes eliminar al administrador principal.", parent=self.root)
            return

        item = self.tree.item(str(self.usuario_id_sel))
        nombre = item["values"][1]

        warning = (
            f"⚠️ ¿ESTÁ COMPLETAMENTE SEGURO?\n\n"
            f"Eliminar el usuario '{nombre}' borrará permanentemente su acceso y permisos del sistema.\n"
            f"Esta acción es irreversible."
        )

        if messagebox.askyesno("Confirmar Eliminación", warning, icon="warning", parent=self.root):
            try:
                from modulos.seguridad.sesion import Sesion
                admin_id = Sesion.get_usuario_id()
                
                eliminar_usuario(self.usuario_id_sel, responsable_id=admin_id)
                messagebox.showinfo("Éxito", f"Usuario '{nombre}' eliminado correctamente.", parent=self.root)
                self.limpiar_form()
                self.cargar_usuarios()
            except Exception as e:
                get_logger("usuarios").exception("Falló la eliminación de usuario")
                messagebox.showerror("Error", f"No se pudo eliminar el usuario: {e}", parent=self.root)


def abrir_modulo_usuarios(root, frame_contenido, volver_menu):
    return ModuloUsuarios(root, frame_contenido, volver_menu)
