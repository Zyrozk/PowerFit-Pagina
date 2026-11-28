from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from membresias import test_asistencia_facial_personal

from .models import Reserva


class DisponibilidadFacialTest(TestCase):

    crear_usuario = (
        test_asistencia_facial_personal
        .AsistenciaFacialPersonalTest.crear_usuario
    )

    def setUp(self):

        test_asistencia_facial_personal.AsistenciaFacialPersonalTest.setUp(
            self
        )

        cache.clear()
        self.addCleanup(cache.clear)

        self.url = (
            "/api/membresias/"
            "asistencia-facial/disponibilidad/"
        )

        self.client.force_authenticate(
            user=self.duena
        )

    def consultar(self):

        return self.client.get(
            self.url,
            {"clase_id": self.clase.id}
        )

    def comprobar_no_disponible(self, codigo):

        respuesta = self.consultar()

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        self.assertFalse(
            respuesta.data["disponible"]
        )

        self.assertEqual(
            respuesta.data["codigo"],
            codigo
        )

        self.assertEqual(
            respuesta.data["reservas"],
            []
        )

    def test_socio_disponible(self):

        respuesta = self.consultar()

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

        reserva = respuesta.data["reservas"][0]

        self.assertEqual(
            reserva["reserva_id"],
            self.reserva.id
        )

        self.assertEqual(
            reserva["socio_id"],
            self.socio.id
        )

        self.assertEqual(
            reserva["clase_id"],
            self.clase.id
        )

    def test_socio_sin_registro_facial(self):

        self.registro.delete()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_socio_sin_consentimiento(self):

        self.registro.consentimiento_otorgado = False
        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_consentimiento_no_confirmado(self):

        self.registro.consentimiento_confirmado_por_socio = False
        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_consentimiento_revocado(self):

        self.registro.fecha_revocacion = (
            self.ahora + timedelta(minutes=1)
        )

        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_registro_facial_inactivo(self):

        self.registro.activo = False
        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_socio_reconocimiento_deshabilitado(self):

        self.socio.reconocimiento_facial_habilitado = False
        self.socio.save()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_socio_sin_datos_biometricos(self):

        self.registro.datos_biometricos_cifrados = None
        self.registro.save()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_socio_sin_reserva(self):

        self.reserva.delete()

        self.comprobar_no_disponible(
            "SIN_RESERVAS"
        )

    def test_reserva_pendiente(self):

        self.reserva.estado = Reserva.Estado.PENDIENTE
        self.reserva.save()

        self.comprobar_no_disponible(
            "SIN_RESERVAS"
        )

    def test_reserva_cancelada(self):

        self.reserva.estado = Reserva.Estado.CANCELADA
        self.reserva.save()

        self.comprobar_no_disponible(
            "SIN_RESERVAS"
        )

    def test_clase_inactiva(self):

        self.clase.activa = False
        self.clase.save()

        self.comprobar_no_disponible(
            "CLASE_INACTIVA"
        )

    def test_clase_otro_dia(self):

        self.clase.fecha = (
            timezone.localdate() + timedelta(days=1)
        )

        self.clase.save()

        self.comprobar_no_disponible(
            "FECHA_NO_VALIDA"
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

    def test_duena_puede_consultar(self):

        self.client.force_authenticate(
            user=self.duena
        )

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["disponible"])

    def test_coach_puede_consultar_su_clase(self):

        self.client.force_authenticate(
            user=self.coach
        )

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["disponible"])

    def test_usuario_no_autenticado(self):

        self.client.force_authenticate(
            user=None
        )

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 401)

    def test_otro_coach_no_puede_consultar(self):

        self.client.force_authenticate(
            user=self.otro_coach
        )

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 404)

    def test_consulta_no_modifica_asistencia(self):

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 200)

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

        self.assertIsNone(
            self.reserva.fecha_registro_asistencia
        )

        self.assertIsNone(
            self.reserva.registrado_por_id
        )

    def test_socio_no_puede_consultar(self):

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 403)

    def test_consulta_sin_clase_id(self):

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 400)

    def test_consulta_clase_id_invalido(self):

        respuesta = self.client.get(
            self.url,
            {"clase_id": "invalido"}
        )

        self.assertEqual(respuesta.status_code, 400)

    def test_consulta_clase_inexistente(self):

        respuesta = self.client.get(
            self.url,
            {"clase_id": 999999}
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_socio_inactivo_no_disponible(self):

        self.socio.is_active = False
        self.socio.save()

        self.comprobar_no_disponible(
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_consulta_no_expone_datos_biometricos(self):

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 200)

        campos_prohibidos = [
            "vector",
            "distancia",
            "tolerancia",
            "imagen",
            "fotogramas",
            "datos_biometricos_cifrados"
        ]

        for reserva in respuesta.data["reservas"]:

            for campo in campos_prohibidos:

                self.assertNotIn(campo, reserva)

    def test_totales_disponibilidad(self):

        respuesta = self.consultar()

        self.assertEqual(respuesta.status_code, 200)

        self.assertEqual(
            respuesta.data["total_inscritos"],
            1
        )

        self.assertEqual(
            respuesta.data["total_registrados"],
            0
        )

        self.assertEqual(
            respuesta.data["total_pendientes"],
            1
        )

        self.assertEqual(
            respuesta.data["total_disponibles"],
            1
        )