import time

class Sesion:
    """Clase Singleton para gestionar el usuario logueado en la aplicación."""
    _usuario_actual = None
    _permisos_modulos = {}
    _tiempo_inicio = 0
    _ultima_actividad = 0
    _autorizaciones = {}   # ámbito -> momento en que se autorizó

    # Cierre automático por inactividad.
    #   0 (o negativo) = DESACTIVADO, la sesión no expira nunca.
    #   > 0            = segundos de inactividad antes de cerrar (1800 = 30 min).
    #
    # Desactivado a pedido: cerrar la aplicación entera dejaba al cajero
    # teniendo que reabrir el sistema, y se perdía cualquier venta a medio
    # armar. Para reactivarlo basta con poner los segundos deseados acá.
    _timeout_segundos = 0

    @classmethod
    def iniciar(cls, datos_usuario):
        cls._usuario_actual = datos_usuario
        cls._tiempo_inicio = time.time()
        cls._ultima_actividad = time.time()
        # Cargar permisos granulares desde la DB
        cls._cargar_permisos()

    @classmethod
    def _cargar_permisos(cls):
        """Carga los permisos por módulo del usuario actual."""
        if not cls._usuario_actual:
            cls._permisos_modulos = {}
            return
        try:
            from database.usuarios import obtener_permisos_usuario
            cls._permisos_modulos = obtener_permisos_usuario(cls._usuario_actual["id"])
        except Exception as e:
            from vim_logger import get_logger
            get_logger("seguridad.sesion").error(f"Error cargando permisos: {e}")
            cls._permisos_modulos = {}

    @classmethod
    def recargar_permisos(cls):
        """Recarga permisos desde la DB (útil después de editar permisos)."""
        cls._cargar_permisos()

    @classmethod
    def cerrar(cls):
        cls._usuario_actual = None
        cls._permisos_modulos = {}
        cls._tiempo_inicio = 0
        cls._ultima_actividad = 0
        cls.limpiar_autorizaciones()

    # ============================================================
    # AUTORIZACIONES RECIENTES (ventana de gracia)
    # ============================================================
    # Cuando un admin autoriza una acción con su contraseña, esa autorización
    # queda vigente unos segundos para no pedirla de nuevo si repite la misma
    # acción (ej. borrar varios productos seguidos).
    #
    # Se guarda POR ÁMBITO: autorizar el borrado de productos no habilita
    # anular ventas ni restaurar la base. Y se borra al cerrar sesión.

    @classmethod
    def registrar_autorizacion(cls, ambito: str):
        """Deja constancia de que se autorizó `ambito` recién ahora."""
        if ambito:
            cls._autorizaciones[ambito] = time.time()

    @classmethod
    def autorizacion_vigente(cls, ambito: str, segundos: int) -> bool:
        """True si `ambito` fue autorizado hace menos de `segundos`."""
        if not cls._usuario_actual or not ambito or segundos <= 0:
            return False
        momento = cls._autorizaciones.get(ambito)
        if momento is None:
            return False
        return (time.time() - momento) <= segundos

    @classmethod
    def segundos_restantes_autorizacion(cls, ambito: str, segundos: int) -> int:
        """Cuántos segundos le quedan de vigencia a la autorización."""
        momento = cls._autorizaciones.get(ambito)
        if momento is None:
            return 0
        return max(0, int(segundos - (time.time() - momento)))

    @classmethod
    def limpiar_autorizaciones(cls):
        cls._autorizaciones = {}

    @classmethod
    def registrar_actividad(cls):
        """Actualiza el timestamp de última actividad del usuario."""
        cls._ultima_actividad = time.time()

    @classmethod
    def timeout_activo(cls) -> bool:
        """True si el cierre automático por inactividad está habilitado."""
        return cls._timeout_segundos > 0

    @classmethod
    def sesion_expirada(cls) -> bool:
        """Verifica si la sesión ha expirado por inactividad."""
        if not cls._usuario_actual or not cls.timeout_activo():
            return False
        return (time.time() - cls._ultima_actividad) > cls._timeout_segundos

    @classmethod
    def tiempo_restante(cls) -> int:
        """Segundos restantes antes de que expire la sesión (-1 si no expira)."""
        if not cls._usuario_actual or not cls.timeout_activo():
            return -1
        restante = cls._timeout_segundos - (time.time() - cls._ultima_actividad)
        return max(0, int(restante))

    @classmethod
    def get_usuario(cls):
        return cls._usuario_actual

    @classmethod
    def get_usuario_id(cls):
        return cls._usuario_actual["id"] if cls._usuario_actual else None

    @classmethod
    def get_rol(cls):
        return cls._usuario_actual["rol"] if cls._usuario_actual else None

    @classmethod
    def get_nombre(cls):
        return cls._usuario_actual["nombre"] if cls._usuario_actual else "Invitado"

    @classmethod
    def es_admin(cls):
        return cls.get_rol() == "administrador"

    @classmethod
    def tiene_permiso(cls, nivel_requerido):
        """
        Niveles: 'cajero', 'supervisor', 'administrador'
        """
        if not cls._usuario_actual:
            return False
            
        niveles = {
            "cajero": 1,
            "supervisor": 2,
            "administrador": 3
        }
        
        user_level = niveles.get(cls.get_rol(), 0)
        req_level = niveles.get(nivel_requerido, 0)
        
        return user_level >= req_level

    @classmethod
    def puede_acceder(cls, modulo: str) -> bool:
        """
        Verifica si el usuario actual puede acceder a un módulo específico.
        Los administradores siempre tienen acceso total.
        Para otros roles, se verifica el permiso granular en la tabla permisos_modulo.
        """
        if not cls._usuario_actual:
            return False

        # Administrador siempre tiene acceso total
        if cls.get_rol() == "administrador":
            return True

        return cls._permisos_modulos.get(modulo, False)

    @classmethod
    def get_permisos(cls) -> dict:
        """Retorna copia del dict de permisos actuales."""
        return dict(cls._permisos_modulos)
