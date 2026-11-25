
from unittest.mock import patch

import numpy as np

from cryptography.fernet import Fernet

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from .models import RegistroFacial
from .cifrado_facial import descifrar_datos_faciales
from .servicios_faciales import deserializar_vector_facial


Usuario = get_user_model()


@override_settings(
    POWERFIT_FERNET_KEY=Fernet.generate_key().decode("utf-8")
)
class PruebasEnrolamientoFacial(TestCase):

    def setUp(self):
        self.cliente = APIClient()

        self.duena = Usuario.objects.create_user(
            username="duena_prueba_facial",
            email="duena_facial@test.local",
            password="ClavePrueba123!",
            rol="DUENA",
        )

        self.socio = Usuario.objects.create_user(
            username="socio_prueba_facial",
            email="socio_facial@test.local",
            password="ClavePrueba123!",
            rol="SOCIO",
        )

        self.coach = Usuario.objects.create_user(
            username="coach_prueba_facial",
            email="coach_facial@test.local",
            password="ClavePrueba123!",
            rol="COACH",
        )

        self.ruta = reverse("enrolamiento-facial")

    def consultar(self, usuario=None, socio_id=None):
        self.cliente.force_authenticate(user=usuario)

        ruta = self.ruta

        if socio_id is not None:
            ruta = f"{ruta}?socio_id={socio_id}"

        return self.cliente.get(ruta)

    def crear_consentimiento(self):
        ahora = timezone.now()

        return RegistroFacial.objects.create(
            socio=self.socio,
            consentimiento_otorgado=True,
            consentimiento_confirmado_por_socio=True,
            fecha_consentimiento=ahora,
            fecha_confirmacion_socio=ahora,
            version_consentimiento="1.0",
            activo=False,
        )

    def crear_imagen_prueba(self):
        return SimpleUploadedFile(
            "rostro_prueba.jpg",
            b"contenido_simulado",
            content_type="image/jpeg",
        )

    def enrolar(self, usuario=None, socio_id=None, imagen=None):
        self.cliente.force_authenticate(user=usuario)

        datos = {}

        if socio_id is not None:
            datos["socio_id"] = socio_id

        if imagen is not None:
            datos["imagen"] = imagen

        return self.cliente.post(
            self.ruta,
            datos,
            format="multipart",
        )

    def test_duena_puede_acceder(self):
        respuesta = self.consultar(self.duena)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(
            respuesta.data["enrolamiento_disponible"]
        )

    def test_socio_no_puede_acceder(self):
        respuesta = self.consultar(self.socio)

        self.assertEqual(respuesta.status_code, 403)

    def test_coach_no_puede_acceder(self):
        respuesta = self.consultar(self.coach)

        self.assertEqual(respuesta.status_code, 403)

    def test_usuario_sin_sesion_no_puede_acceder(self):
        respuesta = self.consultar()

        self.assertIn(respuesta.status_code, [401, 403])

    def test_socio_sin_consentimiento_no_cumple_condiciones(self):
        respuesta = self.consultar(
            self.duena,
            self.socio.id,
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertFalse(
            respuesta.data["consentimiento_valido"]
        )

        self.assertFalse(
            respuesta.data["cumple_condiciones_previas"]
        )

        self.assertFalse(
            respuesta.data["enrolamiento_disponible"]
        )

    def test_socio_con_consentimiento_cumple_condiciones_previas(self):
        self.crear_consentimiento()

        respuesta = self.consultar(
            self.duena,
            self.socio.id,
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertTrue(
            respuesta.data["consentimiento_valido"]
        )

        self.assertTrue(
            respuesta.data["cumple_condiciones_previas"]
        )

        self.assertTrue(
            respuesta.data["enrolamiento_disponible"]
        )

    def test_consentimiento_revocado_bloquea_enrolamiento(self):
        ahora = timezone.now()

        RegistroFacial.objects.create(
            socio=self.socio,
            consentimiento_otorgado=False,
            consentimiento_confirmado_por_socio=False,
            fecha_confirmacion_socio=ahora,
            fecha_revocacion=ahora,
            version_consentimiento="1.0",
        )

        respuesta = self.consultar(
            self.duena,
            self.socio.id,
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertFalse(
            respuesta.data["cumple_condiciones_previas"]
        )

    def test_socio_con_datos_almacenados_no_puede_reenrolarse(self):
        ahora = timezone.now()

        RegistroFacial.objects.create(
            socio=self.socio,
            consentimiento_otorgado=True,
            consentimiento_confirmado_por_socio=True,
            fecha_confirmacion_socio=ahora,
            version_consentimiento="1.0",
            datos_biometricos_cifrados=b"datos_ficticios",
        )

        respuesta = self.consultar(
            self.duena,
            self.socio.id,
        )

        self.assertEqual(respuesta.status_code, 200)

        self.assertFalse(
            respuesta.data["cumple_condiciones_previas"]
        )

    def test_socio_inexistente_devuelve_404(self):
        respuesta = self.consultar(
            self.duena,
            999999,
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_socio_id_invalido_devuelve_400(self):
        respuesta = self.consultar(
            self.duena,
            "abc",
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_post_socio_no_puede_enrolar(self):
        respuesta = self.enrolar(
            self.socio,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_post_coach_no_puede_enrolar(self):
        respuesta = self.enrolar(
            self.coach,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_post_usuario_sin_sesion_no_puede_enrolar(self):
        respuesta = self.enrolar(
            None,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertIn(respuesta.status_code, [401, 403])

    def test_post_sin_socio_id_devuelve_400(self):
        respuesta = self.enrolar(
            self.duena,
            imagen=self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_post_socio_id_invalido_devuelve_400(self):
        respuesta = self.enrolar(
            self.duena,
            "abc",
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_post_socio_inexistente_devuelve_404(self):
        respuesta = self.enrolar(
            self.duena,
            999999,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_post_sin_consentimiento_bloquea_enrolamiento(self):
        respuesta = self.enrolar(
            self.duena,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 400)

        self.socio.refresh_from_db()

        self.assertFalse(
            self.socio.reconocimiento_facial_habilitado
        )

    def test_post_sin_imagen_devuelve_400(self):
        self.crear_consentimiento()

        respuesta = self.enrolar(
            self.duena,
            self.socio.id,
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_post_consentimiento_revocado_bloquea_enrolamiento(self):
        registro = self.crear_consentimiento()

        registro.consentimiento_otorgado = False
        registro.consentimiento_confirmado_por_socio = False
        registro.fecha_revocacion = timezone.now()

        registro.save()

        respuesta = self.enrolar(
            self.duena,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 400)

        registro.refresh_from_db()

        self.assertFalse(registro.activo)
        self.assertIsNone(registro.datos_biometricos_cifrados)

    def test_post_imagen_invalida_devuelve_400(self):
        registro = self.crear_consentimiento()

        respuesta = self.enrolar(
            self.duena,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 400)

        registro.refresh_from_db()

        self.assertFalse(registro.activo)
        self.assertIsNone(registro.datos_biometricos_cifrados)

    @patch("usuarios.views.generar_vector_facial")
    def test_post_enrolamiento_correcto(self, generar_vector):
        registro = self.crear_consentimiento()

        vector_original = np.linspace(
            0,
            1,
            128,
            dtype=np.float64,
        )

        generar_vector.return_value = vector_original

        respuesta = self.enrolar(
            self.duena,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data,
        )

        registro.refresh_from_db()
        self.socio.refresh_from_db()

        self.assertTrue(registro.activo)

        self.assertTrue(
            self.socio.reconocimiento_facial_habilitado
        )

        self.assertIsNotNone(
            registro.datos_biometricos_cifrados
        )

        self.assertIsNotNone(
            registro.fecha_enrolamiento
        )

        self.assertEqual(
            registro.registrado_por_id,
            self.duena.id,
        )

        datos_cifrados = bytes(
            registro.datos_biometricos_cifrados
        )

        self.assertNotEqual(
            datos_cifrados,
            vector_original.astype("<f8").tobytes(),
        )

        datos_descifrados = descifrar_datos_faciales(
            datos_cifrados
        )

        vector_recuperado = deserializar_vector_facial(
            datos_descifrados
        )

        self.assertEqual(len(vector_recuperado), 128)

        self.assertTrue(
            np.array_equal(
                vector_original,
                vector_recuperado,
            )
        )

        self.assertTrue(respuesta.data["activo"])

        self.assertNotIn(
            "datos_biometricos_cifrados",
            respuesta.data,
        )

        generar_vector.assert_called_once()

    @patch("usuarios.views.generar_vector_facial")
    def test_post_impide_reenrolamiento(self, generar_vector):
        registro = self.crear_consentimiento()

        generar_vector.return_value = np.zeros(
            128,
            dtype=np.float64,
        )

        primera_respuesta = self.enrolar(
            self.duena,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(
            primera_respuesta.status_code,
            201,
            primera_respuesta.data,
        )

        registro.refresh_from_db()

        datos_originales = bytes(
            registro.datos_biometricos_cifrados
        )

        segunda_respuesta = self.enrolar(
            self.duena,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(
            segunda_respuesta.status_code,
            400,
        )

        registro.refresh_from_db()

        self.assertEqual(
            bytes(registro.datos_biometricos_cifrados),
            datos_originales,
        )

        generar_vector.assert_called_once()

    @override_settings(POWERFIT_FERNET_KEY="")
    @patch("usuarios.views.generar_vector_facial")
    def test_post_error_cifrado_no_activa_registro(self, generar_vector):
        registro = self.crear_consentimiento()

        generar_vector.return_value = np.zeros(
            128,
            dtype=np.float64,
        )

        respuesta = self.enrolar(
            self.duena,
            self.socio.id,
            self.crear_imagen_prueba(),
        )

        self.assertEqual(respuesta.status_code, 500)

        registro.refresh_from_db()
        self.socio.refresh_from_db()

        self.assertFalse(registro.activo)

        self.assertFalse(
            self.socio.reconocimiento_facial_habilitado
        )

        self.assertIsNone(
            registro.datos_biometricos_cifrados
        )

        self.assertIsNone(
            registro.fecha_enrolamiento
        )
