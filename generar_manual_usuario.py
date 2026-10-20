"""Genera el Manual de Uso de VIM ERP en Word, módulo por módulo.

Está escrito para el DUEÑO DEL NEGOCIO y sus cajeros, no para programadores:
sin jerga técnica, con los pasos en el orden real en que se hacen.

Deja recuadros [ 📷 ... ] donde corresponde pegar una captura de pantalla.

Uso:
    python generar_manual_usuario.py
"""

import os

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

for section in doc.sections:
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.2)

AZUL = RGBColor(0x00, 0x2B, 0x5C)
CELESTE = RGBColor(0x17, 0x5E, 0xA6)
GRIS = RGBColor(0x47, 0x55, 0x69)
VERDE = RGBColor(0x15, 0x80, 0x3D)
ROJO = RGBColor(0xC6, 0x28, 0x28)
NARANJA = RGBColor(0xB4, 0x53, 0x09)


# ════════════════════════════════════════════════════════════
# FORMATO
# ════════════════════════════════════════════════════════════

def _fuente(run, size, bold=False, color=None, italic=False):
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    run.font.name = "Segoe UI"
    if color:
        run.font.color.rgb = color


def portada_titulo(texto):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fuente(p.add_run(texto), 30, bold=True, color=AZUL)


def portada_sub(texto, size=12):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fuente(p.add_run(texto), size, color=GRIS, italic=True)


def h1(texto):
    doc.add_page_break()
    p = doc.add_paragraph()
    _fuente(p.add_run(texto), 18, bold=True, color=AZUL)
    p.paragraph_format.space_after = Pt(6)


def h2(texto):
    p = doc.add_paragraph()
    _fuente(p.add_run(texto), 13, bold=True, color=CELESTE)
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(3)


def h3(texto):
    p = doc.add_paragraph()
    _fuente(p.add_run(texto), 11, bold=True, color=GRIS)
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(2)


def texto(cadena):
    p = doc.add_paragraph()
    _fuente(p.add_run(cadena), 10.5)
    p.paragraph_format.space_after = Pt(5)


def punto(cadena):
    p = doc.add_paragraph(style="List Bullet")
    _fuente(p.add_run(cadena), 10.5)
    p.paragraph_format.space_after = Pt(2)


def paso(numero, cadena):
    p = doc.add_paragraph()
    _fuente(p.add_run(f"{numero}.  "), 10.5, bold=True, color=CELESTE)
    _fuente(p.add_run(cadena), 10.5)
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.space_after = Pt(3)


def aviso(cadena, color=NARANJA, icono="⚠"):
    p = doc.add_paragraph()
    _fuente(p.add_run(f"{icono}  {cadena}"), 10, bold=True, color=color)
    p.paragraph_format.left_indent = Cm(0.4)
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)


def tip(cadena):
    p = doc.add_paragraph()
    _fuente(p.add_run(f"💡  {cadena}"), 9.5, italic=True, color=VERDE)
    p.paragraph_format.left_indent = Cm(0.4)
    p.paragraph_format.space_after = Pt(6)


def foto(descripcion):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _fuente(p.add_run(f"[ 📷  {descripcion} ]"), 9,
            italic=True, color=RGBColor(0x94, 0xA3, 0xB8))
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(12)


def espacio():
    doc.add_paragraph()


def tabla(encabezados, filas, ancho_fuente=9.5):
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.style = "Table Grid"
    hdr = t.rows[0].cells
    for i, h in enumerate(encabezados):
        hdr[i].text = h
        for run in hdr[i].paragraphs[0].runs:
            _fuente(run, ancho_fuente, bold=True, color=AZUL)
    for fila in filas:
        celdas = t.add_row().cells
        for i, val in enumerate(fila):
            celdas[i].text = str(val)
            for run in celdas[i].paragraphs[0].runs:
                _fuente(run, ancho_fuente)
    doc.add_paragraph()


# ════════════════════════════════════════════════════════════
# PORTADA
# ════════════════════════════════════════════════════════════

espacio()
espacio()
espacio()
portada_titulo("VIM ERP")
portada_sub("Manual de Uso", 16)
espacio()
portada_sub("Guía completa, módulo por módulo, para el dueño del negocio y sus cajeros")
espacio()
espacio()
foto("Portada: pantalla del menú principal de VIM ERP")
espacio()
portada_sub("Versión 1.0  ·  Octubre 2026")
portada_sub("Desarrollado por Diego Francisco Bustamante Ríos")


# ════════════════════════════════════════════════════════════
# ANTES DE EMPEZAR
# ════════════════════════════════════════════════════════════

h1("Antes de empezar")

h2("¿Qué es VIM ERP?")
texto(
    "Es un programa para manejar el día a día de un negocio: vender en el mostrador, "
    "controlar cuánto stock queda, saber cuánta plata hay en la caja y ver si el negocio "
    "está ganando o perdiendo."
)
texto(
    "Funciona sin internet y guarda todo en su propio computador. Nadie más ve su información."
)

h2("¿Qué NO hace? (léalo antes de instalarlo)")
texto("Para evitar malentendidos, conviene ser claro desde el principio:")
punto(
    "NO emite boletas ni facturas electrónicas ante el SII. Los tickets que imprime son "
    "comprobantes internos para el cliente, sin validez tributaria. Para emitir documentos "
    "válidos debe usar el sistema del SII o un software certificado."
)
punto(
    "NO comparte información entre varios computadores. Cada PC tiene su propia base de datos."
)
punto(
    "NO hace copias de seguridad solo. Usted debe hacerlas (vea el capítulo 9)."
)
punto(
    "NO se actualiza solo. Si sale una versión nueva, hay que descargarla."
)

