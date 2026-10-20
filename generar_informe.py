import os
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# ── Márgenes ──────────────────────────────────────────────────
for section in doc.sections:
    section.top_margin    = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin   = Cm(3)
    section.right_margin  = Cm(2.5)

AZUL   = RGBColor(0x00, 0x2B, 0x5C)
CELESTE= RGBColor(0x17, 0x5E, 0xA6)
GRIS   = RGBColor(0x47, 0x55, 0x69)

def set_font(run, size, bold=False, color=None, italic=False):
    run.bold   = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Segoe UI"
    if color:
        run.font.color.rgb = color

def titulo_doc(texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    set_font(r, 22, bold=True, color=AZUL)

def subtitulo_doc(texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(texto)
    set_font(r, 11, color=GRIS, italic=True)

def h1(texto):
    p = doc.add_paragraph()
    r = p.add_run(texto)
    set_font(r, 15, bold=True, color=AZUL)
    p.paragraph_format.space_before = Pt(18)
    p.paragraph_format.space_after  = Pt(4)

def h2(texto):
    p = doc.add_paragraph()
    r = p.add_run(texto)
    set_font(r, 12, bold=True, color=CELESTE)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after  = Pt(2)

def h3(texto):
    p = doc.add_paragraph()
    r = p.add_run(texto)
    set_font(r, 10, bold=True, color=GRIS)
    p.paragraph_format.space_before = Pt(8)

def cuerpo(texto):
    p = doc.add_paragraph(texto)
    p.paragraph_format.space_after = Pt(4)
    for r in p.runs:
        r.font.name = "Segoe UI"
        r.font.size = Pt(10)

def bullet(texto):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(texto)
    set_font(r, 10)

def nota(texto):
    p = doc.add_paragraph()
    r = p.add_run("📌  " + texto)
    set_font(r, 9, italic=True, color=GRIS)

def separador():
    doc.add_paragraph()

def foto(descripcion):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(f"[ 📷  {descripcion} ]")
    set_font(r, 9, italic=True, color=RGBColor(0x94, 0xA3, 0xB8))
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after  = Pt(10)

def tabla(encabezados, filas):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    hdr = t.rows[0].cells
    for i, h in enumerate(encabezados):
        hdr[i].text = h
        for run in hdr[i].paragraphs[0].runs:
            run.bold = True
            run.font.name = "Segoe UI"
            run.font.size = Pt(9)
            run.font.color.rgb = AZUL
    for fila in filas:
        row = t.add_row().cells
        for i, val in enumerate(fila):
            row[i].text = val
            for run in row[i].paragraphs[0].runs:
                run.font.name = "Segoe UI"
                run.font.size = Pt(9)
    doc.add_paragraph()


def generar_informe(ruta_salida=None):
    """Genera el manual de funcionalidades de VIM ERP como documento Word.

    Llamar esta funcion construye el documento completo y lo guarda.
    Si ruta_salida es None, se guarda en docs/VIM_ERP_Manual.docx.
    
    NOTA: El doc se construye a nivel de modulo para retrocompatibilidad.
    Esta funcion solo guarda el documento ya construido.
    """
    if ruta_salida:
        ruta = ruta_salida
    else:
        docs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
        os.makedirs(docs_dir, exist_ok=True)
        ruta = os.path.join(docs_dir, "VIM_ERP_Manual.docx")

    doc.save(ruta)
    return ruta


# ════════════════════════════════════════════════
# PORTADA
# ════════════════════════════════════════════════
doc.add_paragraph()
doc.add_paragraph()
titulo_doc("VIM ERP")
subtitulo_doc("Manual de Funcionalidades — Guía Completa por Módulo")
doc.add_paragraph()
subtitulo_doc("Versión 1.0  |  Desarrollado por Diego Francisco Bustamante Ríos")
subtitulo_doc("© 2026 VIM ERP — Todos los derechos reservados")
doc.add_page_break()

# ════════════════════════════════════════════════
# ÍNDICE MANUAL
# ════════════════════════════════════════════════
h1("Índice de Contenidos")
indices = [
    "1. Primeros Pasos — Configuración Inicial",
    "2. Módulo: Punto de Venta (POS)",
    "3. Módulo: Productos / Inventario",
    "4. Módulo: Ventas / Reportes",
    "5. Módulo: Administración (Compras y Proveedores)",
    "6. Módulo: Caja",
    "7. Módulo: Usuarios",
    "8. Módulo: Configuración",
    "9. Seguridad y Roles",
    "10. Datos y Almacenamiento",
]
for item in indices:
    bullet(item)
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 1 — PRIMEROS PASOS
# ════════════════════════════════════════════════
h1("1. Primeros Pasos — Configuración Inicial")
cuerpo("Al abrir VIM ERP por primera vez, el sistema solicita usuario y contraseña. El usuario administrador predeterminado es creado automáticamente. Se recomienda seguir los pasos a continuación antes de comenzar a operar.")
foto("Pantalla de Login")

h2("Paso 1 — Configurar la Empresa")
cuerpo("Ingresar a Configuración → Empresa y completar:")
for item in ["Razón Social / Nombre del negocio","RUT de la empresa","Giro comercial","Dirección física","Teléfono y email corporativo","Moneda oficial (ej. CLP)"]:
    bullet(item)
foto("Pantalla Configuración → Empresa")

h2("Paso 2 — Configurar Parámetros Financieros")
cuerpo("Ingresar a Configuración → Finanzas y definir:")
for item in ["IVA estándar (por defecto 19%)","Si los precios incluyen IVA o no","Régimen tributario","Ley de redondeo automático"]:
    bullet(item)
foto("Pantalla Configuración → Finanzas")

h2("Paso 3 — Crear Usuarios")
cuerpo("Ingresar a Usuarios y crear cuentas para los empleados, asignando el rol correspondiente: cajero, supervisor o administrador.")
foto("Pantalla de Usuarios — Nuevo Usuario")

h2("Paso 4 — Ingresar Productos")
cuerpo("Ingresar a Productos y cargar el catálogo de artículos con precios, códigos y stock inicial.")
foto("Pantalla de Productos — Formulario")

h2("Paso 5 — Abrir Caja y Comenzar a Vender")
cuerpo("Ingresar a Caja, definir el monto inicial de efectivo y abrirla. Una vez abierta, se puede acceder al POS para facturar.")
foto("Pantalla Caja — Apertura")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 2 — POS
# ════════════════════════════════════════════════
h1("2. Módulo: Punto de Venta (POS) 🛒")
nota("Requisito: La caja debe estar abierta para acceder al POS.")
foto("Pantalla principal del POS")

h2("2.1 Búsqueda de Productos")
cuerpo("Los productos pueden agregarse al ticket de tres formas:")
bullet("Código de barras: Escribiendo o escaneando el código directamente.")
bullet("Código POS / PLU: Ingresando el código corto numérico.")
bullet("Búsqueda por nombre: El sistema muestra nombre, tipo, precio y stock.")
foto("Panel de búsqueda de productos en POS")

h2("2.2 Gestión del Ticket")
for item in [
    "Agregar productos con cantidad personalizada.",
    "Modificar la cantidad de un ítem ya agregado.",
    "Eliminar un ítem del ticket.",
    "Aplicar descuento por ítem o descuento global al total.",
    "Visualización en tiempo real de subtotal, descuentos e IVA.",
    "Los servicios no generan advertencia de stock insuficiente.",
]:
    bullet(item)
foto("Ticket con productos y descuentos aplicados")

h2("2.3 Medios de Pago")
bullet("Efectivo: El sistema calcula el vuelto automáticamente.")
bullet("Tarjeta de débito / crédito.")
bullet("Transferencia bancaria.")
foto("Pantalla de pago y cálculo de vuelto")

h2("2.4 Cierre de Venta")
cuerpo("Al confirmar el pago, el sistema realiza automáticamente:")
bullet("Descuenta el stock de los productos vendidos (no aplica a servicios).")
bullet("Registra la venta en la base de datos.")
bullet("Registra el movimiento en la caja según el medio de pago.")
bullet("Muestra el ticket de venta.")

h2("2.5 Navegación con Teclado")
cuerpo("El POS está optimizado para uso con teclado, permitiendo operar sin mouse para mayor velocidad en caja.")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 3 — PRODUCTOS
# ════════════════════════════════════════════════
h1("3. Módulo: Productos / Inventario 🏷️")
cuerpo("Permite gestionar el catálogo completo de productos, servicios y combos del negocio.")
foto("Pantalla principal de Productos con tabla de artículos")

h2("3.1 Tabla de Productos")
cuerpo("Muestra todos los artículos registrados con columnas de código, nombre, tipo de ítem, tipo de venta, precios, stock, categoría y proveedor.")

h2("3.2 Crear / Editar Producto")
tabla(
    ["Campo", "Descripción"],
    [
        ["Código de barras", "Código EAN/UPC del producto"],
        ["Código POS / PLU", "Código corto para registro rápido en caja"],
        ["Nombre", "Nombre visible en POS y reportes"],
        ["Descripción", "Información adicional del producto"],
        ["Tipo de ítem", "producto, servicio o combo"],
        ["Tipo de venta", "unidad o peso"],
        ["Precio de compra", "Costo de adquisición (afecta margen)"],
        ["Precio de venta", "Precio al cliente (unidad)"],
        ["Precio por kilo", "Precio al cliente (peso)"],
        ["Stock", "Unidades disponibles actualmente"],
        ["Stock mínimo", "Umbral de alerta de reposición"],
        ["Categoría", "Clasificación del artículo"],
        ["Proveedor", "Proveedor asociado al artículo"],
    ]
)
nota("Si seleccionas el tipo servicio, los campos de stock se deshabilitan automáticamente y se fijan en 0. El servicio puede venderse sin restricción de inventario.")
foto("Formulario con tipo 'servicio' seleccionado")

h2("3.3 Exclusividad de Códigos")
bullet("Si se ingresa un código de barras, el campo POS/PLU queda bloqueado automáticamente.")
bullet("Si se ingresa un código POS/PLU, el campo de código de barras queda bloqueado.")
bullet("Al limpiar un campo, el otro se reactiva.")

h2("3.4 Botones de Acción")
tabla(
    ["Botón", "Función"],
    [
        ["Guardar", "Crea un nuevo producto en el sistema."],
        ["Actualizar", "Guarda cambios sobre el producto seleccionado."],
        ["Nuevo / Limpiar", "Limpia el formulario para ingresar un nuevo artículo."],
        ["Eliminar", "Borra el producto seleccionado (solicita confirmación)."],
        ["Historial", "Muestra movimientos del producto (compras, ventas, ajustes)."],
    ]
)
foto("Historial de movimientos de un producto")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 4 — VENTAS / REPORTES
# ════════════════════════════════════════════════
h1("4. Módulo: Ventas / Reportes 📊")
cuerpo("Centraliza toda la información de ventas e indicadores financieros del negocio.")
foto("Pantalla principal Ventas / Reportes")

h2("4.1 Historial de Ventas")
bullet("Lista todas las ventas con fecha, total, medio de pago y usuario.")
bullet("Filtros por rango de fechas, estado (completada / anulada) y usuario.")
bullet("Detalle completo de ítems al seleccionar una venta.")
bullet("Opción de anular venta (requiere autorización): revierte el stock de productos.")
foto("Historial de ventas con filtros activos")

h2("4.2 Dashboard Financiero")
tabla(
    ["Indicador", "Descripción"],
    [
        ["Ventas del día / mes", "Total facturado en el período seleccionado"],
        ["Costo de ventas", "Suma del costo de los productos vendidos"],
        ["Utilidad bruta", "Ventas menos costo de ventas"],
        ["Margen %", "Porcentaje de rentabilidad del período"],
        ["Ticket promedio", "Valor promedio por transacción"],
        ["N° de transacciones", "Cantidad de ventas en el período"],
    ]
)
foto("Dashboard financiero con KPIs")

h2("4.3 Reportes Financieros")
bullet("Balance General: Activos (inventario, caja), pasivos y patrimonio.")
bullet("Estado de Resultados: Ingresos, costos y utilidad neta.")
bullet("Análisis de liquidez: Ratios financieros clave.")
bullet("Punto de equilibrio: Cálculo automático según costos fijos y margen.")
nota("Los servicios no aparecen en el valor de inventario del balance general, manteniendo la precisión contable.")
foto("Balance general y estado de resultados")

h2("4.4 Productos Más Vendidos")
cuerpo("Ranking de artículos por cantidad vendida y por monto generado, con filtros de período.")
foto("Ranking de productos más vendidos")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 5 — ADMINISTRACIÓN
# ════════════════════════════════════════════════
h1("5. Módulo: Administración (Compras y Proveedores) 🛍️")
foto("Pantalla principal de Administración")

h2("5.1 Gestión de Proveedores")
bullet("Crear, editar y eliminar proveedores.")
bullet("Campos: nombre, RUT, dirección, teléfono, email, contacto.")
bullet("Asociar productos a proveedores para trazabilidad.")
foto("Formulario de registro de proveedor")

h2("5.2 Registro de Compras")
bullet("Seleccionar el proveedor de la compra.")
bullet("Agregar productos con cantidad y precio unitario de compra.")
bullet("El sistema actualiza el stock automáticamente al confirmar.")
bullet("Los servicios no modifican stock al ser comprados (se registran como gasto).")
bullet("Se registra fecha y monto total de la compra.")
foto("Formulario de registro de compra con detalle de ítems")

h2("5.3 Historial de Compras")
bullet("Lista todas las compras con fecha, proveedor, total y estado.")
bullet("Opción de anular compra: revierte el stock de los productos afectados.")
bullet("Vista de detalle con los ítems de cada orden.")
foto("Historial de compras registradas")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 6 — CAJA
# ════════════════════════════════════════════════
h1("6. Módulo: Caja 💰")
cuerpo("Controla el flujo de efectivo diario del negocio.")
foto("Pantalla principal de Caja")

h2("6.1 Apertura de Caja")
bullet("Ingresar el monto inicial (fondo de caja en efectivo).")
bullet("Queda registrado el usuario, la fecha y la hora de apertura.")
nota("Sin caja abierta, el POS no permite operar.")

h2("6.2 Panel de Resumen en Tiempo Real")
tabla(
    ["Dato", "Descripción"],
    [
        ["Estado", "Abierta o Cerrada"],
        ["Usuario", "Quien abrió la sesión de caja"],
        ["Fecha y hora apertura", "Registro del inicio de la jornada"],
        ["Monto inicial", "Fondo base ingresado al abrir"],
        ["Ventas en efectivo", "Total de ventas pagadas en efectivo"],
        ["Ventas con tarjeta", "Total de ventas con tarjeta"],
        ["Ventas por transferencia", "Total de ventas por transferencia"],
        ["Ingresos manuales", "Entradas de dinero adicionales registradas"],
        ["Egresos manuales", "Salidas de dinero registradas"],
        ["Efectivo esperado", "Total calculado de efectivo en caja"],
    ]
)
foto("Resumen de caja abierta con listado de movimientos")

h2("6.3 Movimientos Manuales")
bullet("Ingreso: Registrar entrada de dinero adicional (cambio, depósito, etc.).")
bullet("Egreso: Registrar salida de efectivo (pago a proveedor, gastos, etc.).")
bullet("Cada movimiento requiere un monto y una descripción opcional.")

h2("6.4 Cierre de Caja")
cuerpo("Al cerrar la caja, el sistema realiza un proceso de cuadre en 3 pasos:")
bullet("1. Muestra el resumen completo de operaciones del día.")
bullet("2. Se ingresa el monto contado real (efectivo físico en caja).")
bullet("3. El sistema calcula la diferencia (sobrante o faltante) e informa el resultado.")
nota("Al salir de la aplicación con caja abierta, el sistema ofrece cerrarla automáticamente con el monto esperado.")
foto("Pantalla de cierre de caja con resumen y cuadre")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 7 — USUARIOS
# ════════════════════════════════════════════════
h1("7. Módulo: Usuarios 👨‍💼")
cuerpo("Administra las cuentas de acceso y los permisos de cada empleado.")
foto("Pantalla principal de Usuarios")

h2("7.1 Lista de Usuarios")
cuerpo("Tabla con: ID, nombre de usuario (login), nombre completo, rol asignado, estado (Activo/Inactivo) y fecha del último acceso.")

h2("7.2 Crear Nuevo Usuario")
tabla(
    ["Campo", "Descripción"],
    [
        ["Usuario (Login)", "Nombre con el que inicia sesión en el sistema"],
        ["Nombre Completo", "Nombre para mostrar en registros y reportes"],
        ["Contraseña", "Mínimo 4 caracteres. Se almacena cifrada (hash seguro)"],
        ["Rol", "cajero, supervisor o administrador"],
    ]
)

h2("7.3 Permisos por Módulo")
tabla(
    ["Módulo", "Descripción"],
    [
        ["Punto de Venta (POS)", "Puede facturar en caja"],
        ["Productos", "Puede ver y editar el catálogo"],
        ["Ventas / Reportes", "Puede ver reportes y anular ventas"],
        ["Administración", "Puede gestionar compras y proveedores"],
        ["Caja", "Puede abrir y cerrar caja"],
        ["Gestión de Usuarios", "Puede crear y modificar usuarios"],
        ["Configuración", "Puede acceder a parámetros del sistema"],
        ["Copias de Seguridad", "Puede crear y restaurar backups"],
    ]
)
foto("Panel de permisos por módulo de un usuario")

h2("7.4 Gestión de Cuentas")
bullet("Desactivar usuario: Bloquea el acceso sin eliminar el historial.")
bullet("Reactivar usuario: Restaura el acceso de un usuario desactivado.")
bullet("Eliminar usuario: Borra permanentemente la cuenta (acción irreversible).")
nota("El administrador principal (ID 1) no puede ser desactivado ni eliminado.")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 8 — CONFIGURACIÓN
# ════════════════════════════════════════════════
h1("8. Módulo: Configuración ⚙️")
foto("Pantalla de Configuración con menú lateral")

h2("8.1 Sección: Empresa")
h3("Información comercial")
for item in ["Razón social, RUT, giro comercial","Dirección, teléfono, email","Moneda oficial"]:
    bullet(item)
h3("Diseño del ticket")
bullet("Ancho del papel térmico (58mm u 80mm).")
bullet("Número de copias por defecto.")
bullet("Mostrar/ocultar logo en el ticket.")
bullet("Mostrar/ocultar desglose de IVA.")
bullet("Mensaje de pie de ticket personalizado.")
bullet("Vista previa del ticket en tiempo real.")
foto("Configuración de empresa con vista previa del ticket")

h2("8.2 Sección: Finanzas")
bullet("IVA estándar (%): Por defecto 19%.")
bullet("Precios con IVA incluido (Gross to Net).")
bullet("Redondeo automático según ley chilena.")
bullet("Moneda base: CLP, USD, EUR u otras.")
bullet("Régimen tributario: Pro Pyme, Renta Presunta o General.")
foto("Pantalla de configuración de finanzas")

h2("8.3 Sección: Sistema / Backup")
h3("Estado del sistema")
for item in ["Nombre y tamaño de la base de datos","Fecha del último backup","Total de backups guardados","Conteo de productos, ventas, usuarios y proveedores"]:
    bullet(item)
h3("Acciones disponibles")
bullet("Crear copia de seguridad: Respaldo completo con fecha y hora.")
bullet("Restaurar desde archivo externo: Requiere autorización y confirmación doble.")
bullet("Historial de backups: Lista nombre, fecha y tamaño de cada backup.")
bullet("Restaurar backup del historial o eliminarlo.")
bullet("Abrir carpeta de backups en el explorador.")
foto("Pantalla Sistema/Backup con historial de copias")

h2("8.4 Sección: Acerca De")
bullet("Logo de la empresa, versión y fecha de lanzamiento.")
bullet("Objetivo del sistema y datos del desarrollador.")
bullet("Redes sociales y contacto.")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 9 — SEGURIDAD
# ════════════════════════════════════════════════
h1("9. Seguridad y Roles")

h2("9.1 Sistema de Login")
bullet("Pantalla de autenticación al iniciar el sistema.")
bullet("Las contraseñas se almacenan cifradas con hash seguro (nunca en texto plano).")
bullet("Registro de fecha y hora de cada inicio de sesión.")
foto("Pantalla de Login")

h2("9.2 Recuperación de Contraseña")
cuerpo("El sistema incluye un módulo de pregunta de seguridad para recuperar el acceso en caso de olvido de contraseña.")

h2("9.3 Roles del Sistema")
tabla(
    ["Rol", "Nivel de acceso"],
    [
        ["Cajero", "Acceso a POS y caja por defecto"],
        ["Supervisor", "Acceso a productos, compras y reportes"],
        ["Administrador", "Acceso total al sistema"],
    ]
)
cuerpo("Los permisos por módulo pueden ajustarse individualmente sobre cualquier rol.")

h2("9.4 Autorización de Administrador")
cuerpo("Ciertas acciones críticas requieren que un administrador ingrese su contraseña para autorizarlas:")
bullet("Acceder a módulos bloqueados por permisos.")
bullet("Restaurar base de datos.")
bullet("Anular ventas (según configuración).")
foto("Ventana de autorización de administrador")

h2("9.5 Barra de Estado")
cuerpo("La barra inferior muestra permanentemente: versión del sistema, usuario activo con su rol, y la fecha y hora actual (actualizada cada minuto).")
doc.add_page_break()

# ════════════════════════════════════════════════
# CAP 10 — DATOS
# ════════════════════════════════════════════════
h1("10. Datos y Almacenamiento")

h2("10.1 Base de Datos Local")
cuerpo("VIM ERP utiliza SQLite como motor de base de datos. Toda la información se almacena en el archivo database/vim_erp.db. Este archivo es local y no requiere internet ni servidores externos.")

h2("10.2 Capacidad del Sistema")
tabla(
    ["Dato", "Capacidad estimada"],
    [
        ["Productos registrados", "Ilimitado (cientos de miles)"],
        ["Ventas registradas", "Ilimitado (millones)"],
        ["Usuarios del sistema", "Sin límite práctico"],
        ["1.000.000 de ventas detalladas", "≈ 150–300 MB en disco"],
        ["Límite técnico de SQLite", "Hasta 281 TB"],
    ]
)
nota("Para una tienda o pyme, el sistema es prácticamente ilimitado. Te tomaría décadas de uso intensivo llegar al límite técnico.")

h2("10.3 Respaldos Recomendados")
cuerpo("Se recomienda crear un backup diario o al final de cada jornada desde Configuración → Sistema / Backup. Los backups pueden copiarse manualmente a un disco externo o almacenamiento en la nube.")
separador()


if __name__ == "__main__":
    from vim_logger import get_logger
    _log = get_logger("generar_informe")
    ruta = generar_informe()
    _log.info(f"Documento generado correctamente en: {ruta}")
    print(f"✅ Documento generado correctamente en:\n   {ruta}")
