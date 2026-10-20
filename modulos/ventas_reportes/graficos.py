"""
Gráficos del Análisis Visual (Reportes → Análisis Visual).

Funciones puras: reciben datos y devuelven una Figure de matplotlib, sin
tocar Tk ni la base de datos. Así se pueden probar y previsualizar solas.

Criterios de diseño:
- Un solo color de serie (azul). El color no se usa como adorno: en cada
  gráfico se destaca solo lo importante (la hora pico, el día de hoy).
- Cuadrícula sólida y tenue, sin bordes de caja; valores escritos solo
  donde ayudan (punta de cada barra en rankings, la hora pico).
- Texto en grises, nunca del color de la barra.
- Montos con separador de miles chileno y abreviados en los ejes.
"""
from datetime import date, timedelta

from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter, MaxNLocator

# Paleta (ver skill dataviz: serie validada sobre fondo claro)
AZUL = "#2a78d6"
AZUL_SUAVE = "#b7d3f6"   # barras secundarias cuando se destaca una
TINTA = "#1e293b"
TINTA_2 = "#52514e"
GRIS_EJE = "#898781"
GRILLA = "#e9e8e2"
BASE = "#c3c2b7"
FONDO = "#ffffff"

DIAS_SEMANA = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def miles(valor) -> str:
    """1234567 → '1.234.567'."""
    return f"{round(float(valor)):,}".replace(",", ".")


def monto(valor) -> str:
    return "$" + miles(valor)


def monto_corto(valor, _pos=None) -> str:
    """Para ejes: $1,2M · $350 mil · $900."""
    v = float(valor)
    if abs(v) >= 1e6:
        return "$" + f"{v / 1e6:.1f}".replace(".", ",").replace(",0", "") + "M"
    if abs(v) >= 1e3:
        return "$" + f"{v / 1e3:.0f}" + " mil"
    return "$" + f"{v:.0f}"


def _figura(ancho=6.0, alto=3.0, dpi=96):
    fig = Figure(figsize=(ancho, alto), dpi=dpi, facecolor=FONDO, layout="constrained")
    ax = fig.add_subplot()
    ax.set_facecolor(FONDO)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    ax.tick_params(colors=GRIS_EJE, labelsize=8.5, length=0, pad=6)
    ax.set_axisbelow(True)
    return fig, ax


def _sin_datos(texto="Sin ventas en este período"):
    fig, ax = _figura(alto=2.2)
    ax.axis("off")
    ax.text(0.5, 0.5, texto, ha="center", va="center", color=GRIS_EJE, fontsize=10,
            transform=ax.transAxes)
    return fig


def _grilla_y(ax):
    ax.yaxis.grid(True, color=GRILLA, linewidth=1, linestyle="-")
    ax.xaxis.grid(False)


def _sin_eje_x(ax):
    """En los rankings cada barra lleva su valor escrito: el eje x sobra."""
    ax.xaxis.set_visible(False)
    ax.grid(False)


def _ancho_barra(n):
    # Barras delgadas: nunca llenan todo el espacio de su columna
    return 0.62 if n <= 12 else 0.75


def _fecha(txt):
    a, m, d = str(txt)[:10].split("-")
    return date(int(a), int(m), int(d))


def completar_dias(filas, desde=None, hasta=None):
    """
    Rellena con 0 los días sin ventas (si no, un día sin ventas
    desaparece del gráfico y las barras quedan engañosamente juntas).
    filas: [{'dia': 'AAAA-MM-DD', 'tickets': n, 'ingresos_totales': x}]
    """
    por_dia = {str(f["dia"])[:10]: f for f in filas}
    if not por_dia and not (desde and hasta):
        return []
    inicio = _fecha(desde) if desde else _fecha(min(por_dia))
    fin = _fecha(hasta) if hasta else _fecha(max(por_dia))
    if por_dia:
        inicio = min(inicio, _fecha(min(por_dia)))
        fin = max(fin, _fecha(max(por_dia)))
    salida, d = [], inicio
    while d <= fin:
        f = por_dia.get(d.isoformat(), {})
        salida.append({"dia": d, "tickets": int(f.get("tickets") or 0),
                       "ingresos": float(f.get("ingresos_totales") or 0)})
        d += timedelta(days=1)
    return salida