h2("Cómo está organizado este manual")
texto(
    "Cada capítulo es un módulo del programa, en el mismo orden en que los va a necesitar. "
    "Si es la primera vez, léalo de corrido hasta el capítulo 5; con eso ya puede vender. "
    "El resto consúltelo cuando lo necesite."
)

tabla(
    ["Capítulo", "De qué trata", "¿Cuándo lo necesito?"],
    [
        ["1. Primeros pasos", "Abrir el programa la primera vez", "El primer día"],
        ["2. Configuración", "Datos del negocio, IVA, impresora", "El primer día"],
        ["3. Productos / Servicios", "Cargar lo que vende", "El primer día"],
        ["4. Caja", "Abrir y cerrar la caja", "Todos los días"],
        ["5. Punto de Venta", "Vender y cobrar", "Todo el día"],
        ["6. Ventas y Reportes", "Ver cómo va el negocio", "Cada semana o mes"],
        ["7. Administración", "Registrar gastos y compras", "Cuando llega una factura"],
        ["8. Usuarios", "Dar acceso a los cajeros", "Cuando entra alguien nuevo"],
        ["9. Copias de seguridad", "Proteger su información", "¡Siempre!"],
        ["10. Problemas comunes", "Qué hacer cuando algo falla", "Cuando lo necesite"],
        ["11. Glosario", "Qué significa cada palabra", "Cuando algo no se entienda"],
    ],
)


# ════════════════════════════════════════════════════════════
# 1. PRIMEROS PASOS
# ════════════════════════════════════════════════════════════

h1("1.  Primeros pasos")

h2("1.1  Abrir el programa por primera vez")

paso(1, "Descomprima el archivo que descargó en una carpeta suya (Escritorio o Documentos).")
paso(2, "Haga doble clic en VIM_ERP.exe.")

aviso(
    "Windows puede mostrar una pantalla azul que dice «Windows protegió su PC». "
    "Aparece porque el programa no está firmado digitalmente, no porque tenga algo malo. "
    "Haga clic en «Más información» y después en «Ejecutar de todas formas»."
)
foto("Pantalla azul de Windows SmartScreen, con la opción «Más información» señalada")

texto(
    "Al abrirlo aparece el logo de VIM ERP por un par de segundos mientras el programa se "
    "prepara. Después sale la pantalla de inicio de sesión."
)
foto("Logo de carga al abrir el programa")

h2("1.2  El asistente de configuración inicial")
texto(
    "La primera vez, el programa le hace dos preguntas. No se pueden saltar, porque de ellas "
    "depende cómo funciona todo lo demás."
)

h3("Pregunta 1: ¿Qué tipo de negocio es?")
texto("Aparecen dos tarjetas y hay que elegir una:")

tabla(
    ["Opción", "Para quién", "Qué cambia"],
    [
        ["🏷️ Productos",
         "Almacén, minimarket, tienda, distribuidora",
         "Maneja stock, inventario y proveedores"],
        ["✂️ Servicios",
         "Peluquería, taller, consultora, gimnasio",
         "Sin stock: se cobra por servicio prestado"],
    ],
)

aviso(
    "Elija bien esta primera vez. Se puede cambiar después en Configuración → Finanzas, "
    "pero al cambiarlo se convierten todos sus ítems y el stock queda en cero. Por eso el "
    "programa le pide confirmar y escribir PRODUCTOS o SERVICIOS antes de hacer el cambio."
)
foto("Asistente inicial: las dos tarjetas, Productos y Servicios")

h3("Pregunta 2: Su pregunta de seguridad")
texto(
    "Elija una pregunta y escriba la respuesta dos veces. Esta es la ÚNICA forma de recuperar "
    "el acceso si olvida su contraseña, así que use algo que no se le olvide y que otros no "
    "puedan adivinar."
)
foto("Asistente inicial: pantalla de la pregunta de seguridad")

h2("1.3  Entrar al sistema")
texto("Cuando termina el asistente, entre con:")
punto("Usuario:  admin")
punto("Clave:  1234")

aviso(
    "Esa clave es la misma en TODAS las instalaciones del programa. Cámbiela ahora, antes de "
    "cargar sus productos. Se cambia en el módulo Usuarios (capítulo 8). Si no la cambia, "
    "cualquiera que conozca el programa puede entrar a su sistema y ver sus ventas.",
    color=ROJO, icono="🔒"
)
foto("Pantalla de inicio de sesión")

h2("1.4  Dónde quedan sus datos")
texto("El programa crea todo automáticamente en esta carpeta de su computador:")
texto("        %LOCALAPPDATA%\\VIM_ERP")
texto("Dentro va a encontrar tres carpetas:")
punto("database — su base de datos: ventas, productos, clientes, todo.")
punto("backups — las copias de seguridad que usted haga.")
punto("logs — un registro de errores, útil si algo falla.")
tip(
    "Para llegar rápido: copie esa ruta tal cual, péguela en la barra del explorador de "
    "archivos de Windows y presione Enter."
)


# ════════════════════════════════════════════════════════════
# 2. CONFIGURACIÓN
# ════════════════════════════════════════════════════════════

