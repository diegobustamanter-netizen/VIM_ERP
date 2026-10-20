import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any

from .ventas_ui import construir_interfaz
from database.ventas import buscar_ventas_filtradas, contar_ventas_filtradas, obtener_kpis_ventas, obtener_venta_por_id, obtener_reportes_avanzados
from database.reportes_financieros import obtener_estado_resultados, obtener_resumen_balance_general
from datetime import date, timedelta
from ui_scale import escalar, escalar_fuente
from config import COLOR_PRIMARIO, COLOR_BLANCO, COLOR_PELIGRO
from modulos.utils_globales import aplicar_barra_windows_azul, centrar_ventana_mejorado, preparar_modal_scrollable
from vim_logger import get_logger


def rango_rapido(tipo, hoy):
    """
    Fechas de los botones Hoy / Semana / Mes / Año del panel de Reportes.
    Terminan HOY, no al final de la semana/mes/año: antes "Este mes"
    llegaba hasta el 31, así que los gráficos mostraban días futuros vacíos
    y la comparación con el período anterior medía distinta cantidad de días.
    """
    if tipo == "semana":
        return hoy - timedelta(days=hoy.weekday()), hoy
    if tipo == "mes":
        return hoy.replace(day=1), hoy
    if tipo == "anio":
        return hoy.replace(month=1, day=1), hoy
    return hoy, hoy


def rango_de_atajo(clave, hoy, minimo=None):
    """Fechas (desde, hasta) de los atajos del Centro de Descargas."""
    if clave == "hoy":
        return hoy, hoy
    if clave == "ayer":
        ayer = hoy - timedelta(days=1)
        return ayer, ayer
    if clave == "semana":
        return hoy - timedelta(days=hoy.weekday()), hoy
    if clave == "mes":
        return hoy.replace(day=1), hoy
    if clave == "mes_pasado":
        fin = hoy.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    return minimo or date(2000, 1, 1), hoy      # "todo"


