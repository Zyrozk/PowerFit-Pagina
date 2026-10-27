
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from .models import RegistroFacial


Usuario = get_user_model()


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

    def test_duena_puede_acceder(self):
        respuesta = self.consultar(self.duena)

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(
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
        ahora = timezone.now()

        RegistroFacial.objects.create(
            socio=self.socio,
            consentimiento_otorgado=True,
            consentimiento_confirmado_por_socio=True,
            fecha_consentimiento=ahora,
            fecha_confirmacion_socio=ahora,
            version_consentimiento="1.0",
            activo=False,
        )

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
        self.assertFalse(
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