def grafico_ventas_por_dia(filas, desde=None, hasta=None):
    """Ingresos de cada día del período. El promedio va como línea de referencia."""
    dias = completar_dias(filas, desde, hasta)
    if not dias or not any(d["ingresos"] for d in dias):
        return _sin_datos()

    fig, ax = _figura(ancho=11.0, alto=3.0)
    _grilla_y(ax)
    xs = list(range(len(dias)))
    valores = [d["ingresos"] for d in dias]
    n = len(dias)

    if n <= 62:
        ax.bar(xs, valores, width=0.6, color=AZUL, linewidth=0)
    else:
        ax.fill_between(xs, valores, color=AZUL, alpha=0.10, linewidth=0)
        ax.plot(xs, valores, color=AZUL, linewidth=2, solid_capstyle="round", solid_joinstyle="round")

    con_venta = [v for v in valores if v > 0]
    promedio = sum(valores) / n
    ax.axhline(promedio, color=TINTA_2, linewidth=1)
    # La leyenda de la línea va arriba, fuera de las barras, para no taparlas
    ax.set_title(f"—  promedio diario {monto(promedio)}", loc="right", fontsize=8.5,
                 color=TINTA_2, pad=10)

    # Mejor día, rotulado en la punta
    i_max = max(range(n), key=lambda i: valores[i])
    if con_venta:
        ax.annotate(monto(valores[i_max]), xy=(i_max, valores[i_max]), xytext=(0, 4),
                    textcoords="offset points", ha="center", va="bottom",
                    fontsize=8.5, color=TINTA, fontweight="bold")

    # Etiquetas del eje x: día de semana + número; espaciadas si hay muchos días
    paso = 1 if n <= 14 else (2 if n <= 31 else max(1, n // 12))
    marcas = xs[::paso]
    if n <= 14:
        etiquetas = [f"{DIAS_SEMANA[dias[i]['dia'].weekday()]} {dias[i]['dia'].day}" for i in marcas]
    else:
        etiquetas = [f"{dias[i]['dia'].day} {MESES[dias[i]['dia'].month - 1]}" for i in marcas]
    ax.set_xticks(marcas, etiquetas)
    ax.set_xlim(-0.6, n - 0.4)
    ax.yaxis.set_major_formatter(FuncFormatter(monto_corto))
    ax.yaxis.set_major_locator(MaxNLocator(4))
    ax.set_ylim(0, max(valores) * 1.15)
    return fig


def grafico_ventas_por_hora(filas):
    """Tickets por hora, de la primera a la última hora con ventas. Se destaca la hora pico."""
    por_hora = {}
    for f in filas:
        try:
            h = int(str(f["hora"])[:2])
        except (ValueError, KeyError):
            continue
        por_hora[h] = int(f.get("tickets") or 0)
    if not por_hora or not any(por_hora.values()):
        return _sin_datos()

    horas = list(range(min(por_hora), max(por_hora) + 1))   # incluye horas sin ventas
    valores = [por_hora.get(h, 0) for h in horas]
    i_pico = max(range(len(horas)), key=lambda i: valores[i])

    fig, ax = _figura(ancho=6.4, alto=3.0)
    _grilla_y(ax)
    colores = [AZUL if i == i_pico else AZUL_SUAVE for i in range(len(horas))]
    ax.bar(range(len(horas)), valores, width=_ancho_barra(len(horas)), color=colores, linewidth=0)
    ax.annotate(f"{horas[i_pico]:02d}:00 · {valores[i_pico]} ventas", xy=(i_pico, valores[i_pico]),
                xytext=(0, 4), textcoords="offset points", ha="center", va="bottom",
                fontsize=8.5, color=TINTA, fontweight="bold")
    paso = 1 if len(horas) <= 12 else 2
    ax.set_xticks(range(0, len(horas), paso), [f"{horas[i]:02d}h" for i in range(0, len(horas), paso)])
    ax.set_xlim(-0.6, len(horas) - 0.4)
    ax.yaxis.set_major_locator(MaxNLocator(4, integer=True))
    ax.set_ylim(0, max(valores) * 1.2)
    return fig


def grafico_ranking(nombres, valores, formato=monto, largo_nombre=24):
    """Barras horizontales ordenadas de mayor a menor, con el valor en la punta."""
    pares = [(str(n), float(v)) for n, v in zip(nombres, valores) if float(v or 0) > 0]
    if not pares:
        return _sin_datos()
    pares.sort(key=lambda p: p[1], reverse=True)
    pares = pares[:5]

    def corto(t):
        return t if len(t) <= largo_nombre else t[: largo_nombre - 1] + "…"

    etiquetas = [corto(n) for n, _ in pares][::-1]
    vals = [v for _, v in pares][::-1]

    fig, ax = _figura(ancho=5.6, alto=0.5 * len(pares) + 0.9)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(BASE)
    ax.barh(range(len(vals)), vals, height=0.55, color=AZUL, linewidth=0)
    ax.set_yticks(range(len(vals)), etiquetas)
    ax.tick_params(axis="y", labelsize=9, labelcolor=TINTA)
    for i, v in enumerate(vals):
        ax.annotate(formato(v), xy=(v, i), xytext=(5, 0), textcoords="offset points",
                    va="center", ha="left", fontsize=8.5, color=TINTA_2)
    ax.set_xlim(0, max(vals) * 1.3)
    _sin_eje_x(ax)
    ax.set_ylim(-0.6, len(vals) - 0.4)
    return fig


def grafico_medios_de_pago(efectivo, tarjeta, transferencia):
    """Cuánto entró por cada medio, con su porcentaje del total."""
    datos = [("Efectivo", float(efectivo or 0)), ("Tarjeta", float(tarjeta or 0)),
             ("Transferencia", float(transferencia or 0))]
    total = sum(v for _, v in datos)
    if total <= 0:
        return _sin_datos()
    datos.sort(key=lambda p: p[1], reverse=True)

    fig, ax = _figura(ancho=4.6, alto=0.5 * len(datos) + 0.9)
    ax.spines["bottom"].set_visible(False)
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(BASE)
    vals = [v for _, v in datos][::-1]
    ax.barh(range(len(vals)), vals, height=0.55, color=AZUL, linewidth=0)
    ax.set_yticks(range(len(vals)), [n for n, _ in datos][::-1])
    ax.tick_params(axis="y", labelsize=9, labelcolor=TINTA)
    for i, v in enumerate(vals):
        ax.annotate(f"{monto(v)}  ({v / total * 100:.0f}%)", xy=(v, i), xytext=(5, 0),
                    textcoords="offset points", va="center", ha="left", fontsize=8.5, color=TINTA_2)
    ax.set_xlim(0, max(vals) * 1.6)
    _sin_eje_x(ax)
    ax.set_ylim(-0.6, len(vals) - 0.4)
    return fig


def variacion(actual, anterior):
    """
    % de cambio contra el período anterior, o None si no se puede comparar
    (sin datos previos). Ej: (120, 100) → 20.0
    """
    try:
        actual, anterior = float(actual or 0), float(anterior or 0)
    except (TypeError, ValueError):
        return None
    if anterior <= 0:
        return None
    return (actual - anterior) / anterior * 100


def _mismo_dia_mes_anterior(d):
    """20-oct → 20-sep; 31-mar → 28/29-feb (si el mes anterior es más corto)."""
    primero_anterior = (d.replace(day=1) - timedelta(days=1)).replace(day=1)
    ultimo = (d.replace(day=1) - timedelta(days=1)).day
    return primero_anterior.replace(day=min(d.day, ultimo))


def periodo_anterior(desde, hasta):
    """
    Con qué período comparar. Recibe y devuelve 'AAAA-MM-DD'; None si las
    fechas no sirven.
    - Mes en curso (desde el día 1): los mismos días del mes anterior.
      1..20 de octubre → 1..20 de septiembre.
    - Año en curso (desde el 1 de enero): los mismos días del año anterior.
    - Cualquier otro: mismo largo, justo antes. 08..14 oct → 01..07 oct.
    """
    try:
        d, h = _fecha(desde), _fecha(hasta)
    except Exception:
        return None
    if h < d:
        return None
    mismo_mes = (d.year, d.month) == (h.year, h.month)
    if d.day == 1 and mismo_mes:
        fin_de_mes = (h + timedelta(days=1)).day == 1
        h_prev = d - timedelta(days=1) if fin_de_mes else _mismo_dia_mes_anterior(h)
        return _mismo_dia_mes_anterior(d).isoformat(), h_prev.isoformat()
    if (d.month, d.day) == (1, 1) and d.year == h.year and (h.month, h.day) != (12, 31):
        try:
            h_prev = h.replace(year=h.year - 1)
        except ValueError:          # 29 de febrero
            h_prev = h.replace(year=h.year - 1, day=28)
        return d.replace(year=d.year - 1).isoformat(), h_prev.isoformat()
    largo = (h - d).days + 1
    fin = d - timedelta(days=1)
    inicio = fin - timedelta(days=largo - 1)
    return inicio.isoformat(), fin.isoformat()
