from typing import Any, Dict, Tuple
from .connection import session_db
from .negocio import es_negocio_de_servicios, etiqueta_costo_ventas, maneja_inventario


def _normalizar_periodo(fecha_inicio: str, fecha_fin: str) -> Tuple[str, str]:
    """Rellena fechas vacías para no romper los rangos de las consultas."""
    return (fecha_inicio or "1900-01-01", fecha_fin or "2999-12-31")


def _iva_credito_periodo(conn, fecha_inicio: str, fecha_fin: str) -> float:
    """IVA crédito del período: solo compras con factura dan derecho a crédito.

    Fuente única de verdad, usada por el Estado de Resultados y por el
    Reporte de IVA, para que ambos no puedan divergir.
    """
    fila = conn.execute(
        """
        SELECT SUM(COALESCE(impuesto, 0)) as iva_credito
        FROM compras
        WHERE fecha >= ? AND fecha < date(?, '+1 day')
          AND estado != 'anulada'
          AND tipo_documento IN ('factura', 'factura_electronica')
        """,
        (fecha_inicio, fecha_fin)
    ).fetchone()
    return (fila['iva_credito'] or 0) if fila else 0


def obtener_estado_resultados(fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
    """
    Calcula el Estado de Resultados (P&L) para un período dado con KPIs avanzados.
    """
    fecha_inicio, fecha_fin = _normalizar_periodo(fecha_inicio, fecha_fin)

    with session_db(dict_rows=True) as conn:
        # 1. Ingresos por Ventas (Neto: sin impuestos)
        ingresos_stats = conn.execute(
            """
            SELECT 
                SUM(COALESCE(total, 0) - COALESCE(impuesto, 0)) as neto,
                SUM(COALESCE(impuesto, 0)) as impuestos
            FROM ventas 
            WHERE fecha >= ? AND fecha < date(?, '+1 day') AND estado = 'completada'
            """,
            (fecha_inicio, fecha_fin)
        ).fetchone()
        
        ingresos_ventas = ingresos_stats['neto'] or 0
        recaudacion_impuestos = ingresos_stats['impuestos'] or 0

        # 2. Costo de Ventas (COGS)
        costo_ventas = conn.execute(
            """
            SELECT SUM(dv.cantidad * dv.costo_unitario) as total 
            FROM detalle_ventas dv
            JOIN ventas v ON dv.venta_id = v.id
            WHERE v.fecha >= ? AND v.fecha < date(?, '+1 day') AND v.estado = 'completada'
            """,
            (fecha_inicio, fecha_fin)
        ).fetchone()['total'] or 0

        # 3. Gastos Operativos (compras)
        #
        # IMPORTANTE - dos exclusiones que evitan distorsionar la utilidad:
        #
        # a) Compras inventariables (es_inventariable = 1, típicamente
        #    "Mercaderías"): NO son gasto al comprarlas. Se reconocen como
        #    Costo de Ventas recién cuando el producto se vende. Incluirlas
        #    aquí las contaba dos veces y mostraba pérdidas inexistentes.
        #
        # b) Activos fijos (maquinaria, instalaciones): son inversión, no
        #    gasto del período. Se recuperan vía depreciación, no de golpe
        #    en el mes de la compra.
        gastos_compras = conn.execute(
            """
            SELECT
                COALESCE(pc.nombre,
                    CASE c.tipo_operacion
                        WHEN 'sueldos' THEN 'Sueldos y Remuneraciones'
                        WHEN 'gasto_operativo' THEN 'Gastos Operativos'
                        ELSE 'Otros Gastos'
                    END
                ) as cuenta,
                SUM(COALESCE(c.subtotal, 0)) as total
            FROM compras c
            LEFT JOIN plan_cuentas pc ON c.cuenta_contable_id = pc.id
            WHERE c.fecha >= ? AND c.fecha < date(?, '+1 day')
              AND c.estado != 'anulada'
              AND COALESCE(pc.es_inventariable, 0) = 0
              AND COALESCE(c.tipo_operacion, '') != 'activo_fijo'
              AND COALESCE(pc.tipo, '') != 'activo'
              AND (
                pc.tipo = 'egreso'
                OR c.tipo_operacion IN ('gasto_operativo', 'sueldos')
              )
            GROUP BY COALESCE(pc.id, c.tipo_operacion)
            ORDER BY total DESC
            """,
            (fecha_inicio, fecha_fin)
        ).fetchall()

        # Egresos ad-hoc de caja (gastos pagados directo de caja, sin compra
        # asociada). Solo egresos: antes se restaban también los ingresos
        # ad-hoc, así que meter plata a la caja (un aporte, un préstamo)
        # bajaba los gastos y hacía subir la utilidad sin haber vendido nada.
        #
        # NOTA: estos montos salen de caja tal cual se registraron (brutos,
        # con IVA si lo tenían), mientras que las compras usan subtotal neto.
        gastos_caja = conn.execute(
            """
            SELECT 'Egresos de Caja (Ad-hoc)' as cuenta,
                   SUM(COALESCE(monto, 0)) as total
            FROM movimientos_caja
            WHERE fecha >= ? AND fecha < date(?, '+1 day')
              AND tipo = 'egreso'
              AND (
                referencia_tabla IS NULL
                OR referencia_tabla NOT IN ('compras', 'ventas', 'pagos_documentos')
              )
            """,
            (fecha_inicio, fecha_fin)
        ).fetchone()

        # Ingresos ad-hoc de caja: se informan aparte, NO se netean contra los
        # gastos. Quedan fuera de la utilidad porque pueden ser aportes de
        # capital o préstamos, que no son ingresos del negocio.
        ingresos_caja_row = conn.execute(
            """
            SELECT SUM(COALESCE(monto, 0)) as total
            FROM movimientos_caja
            WHERE fecha >= ? AND fecha < date(?, '+1 day')
              AND tipo = 'ingreso'
              AND (
                referencia_tabla IS NULL
                OR referencia_tabla NOT IN ('compras', 'ventas', 'pagos_documentos')
              )
            """,
            (fecha_inicio, fecha_fin)
        ).fetchone()
        otros_ingresos_caja = (ingresos_caja_row['total'] or 0) if ingresos_caja_row else 0

        gastos_detallados = list(gastos_compras)
        if gastos_caja and gastos_caja['total']:
            gastos_detallados.append({'cuenta': gastos_caja['cuenta'], 'total': gastos_caja['total']})

        # COALESCE en SQL ya evita NULL, pero el `or 0` protege ante filas
        # antiguas o vistas que devuelvan NULL igual.
        total_gastos = sum((g['total'] or 0) for g in gastos_detallados)

        # CÁLCULOS FINANCIEROS
        utilidad_bruta = ingresos_ventas - costo_ventas
        utilidad_neta = utilidad_bruta - total_gastos
        
        # Márgenes (%)
        margen_bruto_pct = (utilidad_bruta / ingresos_ventas * 100) if ingresos_ventas > 0 else 0
        margen_neto_pct = (utilidad_neta / ingresos_ventas * 100) if ingresos_ventas > 0 else 0
        
        # Punto de Equilibrio Estimado: cuánto hay que vender para cubrir los
        # gastos operativos. Trata TODO gasto operativo como fijo, así que es
        # una estimación (los gastos variables inflan el resultado).
        punto_equilibrio = (total_gastos / (margen_bruto_pct / 100)) if margen_bruto_pct > 0 else 0

        # Análisis Vertical para Gastos
        gastos_con_porcentaje = []
        for g in gastos_detallados:
            monto_g = g['total'] or 0
            pct = (monto_g / ingresos_ventas * 100) if ingresos_ventas > 0 else 0
            gastos_con_porcentaje.append({**g, 'porcentaje': pct})

        # 4. Impuestos Estimados (IVA a Pagar)
        # Usa el mismo helper que obtener_reporte_iva() para que ambos reportes
        # no puedan mostrar cifras distintas del mismo impuesto.
        iva_credito = _iva_credito_periodo(conn, fecha_inicio, fecha_fin)
        impuestos_estimados = recaudacion_impuestos - iva_credito

        # ============================================================
        # PRESENTACIÓN SEGÚN EL TIPO DE NEGOCIO
        # ============================================================
        # En un negocio de servicios no existe costo de inventario. El costo
        # directo (insumos, comisión) es opcional: si nadie lo carga queda en
        # 0, y mostrar "Costo 0 / Margen 100%" solo genera ruido. Por eso las
        # líneas de costo y margen bruto se ocultan cuando no hay costo.
        modo_servicios = es_negocio_de_servicios()
        hay_costo = costo_ventas > 0
        mostrar_costo = hay_costo or not modo_servicios

        return {
            "ingresos_ventas": ingresos_ventas,
            "recaudacion_impuestos": recaudacion_impuestos,
            # --- Metadatos de presentación (no afectan ningún cálculo) ---
            "modo_negocio": "servicios" if modo_servicios else "productos",
            "etiqueta_ingresos": "Ingresos por servicios" if modo_servicios else "Ventas Netas",
            "etiqueta_costo": etiqueta_costo_ventas(),
            "mostrar_costo": mostrar_costo,
            "mostrar_margen_bruto": mostrar_costo,
            "costo_ventas": costo_ventas,
            "utilidad_bruta": utilidad_bruta,
            "margen_bruto_pct": margen_bruto_pct,
            "gastos_detallados": gastos_con_porcentaje,
            "total_gastos": total_gastos,
            "utilidad_neta": utilidad_neta,
            "margen_neto_pct": margen_neto_pct,
            "punto_equilibrio": punto_equilibrio,
            "impuestos_estimados": impuestos_estimados,
            # Informativo: NO suma a la utilidad. Puede ser aporte de capital,
            # préstamo o devolución, que no son ingresos del negocio.
            "otros_ingresos_caja": otros_ingresos_caja
        }

def obtener_reporte_iva(fecha_inicio: str, fecha_fin: str) -> Dict[str, Any]:
    """
    Genera un reporte básico de IVA (Débito, Crédito, a Pagar).
    """
    fecha_inicio, fecha_fin = _normalizar_periodo(fecha_inicio, fecha_fin)

    with session_db(dict_rows=True) as conn:
        # IVA Débito (Ventas)
        ventas_stats = conn.execute(
            """
            SELECT 
                SUM(COALESCE(total, 0) - COALESCE(impuesto, 0)) as ventas_netas,
                SUM(COALESCE(impuesto, 0)) as iva_debito
            FROM ventas 
            WHERE fecha >= ? AND fecha < date(?, '+1 day') AND estado = 'completada'
            """,
            (fecha_inicio, fecha_fin)
        ).fetchone()

        # Compras netas con factura (para contexto del reporte)
        compras_stats = conn.execute(
            """
            SELECT SUM(COALESCE(subtotal, 0)) as compras_netas
            FROM compras
            WHERE fecha >= ? AND fecha < date(?, '+1 day') AND estado != 'anulada'
            AND tipo_documento IN ('factura', 'factura_electronica')
            """,
            (fecha_inicio, fecha_fin)
        ).fetchone()

        ventas_netas = ventas_stats['ventas_netas'] if ventas_stats and ventas_stats['ventas_netas'] else 0
        iva_debito = ventas_stats['iva_debito'] if ventas_stats and ventas_stats['iva_debito'] else 0
        compras_netas = compras_stats['compras_netas'] if compras_stats and compras_stats['compras_netas'] else 0

        # Mismo helper que usa el Estado de Resultados (fuente única)
        iva_credito = _iva_credito_periodo(conn, fecha_inicio, fecha_fin)


        iva_a_pagar = iva_debito - iva_credito

        return {
            "ventas_netas": ventas_netas,
            "iva_debito": iva_debito,
            "compras_netas": compras_netas,
            "iva_credito": iva_credito,
            "iva_a_pagar": iva_a_pagar,
            "resultado_iva": "a_pagar" if iva_a_pagar > 0 else "a_favor"
        }


def obtener_resumen_balance_general() -> Dict[str, Any]:
    """
    Obtiene una fotografía rápida del Balance General (Activos vs Pasivos) con indicadores.
    """
    # En un negocio de servicios no hay inventario que valorizar: la consulta
    # daría 0 igual (excluye tipo_item='servicio'), pero mostrar una línea de
    # inventario en $0 hace dudar de que el reporte esté bien.
    con_inventario = maneja_inventario()

    with session_db(dict_rows=True) as conn:
        if con_inventario:
            valor_inventario = conn.execute(
                "SELECT SUM(stock * precio_compra) as total FROM productos WHERE activo = 1 AND tipo_item != 'servicio'"
            ).fetchone()['total'] or 0
        else:
            valor_inventario = 0

        efectivo_total = conn.execute(
            """
            SELECT 
                SUM(CASE WHEN tipo LIKE 'venta_%' OR tipo = 'ingreso' THEN monto ELSE 0 END) -
                SUM(CASE WHEN tipo = 'egreso' THEN monto ELSE 0 END) as total
            FROM movimientos_caja
            """
        ).fetchone()['total'] or 0

        cuentas_por_pagar = conn.execute(
            "SELECT SUM(saldo_pendiente) as total FROM compras WHERE estado_pago != 'pagado' AND estado != 'anulada'"
        ).fetchone()['total'] or 0

        activos_totales = valor_inventario + efectivo_total
        pasivos_totales = cuentas_por_pagar
        patrimonio = activos_totales - pasivos_totales
        
        # Ratio de Liquidez (Activo Circulante / Pasivo Circulante)
        if pasivos_totales > 0:
            ratio_liquidez = activos_totales / pasivos_totales
        else:
            ratio_liquidez = -1  # Indicador especial de sin deudas

        return {
            "mostrar_inventario": con_inventario,
            "activos": {
                "inventario": valor_inventario,
                "efectivo": efectivo_total,
                "total_activos": activos_totales
            },
            "pasivos": {
                "cuentas_por_pagar": pasivos_totales,
                "total_pasivos": pasivos_totales
            },
            "patrimonio_estimado": patrimonio,
            "ratio_liquidez": ratio_liquidez
        }