h1("2.  Configuración del negocio")

texto(
    "Antes de cargar productos conviene dejar configurado el negocio. Se entra desde el "
    "botón ⚙️ Configuración del menú principal."
)
foto("Menú principal con el botón Configuración señalado")

h2("2.1  Datos de la empresa")
texto(
    "En la sección Empresa cargue el nombre del negocio, dirección y teléfono. Estos datos "
    "salen impresos en el ticket que recibe el cliente."
)
punto("Nombre del negocio — aparece arriba del ticket.")
punto("Mensaje al pie — por ejemplo «¡Gracias por su compra!».")
punto("Logo — se puede cambiar por el de su negocio.")
punto(
    "📄 Vista previa — abre un PDF con cómo se verá su ticket, aunque todavía no tenga "
    "impresora."
)
foto("Configuración → Empresa")
foto("Vista previa del ticket en PDF")

h2("2.2  IVA e impuestos")
texto("En la sección Finanzas define cómo se calculan los impuestos. Hay dos decisiones:")

h3("¿Cuánto es el IVA?")
texto(
    "Escriba el porcentaje. En Chile suele ser 19. Si su negocio no maneja IVA, ponga 0 y "
    "el precio que cargue será exactamente el precio que se cobre."
)

h3("¿Los precios que cargo ya incluyen IVA?")
texto("Esta casilla cambia bastante el resultado. Con un ejemplo se entiende mejor:")

tabla(
    ["Si la casilla está...", "Y usted carga un precio de $10.000", "El cliente paga"],
    [
        ["✔ Marcada (los precios ya incluyen IVA)", "$10.000 ya trae el impuesto adentro", "$10.000"],
        ["☐ Sin marcar (los precios son netos)", "Se le suma el 19% encima", "$11.900"],
    ],
)

tip(
    "Para un negocio de mostrador lo normal es dejarla MARCADA: usted carga el precio de la "
    "etiqueta y eso es lo que paga el cliente."
)

h3("Redondear a $10 los pagos en efectivo")
texto(
    "Si marca esta casilla, los cobros en efectivo se redondean a la decena más cercana, "
    "porque no circulan monedas de $1 ni de $5: $1.234 se cobra $1.230 y $1.235 se cobra "
    "$1.240. Con tarjeta o transferencia se cobra el monto exacto, sin redondear."
)

h3("El ejemplo en vivo")
texto(
    "Debajo de las casillas, el programa muestra cómo queda un producto de $1.235 con lo que "
    "tiene marcado. Si cambia el IVA o una casilla, el ejemplo se actualiza al tiro, antes de "
    "guardar. Úselo para comprobar que el precio final es el que usted espera."
)
foto("Configuración → Finanzas, con el IVA, las casillas y el ejemplo en vivo")

h3("Moneda y régimen tributario")
punto(
    "Moneda — el programa trabaja con el signo $ y montos sin decimales. Sirve para "
    "cualquier país que use el peso o una moneda sin centavos."
)
punto(
    "Régimen tributario — es solo un dato informativo para usted y su contador. No cambia "
    "precios, IVA ni totales."
)

h2("2.3  Impresora de tickets")
texto(
    "El programa funciona con impresoras térmicas de 58mm y 80mm que ya estén instaladas en "
    "Windows. Se eligen en Configuración → Empresa."
)
punto("La impresora queda guardada apenas la elige en la lista.")
punto(
    "Si no configura ninguna impresora, igual puede vender: el comprobante se muestra en "
    "pantalla y lo puede guardar en PDF."
)
punto("Puede activar o desactivar la impresión automática al cerrar cada venta.")
punto("Puede decidir si el ticket muestra el desglose del IVA o solo el total.")
foto("Configuración de la impresora térmica")

aviso(
    "Lo que imprime VIM ERP es un COMPROBANTE INTERNO de venta y así lo dice al pie: "
    "«No válido como boleta (SII)». Si necesita emitir boletas, hágalo aparte con el sistema "
    "del SII o con un proveedor certificado."
)


# ════════════════════════════════════════════════════════════
# 3. PRODUCTOS
# ════════════════════════════════════════════════════════════

h1("3.  Productos y Servicios")

texto(
    "Acá carga todo lo que vende. Si eligió negocio de servicios, el módulo se llama "
    "«Servicios» y no le pide stock ni proveedor."
)
foto("Módulo Productos: la lista completa")

h2("3.1  Cargar un producto nuevo")

paso(1, "Entre a 🏷️ Productos desde el menú principal.")
paso(2, "Complete los campos del formulario de la izquierda.")
paso(3, "Presione «Guardar producto nuevo» o la tecla Enter. El producto aparece en la lista de la derecha.")

h3("Qué significa cada campo")

tabla(
    ["Campo", "Para qué sirve"],
    [
        ["Nombre", "Cómo lo va a buscar el cajero. Sea claro: «Coca-Cola 1.5L», no «bebida»."],
        ["Código de barras", "El código que trae el envase. Si tiene lector, es lo que escanea."],
        ["Código POS (PLU)", "Un número corto que usted inventa, para lo que no tiene código de barras."],
        ["Precio compra", "Lo que a usted le cuesta. Sirve para saber cuánto gana."],
        ["Precio venta", "Lo que paga el cliente."],
        ["Stock", "Cuántas unidades tiene ahora."],
        ["Stock mínimo", "Cuando baje de este número, el producto se marca en rojo."],
        ["Categoría", "Para agrupar y ordenar los reportes."],
        ["Proveedor", "A quién se lo compra."],
    ],
)

