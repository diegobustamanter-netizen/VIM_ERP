from typing import Any, Dict, List, Optional
from .connection import session_db
from .utils import ahora


def obtener_liquidaciones(empleado_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Obtiene todas las liquidaciones, opcionalmente filtradas por empleado."""
    query = """
        SELECT l.*, e.nombre AS nombre_empleado, e.cargo
        FROM liquidaciones_sueldo l
        JOIN empleados e ON e.id = l.empleado_id
    """
    params = []
    if empleado_id:
        query += " WHERE l.empleado_id = ?"
        params.append(empleado_id)
    query += " ORDER BY l.periodo DESC"

    with session_db(dict_rows=True) as conn:
        return conn.execute(query, params).fetchall()


def crear_liquidacion(
    empleado_id: int,
    periodo: str,          # formato AAAA-MM  ej: 2026-04
    sueldo_base: float,
    bonos: float = 0,
    descuentos: float = 0,
    observacion: str = ""
) -> int:
    """Registra una nueva liquidación de sueldo y la refleja como gasto en compras."""
    total_liquido = sueldo_base + bonos - descuentos

    with session_db(dict_rows=True) as conn:
        cursor = conn.cursor()

        # 0. Evitar doble pago: ya existe liquidación vigente para este período
        existente = conn.execute(
            """SELECT id FROM liquidaciones_sueldo
               WHERE empleado_id = ? AND periodo = ? AND estado != 'anulada'""",
            (empleado_id, periodo)
        ).fetchone()
        if existente:
            raise ValueError(
                f"Ya existe una liquidación vigente para este empleado en el período {periodo}. "
                "Anúlela primero si necesita corregirla."
            )

        # 1. Insertar la liquidación. La tabla tiene UNIQUE(empleado_id, periodo),
        # así que si existe una ANULADA para este período se reutiliza esa fila
        # (antes esto fallaba con "UNIQUE constraint failed").
        anulada = conn.execute(
            """SELECT id FROM liquidaciones_sueldo
               WHERE empleado_id = ? AND periodo = ? AND estado = 'anulada'""",
            (empleado_id, periodo)
        ).fetchone()

        if anulada:
            liq_id = anulada["id"]
            cursor.execute(
                """
                UPDATE liquidaciones_sueldo
                SET sueldo_base = ?, bonos = ?, descuentos = ?, total_liquido = ?,
                    fecha_pago = ?, estado = 'pagado', observacion = ?
                WHERE id = ?
                """,
                (sueldo_base, bonos, descuentos, total_liquido, ahora(), observacion, liq_id)
            )
        else:
            cursor.execute(
                """
                INSERT INTO liquidaciones_sueldo
                    (empleado_id, periodo, sueldo_base, bonos, descuentos, total_liquido, fecha_pago, estado, observacion)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pagado', ?)
                """,
                (empleado_id, periodo, sueldo_base, bonos, descuentos, total_liquido, ahora(), observacion)
            )
            liq_id = cursor.lastrowid

        # 2. Registrar en tabla compras como gasto (tipo sueldos) para que aparezca en P&L
        # Buscar id de cuenta contable de sueldos
        cuenta_row = conn.execute(
            "SELECT id FROM plan_cuentas WHERE nombre LIKE '%sueldo%' OR nombre LIKE '%personal%' OR nombre LIKE '%remuneraci%' LIMIT 1"
        ).fetchone()
        cuenta_id = cuenta_row["id"] if cuenta_row else None

        empleado_row = conn.execute("SELECT nombre FROM empleados WHERE id = ?", (empleado_id,)).fetchone()
        nombre_emp = empleado_row["nombre"] if empleado_row else f"Empleado {empleado_id}"

        cursor.execute(
            """
            INSERT INTO compras
                (numero_documento, fecha, tipo_operacion, total, estado_pago, saldo_pendiente,
                 cuenta_contable_id, estado, observacion)
            VALUES (?, ?, 'sueldos', ?, 'pagado', 0, ?, 'registrada', ?)
            """,
            (
                f"LIQ-{periodo}-EMP{empleado_id}",
                ahora(),
                total_liquido,
                cuenta_id,
                f"Liquidación sueldo {nombre_emp} | Período: {periodo}"
            )
        )

        conn.commit()

    return liq_id


def anular_liquidacion(liq_id: int) -> bool:
    """Anula una liquidación y revierte el gasto asociado en compras.

    Antes solo marcaba la liquidación: el gasto 'sueldos' quedaba vivo en
    compras y el P&L seguía descontándolo aunque la liquidación estuviera
    anulada.
    """
    with session_db(dict_rows=True) as conn:
        liq = conn.execute(
            "SELECT empleado_id, periodo, estado FROM liquidaciones_sueldo WHERE id = ?",
            (liq_id,)
        ).fetchone()
        if not liq or liq["estado"] == "anulada":
            return False

        conn.execute(
            "UPDATE liquidaciones_sueldo SET estado = 'anulada' WHERE id = ?",
            (liq_id,)
        )

        # Revertir el gasto espejo en compras (creado por crear_liquidacion)
        conn.execute(
            """UPDATE compras SET estado = 'anulada', estado_pago = 'anulado', saldo_pendiente = 0
               WHERE numero_documento = ? AND tipo_operacion = 'sueldos' AND estado != 'anulada'""",
            (f"LIQ-{liq['periodo']}-EMP{liq['empleado_id']}",)
        )

        conn.commit()
        return True
