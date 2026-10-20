"""
Rate limiter anti fuerza bruta para login de VIM ERP.

Rastrea intentos fallidos por nombre de usuario en memoria.
Configuración:
  - 5 intentos fallidos
  - Bloqueo de 5 minutos (300 segundos)
  - Se resetea al cerrar la aplicación
"""

import time
from collections import defaultdict

MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 300
CLEANUP_INTERVAL = 600


class LoginRateLimiter:
    def __init__(self):
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup = time.monotonic()

    def _cleanup(self):
        now = time.monotonic()
        if now - self._last_cleanup < CLEANUP_INTERVAL:
            return
        cutoff = now - LOCKOUT_SECONDS
        expired = [k for k, v in self._failures.items()
                   if not any(t > cutoff for t in v)]
        for k in expired:
            del self._failures[k]
        self._last_cleanup = now

    def is_locked_out(self, username: str) -> bool:
        self._cleanup()
        if username not in self._failures:
            return False
        now = time.monotonic()
        cutoff = now - LOCKOUT_SECONDS
        recent = [t for t in self._failures[username] if t > cutoff]
        self._failures[username] = recent
        return len(recent) >= MAX_ATTEMPTS

    def record_failure(self, username: str):
        self._failures[username].append(time.monotonic())
        from vim_logger import get_logger
        get_logger("seguridad.rate_limiter").warning(
            "Intento fallido para '%s' (%d de %d)",
            username, len(self._failures[username]), MAX_ATTEMPTS
        )

    def reset(self, username: str):
        self._failures.pop(username, None)

    def remaining_attempts(self, username: str) -> int:
        self._cleanup()
        if username not in self._failures:
            return MAX_ATTEMPTS
        now = time.monotonic()
        cutoff = now - LOCKOUT_SECONDS
        recent = [t for t in self._failures[username] if t > cutoff]
        return max(0, MAX_ATTEMPTS - len(recent))


limiter = LoginRateLimiter()