aviso(
    "El precio de compra no es un dato opcional. Sin él, el programa no puede decirle "
    "cuánto está ganando de verdad: le va a mostrar que toda la venta es ganancia."
)
foto("Formulario de producto con los campos completos")

h3("Códigos repetidos")
texto(
    "Un mismo código no puede ser de dos productos, ni siquiera si en uno es código de barras "
    "y en otro es PLU: el lector no sabría cuál cobrar. Si lo intenta, el programa le avisa "
    "qué producto ya usa ese código y no guarda."
)
tip(
    "Si eliminó un producto, su código queda libre y lo puede usar en uno nuevo."
)
foto("Aviso de código repetido")

h2("3.2  Vender por unidad o por peso")
texto("En el campo «Tipo de venta» elige cómo se cobra:")

punto(
    "Por unidad — lo normal. Se vende de a 1, 2, 3 unidades. Se usa el «Precio venta»."
)
punto(
    "Por peso — para fruta, verdura, carnicería, fiambres. El cajero ingresa los kilos y se "
    "usa el «Precio por kilo»."
)
tip(
    "En un producto por peso, el campo «Precio venta» se bloquea y se habilita «Precio por "
    "kilo». Es normal, no es un error."
)

h2("3.3  Servicios: el campo Costo Directo")
texto(
    "Si su negocio es de servicios, donde antes decía «Precio compra» ahora dice «Costo "
    "directo». Ahí puede poner lo que le cuesta prestar ese servicio: insumos, comisión del "
    "empleado, lo que corresponda."
)
texto(
    "Es opcional. Si lo deja en cero, el reporte simplemente no muestra la línea de costo ni "
    "el margen, y va directo de ingresos a gastos."
)

h2("3.4  Editar y eliminar")
punto(
    "Para editar: haga clic en el producto de la lista. El botón cambia a «Guardar cambios»; "
    "cambie lo que necesite y presiónelo."
)
punto("Para volver a cargar uno nuevo, presione «Nuevo / Limpiar».")
punto("Para eliminar: seleccione el producto y presione Eliminar.")

texto(
    "Eliminar un producto pide la contraseña de administrador. Si necesita borrar varios "
    "seguidos, el programa no se la vuelve a pedir durante el minuto siguiente: se lo avisa "
    "en el mensaje de confirmación."
)
foto("Mensaje de confirmación al eliminar un producto")


# ════════════════════════════════════════════════════════════
# 4. CAJA
# ════════════════════════════════════════════════════════════

h1("4.  Caja")

aviso(
    "Esto es lo más importante del manual: SIN CAJA ABIERTA NO SE PUEDE VENDER. "
    "Si el Punto de Venta le dice «No hay caja abierta», venga a este módulo y ábrala.",
    color=ROJO, icono="🔑"
)

h2("4.1  Abrir la caja (cada mañana)")

paso(1, "Entre a 💰 Caja desde el menú principal.")
paso(2, "Presione «Abrir Caja».")
paso(3, "Escriba cuánta plata hay físicamente en el cajón para dar vuelto.")
paso(4, "Confirme. Ya puede vender.")

tip(
    "Ese monto inicial es su «fondo de caja». Al cerrar, el programa lo usa para calcular "
    "cuánta plata debería haber."
)
foto("Pantalla de apertura de caja")

h2("4.2  El resumen en tiempo real")
texto("Mientras la caja está abierta, el módulo le muestra:")
punto("Cuánto vendió en efectivo, con tarjeta y por transferencia.")
punto("Los ingresos y egresos manuales que haya registrado.")
punto("Cuánto efectivo debería haber en el cajón en este momento.")
foto("Panel de resumen de caja con las ventas del día")

tip(
    "Si anula una venta pagada con tarjeta o transferencia, se descuenta de esas ventas y el "
    "efectivo del cajón no cambia. Solo la anulación de una venta en efectivo aparece como "
    "egreso, porque ahí sí sale plata del cajón."
)

h2("4.3  Movimientos manuales")
texto(
    "Sirve para la plata que entra o sale del cajón sin ser una venta: pagar un flete, "
    "comprar café, sacar plata para el banco."
)
punto("Egreso — sale plata del cajón. Estos SÍ cuentan como gasto en sus reportes.")
punto("Ingreso — entra plata que no es una venta. Estos NO se cuentan como ganancia.")

tip(
    "Si usted mete plata suya al negocio, regístrela como ingreso. El programa la informa "
    "aparte y no la confunde con una venta, para que su ganancia no salga inflada."
)

h2("4.4  Cerrar la caja (al terminar el día)")

paso(1, "Presione «Cerrar Caja».")
paso(2, "Cuente la plata real del cajón y escriba ese número.")
paso(3, "El programa compara con lo que debería haber y le muestra la diferencia.")

texto(
    "Si hay diferencia, no se asuste: puede ser un vuelto mal dado o una venta cobrada de "
    "otra forma. Queda registrada para que pueda revisarla."
)
foto("Pantalla de cierre de caja con el arqueo")


# ════════════════════════════════════════════════════════════
# 5. POS
# ════════════════════════════════════════════════════════════

h1("5.  Punto de Venta (POS)")