class ModuloVentasReportes:
    def __init__(self, root, frame_contenido, volver_menu):
        self.root = root
        self.frame_contenido = frame_contenido
        self.volver_menu = volver_menu
        self.ventas_actuales = []  # Para mapear i -> ID de venta en la tabla
        self.btn_filtro_activo = None

        self._pagina_actual = 0
        self._tamanio_pagina = 50
        self._total_ventas = 0
        self._busqueda_en_progreso = False
        self._ultimo_filtros = {}
        self._historial_cargando = False
        self._panel_activo = "resumen"

        # Obtener la fecha de la primera venta registrada en la BD
        self._fecha_minima = self._obtener_fecha_minima_bd()

        self._construir_ui()

        # Pre-cargar matplotlib en segundo plano: su primer import tarda
        # 1-2s y antes congelaba la UI al abrir "Análisis Visual" por
        # primera vez. Así ya está listo cuando el usuario llega ahí.
        threading.Thread(target=self._prewarm_matplotlib, daemon=True).start()

        # Diferir la carga inicial de datos 50ms para permitir que el
        # double-buffering termine el swap atómico y la UI responda instantáneamente
        self.root.after(50, lambda: self.set_fecha_rápida("mes"))

    @staticmethod
    def _prewarm_matplotlib():
        try:
            import matplotlib
            matplotlib.use("TkAgg")
            import matplotlib.pyplot  # noqa: F401
            from matplotlib.backends import backend_tkagg  # noqa: F401
        except Exception as e:
            # Sin matplotlib el panel visual mostrará su propio error, pero
            # dejamos registrado el motivo real (falta la librería, versión
            # incompatible, backend roto) para no adivinar después.
            from vim_logger import get_logger
            get_logger("ventas.graficos").warning(
                f"No se pudo cargar matplotlib, el panel visual no estará disponible: {e}"
            )

    def _obtener_fecha_minima_bd(self) -> date:
        """Retorna la fecha de la primera venta/apertura en la BD. Si no hay datos, retorna hoy."""
        try:
            from database.connection import conectar_db as _cdb
            _c = _cdb()
            _r = _c.execute("SELECT MIN(fecha) FROM ventas").fetchone()
            _c.close()
            if _r and _r[0]:
                return date.fromisoformat(str(_r[0])[:10])
        except Exception as e:
            # Si no se puede leer la fecha de la venta más antigua, los
            # filtros por período arrancan desde hoy y el usuario cree que
            # no hay historial. Conviene saber por qué.
            from vim_logger import get_logger
            get_logger("ventas.reportes").warning(
                f"No se pudo determinar la fecha de la primera venta: {e}"
            )
        return date.today()

    def _construir_ui(self):
        construir_interfaz(self)

    def _mostrar_loader_historial(self, mostrar: bool):
        self._historial_cargando = mostrar
        try:
            if hasattr(self, 'frame_loader_historial') and self.frame_loader_historial.winfo_exists():
                if mostrar:
                    self.frame_loader_historial.place(relx=0.5, rely=0.5, anchor="center")
                    self.pb_loader_historial.start(12)
                else:
                    self.pb_loader_historial.stop()
                    self.frame_loader_historial.place_forget()
        except tk.TclError:
            pass  # Widget destruido durante el cierre

    def _mostrar_placeholder_graficos(self, texto: str, cargando: bool = False):
        try:
            # Check if app is shutting down
            if hasattr(self, 'root') and self.root and not self.root.winfo_exists():
                return

            if hasattr(self, 'lbl_placeholder_graficos'):
                # Verify widget still exists
                if self.lbl_placeholder_graficos.winfo_exists():
                    self.lbl_placeholder_graficos.config(text=texto)
                    self.lbl_placeholder_graficos.pack(fill="both", expand=True, pady=(100, 10))
                    if hasattr(self, 'pb_loader_graficos') and self.pb_loader_graficos.winfo_exists():
                        if cargando:
                            self.pb_loader_graficos.pack(pady=(0, 100))
                            self.pb_loader_graficos.start(12)
                        else:
                            self.pb_loader_graficos.stop()
                            self.pb_loader_graficos.pack_forget()
        except tk.TclError:
            # Widget was destroyed, safely ignore
            pass
        except Exception as e:
            # Registrar sin interrumpir: esto es solo el indicador de carga.
            # El logger ya maneja sus propios errores internamente, así que no
            # hace falta envolverlo en otro try.
            from vim_logger import get_logger
            get_logger("ventas").warning(f"Error mostrando placeholder gráficos: {e}")


    def _set_panel_activo(self, slug: str):
        self._panel_activo = slug

    def _on_historial_scroll(self, lo, hi):
        if hasattr(self, '_historial_scrollbar'):
            self._historial_scrollbar.set(lo, hi)
        try:
            if not self._historial_cargando and float(hi) >= 0.99:
                if len(self.ventas_actuales) < self._total_ventas:
                    self.cargar_mas_ventas()
        except Exception as e:
            # Si esto falla, el historial deja de cargar más ventas al llegar
            # abajo y parece que no hubiera más registros.
            from vim_logger import get_logger
            get_logger("ventas.historial").warning(
                f"Error cargando más ventas al hacer scroll: {e}"
            )

    def aplicar_resalte_boton(self, boton, color):
        boton.bind("<Enter>", lambda e: boton.config(bg="#343a40"))
        boton.bind("<Leave>", lambda e: boton.config(bg=color))

    def aplicar_resalte_fecha(self, boton):
        boton.bind("<Enter>", lambda e, b=boton: b.config(bg="#d1d5db") if getattr(self, 'btn_filtro_activo', None) != b else b.config(bg="#138496"))
        boton.bind("<Leave>", lambda e, b=boton: b.config(bg="#e9ecef", fg="#333") if getattr(self, 'btn_filtro_activo', None) != b else b.config(bg="#17a2b8", fg="white"))

    def aplicar_resalte_focus(self, widget):
        if hasattr(widget, "bind"):
            widget.bind("<FocusIn>", lambda e: widget.config(bg="#f8f9fa" if isinstance(widget, tk.Entry) else COLOR_BLANCO))
            widget.bind("<FocusOut>", lambda e: widget.config(bg="white"))

    def formatear_moneda(self, valor):
        try:
            return f"$ {float(valor):,.0f}".replace(",", ".")
        except Exception:
            return "$ 0"

    def _a_iso(self, fecha_dd_mm_aaaa: str) -> str:
        """Convierte DD-MM-AAAA → AAAA-MM-DD para consultas SQL.
        Si la fecha ya está en ISO o hay error, la devuelve tal cual."""
        try:
            partes = fecha_dd_mm_aaaa.strip().split("-")
            if len(partes) == 3 and len(partes[2]) == 4:
                # Formato DD-MM-AAAA
                return f"{partes[2]}-{partes[1]}-{partes[0]}"
        except Exception:
            pass
        return fecha_dd_mm_aaaa  # ya estaba en ISO o no tiene formato reconocido

    def set_fecha_rápida(self, tipo):
        if getattr(self, 'btn_filtro_activo', None):
            self.btn_filtro_activo.config(bg="#e9ecef", fg="#333")
            self.btn_filtro_activo = None

        desde, hasta = rango_rapido(tipo, date.today())
        btn = getattr(self, f'btn_{tipo}', None)

        if btn:
            btn.config(bg="#17a2b8", fg="white")
            self.btn_filtro_activo = btn
            
        self.entry_fecha_desde.set_date(desde)
        self.entry_fecha_hasta.set_date(hasta)
        self.buscar()

    def limpiar_filtros(self):
        if getattr(self, 'btn_filtro_activo', None):
            self.btn_filtro_activo.config(bg="#e9ecef", fg="#333")
            self.btn_filtro_activo = None

        # Usar la fecha mínima real de la BD en lugar del hardcode 2024-01-01
        self.entry_fecha_desde.set_date(self._fecha_minima)
        self.entry_fecha_hasta.set_date(date.today())
        self.entry_folio.delete(0, tk.END)
        self.combo_metodo.current(0)
        self.buscar()

    def exportar_csv_rapido(self):
        """Exporta las ventas actualmente filtradas a CSV con un solo clic."""
        if not self.ventas_actuales and not self._ultimo_filtros:
            messagebox.showwarning("Sin datos", "No hay ventas en la vista actual para exportar.")
            return

        from tkinter import filedialog
        import csv

        resultados_exportar = self.ventas_actuales
        if self._total_ventas and len(self.ventas_actuales) < self._total_ventas:
            resultados_exportar = buscar_ventas_filtradas(
                self._ultimo_filtros.get("fecha_desde", ""),
                self._ultimo_filtros.get("fecha_hasta", ""),
                self._ultimo_filtros.get("metodo_pago", ""),
                self._ultimo_filtros.get("busqueda_folio", ""),
                limit=0,
                offset=0,
            )

        if not resultados_exportar:
            messagebox.showwarning("Sin datos", "No hay ventas en la vista actual para exportar.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            title="Exportar Ventas a CSV",
            initialfile=f"ventas_{date.today().strftime('%Y%m%d')}.csv"
        )
        if not filepath:
            return

        try:
            with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                writer = csv.writer(f, delimiter=";")
                # Metadata
                writer.writerow(["# VIM ERP — Reporte de Ventas"])
                writer.writerow([f"# Generado: {date.today().strftime('%d/%m/%Y')}"])
                writer.writerow([f"# Total registros: {len(resultados_exportar)}"])
                writer.writerow([])
                writer.writerow(["Folio", "Fecha", "Hora", "Usuario", "Metodo Pago",
                                  "N° Items", "Subtotal", "Descuento", "Total", "Vuelto", "Estado"])
                for v in resultados_exportar:
                    fecha_raw = str(v.get("fecha", ""))
                    try:
                        partes = fecha_raw.replace("T", " ").split(" ")
                        y, m, d = partes[0].split("-")
                        fecha_fmt = f"{d}/{m}/{y}"
                        hora_fmt = partes[1][:5] if len(partes) > 1 else ""
                    except Exception:
                        fecha_fmt = fecha_raw[:10]
                        hora_fmt = ""
                    writer.writerow([
                        v.get("folio", ""),
                        fecha_fmt,
                        hora_fmt,
                        v.get("usuario_nombre") or "Admin",
                        str(v.get("metodo_pago", "")).capitalize(),
                        v.get("cantidad_items", ""),
                        v.get("subtotal", v.get("total", 0)),
                        v.get("descuento_total", 0),
                        v.get("total", 0),
                        v.get("vuelto", 0),
                        str(v.get("estado", "")).capitalize(),
                    ])
            self._avisar_reporte_listo(filepath)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def _ejecutar_super_reporte(self, desde_iso=None, hasta_iso=None, desde_dmy="", hasta_dmy=""):  # noqa: C901
        from tkinter import filedialog, messagebox

        # Verificar openpyxl
        try:
            import openpyxl
        except ImportError:
            messagebox.showerror(
                "Librería faltante",
                "Se necesita instalar openpyxl para generar Excel.\n\n"
                "Ejecuta en consola:\n  pip install openpyxl"
            )
            return

        from datetime import datetime as dt
        fecha_hoy = dt.now().strftime("%Y%m%d_%H%M")
        filepath = filedialog.asksaveasfilename(
            title="Guardar Reporte Maestro Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"VIM_ERP_Reporte_Maestro_{fecha_hoy}.xlsx"
        )
        if not filepath:
            return

        try:
            from database.connection import session_db
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter

            meta_fecha = dt.now().strftime("%d/%m/%Y %H:%M")

            # Filtro de período para las hojas de Ventas y Caja.
            # Antes el Reporte Maestro ignoraba las fechas elegidas en el modal.
            filtro_periodo = ""
            params_periodo = []
            texto_periodo = "Histórico completo"
            if desde_iso and hasta_iso:
                filtro_periodo = " AND fecha >= ? AND fecha < date(?, '+1 day')"
                params_periodo = [desde_iso, hasta_iso]
                texto_periodo = f"Período: {desde_dmy} al {hasta_dmy}"

            # ── Estilos globales ──────────────────────────────────────────────
            COLOR_AZUL   = "002060"
            COLOR_CIAN   = "17A2B8"
            COLOR_VERDE  = "28A745"
            COLOR_ROJO   = "DC3545"
            COLOR_GRIS_C = "EDF2F7"   # fila par (clara)
            COLOR_GRIS_H = "D6E4F0"   # encabezado suave

            f_titulo  = Font(name="Calibri", bold=True, size=14, color="FFFFFF")
            f_cab     = Font(name="Calibri", bold=True, size=10, color="FFFFFF")
            f_normal  = Font(name="Calibri", size=10)
            f_meta    = Font(name="Calibri", italic=True, size=9, color="666666")
            al_centro = Alignment(horizontal="center", vertical="center", wrap_text=True)
            al_izq    = Alignment(horizontal="left",   vertical="center")
            al_der    = Alignment(horizontal="right",  vertical="center")
            borde_fino = Border(
                bottom=Side(style="thin", color="CCCCCC"),
                right=Side(style="thin",  color="CCCCCC")
            )

            def estilo_hoja(ws, color_titulo, titulo_texto, subtitulo_texto, n_cols):
                """Aplica encabezado visual a una hoja."""
                letra_fin = get_column_letter(n_cols)
                ws.merge_cells(f"A1:{letra_fin}1")
                ws["A1"] = titulo_texto
                ws["A1"].font = f_titulo
                ws["A1"].fill = PatternFill("solid", fgColor=color_titulo)
                ws["A1"].alignment = al_centro
                ws.row_dimensions[1].height = 32

                ws.merge_cells(f"A2:{letra_fin}2")
                ws["A2"] = subtitulo_texto
                ws["A2"].font = f_meta
                ws["A2"].alignment = al_centro
                ws.row_dimensions[2].height = 18

            def escribir_cabeceras(ws, fila, cabeceras, color_fondo):
                for ci, texto in enumerate(cabeceras, 1):
                    c = ws.cell(fila, ci, texto)
                    c.font = f_cab
                    c.fill = PatternFill("solid", fgColor=color_fondo)
                    c.alignment = al_centro
                    c.border = borde_fino

            def escribir_fila(ws, fila_idx, valores, es_par):
                bg = COLOR_GRIS_C if es_par else "FFFFFF"
                for ci, val in enumerate(valores, 1):
                    c = ws.cell(fila_idx, ci, val)
                    c.font = f_normal
                    c.fill = PatternFill("solid", fgColor=bg)
                    c.border = borde_fino
                    if isinstance(val, (int, float)):
                        c.alignment = al_der
                        c.number_format = "#,##0"
                    else:
                        c.alignment = al_izq

            def autoajustar(ws):
                for col in ws.columns:
                    max_len = 0
                    col_letra = get_column_letter(col[0].column)
                    for cell in col:
                        try:
                            max_len = max(max_len, len(str(cell.value or "")))
                        except Exception:
                            pass
                    ws.column_dimensions[col_letra].width = min(max_len + 4, 40)

            wb = openpyxl.Workbook()

            with session_db(dict_rows=True) as conn:

                # ════════════════════════════════════════════════════════════
                # HOJA 1 — Ventas Detalladas
                # ════════════════════════════════════════════════════════════
                ws1 = wb.active
                ws1.title = "Ventas Detalladas"
                estilo_hoja(ws1, COLOR_AZUL,
                    "📊  VIM ERP — Ventas Detalladas",
                    f"Generado: {meta_fecha}  |  {texto_periodo}",
                    14)

                cabs1 = ["Folio", "Fecha", "Hora", "Usuario", "Método Pago", "Estado",
                         "Producto", "Tipo Ítem", "Tipo Venta", "Cantidad",
                         "Precio Unitario", "Dto. Línea", "Total Línea", "Total Venta"]
                keys1 = ["folio", "fecha", "hora", "usuario", "metodo_pago", "estado",
                         "nombre_producto", "tipo_item", "tipo_venta", "cantidad",
                         "precio_unitario", "descuento_linea", "total_linea", "total_venta"]
                escribir_cabeceras(ws1, 3, cabs1, COLOR_AZUL)

                filtro_v = filtro_periodo.replace("fecha", "v.fecha") if filtro_periodo else ""
                datos_ventas = conn.execute(f"""
                    SELECT v.folio,
                           strftime('%d/%m/%Y', v.fecha) as fecha,
                           strftime('%H:%M', v.fecha) as hora,
                           COALESCE(u.nombre, 'Admin') as usuario,
                           v.metodo_pago, v.estado,
                           dv.nombre_producto,
                           COALESCE(p.tipo_item, 'producto') as tipo_item,
                           dv.tipo_venta, dv.cantidad, dv.precio_unitario,
                           COALESCE(dv.descuento_linea, 0) as descuento_linea,
                           dv.total_linea, v.total as total_venta
                    FROM ventas v
                    JOIN detalle_ventas dv ON v.id = dv.venta_id
                    LEFT JOIN usuarios u ON v.usuario_id = u.id
                    LEFT JOIN productos p ON dv.producto_id = p.id
                    WHERE v.estado != 'anulada'{filtro_v}
                    ORDER BY v.fecha DESC
                """, params_periodo).fetchall()
                tot_lineas = 0.0
                for i, row in enumerate(datos_ventas):
                    fila_vals = [row.get(k, "") for k in keys1]
                    # convertir numéricos
                    for ni in (9, 10, 11, 12, 13):
                        try: fila_vals[ni] = float(fila_vals[ni])
                        except Exception: pass
                    try: tot_lineas += float(row.get("total_linea") or 0)
                    except Exception: pass
                    escribir_fila(ws1, 4 + i, fila_vals, i % 2 == 0)
                # Fila de totales al pie
                fila_tot = 4 + len(datos_ventas)
                escribir_fila(ws1, fila_tot,
                              ["TOTAL", "", "", "", "", "", "", "", "", "", "", "", tot_lineas, ""],
                              False)
                for ci in range(1, 15):
                    ws1.cell(fila_tot, ci).font = f_cab
                    ws1.cell(fila_tot, ci).fill = PatternFill("solid", fgColor=COLOR_AZUL)
                autoajustar(ws1)
                ws1.freeze_panes = "A4"

                # ════════════════════════════════════════════════════════════
                # HOJA 2 — Movimientos de Caja
                # ════════════════════════════════════════════════════════════
                ws2 = wb.create_sheet("Movimientos de Caja")
                estilo_hoja(ws2, COLOR_CIAN,
                    "💰  VIM ERP — Movimientos de Caja",
                    f"Generado: {meta_fecha}  |  {texto_periodo}",
                    5)
                cabs2 = ["Fecha", "Hora", "Tipo Movimiento", "Monto", "Descripción"]
                keys2 = ["fecha", "hora", "tipo", "monto", "descripcion"]
                escribir_cabeceras(ws2, 3, cabs2, COLOR_CIAN)

                datos_caja = conn.execute(f"""
                    SELECT strftime('%d/%m/%Y', fecha) as fecha,
                           strftime('%H:%M', fecha) as hora,
                           tipo, monto,
                           COALESCE(descripcion, 'Sin descripcion') as descripcion
                    FROM movimientos_caja
                    WHERE 1=1{filtro_periodo}
                    ORDER BY fecha DESC
                """, params_periodo).fetchall()
                for i, row in enumerate(datos_caja):
                    vals = [row.get(k, "") for k in keys2]
                    try: vals[3] = float(vals[3])
                    except Exception: pass
                    escribir_fila(ws2, 4 + i, vals, i % 2 == 0)
                autoajustar(ws2)
                ws2.freeze_panes = "A4"

                # ════════════════════════════════════════════════════════════
                # HOJA 3 — Inventario / Valoración
                # (solo si el negocio maneja stock: un negocio de servicios
                #  generaría una hoja entera con ceros)
                # ════════════════════════════════════════════════════════════
                from database.negocio import maneja_inventario
                if maneja_inventario():
                    ws3 = wb.create_sheet("Inventario")
                    estilo_hoja(ws3, COLOR_VERDE,
                        "🏷️  VIM ERP — Inventario y Valoración",
                        f"Generado: {meta_fecha}  |  Productos activos con valoración",
                        11)
                    cabs3 = ["Nombre", "Categoría", "Tipo Ítem", "Tipo Venta", "Stock",
                             "Stock Mín.", "Precio Compra", "Precio Venta (por kg si es a granel)",
                             "Valor Costo Total", "Valor Venta Total", "Proveedor"]
                    keys3 = ["nombre", "categoria", "tipo_item", "tipo_venta", "stock",
                             "stock_minimo", "precio_compra", "precio_venta",
                             "valor_costo_total", "valor_venta_total", "proveedor"]
                    escribir_cabeceras(ws3, 3, cabs3, COLOR_VERDE)

                    datos_inv = conn.execute("""
                        SELECT p.nombre,
                               COALESCE(c.nombre, 'Sin categoria') as categoria,
                               COALESCE(p.tipo_item, 'producto') as tipo_item,
                               p.tipo_venta, p.stock, p.stock_minimo,
                               p.precio_compra,
                               -- Los productos a granel se venden por kilo: su
                               -- precio_venta es 0 y el valor salía en $0.
                               CASE WHEN p.tipo_venta = 'peso' THEN p.precio_por_kilo
                                    ELSE p.precio_venta END as precio_venta,
                               CASE WHEN COALESCE(p.tipo_item,'producto') != 'servicio'
                                    THEN ROUND(p.stock * p.precio_compra, 0) ELSE 0 END as valor_costo_total,
                               CASE WHEN COALESCE(p.tipo_item,'producto') = 'servicio' THEN 0
                                    WHEN p.tipo_venta = 'peso' THEN ROUND(p.stock * p.precio_por_kilo, 0)
                                    ELSE ROUND(p.stock * p.precio_venta, 0) END as valor_venta_total,
                               COALESCE(prov.nombre, 'Sin proveedor') as proveedor
                        FROM productos p
                        LEFT JOIN categorias c ON p.categoria_id = c.id
                        LEFT JOIN proveedores prov ON p.proveedor_id = prov.id
                        WHERE p.activo = 1 ORDER BY p.nombre ASC
                    """).fetchall()
                    for i, row in enumerate(datos_inv):
                        vals = [row.get(k, "") for k in keys3]
                        for ni in (4, 5, 6, 7, 8, 9):
                            try: vals[ni] = float(vals[ni])
                            except Exception: pass
                        escribir_fila(ws3, 4 + i, vals, i % 2 == 0)
                    autoajustar(ws3)
                    ws3.freeze_panes = "A4"

                # ════════════════════════════════════════════════════════════
                # HOJA 4 — Cuentas por Pagar
                # ════════════════════════════════════════════════════════════
                ws4 = wb.create_sheet("Cuentas por Pagar")
                estilo_hoja(ws4, COLOR_ROJO,
                    "📋  VIM ERP — Cuentas por Pagar",
                    f"Generado: {meta_fecha}  |  Compras con saldo pendiente",
                    7)
                cabs4 = ["Proveedor", "RUT", "N° Documento", "Fecha",
                         "Total", "Saldo Pendiente", "Estado Pago"]
                keys4 = ["proveedor", "rut", "numero_documento", "fecha",
                         "total", "saldo_pendiente", "estado_pago"]
                escribir_cabeceras(ws4, 3, cabs4, COLOR_ROJO)

                datos_deudas = conn.execute("""
                    SELECT pr.nombre as proveedor, pr.rut, c.numero_documento,
                           strftime('%d/%m/%Y', c.fecha) as fecha,
                           c.total, c.saldo_pendiente, c.estado_pago
                    FROM compras c JOIN proveedores pr ON c.proveedor_id = pr.id
                    WHERE c.estado_pago != 'pagado' ORDER BY c.fecha ASC
                """).fetchall()
                for i, row in enumerate(datos_deudas):
                    vals = [row.get(k, "") for k in keys4]
                    for ni in (4, 5):
                        try: vals[ni] = float(vals[ni])
                        except Exception: pass
                    escribir_fila(ws4, 4 + i, vals, i % 2 == 0)
                autoajustar(ws4)
                ws4.freeze_panes = "A4"

                # ════════════════════════════════════════════════════════════
                # HOJA 5 — Nómina / Personal
                # ════════════════════════════════════════════════════════════
                ws5 = wb.create_sheet("Nómina Personal")
                estilo_hoja(ws5, "6F42C1",
                    "👥  VIM ERP — Nómina del Personal",
                    f"Generado: {meta_fecha}  |  Empleados activos",
                    6)
                cabs5 = ["RUT", "Nombre", "Cargo", "Sueldo Base",
                         "Liquidaciones Pagadas", "Último Pago"]
                keys5 = ["rut", "nombre", "cargo", "sueldo_base",
                         "liquidaciones_pagadas", "ultimo_pago"]
                escribir_cabeceras(ws5, 3, cabs5, "6F42C1")

                datos_personal = conn.execute("""
                    SELECT e.rut, e.nombre, e.cargo, e.sueldo_base,
                           COUNT(l.id) as liquidaciones_pagadas,
                           MAX(strftime('%d/%m/%Y', l.fecha_pago)) as ultimo_pago
                    FROM empleados e LEFT JOIN liquidaciones_sueldo l ON e.id = l.empleado_id
                    WHERE e.activo = 1 GROUP BY e.id ORDER BY e.nombre ASC
                """).fetchall()
                for i, row in enumerate(datos_personal):
                    vals = [row.get(k, "") for k in keys5]
                    try: vals[3] = float(vals[3])
                    except Exception: pass
                    try: vals[4] = int(vals[4])
                    except Exception: pass
                    escribir_fila(ws5, 4 + i, vals, i % 2 == 0)
                autoajustar(ws5)
                ws5.freeze_panes = "A4"

            wb.save(filepath)

            # La hoja de Inventario sólo existe si el negocio maneja stock:
            # listarla igual haría dudar de que el reporte esté completo.
            hojas = ["📊 Ventas Detalladas", "💰 Movimientos de Caja"]
            if maneja_inventario():
                hojas.append("🏷️ Inventario")
            hojas += ["📋 Cuentas por Pagar", "👥 Nómina Personal"]

            self._avisar_reporte_listo(
                filepath,
                detalle=f"{len(hojas)} hojas:\n  " + "\n  ".join(hojas)
            )
        except Exception as e:
            import traceback
            messagebox.showerror("Error", f"Error al generar el reporte:\n{e}\n\n{traceback.format_exc()[:300]}")

    def _guardar_csv_desde_dicts(self, carpeta, nombre_archivo, columnas, datos):
        import csv
        import os
        filepath = os.path.join(carpeta, nombre_archivo)
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=';')
            writer.writerow(columnas)
            for row in datos:
                writer.writerow([row[col] if isinstance(row, dict) else row for col in columnas])

    def _guardar_csv_individual(self, carpeta, nombre_archivo, columnas, datos):
        import csv
        import os
        filepath = os.path.join(carpeta, nombre_archivo)
        with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f, delimiter=';') 
            writer.writerow(columnas)
            writer.writerows(datos)

    def buscar(self, event=None):
        if self._busqueda_en_progreso:
            return

        # get_date() retorna objeto date de Python → sin ambigüedad de formato
        d_desde, d_hasta = self.entry_fecha_desde.get_date(), self.entry_fecha_hasta.get_date()
        if d_desde > d_hasta:
            # Antes buscaba igual y mostraba "sin resultados" sin decir por qué
            messagebox.showwarning("Fechas", "La fecha 'Desde' no puede ser posterior a 'Hasta'.",
                                   parent=self.root)
            return
        desde = d_desde.strftime("%Y-%m-%d")
        hasta = d_hasta.strftime("%Y-%m-%d")
        folio = self.entry_folio.get().strip()
        metodo = self.combo_metodo.get()

        self._ultimo_filtros = {
            "fecha_desde": desde,
            "fecha_hasta": hasta,
            "metodo_pago": metodo,
            "busqueda_folio": folio,
        }
        self._pagina_actual = 0
        self._total_ventas = 0

        self._mostrar_loader_historial(True)
        self._mostrar_placeholder_graficos("Cargando análisis de ventas...", cargando=True)

        self.tree_historial.delete(*self.tree_historial.get_children())
        self.tree_ranking_prod.delete(*self.tree_ranking_prod.get_children())
        self.tree_ranking_cat.delete(*self.tree_ranking_cat.get_children())
        self.tree_horas.delete(*self.tree_horas.get_children())

        self._busqueda_en_progreso = True
        thread = threading.Thread(
            target=self._buscar_worker,
            args=(desde, hasta, metodo, folio),
            daemon=True
        )
        thread.start()

    def _buscar_worker(self, desde, hasta, metodo, folio):
        try:
            resultados = buscar_ventas_filtradas(desde, hasta, metodo, folio, limit=self._tamanio_pagina, offset=0)
            total = contar_ventas_filtradas(desde, hasta, metodo, folio)
            reportes = obtener_reportes_avanzados(desde, hasta, metodo, folio)
            kpis = obtener_kpis_ventas(desde, hasta, metodo, folio)
            # Mismo largo de período, justo antes, para comparar en los KPIs
            kpis_prev = None
            try:
                from .graficos import periodo_anterior
                previo = periodo_anterior(desde, hasta)
                if previo:
                    kpis_prev = obtener_kpis_ventas(previo[0], previo[1], metodo, folio)
            except Exception:
                get_logger("ventas_reportes").warning("No se pudo calcular el período anterior", exc_info=True)
            self.kpis_previos = kpis_prev
            # Finanzas TAMBIÉN en el worker: antes se consultaban en el hilo
            # de la UI (refrescar_finanzas) y congelaban la pantalla.
            finanzas = self._obtener_finanzas_worker(desde, hasta)
            self.root.after(0, lambda: self._terminar_busqueda(resultados, total, kpis, reportes, finanzas))
        except Exception:
            get_logger("ventas_reportes").exception("Falló la búsqueda de ventas")
            self.root.after(0, lambda: self._terminar_busqueda([], 0, {}, {"top_productos": [], "top_categorias": [], "ventas_por_hora": []}, None))

    @staticmethod
    def _obtener_finanzas_worker(desde, hasta):
        """Consulta P&L, IVA y balance (para ejecutar en un hilo, NO en la UI)."""
        try:
            from database.reportes_financieros import obtener_reporte_iva
            return {
                "pnl": obtener_estado_resultados(desde, hasta),
                "iva": obtener_reporte_iva(desde, hasta),
                "bal": obtener_resumen_balance_general(),
            }
        except Exception as e:
            from vim_logger import get_logger
            get_logger("ventas.finanzas").error(f"Error consultando finanzas: {e}")
            return None

    def _terminar_busqueda(self, resultados, total, kpis, reportes, finanzas=None):
        self._busqueda_en_progreso = False
        self._total_ventas = total
        self.ventas_actuales = resultados
        self._pagina_actual = 0

        self._mostrar_loader_historial(False)

        self.kpis_actuales = kpis
        if hasattr(self, 'lbl_kpi_ventas_total'):
            self.lbl_kpi_ventas_total.config(text=self.formatear_moneda(kpis.get("ventas_totales", 0)))
            self.lbl_kpi_ventas_efectivo.config(text=self.formatear_moneda(kpis.get("total_efectivo", 0)))
            self.lbl_kpi_ventas_tarjeta.config(text=self.formatear_moneda(kpis.get("total_tarjeta", 0)))
            self.lbl_kpi_ventas_transferencia.config(text=self.formatear_moneda(kpis.get("total_transferencia", 0)))

        self.tree_historial.delete(*self.tree_historial.get_children())

        if not resultados:
            self.tree_historial.insert("", "end", values=("—", "—", "—", "Sin resultados", "—", "—", "—"), tags=("par",))
            self._mostrar_placeholder_graficos("No se encontraron ventas para esos filtros.")
        else:
            for i, v in enumerate(resultados):
                folio_v = v.get("folio", "")
                fecha = str(v.get("fecha", ""))
                try:
                    p = fecha.replace("T", " ").split(" ")
                    y, m, d = p[0].split("-")
                    hora = p[1][:5] if len(p) > 1 else ""
                    fecha_str = f"{d}-{m}-{y} {hora}"
                except Exception:
                    fecha_str = fecha[:16]

                usuario = str(v.get("usuario_nombre") or "Administrador")
                metod_pago = str(v.get("metodo_pago", "")).capitalize()
                total = self.formatear_moneda(v.get("total", 0))
                vuelto = self.formatear_moneda(v.get("vuelto", 0))
                estado = str(v.get("estado", "")).capitalize()
                tag = "impar" if i % 2 != 0 else "par"

                self.tree_historial.insert("", "end", values=(folio_v, fecha_str, usuario, metod_pago, total, vuelto, estado), tags=(tag,))

        self.reportes_actuales = reportes
        for i, p in enumerate(reportes["top_productos"]):
            tag = "impar" if i % 2 != 0 else "par"
            self.tree_ranking_prod.insert("", "end", values=(i+1, p["nombre_producto"], p["cantidad_total"], self.formatear_moneda(p["ingresos_totales"]), self.formatear_moneda(p.get("utilidad_total", 0))), tags=(tag,))
        for i, c in enumerate(reportes["top_categorias"]):
            tag = "impar" if i % 2 != 0 else "par"
            self.tree_ranking_cat.insert("", "end", values=(i+1, c["categoria"], c["cantidad_total"], self.formatear_moneda(c["ingresos_totales"]), self.formatear_moneda(c.get("utilidad_total", 0))), tags=(tag,))
        for i, h in enumerate(reportes["ventas_por_hora"]):
            tag = "impar" if i % 2 != 0 else "par"
            self.tree_horas.insert("", "end", values=(h["hora"], h["tickets"], self.formatear_moneda(h["ingresos_totales"])), tags=(tag,))

        # Aplicar finanzas ya consultadas por el worker (solo actualiza labels)
        if finanzas:
            self._aplicar_finanzas(finanzas["pnl"], finanzas["iva"], finanzas["bal"])
        if self._panel_activo == "visual":
            self.renderizar_dashboard_graficos()
        else:
            self._mostrar_placeholder_graficos("Abre la pestaña Análisis Visual para ver los gráficos.")

    def cargar_mas_ventas(self):
        if self._busqueda_en_progreso:
            return
        if len(self.ventas_actuales) >= self._total_ventas:
            return

        self._mostrar_loader_historial(True)
        self._busqueda_en_progreso = True
        offset = (self._pagina_actual + 1) * self._tamanio_pagina
        thread = threading.Thread(
            target=self._cargar_mas_ventas_worker,
            args=(offset,),
            daemon=True
        )
        thread.start()

    def _cargar_mas_ventas_worker(self, offset):
        try:
            nuevos = buscar_ventas_filtradas(
                self._ultimo_filtros.get("fecha_desde", ""),
                self._ultimo_filtros.get("fecha_hasta", ""),
                self._ultimo_filtros.get("metodo_pago", ""),
                self._ultimo_filtros.get("busqueda_folio", ""),
                limit=self._tamanio_pagina,
                offset=offset,
            )
            self.root.after(0, lambda: self._append_ventas(nuevos))
        except Exception:
            get_logger("ventas_reportes").exception("Falló la carga de más ventas")
            self.root.after(0, lambda: self._append_ventas([]))

    def _append_ventas(self, nuevos):
        self._busqueda_en_progreso = False
        self._mostrar_loader_historial(False)

        if not nuevos:
            return

        start = len(self.ventas_actuales)
        self.ventas_actuales.extend(nuevos)

        for i, v in enumerate(nuevos, start=start):
            folio_v = v.get("folio", "")
            fecha = str(v.get("fecha", ""))
            try:
                p = fecha.replace("T", " ").split(" ")
                y, m, d = p[0].split("-")
                hora = p[1][:5] if len(p) > 1 else ""
                fecha_str = f"{d}-{m}-{y} {hora}"
            except Exception:
                fecha_str = fecha[:16]

            usuario = str(v.get("usuario_nombre") or "Administrador")
            metod_pago = str(v.get("metodo_pago", "")).capitalize()
            total = self.formatear_moneda(v.get("total", 0))
            vuelto = self.formatear_moneda(v.get("vuelto", 0))
            estado = str(v.get("estado", "")).capitalize()
            tag = "impar" if i % 2 != 0 else "par"
            self.tree_historial.insert("", "end", values=(folio_v, fecha_str, usuario, metod_pago, total, vuelto, estado), tags=(tag,))

        self._pagina_actual += 1

    def renderizar_dashboard_graficos(self):
        """Inicia la generación de gráficos con diferimiento para no bloquear la UI."""
        try:
            if not hasattr(self, 'reportes_actuales') or not self.reportes_actuales:
                return
            
            # Check if root still exists
            if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
                return

            # Mostrar placeholder mientras se generan los gráficos
            self._mostrar_placeholder_graficos("Generando gráficos...", cargando=True)
            
            # Diferir la generación de gráficos 50ms para permitir que la UI se actualice
            self.root.after(50, self._generar_graficos_deferred)
        except tk.TclError:
            pass  # Widget destroyed
        except Exception as e:
            get_logger("ventas_reportes").exception("Falló la preparación de gráficos de ventas")  # Silently ignore errors

    def _generar_graficos_deferred(self):
        """Genera el dashboard visual (KPIs + gráficos) tras un diferimiento."""
        try:
            if not hasattr(self, 'root') or not self.root or not self.root.winfo_exists():
                return
            if not hasattr(self, 'reportes_actuales') or not self.reportes_actuales:
                return
        except Exception:
            return

        reportes = self.reportes_actuales
        kpis = self.kpis_actuales
        kpis_prev = getattr(self, "kpis_previos", None) or {}

        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            from . import graficos as g
        except ImportError:
            self._mostrar_placeholder_graficos("Error: No se pudo cargar matplotlib")
            return

        try:
            # Limpiar solo los contenidos generados (conservar placeholder y barra)
            protegidos = {getattr(self, 'lbl_placeholder_graficos', None),
                          getattr(self, 'pb_loader_graficos', None)}
            for widget in self.frame_graficos.winfo_children():
                if widget in protegidos:
                    widget.pack_forget()
                else:
                    widget.destroy()
            try:
                self.pb_loader_graficos.stop()
            except Exception:
                pass

            C_BG = "#f8fafc"; C_CARD = "#ffffff"; C_BORDE = "#e2e8f0"
            C_TXT = g.TINTA; C_MUTED = "#64748b"
            C_SUBE = "#006300"; C_BAJA = "#d03b3b"
            # Figuras al mismo DPI que la escala de la app: nítidas en
            # pantallas con zoom de Windows (125 %, 150 %).
            DPI = max(72, round(96 * escalar(100) / 100))

            main = tk.Frame(self.frame_graficos, bg=C_BG)
            main.pack(fill="both", expand=True, padx=escalar(16), pady=escalar(14))

            # ── Encabezado ────────────────────────────────────────
            desde = self._ultimo_filtros.get("fecha_desde", "")
            hasta = self._ultimo_filtros.get("fecha_hasta", "")
            head = tk.Frame(main, bg=C_BG)
            head.pack(fill="x", pady=(0, escalar(10)))
            tk.Label(head, text="Análisis Visual del Período",
                     font=("Segoe UI", escalar_fuente(15), "bold"), bg=C_BG, fg=C_TXT).pack(side="left")
            if desde and hasta:
                tk.Label(head, text=f"  {self._formatear_fecha_display(desde)}  →  {self._formatear_fecha_display(hasta)}",
                         font=("Segoe UI", escalar_fuente(10)), bg=C_BG, fg=C_MUTED).pack(side="left", pady=(4, 0))

            # ── KPIs con comparación contra el período anterior ──
            total_ingresos = float(kpis.get("ventas_totales", 0))
            transacciones = int(kpis.get("cantidad_ventas", 0))
            ticket_prom = float(kpis.get("ticket_promedio", 0))
            utilidad = float(kpis.get("utilidad_total", 0))
            margen = (utilidad / total_ingresos * 100) if total_ingresos > 0 else 0

            fila_kpi = tk.Frame(main, bg=C_BG)
            fila_kpi.pack(fill="x", pady=(0, escalar(10)))
            for i in range(4):
                fila_kpi.grid_columnconfigure(i, weight=1, uniform="kpi")

            def _kpi_card(col, titulo, valor, cambio=None, detalle=""):
                card = tk.Frame(fila_kpi, bg=C_CARD, highlightbackground=C_BORDE, highlightthickness=1)
                card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else escalar(8), 0))
                tk.Label(card, text=titulo, font=("Segoe UI", escalar_fuente(9)),
                         bg=C_CARD, fg=C_MUTED, anchor="w").pack(fill="x", padx=escalar(14), pady=(escalar(12), 0))
                tk.Label(card, text=valor, font=("Segoe UI", escalar_fuente(19), "bold"),
                         bg=C_CARD, fg=C_TXT, anchor="w").pack(fill="x", padx=escalar(14))
                if cambio is not None:
                    # Flecha + texto: el color nunca es la única señal
                    sube = cambio >= 0
                    texto = f"{'▲' if sube else '▼'} {abs(cambio):.0f}% vs período anterior"
                    color = C_SUBE if sube else C_BAJA
                else:
                    texto, color = detalle or "Sin datos del período anterior", C_MUTED
                tk.Label(card, text=texto, font=("Segoe UI", escalar_fuente(8)),
                         bg=C_CARD, fg=color, anchor="w").pack(fill="x", padx=escalar(14), pady=(0, escalar(12)))

            _kpi_card(0, "Ingresos", self.formatear_moneda(total_ingresos),
                      g.variacion(total_ingresos, kpis_prev.get("ventas_totales")))
            _kpi_card(1, "Ventas realizadas", g.miles(transacciones),
                      g.variacion(transacciones, kpis_prev.get("cantidad_ventas")))
            _kpi_card(2, "Ticket promedio", self.formatear_moneda(ticket_prom),
                      g.variacion(ticket_prom, kpis_prev.get("ticket_promedio")))
            _kpi_card(3, "Utilidad bruta", self.formatear_moneda(utilidad),
                      detalle=f"Margen {margen:.1f}% de lo vendido".replace(".", ","))

            # ── Tarjetas de gráfico ───────────────────────────────
            def _grafico_card(parent, col, titulo, subtitulo=""):
                card = tk.Frame(parent, bg=C_CARD, highlightbackground=C_BORDE, highlightthickness=1)
                card.grid(row=0, column=col, sticky="nsew", padx=(0 if col == 0 else escalar(8), 0))
                tk.Label(card, text=titulo, font=("Segoe UI", escalar_fuente(10), "bold"),
                         bg=C_CARD, fg=C_TXT, anchor="w").pack(fill="x", padx=escalar(14), pady=(escalar(12), 0))
                if subtitulo:
                    tk.Label(card, text=subtitulo, font=("Segoe UI", escalar_fuente(8)),
                             bg=C_CARD, fg=C_MUTED, anchor="w").pack(fill="x", padx=escalar(14))
                return card

            def _montar_figura(fig, card):
                fig.set_dpi(DPI)
                canvas = FigureCanvasTkAgg(fig, master=card)
                canvas.draw()
                # La figura se ajusta sola al ancho de la tarjeta
                canvas.get_tk_widget().pack(fill="both", expand=True, padx=escalar(8), pady=escalar(8))

            def _fila(pesos):
                fila = tk.Frame(main, bg=C_BG)
                fila.pack(fill="x", pady=(0, escalar(10)))
                for i, w in enumerate(pesos):
                    fila.grid_columnconfigure(i, weight=w, uniform=str(id(fila)))
                return fila

            # Fila 1: ventas por día (solo si el período tiene más de un día)
            if desde and hasta and desde != hasta:
                fila = _fila([1])
                card = _grafico_card(fila, 0, "Ventas por día",
                                     "Ingresos de cada día. Los días sin barra no tuvieron ventas.")
                _montar_figura(g.grafico_ventas_por_dia(reportes.get("ventas_por_dia", []), desde, hasta), card)

            # Fila 2: horas + medios de pago
            fila = _fila([3, 2])
            card = _grafico_card(fila, 0, "¿A qué hora se vende más?", "Cantidad de ventas por hora; en azul fuerte, la hora pico.")
            _montar_figura(g.grafico_ventas_por_hora(reportes.get("ventas_por_hora", [])), card)
            card = _grafico_card(fila, 1, "Medios de pago", "Cuánto entró por cada medio.")
            _montar_figura(g.grafico_medios_de_pago(kpis.get("total_efectivo", 0), kpis.get("total_tarjeta", 0),
                                                    kpis.get("total_transferencia", 0)), card)

            # Fila 3: rankings por ingresos
            fila = _fila([1, 1])
            prods = reportes.get("top_productos", [])
            card = _grafico_card(fila, 0, "Productos que más venden", "Top 5 por ingresos.")
            _montar_figura(g.grafico_ranking([p["nombre_producto"] for p in prods],
                                             [p["ingresos_totales"] for p in prods]), card)
            cats = reportes.get("top_categorias", [])
            card = _grafico_card(fila, 1, "Categorías que más venden", "Top 5 por ingresos.")
            _montar_figura(g.grafico_ranking([c["categoria"] for c in cats],
                                             [c["ingresos_totales"] for c in cats]), card)

        except Exception as e:
            get_logger("ui.graficos").error(f"Error al generar gráficos: {e}", exc_info=True)
            self._mostrar_placeholder_graficos("Error al generar los gráficos. Intenta de nuevo.")

    def refrescar_finanzas(self, desde, hasta):
        """Compatibilidad: consulta en un hilo y aplica en la UI al terminar."""
        def _worker():
            finanzas = self._obtener_finanzas_worker(desde, hasta)
            if finanzas:
                self.root.after(0, lambda: self._aplicar_finanzas(
                    finanzas["pnl"], finanzas["iva"], finanzas["bal"]))
        threading.Thread(target=_worker, daemon=True).start()

    def _adaptar_pnl_al_tipo_negocio(self, pnl):
        """Renombra y oculta filas del P&L según sea negocio de productos o servicios."""
        try:
            etiqueta_ing = pnl.get("etiqueta_ingresos", "Ventas Netas")
            self.lbl_pnl_ingresos._lbl_texto.config(text=f"(+) {etiqueta_ing}")

            etiqueta_costo = pnl.get("etiqueta_costo", "Costos Netos")
            self.lbl_pnl_costos._lbl_texto.config(text=f"(-) {etiqueta_costo}")

            # Mostrar/ocultar preservando el orden original de las filas:
            # pack(before=...) reinserta en la posición correcta.
            mostrar_costo = pnl.get("mostrar_costo", True)
            fila_costo = self.lbl_pnl_costos._fila
            if mostrar_costo:
                if not fila_costo.winfo_ismapped():
                    fila_costo.pack(fill="x", pady=2, before=self._sep_pnl)
            else:
                fila_costo.pack_forget()

            mostrar_bruta = pnl.get("mostrar_margen_bruto", True)
            fila_bruta = self.lbl_pnl_utilidad_bruta._fila
            if mostrar_bruta:
                if not fila_bruta.winfo_ismapped():
                    fila_bruta.pack(fill="x", pady=2, before=self._lbl_titulo_gastos)
                if not self._sep_pnl.winfo_ismapped():
                    self._sep_pnl.pack(fill="x", pady=6, before=fila_bruta)
            else:
                fila_bruta.pack_forget()
                self._sep_pnl.pack_forget()
        except Exception as e:
            from vim_logger import get_logger
            get_logger("ventas.finanzas").warning(f"No se pudo adaptar el P&L: {e}")

    def _aplicar_finanzas(self, pnl, rep_iva, bal):
        """Solo actualiza widgets — los datos ya vienen consultados."""
        try:
            # --- Adaptar etiquetas y filas al tipo de negocio ---
            # En un negocio de servicios no hay costo de inventario. Si además
            # no se carga costo directo, las líneas de costo y utilidad bruta
            # no aportan nada (serían "0" y "100%") y se ocultan.
            self._adaptar_pnl_al_tipo_negocio(pnl)

            # --- Actualizar Estado de Resultados (P&L) ---
            ingresos = pnl.get('ingresos_ventas', 0)
            self.lbl_pnl_ingresos.config(text=self.formatear_moneda(ingresos))
            if hasattr(self, 'lbl_pnl_ingresos_pct'):
                self.lbl_pnl_ingresos_pct.config(text="(100%)" if ingresos > 0 else "")

            self.lbl_pnl_iva_debito.config(text=self.formatear_moneda(rep_iva.get('iva_debito', 0)))
            self.lbl_pnl_iva_credito.config(text=self.formatear_moneda(rep_iva.get('iva_credito', 0)))
            
            iva_pagar = rep_iva.get('iva_a_pagar', 0)
            self.lbl_pnl_impuestos.config(text=self.formatear_moneda(iva_pagar))
            if hasattr(self, 'lbl_pnl_impuestos_pct'):
                iva_pct = (iva_pagar / ingresos * 100) if ingresos > 0 else 0
                self.lbl_pnl_impuestos_pct.config(text=f"({iva_pct:.1f}%)" if ingresos > 0 else "")
            
            costos = pnl.get('costo_ventas', 0)
            self.lbl_pnl_costos.config(text=self.formatear_moneda(costos))
            
            mg_bruto = pnl.get('margen_bruto_pct', 0)
            # Costos como % de ingresos
            costos_pct = (costos / ingresos * 100) if ingresos > 0 else 0
            self.lbl_pnl_costos_pct.config(text=f"({costos_pct:.1f}%)" if ingresos > 0 else "") 
            
            self.lbl_pnl_utilidad_bruta.config(text=self.formatear_moneda(pnl.get('utilidad_bruta', 0)))
            self.lbl_pnl_utilidad_bruta_pct.config(text=f"({mg_bruto:.1f}%)" if ingresos > 0 else "")

            # Detalle de Gastos
            for widget in self.frame_gastos_pnl.winfo_children():
                widget.destroy()
            
            gastos = pnl.get('gastos_detallados', [])
            if not gastos:
                tk.Label(self.frame_gastos_pnl, text="Sin gastos registrados", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(9), "italic")).pack(anchor="w")
            else:
                for g in gastos:
                    f_g = tk.Frame(self.frame_gastos_pnl, bg=COLOR_BLANCO)
                    f_g.pack(fill="x", pady=2)
                    tk.Label(f_g, text=f"• {g['cuenta']}", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10))).pack(side="left")
                    tk.Label(f_g, text=self.formatear_moneda(g['total']), bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(10), "bold")).pack(side="right")
                    
                    pct_g = g.get('porcentaje', 0)
                    tk.Label(f_g, text=f"({pct_g:.1f}%)", bg=COLOR_BLANCO, font=("Segoe UI", escalar_fuente(8)), fg="#dc3545").pack(side="right", padx=10)

            utilidad_neta = pnl.get('utilidad_neta', 0)
            self.lbl_pnl_utilidad_neta.config(text=self.formatear_moneda(utilidad_neta))
            self.lbl_pnl_utilidad_neta.config(fg="#28a745" if utilidad_neta >= 0 else COLOR_PELIGRO)
            
            # --- 4. Actualizar Balance General ---
            # Un negocio de servicios no tiene inventario que valorizar:
            # la línea se oculta en vez de mostrar un $0 que hace dudar.
            if bal.get("mostrar_inventario", True):
                self.lbl_bal_inventario.config(text=f"Inventario: {self.formatear_moneda(bal['activos'].get('inventario', 0))}")
                if not self.lbl_bal_inventario.winfo_ismapped():
                    self.lbl_bal_inventario.pack(anchor="w", pady=(4, 0), before=self.lbl_bal_efectivo)
            else:
                self.lbl_bal_inventario.pack_forget()
            self.lbl_bal_efectivo.config(text=f"Efectivo: {self.formatear_moneda(bal['activos'].get('efectivo', 0))}")
            self.lbl_bal_cuentas_pagar.config(text=f"Deudas: {self.formatear_moneda(bal['pasivos'].get('cuentas_por_pagar', 0))}")
            
            patrimonio = bal.get('patrimonio_estimado', 0)
            self.lbl_bal_patrimonio.config(text=self.formatear_moneda(patrimonio))
            self.lbl_bal_patrimonio.config(fg=COLOR_PRIMARIO if patrimonio >= 0 else COLOR_PELIGRO)
            
        except Exception as e:
            from vim_logger import get_logger
            get_logger("ventas.finanzas").error(f"Error aplicando finanzas a la UI: {e}", exc_info=True)

    def ver_detalle_venta(self):
        item_id = self.tree_historial.focus()
        if not item_id:
            return

        idx = self.tree_historial.index(item_id)
        if idx >= len(self.ventas_actuales) or not self.ventas_actuales:
            return

        venta = self.ventas_actuales[idx]
        venta_id = venta["id"]
        
        venta_completa = obtener_venta_por_id(venta_id)
        if not venta_completa:
            messagebox.showerror("Error", "No se encontró el detalle de la venta.")
            return

        self._abrir_modal_detalle(venta_completa)

    def _abrir_modal_detalle(self, venta: Dict[str, Any]):
        top = tk.Toplevel(self.root)
        top.withdraw()
        top.title(f"Detalle de Venta - {venta['folio']}")
        top.configure(bg=COLOR_BLANCO)
        aplicar_barra_windows_azul(top)
        top.grab_set()
        
        centrar_ventana_mejorado(top, escalar(700), escalar(550), relativo_a=self.root)

        # Cabecera Modal
        header = tk.Frame(top, bg=COLOR_PRIMARIO, height=escalar(50))
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(header, text=f"Detalle de Venta: {venta['folio']}", font=("Segoe UI", escalar_fuente(12), "bold"), fg=COLOR_BLANCO, bg=COLOR_PRIMARIO).pack(side="left", padx=15, pady=10)

        body = preparar_modal_scrollable(top, bg=COLOR_BLANCO)

        # Info Cabecera Venta
        info = tk.Frame(body, bg=COLOR_BLANCO)
        info.pack(fill="x", padx=15, pady=15)
        
        tk.Label(info, text=f"Fecha: {self._formatear_fecha_display(str(venta['fecha']))}", font=("Segoe UI", escalar_fuente(10)), bg=COLOR_BLANCO).grid(row=0, column=0, sticky="w", pady=2)
        tk.Label(info, text=f"Método Pago: {venta['metodo_pago'].capitalize()}", font=("Segoe UI", escalar_fuente(10)), bg=COLOR_BLANCO).grid(row=0, column=1, sticky="w", padx=40, pady=2)
        tk.Label(info, text=f"Vendedor: {venta.get('usuario_nombre') or 'Admin'}", font=("Segoe UI", escalar_fuente(10)), bg=COLOR_BLANCO).grid(row=1, column=0, sticky="w", pady=2)
        tk.Label(info, text=f"Total: {self.formatear_moneda(venta['total'])}", font=("Segoe UI", escalar_fuente(10), "bold"), bg=COLOR_BLANCO).grid(row=1, column=1, sticky="w", padx=40, pady=2)

        # Detalles Grid
        tabla_frame = tk.Frame(body, bg=COLOR_BLANCO)
        tabla_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        columnas = ("Producto", "Cant", "P.Unitario", "Descuento", "Subtotal")
        tree_dt = ttk.Treeview(tabla_frame, columns=columnas, show="headings", height=10)

        for col in columnas:
            tree_dt.heading(col, text=col)

        tree_dt.column("Producto", width=escalar(300), anchor="w")
        tree_dt.column("Cant", width=escalar(70), anchor="center")
        tree_dt.column("P.Unitario", width=escalar(100), anchor="e")
        tree_dt.column("Descuento", width=escalar(100), anchor="e")
        tree_dt.column("Subtotal", width=escalar(100), anchor="e")

        vsb = ttk.Scrollbar(tabla_frame, orient="vertical", command=tree_dt.yview)
        tree_dt.configure(yscrollcommand=vsb.set)
        tree_dt.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        detalles = venta.get("detalles", [])
        for i, d in enumerate(detalles):
            prod = str(d.get("nombre_producto", ""))
            cant = str(d.get("cantidad", ""))
            pu = self.formatear_moneda(d.get("precio_unitario", 0))
            desc = self.formatear_moneda(d.get("descuento_linea", 0))
            sbt = self.formatear_moneda(d.get("total_linea", 0))

            tag = "impar" if i % 2 != 0 else "par"
            tree_dt.insert("", "end", values=(prod, cant, pu, desc, sbt), tags=(tag,))

        tree_dt.tag_configure("impar", background="#edf2f7")
        tree_dt.tag_configure("par", background="#ffffff")

        # Boton Cerrar
        btn = tk.Button(body, text="Cerrar", bg="#6c757d", fg=COLOR_BLANCO, relief="flat", font=("Segoe UI", escalar_fuente(10)), cursor="hand2", command=top.destroy)
        btn.pack(pady=(0, 15))
        self.aplicar_resalte_boton(btn, "#6c757d")

    def _formatear_fecha_display(self, fecha_str: str) -> str:
        """Convierte fecha ISO (AAAA-MM-DD HH:MM) a formato legible DD-MM-AAAA HH:MM."""
        try:
            p = fecha_str.replace("T", " ").split(" ")
            y, m, d = p[0].split("-")
            hora = p[1][:5] if len(p) > 1 else ""
            return f"{d}-{m}-{y} {hora}".strip()
        except Exception:
            return fecha_str[:16]

    def _avisar_reporte_listo(self, filepath, detalle=""):
        """Avisa dónde quedó el reporte y ofrece abrirlo.

        Antes sólo se mostraba la ruta en un cartel: había que ir a buscar el
        archivo a mano en el explorador.
        """
        import os
        import subprocess

        nombre = os.path.basename(filepath)
        carpeta = os.path.dirname(filepath)

        abrir = messagebox.askyesno(
            "Reporte generado",
            f"Archivo:\n{nombre}\n\n"
            f"Guardado en:\n{carpeta}\n\n"
            + (f"{detalle}\n\n" if detalle else "")
            + "¿Querés abrirlo ahora?",
            parent=self.root
        )
        if not abrir:
            return

        try:
            os.startfile(filepath)
        except Exception as e:
            from vim_logger import get_logger
            get_logger("ventas.exportacion").warning(
                f"No se pudo abrir el reporte '{filepath}': {e}"
            )
            try:
                subprocess.Popen(["explorer", "/select,", os.path.normpath(filepath)])
            except Exception:
                messagebox.showinfo(
                    "Reporte generado",
                    f"No se pudo abrir automáticamente.\n\nEstá acá:\n{filepath}",
                    parent=self.root
                )

    def abrir_modal_exportacion(self):
        top = tk.Toplevel(self.root)
        top.withdraw()
        top.title("Centro de Descargas")
        top.configure(bg=COLOR_BLANCO)
        # Ajustable: con pantallas chicas o escalado alto, el tamaño fijo
        # dejaba el contenido recortado y sin forma de agrandarlo.
        top.resizable(True, True)
        aplicar_barra_windows_azul(top)
        top.grab_set()

        centrar_ventana_mejorado(top, escalar(720), escalar(700), relativo_a=self.root)

        # El mínimo nunca puede superar lo que realmente entró en pantalla:
        # centrar_ventana_mejorado recorta al área útil del monitor, y un
        # minsize mayor dejaría parte de la ventana fuera de la vista.
        top.update_idletasks()
        top.minsize(min(escalar(560), top.winfo_width()),
                    min(escalar(420), top.winfo_height()))

        # ── Header ───────────────────────────────────────────
        header = tk.Frame(top, bg=COLOR_PRIMARIO)
        header.pack(side="top", fill="x")
        tk.Label(
            header, text="📥  Centro de Descargas",
            font=("Segoe UI", escalar_fuente(14), "bold"), fg=COLOR_BLANCO, bg=COLOR_PRIMARIO
        ).pack(anchor="w", padx=escalar(16), pady=(escalar(12), 0))
        tk.Label(
            header, text="Elige el período y el reporte",
            font=("Segoe UI", escalar_fuente(9)), fg="#a9c0dd", bg=COLOR_PRIMARIO
        ).pack(anchor="w", padx=escalar(16), pady=(0, escalar(12)))

        # ── Pie reservado ANTES del cuerpo ───────────────────
        # El botón se empaquetaba al final, después de un área con
        # expand=True: Tk ya había repartido todo el espacio y el botón
        # quedaba aplastado fuera de la vista. Reservando el pie primero,
        # el cuerpo desplazable ocupa sólo lo que queda en el medio.
        pie = tk.Frame(top, bg=COLOR_BLANCO)
        pie.pack(side="bottom", fill="x")

        body = preparar_modal_scrollable(top, bg=COLOR_BLANCO)
        cuerpo = tk.Frame(body, bg=COLOR_BLANCO, padx=escalar(14), pady=escalar(12))
        cuerpo.pack(fill="both", expand=True)

        # Las descripciones se recortaban con un ancho fijo. Se recalculan
        # cada vez que cambia el tamaño de la ventana.
        etiquetas_ajustables = []

        def _reajustar_textos(event):
            # El texto arranca a escalar(16) del borde de la tarjeta; se deja
            # margen para eso y para la barra de desplazamiento.
            ancho = max(escalar(200), event.width - escalar(60))
            for lbl in etiquetas_ajustables:
                try:
                    lbl.config(wraplength=ancho)
                except Exception:
                    pass  # SILENCIO DELIBERADO: el widget pudo destruirse

        cuerpo.bind("<Configure>", _reajustar_textos)

        # ── Período ──────────────────────────────────────────
        tk.Label(cuerpo, text="PERÍODO", font=("Segoe UI", escalar_fuente(8), "bold"),
                 bg=COLOR_BLANCO, fg="#94a3b8").pack(anchor="w")

        f_fechas = tk.Frame(cuerpo, bg="#f8fafc", highlightbackground="#e2e8f0", highlightthickness=1)
        f_fechas.pack(fill="x", pady=(escalar(6), escalar(16)))
        f_cal = tk.Frame(f_fechas, bg="#f8fafc")
        f_cal.pack(pady=escalar(12))

        from tkcalendar import DateEntry
        cal_style = {
            'background': COLOR_PRIMARIO, 'foreground': 'white',
            'headersbackground': COLOR_PRIMARIO, 'headersforeground': 'white',
            'date_pattern': 'dd-mm-yyyy', 'width': 12,
            'font': ("Segoe UI", escalar_fuente(10)),
        }
        _min = self._fecha_minima

        tk.Label(f_cal, text="Desde", bg="#f8fafc", fg="#475569",
                 font=("Segoe UI", escalar_fuente(9), "bold")).grid(row=0, column=0, padx=(escalar(10), escalar(6)))
        cal_desde = DateEntry(f_cal, mindate=_min, maxdate=date.today(), **cal_style)
        cal_desde.grid(row=0, column=1, padx=(0, escalar(18)))
        cal_desde.set_date(self.entry_fecha_desde.get_date())

        tk.Label(f_cal, text="Hasta", bg="#f8fafc", fg="#475569",
                 font=("Segoe UI", escalar_fuente(9), "bold")).grid(row=0, column=2, padx=(0, escalar(6)))
        cal_hasta = DateEntry(f_cal, mindate=_min, maxdate=date.today(), **cal_style)
        cal_hasta.grid(row=0, column=3, padx=(0, escalar(10)))
        cal_hasta.set_date(self.entry_fecha_hasta.get_date())

        # ── Atajos de período ────────────────────────────────
        # El panel principal ya los tiene; acá había que elegir dos fechas a
        # mano cada vez, incluso para lo más común ("lo de hoy", "este mes").
        # Los atajos se reparten en dos filas para que entren aunque la
        # ventana esté angosta o la pantalla tenga escalado alto.
        f_atajos = tk.Frame(f_fechas, bg="#f8fafc")
        f_atajos.pack(pady=(0, escalar(10)))
        fila_atajos_1 = tk.Frame(f_atajos, bg="#f8fafc")
        fila_atajos_1.pack()
        fila_atajos_2 = tk.Frame(f_atajos, bg="#f8fafc")
        fila_atajos_2.pack(pady=(escalar(4), 0))

        def _aplicar_rango(desde, hasta):
            cal_desde.set_date(max(desde, _min) if _min else desde)
            cal_hasta.set_date(hasta)
            _actualizar_vista_previa()

        def _rango(clave):
            return rango_de_atajo(clave, date.today(), _min)

        for indice, (etiqueta, clave) in enumerate((
                ("Hoy", "hoy"), ("Ayer", "ayer"), ("Esta semana", "semana"),
                ("Este mes", "mes"), ("Mes pasado", "mes_pasado"), ("Todo", "todo"))):
            contenedor_atajo = fila_atajos_1 if indice < 3 else fila_atajos_2
            b = tk.Button(
                contenedor_atajo, text=etiqueta, bg=COLOR_BLANCO, fg="#334155",
                font=("Segoe UI", escalar_fuente(8)), relief="flat", cursor="hand2",
                highlightbackground="#cbd5e1", highlightthickness=1, padx=escalar(8),
                command=lambda c=clave: _aplicar_rango(*_rango(c))
            )
            b.pack(side="left", padx=escalar(3))

        # ── Vista previa de lo que se va a exportar ──────────
        # Antes había que elegir el archivo y recién ahí aparecía
        # "no hay datos en este rango".
        lbl_previa = tk.Label(
            cuerpo, text="", font=("Segoe UI", escalar_fuente(9)),
            bg=COLOR_BLANCO, fg="#475569", anchor="w"
        )
        lbl_previa.pack(fill="x", pady=(0, escalar(12)))

        def _actualizar_vista_previa(*_):
            from database.ventas import resumen_ventas_periodo
            try:
                d, h = cal_desde.get_date(), cal_hasta.get_date()
            except Exception:
                return
            if d > h:
                lbl_previa.config(text="⚠  La fecha 'Desde' es posterior a 'Hasta'.",
                                  fg=COLOR_PELIGRO)
                return

            datos = resumen_ventas_periodo(d.strftime("%Y-%m-%d"), h.strftime("%Y-%m-%d"))
            if datos["cantidad"] == 0:
                lbl_previa.config(text="⚠  No hay ventas en este período.", fg="#b45309")
            else:
                lbl_previa.config(
                    text=f"✓  {datos['cantidad']} venta(s) · {self.formatear_moneda(datos['total'])} en el período",
                    fg="#15803d"
                )

        cal_desde.bind("<<DateEntrySelected>>", _actualizar_vista_previa)
        cal_hasta.bind("<<DateEntrySelected>>", _actualizar_vista_previa)
        _actualizar_vista_previa()

        # ── Tarjetas de tipo de reporte (seleccionables) ─────
        tk.Label(cuerpo, text="TIPO DE REPORTE", font=("Segoe UI", escalar_fuente(8), "bold"),
                 bg=COLOR_BLANCO, fg="#94a3b8").pack(anchor="w")

        opcion_var = tk.IntVar(value=1)
        tarjetas = []

        C_SEL_BG = "#eff6ff"; C_SEL_BD = "#2563eb"
        C_NRM_BG = COLOR_BLANCO; C_NRM_BD = "#e2e8f0"

        def _refrescar_seleccion():
            for val, card, widgets, radio in tarjetas:
                activo = (opcion_var.get() == val)
                bg = C_SEL_BG if activo else C_NRM_BG
                card.config(bg=bg, highlightbackground=C_SEL_BD if activo else C_NRM_BD,
                            highlightthickness=2 if activo else 1)
                for w in widgets:
                    w.config(bg=bg)
                radio.config(bg=bg, activebackground=bg)

        def _tarjeta_opcion(valor, icono, titulo, badge, badge_bg, descripcion):
            card = tk.Frame(cuerpo, bg=C_NRM_BG, highlightbackground=C_NRM_BD,
                            highlightthickness=1, cursor="hand2")
            card.pack(fill="x", pady=(escalar(6), 0))

            fila = tk.Frame(card, bg=C_NRM_BG, cursor="hand2")
            fila.pack(fill="x", padx=escalar(12), pady=(escalar(10), 0))

            radio = tk.Radiobutton(fila, variable=opcion_var, value=valor, bg=C_NRM_BG,
                                   activebackground=C_NRM_BG, cursor="hand2",
                                   command=_refrescar_seleccion)
            radio.pack(side="left")

            lbl_icono = tk.Label(fila, text=icono, font=("Segoe UI", escalar_fuente(14)),
                                 bg=C_NRM_BG, cursor="hand2")
            lbl_icono.pack(side="left", padx=(0, escalar(8)))

            lbl_titulo = tk.Label(fila, text=titulo, font=("Segoe UI", escalar_fuente(10), "bold"),
                                  bg=C_NRM_BG, fg="#1e293b", cursor="hand2")
            lbl_titulo.pack(side="left")

            lbl_badge = tk.Label(fila, text=f" {badge} ", font=("Segoe UI", escalar_fuente(7), "bold"),
                                 bg=badge_bg, fg="white")
            lbl_badge.pack(side="right")

            lbl_desc = tk.Label(card, text=descripcion, font=("Segoe UI", escalar_fuente(8)),
                                bg=C_NRM_BG, fg="#64748b", justify="left",
                                wraplength=escalar(440), cursor="hand2")
            lbl_desc.pack(anchor="w", padx=escalar(16), pady=(escalar(2), escalar(10)))
            etiquetas_ajustables.append(lbl_desc)

            widgets = [fila, lbl_icono, lbl_titulo, lbl_desc]

            def _elegir(_e=None, v=valor):
                opcion_var.set(v)
                _refrescar_seleccion()
            for w in (card, fila, lbl_icono, lbl_titulo, lbl_desc):
                w.bind("<Button-1>", _elegir)

            tarjetas.append((valor, card, widgets, radio))

        _tarjeta_opcion(
            1, "📄", "Ventas del Período", "CSV", "#16a34a",
            "Listado simple de ventas. Se abre en Excel."
        )
        _tarjeta_opcion(
            2, "📊", "Ventas + Resultados", "EXCEL", "#2563eb",
            "Las ventas más la utilidad y los gastos."
        )
        # En modo servicios no se genera la hoja de Inventario (ver
        # _ejecutar_super_reporte), así que el reporte trae una hoja menos.
        from database.negocio import maneja_inventario
        _hojas = 5 if maneja_inventario() else 4
        _tarjeta_opcion(
            3, "🗂", "Reporte Maestro", f"{_hojas} HOJAS", "#7c3aed",
            "Todo el negocio: ventas, caja, deudas y personal."
        )

        _refrescar_seleccion()

        # ── Botón de acción ──────────────────────────────────
        def confirmar():
            opt = opcion_var.get()
            d_date, h_date = cal_desde.get_date(), cal_hasta.get_date()
            if d_date > h_date:
                messagebox.showwarning("Período inválido",
                                       "La fecha 'Desde' no puede ser posterior a 'Hasta'.",
                                       parent=top)
                return
            d_dmy = d_date.strftime("%d-%m-%Y")
            h_dmy = h_date.strftime("%d-%m-%Y")
            d_iso = d_date.strftime("%Y-%m-%d")
            h_iso = h_date.strftime("%Y-%m-%d")

            top.destroy()
            if opt == 1:
                self._ejecutar_exportacion_especifica(d_dmy, h_dmy, d_iso, h_iso, 2)
            elif opt == 2:
                self._ejecutar_exportacion_especifica(d_dmy, h_dmy, d_iso, h_iso, 1)
            else:
                self._ejecutar_super_reporte(d_iso, h_iso, d_dmy, h_dmy)

        btn_exp = tk.Button(
            pie, text="📥  DESCARGAR REPORTE", bg=COLOR_PRIMARIO, fg="white",
            font=("Segoe UI", escalar_fuente(11), "bold"), relief="flat", cursor="hand2",
            command=confirmar, bd=0
        )
        btn_exp.pack(fill="x", padx=escalar(24), pady=(escalar(8), escalar(20)), ipady=escalar(10))
        btn_exp.bind("<Enter>", lambda e: btn_exp.config(bg="#1e3a8a"))
        btn_exp.bind("<Leave>", lambda e: btn_exp.config(bg=COLOR_PRIMARIO))
        top.bind("<Return>", lambda e: confirmar())
        top.bind("<Escape>", lambda e: top.destroy())

    def _ejecutar_exportacion_especifica(self, desde_dmy, hasta_dmy, desde_iso, hasta_iso, opcion):
        # 1. Obtener datos con la fecha seleccionada independientemente de la vista
        from database.ventas import buscar_ventas_filtradas
        ventas_exportar = buscar_ventas_filtradas(desde_iso, hasta_iso, "Todos", "")
        
        if not ventas_exportar:
            messagebox.showwarning("Exportar", "No hay datos de ventas en este rango de fechas.")
            return

        from tkinter import filedialog
        
        if opcion == 1:
            # Excel con openpyxl
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx")],
                title="Guardar Reporte Excel Completo",
                initialfile=f"VIM_Ventas_PnL_{desde_iso.replace('-','')}_{hasta_iso.replace('-','')}.xlsx"
            )
            if not filepath: return

            try:
                self._exportar_excel_completo(filepath, ventas_exportar, desde_dmy, hasta_dmy, desde_iso, hasta_iso)
            except ImportError:
                messagebox.showerror("Error", "La librería openpyxl no está instalada. No se puede generar el Excel completo.")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo generar el Excel:\n{e}")
                
        elif opcion == 2:
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv", filetypes=[("CSV files", "*.csv")],
                title="Guardar Reporte de Ventas CSV",
                initialfile=f"ventas_{desde_iso.replace('-','')}_{hasta_iso.replace('-','')}.csv"
            )
            if not filepath: return

            import csv
            from datetime import datetime as dt
            try:
                # N° de ítems reales por venta (antes se usaba una clave
                # inexistente y la columna salía siempre vacía)
                items_por_venta = {}
                try:
                    from database.connection import session_db
                    with session_db() as conn:
                        for vid, n in conn.execute(
                            "SELECT venta_id, SUM(cantidad) FROM detalle_ventas GROUP BY venta_id"
                        ).fetchall():
                            # Mostrar entero cuando no hay decimales (2.0 → 2)
                            n = float(n or 0)
                            items_por_venta[vid] = int(n) if n == int(n) else round(n, 2)
                except Exception:
                    pass  # Sin conteo de items el reporte sigue siendo útil

                tot_subtotal = tot_desc = tot_total = 0.0
                with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f, delimiter=";")
                    writer.writerow(["# VIM ERP — Reporte de Ventas"])
                    writer.writerow([f"# Período: {desde_dmy} al {hasta_dmy}"])
                    writer.writerow([f"# Generado: {dt.now().strftime('%d/%m/%Y %H:%M')}"])
                    writer.writerow([f"# Total registros: {len(ventas_exportar)}"])
                    writer.writerow([])
                    writer.writerow(["Folio", "Fecha", "Hora", "Usuario",
                                      "Metodo Pago", "N Items", "Subtotal",
                                      "Descuento", "Total", "Vuelto", "Estado"])
                    for v in ventas_exportar:
                        fecha_raw = str(v.get("fecha", ""))
                        try:
                            partes = fecha_raw.replace("T", " ").split(" ")
                            y, m, d = partes[0].split("-")
                            fecha_fmt = f"{d}/{m}/{y}"
                            hora_fmt = partes[1][:5] if len(partes) > 1 else ""
                        except Exception:
                            fecha_fmt = fecha_raw[:10]; hora_fmt = ""

                        subtotal = float(v.get("subtotal") or v.get("total") or 0)
                        descuento = float(v.get("descuento") or 0)
                        total_v = float(v.get("total") or 0)
                        if str(v.get("estado")) == "completada":
                            tot_subtotal += subtotal
                            tot_desc += descuento
                            tot_total += total_v

                        writer.writerow([
                            v.get("folio", ""),
                            fecha_fmt, hora_fmt,
                            v.get("usuario_nombre") or "Admin",
                            str(v.get("metodo_pago", "")).capitalize(),
                            items_por_venta.get(v.get("id"), ""),
                            round(subtotal),
                            round(descuento),
                            round(total_v),
                            round(float(v.get("vuelto") or 0)),
                            str(v.get("estado", "")).capitalize(),
                        ])
                    # Fila de totales (solo ventas completadas)
                    writer.writerow([])
                    writer.writerow(["TOTALES (completadas)", "", "", "", "", "",
                                      round(tot_subtotal), round(tot_desc), round(tot_total), "", ""])
                self._avisar_reporte_listo(filepath)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo exportar: {e}")

    def _exportar_excel_completo(self, filepath, ventas, desde_dmy, hasta_dmy, desde_iso, hasta_iso):
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
        from database.reportes_financieros import obtener_estado_resultados

        wb = openpyxl.Workbook()

        # HOJA 1: VENTAS
        ws1 = wb.active
        ws1.title = "Ventas Detalladas"

        fuente_header = Font(name="Calibri", bold=True, color="FFFFFF", size=11)
        fill_header = PatternFill("solid", fgColor="002060")
        centrado = Alignment(horizontal="center", vertical="center")

        ws1.merge_cells("A1:G1")
        ws1["A1"] = f"Reporte de Ventas  |  Período: {desde_dmy} al {hasta_dmy}"
        ws1["A1"].font = Font(name="Calibri", bold=True, size=13, color="002060")
        ws1["A1"].alignment = centrado
        ws1.row_dimensions[1].height = 28

        cabeceras = ["Folio", "Fecha", "Usuario", "Método Pago", "Total", "Vuelto", "Estado"]
        ws1.append([])
        ws1.append(cabeceras)
        fila_cab = ws1.max_row
        for col_i, val in enumerate(cabeceras, 1):
            celda = ws1.cell(fila_cab, col_i)
            celda.font = fuente_header
            celda.fill = fill_header
            celda.alignment = centrado

        for i, v in enumerate(ventas):
            fecha_d = self._formatear_fecha_display(str(v.get("fecha", "")))
            fila = [
                v.get("folio", ""), fecha_d, v.get("usuario_nombre") or "Admin",
                str(v.get("metodo_pago", "")).capitalize(), float(v.get("total", 0)),
                float(v.get("vuelto", 0)), str(v.get("estado", "")).capitalize()
            ]
            ws1.append(fila)
            if i % 2 == 0:
                for col_i in range(1, 8):
                    ws1.cell(ws1.max_row, col_i).fill = PatternFill("solid", fgColor="EDF2F7")

        for col in ws1.columns:
            max_len = max((len(str(c.value)) for c in col if c.value), default=10)
            ws1.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 30)

        # HOJA 2: ESTADO DE RESULTADOS
        ws2 = wb.create_sheet("Estado de Resultados Financiero")
        pnl = obtener_estado_resultados(desde_iso, hasta_iso)

        ws2.merge_cells("A1:C1")
        ws2["A1"] = "ESTADO DE RESULTADOS (P&L)"
        ws2["A1"].font = Font(name="Calibri", bold=True, size=14, color="002060")
        ws2["A1"].alignment = centrado
        ws2.row_dimensions[1].height = 30

        ws2.merge_cells("A2:C2")
        ws2["A2"] = f"Período Exportado: {desde_dmy} al {hasta_dmy}"
        ws2["A2"].alignment = centrado
        ws2["A2"].font = Font(name="Calibri", italic=True, size=10, color="666666")

        def add_line(etiq, valor, bold=False, bg=None, txt_col="000000"):
            ws2.append([etiq, "", valor])
            f = ws2.max_row
            ws2.cell(f, 1).font = Font(name="Calibri", bold=bold, size=11, color=txt_col)
            ws2.cell(f, 3).font = Font(name="Calibri", bold=bold, size=11, color=txt_col)
            ws2.cell(f, 3).number_format = "$ #,##0"
            ws2.cell(f, 3).alignment = Alignment(horizontal="right")
            if bg:
                fl = PatternFill("solid", fgColor=bg)
                for ci in range(1, 4): ws2.cell(f, ci).fill = fl

        ws2.append([])
        add_line(f"(+) {pnl.get('etiqueta_ingresos', 'Ventas Netas')}", pnl.get("ingresos_ventas", 0), True, "D6E4F0", "002060")
        add_line("(i) Impuestos (IVA)", pnl.get("recaudacion_impuestos", 0), False, None, "6C757D")

        # En servicios sin costo directo cargado, costo y margen bruto no
        # aportan (serían 0 y 100%): se omiten en vez de ensuciar el reporte.
        if pnl.get("mostrar_costo", True):
            add_line(f"(-) {pnl.get('etiqueta_costo', 'Costo de Ventas (COGS)')}", pnl.get("costo_ventas", 0), False, None, "991B1B")
        if pnl.get("mostrar_margen_bruto", True):
            ws2.append([])
            add_line("(=) UTILIDAD BRUTA", pnl.get("utilidad_bruta", 0), True, "E8F5E9", "166534")
            add_line("    Margen Bruto", f"{pnl.get('margen_bruto_pct', 0):.1f}%", False, None, "28A745")
        ws2.append([])
        ws2.append(["GASTOS OPERATIVOS:"])
        ws2.cell(ws2.max_row, 1).font = Font(name="Calibri", bold=True, size=9, color="666666")
        for g in pnl.get("gastos_detallados", []):
            add_line(f"  • {g['cuenta']}", g["total"], False, None, "552000")
        ws2.append([])
        add_line("(=) UTILIDAD NETA", pnl.get("utilidad_neta", 0), True, "E8F5E9" if pnl.get("utilidad_neta", 0) >= 0 else "FEF2F2", "166534" if pnl.get("utilidad_neta", 0) >= 0 else "991B1B")
        add_line("    Margen Neto", f"{pnl.get('margen_neto_pct', 0):.1f}%", False, None, "28A745")

        # Indicadores complementarios (no forman parte de la utilidad)
        ws2.append([])
        ws2.append(["INDICADORES:"])
        ws2.cell(ws2.max_row, 1).font = Font(name="Calibri", bold=True, size=9, color="666666")
        add_line("  Punto de equilibrio (ventas necesarias)", round(pnl.get("punto_equilibrio", 0) or 0), False, None, "002060")

        otros_ing = pnl.get("otros_ingresos_caja", 0)
        if otros_ing:
            add_line("  Otros ingresos de caja (no operacionales)", otros_ing, False, None, "6C757D")

        ws2.append([])
        ws2.append(["Nota: no se incluyen como gasto las compras de mercadería (se reconocen"])
        ws2.append(["como Costo de Ventas al vender) ni los activos fijos (son inversión)."])
        for fila_nota in (ws2.max_row - 1, ws2.max_row):
            ws2.cell(fila_nota, 1).font = Font(name="Calibri", italic=True, size=8, color="888888")

        ws2.column_dimensions["A"].width = 40
        ws2.column_dimensions["B"].width = 5
        ws2.column_dimensions["C"].width = 25

        wb.save(filepath)
        self._avisar_reporte_listo(
            filepath, detalle="Incluye el historial de ventas y el Estado de Resultados."
        )

    def solicitar_anulacion(self):
        """Solicita confirmación y motivo para anular la venta seleccionada."""
        item_id = self.tree_historial.focus()
        if not item_id:
            messagebox.showwarning("Anulación", "Por favor seleccione una venta de la lista.")
            return

        idx = self.tree_historial.index(item_id)
        if idx >= len(self.ventas_actuales):
            return

        venta = self.ventas_actuales[idx]
        
        if venta["estado"] == "anulada":
            messagebox.showwarning("Anulación", "Esta venta ya está anulada.")
            return

        # --- SEGURIDAD: Control de Acceso ---
        from modulos.seguridad.sesion import Sesion
        from modulos.seguridad.autorizacion_ui import solicitar_autorizacion_admin
        
        if not Sesion.tiene_permiso("supervisor"):
            if not solicitar_autorizacion_admin(self.root, f"Anular venta {venta['folio']}"):
                return
        # -----------------------------------

        confirmar = messagebox.askyesno("Confirmar Anulación", f"¿Está seguro que desea anular la venta {venta['folio']}?\nEsta acción devolverá el stock al inventario.")
        
        if confirmar:
            # Podríamos pedir un motivo, por ahora usaremos uno genérico
            from database.ventas import anular_venta
            
            exito, msj = anular_venta(venta["id"], None, "Anulación desde módulo reportes")
            if exito:
                messagebox.showinfo("Éxito", msj)
                self.buscar()
            else:
                messagebox.showerror("Error", msj)
