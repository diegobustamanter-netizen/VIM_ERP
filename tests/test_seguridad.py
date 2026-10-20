"""Seguridad: contraseñas, sesión y la ventana de gracia de autorizaciones."""

import time

from base import PruebaVIM

VENTANA = 60
AMBITO = "eliminar_producto"


class PruebaVentanaDeGracia(PruebaVIM):
    """Tras autorizar una acción, no se vuelve a pedir la clave por un minuto.

    Es una flexibilización deliberada de la seguridad: estas pruebas cuidan
    que no se vuelva más flexible de lo acordado.
    """

    def setUp(self):
        super().setUp()
        from modulos.seguridad.sesion import Sesion
        self.Sesion = Sesion
        Sesion.iniciar({"id": 1, "nombre": "Prueba", "rol": "administrador"})

    def tearDown(self):
        self.Sesion.cerrar()
        super().tearDown()

    def test_sin_autorizar_no_hay_vigencia(self):
        self.assertFalse(self.Sesion.autorizacion_vigente(AMBITO, VENTANA))

    def test_recien_autorizado_esta_vigente(self):
        self.Sesion.registrar_autorizacion(AMBITO)
        self.assertTrue(self.Sesion.autorizacion_vigente(AMBITO, VENTANA))

    def test_expira_pasada_la_ventana(self):
        self.Sesion.registrar_autorizacion(AMBITO)
        # Simular el paso del tiempo sin esperar 61 segundos reales
        self.Sesion._autorizaciones[AMBITO] = time.time() - (VENTANA + 1)

        self.assertFalse(self.Sesion.autorizacion_vigente(AMBITO, VENTANA),
                         "La autorización no expiró")

    def test_sigue_vigente_justo_antes_de_expirar(self):
        self.Sesion.registrar_autorizacion(AMBITO)
        self.Sesion._autorizaciones[AMBITO] = time.time() - (VENTANA - 5)

        self.assertTrue(self.Sesion.autorizacion_vigente(AMBITO, VENTANA))
        self.assertGreater(self.Sesion.segundos_restantes_autorizacion(AMBITO, VENTANA), 0)

    def test_no_se_contagia_entre_acciones(self):
        """LO MÁS IMPORTANTE: autorizar un borrado no habilita otra cosa."""
        self.Sesion.registrar_autorizacion(AMBITO)

        for otro in ("anular_venta", "restaurar_backup", "vaciar_ticket",
                     "modificar_precio"):
            with self.subTest(ambito=otro):
                self.assertFalse(
                    self.Sesion.autorizacion_vigente(otro, VENTANA),
                    f"Autorizar '{AMBITO}' habilitó '{otro}'")

    def test_cerrar_sesion_borra_las_autorizaciones(self):
        """Si se va el admin y entra un cajero, la ventana no puede seguir viva."""
        self.Sesion.registrar_autorizacion(AMBITO)
        self.assertTrue(self.Sesion.autorizacion_vigente(AMBITO, VENTANA))

        self.Sesion.cerrar()

        self.assertFalse(self.Sesion.autorizacion_vigente(AMBITO, VENTANA),
                         "La autorización sobrevivió al cierre de sesión")

    def test_sin_ambito_nunca_hay_vigencia(self):
        """Las llamadas que no declaran ámbito piden la clave siempre."""
        self.Sesion.registrar_autorizacion(AMBITO)
        self.assertFalse(self.Sesion.autorizacion_vigente(None, VENTANA))

    def test_ventana_en_cero_desactiva_la_gracia(self):
        self.Sesion.registrar_autorizacion(AMBITO)
        self.assertFalse(self.Sesion.autorizacion_vigente(AMBITO, 0))


class PruebaSesion(PruebaVIM):

    def setUp(self):
        super().setUp()
        from modulos.seguridad.sesion import Sesion
        self.Sesion = Sesion

    def tearDown(self):
        self.Sesion._timeout_segundos = 0
        self.Sesion.cerrar()
        super().tearDown()

    def test_el_cierre_por_inactividad_esta_desactivado(self):
        """Se desactivó a pedido: la sesión no debe expirar sola."""
        self.Sesion.iniciar({"id": 1, "nombre": "Prueba", "rol": "administrador"})
        self.Sesion._ultima_actividad = time.time() - 999999

        self.assertFalse(self.Sesion.timeout_activo())
        self.assertFalse(self.Sesion.sesion_expirada(),
                         "La sesión expiró aunque el timeout está desactivado")
        self.assertEqual(self.Sesion.tiempo_restante(), -1)

    def test_se_puede_reactivar_el_timeout(self):
        """Poner los segundos deseados tiene que alcanzar para reactivarlo."""
        self.Sesion.iniciar({"id": 1, "nombre": "Prueba", "rol": "administrador"})
        self.Sesion._timeout_segundos = 1800
        self.Sesion._ultima_actividad = time.time() - 1801

        self.assertTrue(self.Sesion.timeout_activo())
        self.assertTrue(self.Sesion.sesion_expirada())


class PruebaContrasenas(PruebaVIM):

    def test_las_contrasenas_no_se_guardan_en_texto_plano(self):
        from modulos.seguridad.auth import hash_password

        guardado = hash_password("1234")

        self.assertNotIn("1234", guardado)
        self.assertGreater(len(guardado), 40, "El hash parece demasiado corto")

    def test_el_mismo_texto_da_hashes_distintos(self):
        """Con salt, dos usuarios con la misma clave no comparten hash."""
        from modulos.seguridad.auth import hash_password

        self.assertNotEqual(hash_password("1234"), hash_password("1234"))

    def test_la_verificacion_acepta_la_correcta_y_rechaza_la_incorrecta(self):
        from modulos.seguridad.auth import hash_password, verify_password

        guardado = hash_password("miClave123")

        self.assertTrue(verify_password("miClave123", guardado))
        self.assertFalse(verify_password("miClave124", guardado))
        self.assertFalse(verify_password("", guardado))