texto(
    "Es la pantalla donde va a pasar la mayor parte del día. Está dividida en tres partes: "
    "la búsqueda de productos a la izquierda, el ticket en el centro y el cobro a la derecha."
)
foto("Pantalla completa del Punto de Venta, con las tres zonas señaladas")

h2("5.1  Agregar productos al ticket")

h3("Con lector de código de barras (lo más rápido)")
texto(
    "Escanee el producto y listo: se agrega solo al ticket. No hay que apretar nada más."
)

h3("Sin lector, buscando por nombre")
paso(1, "Escriba parte del nombre en el buscador. La lista se filtra sola.")
paso(2, "Haga clic en el producto que quiere, o use las flechas del teclado.")
paso(3, "Presione Enter o el botón ➕ Agregar.")

h3("Productos por peso")
texto(
    "Si el producto se vende por peso, el programa NO lo agrega solo. Le pide los kilos "
    "primero, porque nadie puede adivinar cuánto pesa. Escriba los kilos y presione Enter."
)
tip(
    "Fíjese en la línea «Modo:» debajo del buscador. Le dice si el producto seleccionado se "
    "vende por unidad o por peso."
)

h2("5.2  Corregir el ticket")

punto("Editar una línea — cambia la cantidad o el peso. Botón ✏️ Editar o tecla F6.")
punto("Eliminar una línea — la saca del ticket. Botón 🗑️ Eliminar o tecla Suprimir.")
punto("Vaciar todo — borra el ticket completo. Botón ❌ Vaciar o tecla F3.")

texto(
    "Eliminar y vaciar piden la contraseña de administrador. Si está corrigiendo varias "
    "líneas seguidas, no se la vuelve a pedir por un minuto."
)

h3("Cambiar el precio de una línea")
texto(
    "Al editar una línea, el programa le pregunta si además quiere cambiar el precio. Esto "
    "pide autorización de administrador y queda registrado en el historial, con el precio "
    "anterior y el nuevo."
)
foto("Ticket con varias líneas cargadas")

h2("5.3  Cobrar")

texto("A la derecha tiene el total y tres formas de cobrar:")

tabla(
    ["Botón", "Cuándo se usa", "Qué hace"],
    [
        ["💵 COBRAR EFECTIVO", "El cliente paga con billetes",
         "Pide cuánto entregó y calcula el vuelto"],
        ["💳 Tarjeta", "Pago con débito o crédito", "Cobra el total exacto"],
        ["📱 Transfer.", "Transferencia bancaria", "Cobra el total exacto"],
    ],
)

h3("El recuadro de VUELTO")
texto("Escriba cuánto le dio el cliente y el recuadro le responde:")
punto("En verde, «VUELTO» — cuánto tiene que devolver.")
punto("En rojo, «FALTA» — cuánta plata falta todavía para cubrir el total.")

tip(
    "Si el cliente paga justo, el vuelto queda en $0 y en verde. Si ve rojo, todavía falta plata."
)
foto("Recuadro de cobro mostrando el vuelto en verde")

h3("Por qué el total puede cambiar según cómo pague")
texto(
    "Bajo el total aparece una línea chica que explica la diferencia cuando la hay: el IVA "
    "sumado (si sus precios no lo incluyen) o el redondeo. Como el redondeo a $10 es solo "
    "para efectivo, la misma compra puede costar $1.240 en efectivo y $1.235 con tarjeta. "
    "No es un error."
)

h2("5.4  Después de cobrar")
texto("Al confirmar la venta pasan tres cosas:")
punto("Se descuenta el stock de los productos vendidos.")
punto("Si tiene impresora configurada, sale el ticket automáticamente.")
punto("Aparece el comprobante en pantalla, con el folio y la fecha de la venta.")
punto(
    "Con el botón 📄 PDF lo guarda como archivo, por ejemplo para mandarlo por WhatsApp o "
    "correo, o si no tiene impresora."
)

texto(
    "El folio es el número que identifica la venta, con el formato VTA-20260820-0001. "
    "Se reinicia cada día y nunca se repite."
)
foto("Comprobante en pantalla después de cobrar, con el botón 📄 PDF")
foto("Comprobante guardado en PDF")

h2("5.5  Atajos de teclado")
texto("Para trabajar rápido sin soltar el teclado:")

tabla(
    ["Tecla", "Qué hace"],
    [
        ["F2", "Cobrar la venta"],
        ["F3", "Vaciar el ticket"],
        ["F4", "Ir al buscador"],
        ["F5", "Mostrar todos los productos"],
        ["F6", "Editar la línea seleccionada"],
        ["Suprimir", "Eliminar la línea seleccionada"],
        ["Escape", "Volver al menú principal"],
        ["Flechas", "Moverse entre los campos y botones"],
    ],
)

aviso(
    "Si presiona Escape con un ticket a medio armar, el programa le avisa cuántas líneas hay "
    "y cuánto suman antes de salir. Si dice que sí, ese ticket se pierde."
)


# ════════════════════════════════════════════════════════════
# 6. VENTAS Y REPORTES
# ════════════════════════════════════════════════════════════

h1("6.  Ventas y Reportes")

texto(
    "Acá ve cómo va el negocio. Es el módulo que conviene mirar una vez por semana, aunque "
    "sea cinco minutos."
)
foto("Módulo Ventas / Reportes: vista general")

