from datetime import datetime


def ahora(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Timestamp unificado para toda la aplicacion.
    
    Uso: 
        ahora()                    # '2026-07-14 15:30:00' (formato DB)
        ahora("%d/%m/%Y %H:%M")    # '14/07/2026 15:30' (formato pantalla)
        ahora("%Y%m%d_%H%M%S")     # '20260714_153000' (nombres archivo)
    """
    return datetime.now().strftime(fmt)