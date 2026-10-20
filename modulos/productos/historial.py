import tkinter as tk
from tkinter import ttk

from config import COLOR_BLANCO, COLOR_PRIMARIO, COLOR_GRIS
from modulos.utils_globales import aplicar_barra_windows_azul, centrar_ventana_mejorado
from database import obtener_historial
from ui_scale import escalar, escalar_fuente


class ProductosHistorialMixin:
    def abrir_historial(self):
        win = tk.Toplevel(self.root)
        win.title("Historial del Sistema")
        win.configure(bg=COLOR_GRIS)
        win.grab_set()
        aplicar_barra_windows_azul(win)
        centrar_ventana_mejorado(win, escalar(1150), escalar(580))

        contenedor = tk.Frame(win, bg=COLOR_GRIS)
        contenedor.pack(fill="both", expand=True, padx=15, pady=15)

        tk.Label(
            contenedor,
            text="Historial de movimientos",
            font=("Segoe UI", escalar_fuente(18), "bold"),
            bg=COLOR_GRIS,
            fg=COLOR_PRIMARIO
        ).pack(anchor="w", pady=(0, 10))

        frame_tabla = tk.Frame(
            contenedor,
            bg=COLOR_BLANCO,
            highlightthickness=1,
            highlightbackground="#d9dee7"
        )
        frame_tabla.pack(fill="both", expand=True)

        columnas = (
            "Hora",
            "Usuario",
            "Accion",
            "Producto",
            "Total",
            "ItemsVendidos",
            "Documento",
            "Categoria",
            "Proveedor",
            "Tabla",
            "RefID",
            "Detalles"
        )

        # El tema se fija una sola vez al iniciar (ventana_principal.py);
        # cambiarlo acá alteraba el aspecto de todo el programa.
        style = ttk.Style()

        style.configure(
            "Historial.Treeview",
            rowheight=escalar(30),
            font=("Segoe UI", escalar_fuente(10)),
            background="white",
            fieldbackground="white",
            borderwidth=0
        )

        style.configure(
            "Historial.Treeview.Heading",
            font=("Segoe UI", escalar_fuente(10), "bold"),
            background="#e2e8f0",
            foreground="#333333",
            relief="flat"
        )

        style.map(
            "Historial.Treeview.Heading",
            background=[("active", "#cbd5e1")]
        )

        tree = ttk.Treeview(
            frame_tabla,
            columns=columnas,
            show="headings",
            style="Historial.Treeview"
        )

        vsb = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame_tabla, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        encabezados = {
            "Hora": "Fecha / Hora",
            "Usuario": "Ejecutado por",
            "Accion": "Acción",
            "Producto": "Producto",
            "Total": "Total",
            "ItemsVendidos": "Artículos (Items)",
            "Documento": "Documento",
            "Categoria": "Categoría",
            "Proveedor": "Proveedor",
            "Tabla": "Origen",
            "RefID": "ID",
            "Detalles": "Detalles Internos"
        }

        for col in columnas:
            tree.heading(col, text=encabezados[col])

        tree.column("Hora", width=escalar(120), anchor="center", stretch=False)
        tree.column("Usuario", width=escalar(130), anchor="w", stretch=False)
        tree.column("Accion", width=escalar(140), anchor="center", stretch=False)
        tree.column("Producto", width=escalar(180), anchor="w", stretch=False)
        tree.column("Total", width=escalar(100), anchor="e", stretch=False)
        tree.column("ItemsVendidos", width=escalar(250), anchor="w", stretch=False)
        tree.column("Documento", width=escalar(120), anchor="center", stretch=False)
        tree.column("Categoria", width=escalar(140), anchor="w", stretch=False)
        tree.column("Proveedor", width=escalar(150), anchor="w", stretch=False)
        tree.column("Tabla", width=escalar(90), anchor="center", stretch=False)
        tree.column("RefID", width=escalar(60), anchor="center", stretch=False)
        tree.column("Detalles", width=escalar(420), anchor="w", stretch=True)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        frame_tabla.grid_rowconfigure(0, weight=1)
        frame_tabla.grid_columnconfigure(0, weight=1)

        historial = obtener_historial()

        for i, fila in enumerate(historial):
            fecha = fila.get("fecha", "")
            usuario_nombre = fila.get("usuario_nombre") or "Sistema"
            accion = fila.get("accion", "")
            tabla = fila.get("tabla", "") or ""
            registro_id = fila.get("id", "")
            referencia_id = fila.get("referencia_id", "") or ""
            detalles = fila.get("detalles", "") or ""

            producto = ""
            categoria = ""
            proveedor = ""
            documento = ""
            total = ""
            items_vendidos = ""

            accion_mostrar = (accion or "").replace("_", " ").title()

            # =====================================================
            # ALTAS / PRODUCTOS
            # =====================================================
            if "Producto agregado:" in detalles:
                accion_mostrar = "Alta producto"
                partes = [p.strip() for p in detalles.split("|")]

                for parte in partes:
                    if parte.startswith("Producto agregado:"):
                        producto = parte.replace("Producto agregado:", "").strip()
                    elif parte.startswith("Categoría texto:"):
                        categoria = parte.replace("Categoría texto:", "").strip()
                    elif parte.startswith("Proveedor texto:"):
                        proveedor = parte.replace("Proveedor texto:", "").strip()

            elif detalles.startswith("Producto actualizado:"):
                accion_mostrar = "Modificación"
                resto = detalles.replace("Producto actualizado:", "").strip()
                if "|" in resto:
                    producto = resto.split("|")[0].strip()
                else:
                    producto = resto

                partes = [p.strip() for p in detalles.split("|")]
                for parte in partes:
                    if parte.startswith("Categoría texto:"):
                        categoria = parte.replace("Categoría texto:", "").strip()
                    elif parte.startswith("Proveedor texto:"):
                        proveedor = parte.replace("Proveedor texto:", "").strip()

            elif detalles.startswith("Producto:"):
                accion_mostrar = "Crear producto"
                producto = detalles.replace("Producto:", "").strip()

            elif detalles.startswith("Categoría:"):
                accion_mostrar = "Crear categoría"
                categoria = detalles.replace("Categoría:", "").strip()

            elif detalles.startswith("Proveedor:"):
                accion_mostrar = "Crear proveedor"
                proveedor = detalles.replace("Proveedor:", "").strip()

            # =====================================================
            # VENTAS
            # Formatos soportados:
            # 1) Venta VTA-... total: 1190.0
            # 2) Venta VTA-... total: 1190.0 | Items: Coca-Cola x2, Leche x1
            # =====================================================
            elif detalles.startswith("Venta "):
                accion_mostrar = "Venta"

                if " total: " in detalles:
                    partes_total = detalles.split(" total: ", 1)
                    documento = partes_total[0].replace("Venta", "").strip()

                    resto = partes_total[1].strip()

                    if " | Items: " in resto:
                        total, items_vendidos = resto.split(" | Items: ", 1)
                        total = total.strip()
                        items_vendidos = items_vendidos.strip()
                    else:
                        total = resto.strip()

            # =====================================================
            # COMPRAS
            # =====================================================
            elif detalles.startswith("Compra total:"):
                accion_mostrar = "Compra"
                total = detalles.replace("Compra total:", "").strip()

            tag = "par" if i % 2 == 0 else "impar"
            
            # Formatear la hora
            if fecha and len(fecha) >= 16:
                try:
                    p = fecha.replace("T", " ").split(" ")
                    y, m, d = p[0].split("-")
                    fecha_legible = f"{d}/{m} {p[1][:5]}"
                except (ValueError, IndexError):
                    # Fecha con un formato distinto al esperado: se muestra
                    # cruda, que es preferible a no mostrar la fila.
                    fecha_legible = fecha[:16]
            else:
                fecha_legible = fecha

            tree.insert(
                "",
                "end",
                values=(
                    fecha_legible,
                    usuario_nombre,
                    accion_mostrar,
                    producto,
                    total,
                    items_vendidos,
                    documento,
                    categoria,
                    proveedor,
                    tabla,
                    registro_id,
                    detalles
                ),
                tags=(tag,)
            )

        tree.tag_configure("par", background="#ffffff")
        tree.tag_configure("impar", background="#edf2f7")