h2("6.1  Historial de ventas")
texto(
    "La lista de todas sus ventas, de la más nueva a la más vieja. Arriba están los filtros:"
)
punto(
    "Fechas — los botones Hoy, Esta Semana, Este Mes y Este Año llegan siempre hasta hoy. "
    "También puede elegir un rango con los calendarios Desde y Hasta."
)
punto("Método — muestra solo efectivo, tarjeta o transferencia. Se actualiza al elegirlo.")
punto("Folio — escriba el número de una venta y presione Enter.")
tip(
    "El folio se busca dentro de las fechas elegidas. Si no lo encuentra, presione «Limpiar "
    "Filtros» y vuelva a buscarlo."
)
foto("Filtros de fecha, método y folio")
punto("Haga doble clic en una venta para ver el detalle de qué se vendió.")
punto("Desde ahí también puede anular una venta, si se cobró por error.")

tip(
    "Anular una venta devuelve el stock a los productos y saca esa venta de sus reportes. "
    "Queda registrada como anulada, no desaparece."
)

h2("6.2  Estado de Resultados: ¿estoy ganando?")
texto(
    "Este es el reporte más importante y también el que más se malinterpreta. Le explica, "
    "en orden, de dónde sale su ganancia:"
)

tabla(
    ["Línea", "Qué significa en criollo"],
    [
        ["(+) Ventas netas", "Todo lo que vendió, sin contar el IVA"],
        ["(−) Costo de ventas", "Lo que le costaron a usted los productos que vendió"],
        ["(=) UTILIDAD BRUTA", "Lo que le queda antes de pagar los gastos del local"],
        ["(−) Gastos operativos", "Arriendo, luz, sueldos, todo lo que paga para funcionar"],
        ["(=) UTILIDAD NETA", "Lo que realmente ganó. Este es el número que importa"],
    ],
)

h3("Qué cuenta como gasto y qué no")
texto(
    "Acá hay dos reglas que confunden a mucha gente, y el programa las aplica correctamente:"
)

punto(
    "Comprar mercadería NO es un gasto. Cuando usted compra 100 unidades, no perdió esa "
    "plata: la cambió por mercadería que vale lo mismo. Se convierte en gasto recién cuando "
    "la vende, y ahí aparece como «Costo de ventas»."
)
punto(
    "Comprar una máquina o un mueble tampoco es un gasto del mes. Es una inversión que le "
    "va a durar años."
)

aviso(
    "Si estas dos cosas se contaran como gasto, el mes que usted reponga mercadería el "
    "reporte le mostraría una pérdida enorme que no es real."
)

h3("Punto de equilibrio")
texto(
    "Le dice cuánto necesita vender para cubrir sus gastos y no perder plata. Si vende por "
    "encima de ese número, gana; por debajo, pierde."
)
foto("Panel del Estado de Resultados")

h2("6.3  Análisis Visual")
texto(
    "En la pestaña 📈 Análisis Visual ve el período elegido en gráficos, para entender de "
    "un vistazo cómo le fue."
)
punto(
    "Tarjetas de arriba — ingresos, cantidad de ventas y ticket promedio, comparados con el "
    "período anterior (▲ subió, ▼ bajó). El mes en curso se compara con los mismos días del "
    "mes anterior: del 1 al 20 de octubre contra el 1 al 20 de septiembre."
)
punto("Ventas por día — una barra por día y una línea con el promedio diario.")
punto("¿A qué hora se vende más? — ventas por hora; la hora pico aparece destacada.")
punto("Medios de pago — cuánto entró en efectivo, tarjeta y transferencia, con su porcentaje.")
punto("Productos y categorías que más venden — los 5 primeros según lo que vendieron en plata.")
tip(
    "Use la hora pico para decidir cuándo reforzar la caja, y el ranking para saber qué "
    "productos no le pueden faltar."
)
foto("Análisis Visual: tarjetas y gráfico de ventas por día")
foto("Análisis Visual: horas, medios de pago y rankings")

h2("6.4  Centro de Descargas")
texto(
    "Sirve para bajar sus datos a Excel, para el contador o para guardarlos aparte. Se abre "
    "con el botón 📥 Centro de Descargas."
)

paso(1, "Elija el período con los botones rápidos (Hoy, Esta semana, Este mes...) o con los calendarios.")
paso(2, "Mire la línea verde: le dice cuántas ventas y cuánta plata hay en ese período, antes de descargar.")
paso(3, "Elija qué tipo de reporte quiere.")
paso(4, "Presione DESCARGAR REPORTE y elija dónde guardarlo.")

tabla(
    ["Reporte", "Qué trae", "Para qué sirve"],
    [
        ["Ventas del Período", "Listado simple de ventas", "Revisar o mandar por correo"],
        ["Ventas + Resultados", "Las ventas más la ganancia y los gastos", "Para el contador"],
        ["Reporte Maestro", "Todo el negocio en varias hojas", "Cierre de mes o revisión completa"],
    ],
)

aviso(
    "En el Reporte Maestro, las hojas de Inventario, Cuentas por Pagar y Personal muestran "
    "el estado ACTUAL, no el del período que eligió."
)
foto("Centro de Descargas con los botones de período")


# ════════════════════════════════════════════════════════════
# 7. ADMINISTRACIÓN
# ════════════════════════════════════════════════════════════

h1("7.  Administración: compras, proveedores y personal")

