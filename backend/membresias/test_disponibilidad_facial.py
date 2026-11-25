
from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from clases.models import Clase
from usuarios.models import RegistroFacial

from .models import Reserva, SesionAsistenciaFacial


Usuario = get_user_model()


class DisponibilidadFacialTest(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.ahora = timezone.make_aware(
            timezone.datetime.combine(
                timezone.localdate(),
                time(18, 30)
            )
        )

        parche = patch(
            "django.utils.timezone.now",
            return_value=self.ahora
        )

        parche.start()
        self.addCleanup(parche.stop)

        self.duena = Usuario.objects.create_user(
            username="duena_facial",
            email="duena_facial@prueba.cl",
            password="Prueba123456",
            rol="DUENA"
        )

        self.coach = Usuario.objects.create_user(
            username="coach_facial",
            email="coach_facial@prueba.cl",
            password="Prueba123456",
            rol="COACH"
        )

        self.socio = Usuario.objects.create_user(
            username="socio_facial",
            email="socio_facial@prueba.cl",
            password="Prueba123456",
            rol="SOCIO",
            reconocimiento_facial_habilitado=True
        )

        self.registro = RegistroFacial.objects.create(
            socio=self.socio,
            activo=True,
            consentimiento_otorgado=True,
            consentimiento_confirmado_por_socio=True,
            fecha_consentimiento=self.ahora,
            fecha_confirmacion_socio=self.ahora,
            fecha_enrolamiento=self.ahora,
            version_consentimiento="1.0",
            datos_biometricos_cifrados=b"datos_de_prueba",
            registrado_por=self.duena
        )

        self.clase = Clase.objects.create(
            tipo="STEP",
            fecha=timezone.localdate(),
            hora_inicio=time(18, 0),
            hora_fin=time(19, 0),
            coach=self.coach,
            cupos=17,
            activa=True
        )

        self.reserva = Reserva.objects.create(
            socio=self.socio,
            clase=self.clase,
            estado=Reserva.Estado.CONFIRMADA,
            asistencia=Reserva.Asistencia.PENDIENTE
        )

        self.sesion = SesionAsistenciaFacial.objects.create(
            clase=self.clase,
            habilitada=True,
            habilitada_por=self.duena,
            fecha_habilitacion=self.ahora
        )

        self.url = (
            "/api/membresias/"
            "asistencia-facial/disponibilidad/"
        )

        self.client.force_authenticate(
            user=self.socio
        )

    def comprobar_no_disponible(self, codigo):

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["disponible"])
        self.assertEqual(respuesta.data["codigo"], codigo)
        self.assertEqual(respuesta.data["reservas"], [])

    def test_socio_disponible(self):

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["disponible"])
        self.assertEqual(
            respuesta.data["codigo"],
            "DISPONIBLE"
        )

        self.assertEqual(
            len(respuesta.data["reservas"]),
            1
        )

        self.assertEqual(
            respuesta.data["reservas"][0]["reserva_id"],
            self.reserva.id
        )

    def test_socio_sin_registro_facial(self):

        self.registro.delete()

        self.comprobar_no_disponible(
            "SIN_REGISTRO_FACIAL"
        )

    def test_socio_sin_consentimiento(self):

        self.registro.consentimiento_otorgado = False
        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_CONSENTIMIENTO"
        )

    def test_consentimiento_no_confirmado(self):

        self.registro.consentimiento_confirmado_por_socio = False
        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_CONSENTIMIENTO"
        )

    def test_consentimiento_revocado(self):

        self.registro.fecha_revocacion = (
            self.ahora + timedelta(minutes=1)
        )

        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_CONSENTIMIENTO"
        )

    def test_registro_facial_inactivo(self):

        self.registro.activo = False
        self.registro.save()

        self.comprobar_no_disponible(
            "RECONOCIMIENTO_INACTIVO"
        )

    def test_socio_reconocimiento_deshabilitado(self):

        self.socio.reconocimiento_facial_habilitado = False
        self.socio.save()

        self.comprobar_no_disponible(
            "RECONOCIMIENTO_INACTIVO"
        )

    def test_socio_sin_datos_biometricos(self):

        self.registro.datos_biometricos_cifrados = None
        self.registro.save()

        self.comprobar_no_disponible(
            "RECONOCIMIENTO_INACTIVO"
        )

    def test_socio_sin_reserva(self):

        self.reserva.delete()

        self.comprobar_no_disponible(
            "SIN_RESERVA"
        )

    def test_reserva_pendiente(self):

        self.reserva.estado = Reserva.Estado.PENDIENTE
        self.reserva.save()

        self.comprobar_no_disponible(
            "SIN_RESERVA"
        )

    def test_reserva_cancelada(self):

        self.reserva.estado = Reserva.Estado.CANCELADA
        self.reserva.save()

        self.comprobar_no_disponible(
            "SIN_RESERVA"
        )

    def test_clase_inactiva(self):

        self.clase.activa = False
        self.clase.save()

        self.comprobar_no_disponible(
            "SIN_RESERVA"
        )

    def test_clase_otro_dia(self):

        self.clase.fecha = (
            timezone.localdate() + timedelta(days=1)
        )

        self.clase.save()

        self.comprobar_no_disponible(
            "SIN_RESERVA"
        )

    def test_sesion_facial_inexistente(self):

        self.sesion.delete()

        self.comprobar_no_disponible(
            "SESION_NO_DISPONIBLE"
        )

    def test_sesion_facial_deshabilitada(self):

        self.sesion.habilitada = False
        self.sesion.save()

        self.comprobar_no_disponible(
            "SESION_NO_DISPONIBLE"
        )

    def test_sesion_antes_del_horario(self):

        with patch(
            "django.utils.timezone.now",
            return_value=self.ahora - timedelta(hours=3)
        ):

            self.comprobar_no_disponible(
                "SESION_NO_DISPONIBLE"
            )

    def test_sesion_despues_del_horario(self):

        with patch(
            "django.utils.timezone.now",
            return_value=self.ahora + timedelta(hours=3)
        ):

            self.comprobar_no_disponible(
                "SESION_NO_DISPONIBLE"
            )

    def test_asistencia_ya_registrada(self):

        self.reserva.asistencia = Reserva.Asistencia.ASISTIO
        self.reserva.save()

        self.comprobar_no_disponible(
            "ASISTENCIA_RESUELTA"
        )

    def test_asistencia_no_asistio(self):

        self.reserva.asistencia = Reserva.Asistencia.NO_ASISTIO
        self.reserva.save()

        self.comprobar_no_disponible(
            "ASISTENCIA_RESUELTA"
        )

    def test_duena_no_puede_consultar_como_socio(self):

        self.client.force_authenticate(
            user=self.duena
        )

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_coach_no_puede_consultar_como_socio(self):

        self.client.force_authenticate(
            user=self.coach
        )

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_usuario_no_autenticado(self):

        self.client.force_authenticate(
            user=None
        )

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 401)

    def test_no_consultar_reservas_de_otro_socio(self):

        otro_socio = Usuario.objects.create_user(
            username="otro_socio",
            email="otro_socio@prueba.cl",
            password="Prueba123456",
            rol="SOCIO",
            reconocimiento_facial_habilitado=True
        )

        self.reserva.socio = otro_socio
        self.reserva.save()

        self.comprobar_no_disponible(
            "SIN_RESERVA"
        )

    def test_consulta_no_modifica_asistencia(self):

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

        self.assertIsNone(
            self.reserva.fecha_registro_asistencia
        )
