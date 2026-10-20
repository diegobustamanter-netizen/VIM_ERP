import hashlib
import hmac
import os
from database.connection import session_db
from database.utils import ahora

def hash_password(password, salt=None):
    if not password:
        return ""
    if not salt:
        salt = os.urandom(16).hex()
    pwd_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    # PBKDF2 with 100k iterations is safe enough for a desktop app
    hash_obj = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
    return f"{salt}${hash_obj.hex()}"

def verify_password(password, stored_hash):
    if not stored_hash:
        return False
    if "$" not in stored_hash:
        from vim_logger import get_logger
        get_logger("seguridad.auth").critical(
            "SECURITY: Hash de contraseña corrupto o en texto plano detectado. "
            "El administrador debe resetear esta cuenta manualmente."
        )
        return False
    try:
        salt, _ = stored_hash.split('$', 1)
        # compare_digest evita ataques de timing (comparación en tiempo constante)
        return hmac.compare_digest(hash_password(password, salt), stored_hash)
    except Exception:
        return False

def autenticar_usuario(username, password):
    """
    Valida las credenciales de un usuario con proteccion anti fuerza bruta.
    Retorna el dict del usuario si es exito, None en caso contrario.
    """
    from .rate_limiter import limiter

    username = username.strip()

    if limiter.is_locked_out(username):
        return None

    with session_db(dict_rows=True) as conn:
        user = conn.execute(
            "SELECT * FROM usuarios WHERE username = ? AND activo = 1",
            (username,)
        ).fetchone()

        if user and verify_password(password, user["password_hash"]):
            limiter.reset(username)
            conn.execute(
                "UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?",
                (ahora(), user["id"])
            )
            conn.commit()
            return dict(user)

    limiter.record_failure(username)
    return None

def validar_admin(password):
    """Valida si la contraseña corresponde a un usuario con rol administrador."""
    with session_db(dict_rows=True) as conn:
        # Buscamos cualquier admin activo
        admins = conn.execute(
            "SELECT password_hash FROM usuarios WHERE rol = 'administrador' AND activo = 1"
        ).fetchall()
        
        for row in admins:
            if verify_password(password, row["password_hash"]):
                return True
    return False