texto(
    "Acá registra todo lo que el negocio PAGA. Es lo que permite que el Estado de Resultados "
    "le diga la verdad: si nunca carga sus gastos, el programa va a creer que todo lo que "
    "vende es ganancia."
)
foto("Módulo Administración")

h2("7.1  Registrar un gasto o una compra")

paso(1, "Entre a 🛍️ Administración.")
paso(2, "Elija el Tipo de Operación (vea la tabla de abajo).")
paso(3, "Complete el documento: tipo, número, fecha y proveedor.")
paso(4, "Elija la Cuenta Contable, que es la categoría del gasto.")
paso(5, "Escriba el monto y si ya está pagado o queda pendiente.")

h3("Los tipos de operación")

tabla(
    ["Tipo", "Cuándo se usa", "¿Cuenta como gasto?"],
    [
        ["Compra de inventario", "Repone mercadería para vender",
         "No: pasa a ser costo cuando la vende"],
        ["Gasto operativo", "Arriendo, luz, agua, internet, publicidad", "Sí"],
        ["Sueldos", "Pago de remuneraciones", "Sí"],
        ["Activo fijo", "Máquinas, muebles, vitrinas", "No: es una inversión"],
    ],
)

tip(
    "Si su negocio es de servicios, la opción «Compra de inventario» no aparece, porque no "
    "hay mercadería que reponer."
)

h2("7.2  Proveedores")
texto(
    "La lista de a quién le compra. Cargue al menos el nombre; el RUT y el teléfono son "
    "opcionales pero ayudan cuando hay que reclamar algo."
)

h2("7.3  Cuentas por pagar")
texto(
    "Si registró una compra como «pendiente», aparece acá con su saldo. Cuando la pague, "
    "registre el pago y el saldo baja."
)
foto("Listado de cuentas por pagar")

h2("7.4  Personal y liquidaciones")
texto(
    "Puede cargar a sus empleados con su sueldo base y registrar las liquidaciones mensuales, "
    "con bonos y descuentos."
)


# ════════════════════════════════════════════════════════════
# 8. USUARIOS
# ════════════════════════════════════════════════════════════

h1("8.  Usuarios y permisos")

texto(
    "Si más de una persona usa el programa, conviene que cada una tenga su propio usuario. "
    "Así queda registrado quién hizo cada venta."
)
foto("Módulo Usuarios")

h2("8.1  Cambiar su contraseña (hágalo ahora)")

paso(1, "Entre a 👨‍💼 Usuarios.")
paso(2, "Seleccione el usuario admin de la lista.")
paso(3, "Escriba la contraseña nueva y guarde.")

aviso(
    "Si todavía tiene la clave 1234, este es el momento. Cualquiera que haya descargado el "
    "programa la conoce.",
    color=ROJO, icono="🔒"
)

h2("8.2  Crear un usuario para un cajero")

paso(1, "Complete nombre, usuario y contraseña.")
paso(2, "Elija el rol.")
paso(3, "Guarde.")

h3("Los tres roles")

tabla(
    ["Rol", "Qué puede hacer"],
    [
        ["Cajero", "Vender y manejar la caja. Nada más."],
        ["Supervisor", "Lo del cajero, más productos, compras y reportes."],
        ["Administrador", "Todo, incluida la configuración y los usuarios."],
    ],
)

tip(
    "Dele a cada persona el rol más bajo que le sirva para trabajar. Un cajero no necesita "
    "poder cambiar precios ni ver las utilidades del negocio."
)

h2("8.3  Permisos por módulo")
texto(
    "Si necesita algo más fino que los roles, puede activar o desactivar módulos uno por uno "
    "para cada usuario."
)
foto("Pantalla de permisos por módulo")


# ════════════════════════════════════════════════════════════
# 9. BACKUPS
# ════════════════════════════════════════════════════════════

h1("9.  Copias de seguridad")

aviso(
    "El programa NO hace copias solo. Si el computador se rompe, se moja o se lo roban, y "
    "usted nunca hizo una copia, pierde todo: ventas, productos, historial. Todo.",
    color=ROJO, icono="🛡"
)

h2("9.1  Hacer una copia")

paso(1, "Entre al módulo de Backup.")
paso(2, "Presione el botón de crear copia de seguridad.")
paso(3, "El programa le muestra el nombre del archivo y en qué carpeta quedó.")
paso(4, "Le ofrece abrir la carpeta. Diga que sí la primera vez, para saber dónde están.")

texto("Las copias quedan en:")
texto("        %LOCALAPPDATA%\\VIM_ERP\\backups")
tip(
    "En el módulo hay una línea «Se guardan en:» con la ruta completa y un botón «Copiar "
    "ruta», por si necesita pegarla en otro lado."
)
foto("Módulo Backup, con la ruta y el listado de copias")

h2("9.2  Cada cuánto hacerlas")
texto(
    "Depende de cuánto le dolería perder. Una regla simple: hágala al cerrar la caja, todos "
    "los días. Si un día no la hizo, lo peor que puede pasar es perder un día de ventas."
)

aviso(
    "Las copias quedan en el MISMO computador. Si se rompe el disco, se pierden junto con "
    "todo lo demás. Cada cierto tiempo copie esos archivos .db a un pendrive o a la nube. "
    "Una copia que vive en el mismo lugar que el original no es una copia de seguridad."
)

h2("9.3  Restaurar una copia")

texto("Restaurar reemplaza TODO lo que hay ahora por lo que había cuando hizo la copia.")

paso(1, "Cierre el Punto de Venta y las demás ventanas.")
paso(2, "En el módulo Backup, elija la copia de la lista.")
paso(3, "Presione Restaurar. Le pide la contraseña de administrador.")
paso(4, "Confirme. El programa se cierra solo y hay que volver a abrirlo.")

tip(
    "Antes de restaurar, el programa guarda solo una copia del estado actual, con el nombre "
    "«pre_restauracion_...». Si restauró por error, puede volver atrás con esa."
)
foto("Advertencia antes de restaurar una copia")


# ════════════════════════════════════════════════════════════
# 10. PROBLEMAS
# ════════════════════════════════════════════════════════════

h1("10.  Problemas comunes")

h2("«No hay caja abierta» y no me deja vender")
texto(
    "Es lo más frecuente. Vaya al módulo Caja y ábrala con el monto inicial. Pasa todas las "
    "mañanas y cuando alguien cerró la caja antes de tiempo."
)

h2("Olvidé la contraseña de administrador")
texto(
    "En la pantalla de inicio de sesión hay una opción para recuperarla con su pregunta de "
    "seguridad, la que configuró al instalar. Si tampoco recuerda esa respuesta, no hay forma "
    "de recuperar el acceso."
)

h2("El reporte dice que perdí plata y yo creo que gané")
texto("Revise, en este orden:")
punto("¿Cargó el precio de compra en sus productos? Sin eso, el costo sale en cero.")
punto("¿Registró alguna compra grande de mercadería como «gasto operativo» en vez de «compra de inventario»?")
punto("¿El período que está mirando es el correcto?")

h2("No imprime el ticket")
punto("Revise que la impresora esté encendida, con papel y instalada en Windows.")
punto("Revise que esté seleccionada en Configuración → Empresa.")
punto("La venta igual quedó registrada: la impresión nunca frena una venta.")
punto("Desde el comprobante en pantalla hay un botón 🖨 para reintentar.")
punto("Si no tiene impresora a mano, guarde el comprobante con el botón 📄 PDF.")

h2("Me equivoqué al elegir productos o servicios")
texto(
    "Se cambia en Configuración → Finanzas. El programa le avisa cuántos ítems va a convertir. "
    "Ojo: al pasar a servicios, el stock queda en cero y no se recupera solo."
)

h2("Vendí algo por error")
texto(
    "Vaya a Ventas / Reportes, busque la venta en el historial, ábrala y anúlela. El stock "
    "vuelve solo y la venta deja de contar en los reportes. Si se pagó con tarjeta o "
    "transferencia, la devolución al cliente se hace por ese medio: el efectivo de la caja "
    "no cambia."
)

h2("Windows dice que el programa es peligroso")
texto(
    "Es la advertencia de SmartScreen. Aparece porque el programa no está firmado "
    "digitalmente. Haga clic en «Más información» y después en «Ejecutar de todas formas»."
)


# ════════════════════════════════════════════════════════════
# 11. GLOSARIO
# ════════════════════════════════════════════════════════════

h1("11.  Glosario")

texto("Las palabras que aparecen en el programa, explicadas simple:")

tabla(
    ["Palabra", "Qué significa"],
    [
        ["Arqueo", "Contar la plata real del cajón y compararla con la que debería haber"],
        ["Activo fijo", "Algo que compró para usar por años: una máquina, un mueble, una vitrina"],
        ["Comprobante", "Lo que recibe el cliente, impreso o en PDF. Es interno: no reemplaza a la boleta del SII"],
        ["Costo de ventas", "Lo que a usted le costaron los productos que efectivamente vendió"],
        ["Cuenta contable", "La categoría de un gasto: arriendo, luz, sueldos, publicidad"],
        ["Folio", "El número único que identifica cada venta"],
        ["IVA crédito", "El IVA que usted pagó en sus compras con factura"],
        ["IVA débito", "El IVA que usted cobró en sus ventas"],
        ["Margen", "Qué porcentaje de lo que vende le queda como ganancia"],
        ["PLU", "Código corto que usted inventa para productos sin código de barras"],
        ["POS", "Punto de Venta: la pantalla donde se cobra"],
        ["Punto de equilibrio", "Cuánto necesita vender para no ganar ni perder"],
        ["Stock", "Cuántas unidades tiene disponibles"],
        ["Stock mínimo", "El número que, al alcanzarse, le avisa que hay que reponer"],
        ["Utilidad bruta", "Lo que queda después de descontar el costo de lo vendido"],
        ["Utilidad neta", "Lo que realmente ganó, después de TODOS los gastos"],
    ],
)

espacio()
espacio()
portada_sub("VIM ERP  ·  Manual de Uso  ·  Versión 1.0")
portada_sub(
    "Este programa se entrega gratis y tal como está, sin garantía de ningún tipo. "
    "Usted es responsable de verificar sus propios números y de mantener copias de "
    "seguridad de su información.", 8
)


# ════════════════════════════════════════════════════════════
# GUARDAR
# ════════════════════════════════════════════════════════════

def generar(ruta_salida=None):
    """Construye y guarda el manual. Devuelve la ruta del archivo."""
    ruta = ruta_salida or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "Manual_de_Uso_VIM_ERP.docx"
    )
    doc.save(ruta)
    return ruta


if __name__ == "__main__":
    destino = generar()
    print(f"Manual generado: {destino}")
