
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile

from django.test import TestCase
from membresias import test_asistencia_facial_personal

from .models import Reserva


class VerificacionFacialTest(TestCase):

    crear_usuario = (
        test_asistencia_facial_personal
        .AsistenciaFacialPersonalTest.crear_usuario
    )

    def setUp(self):

        test_asistencia_facial_personal.AsistenciaFacialPersonalTest.setUp(
            self
        )

        self.client.force_authenticate(
            user=self.duena
        )

        cache.clear()
        self.addCleanup(cache.clear)

        self.url_verificacion = (
            "/api/membresias/"
            "asistencia-facial/verificar/"
        )

        parche = patch(
            "membresias.views_verificacion_facial."
            "verificar_imagen_facial"
        )

        self.verificador = parche.start()
        self.addCleanup(parche.stop)

        self.verificador.return_value = {
            "coincidencia": True,
            "distancia": 0.32,
            "tolerancia": 0.50
        }

    def crear_imagen(self):

        return SimpleUploadedFile(
            "rostro.jpg",
            b"imagen_simulada",
            content_type="image/jpeg"
        )

    def verificar(self, reserva_id=None):

        if reserva_id is None:
            reserva_id = self.reserva.id

        return self.client.post(
            self.url_verificacion,
            {
                "reserva_id": reserva_id,
                "imagen": self.crear_imagen()
            },
            format="multipart"
        )

    def comprobar_error(
        self,
        respuesta,
        codigo,
        estado=400
    ):

        self.assertEqual(
            respuesta.status_code,
            estado
        )

        self.assertFalse(
            respuesta.data["verificado"]
        )

        self.assertFalse(
            respuesta.data["asistencia_registrada"]
        )

        self.assertEqual(
            respuesta.data["codigo"],
            codigo
        )

    def test_rostro_coincide(self):

        respuesta = self.verificar()

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["verificado"])

        self.assertFalse(
            respuesta.data["asistencia_registrada"]
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "ROSTRO_VERIFICADO"
        )

        self.verificador.assert_called_once()

    def test_rostro_no_coincide(self):

        self.verificador.return_value = {
            "coincidencia": False,
            "distancia": 0.65,
            "tolerancia": 0.50
        }

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "ROSTRO_NO_COINCIDE"
        )

    def test_imagen_no_valida(self):

        self.verificador.side_effect = ValueError(
            "Imagen no válida"
        )

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "IMAGEN_NO_VALIDA"
        )

    def test_error_interno_verificacion(self):

        self.verificador.side_effect = RuntimeError(
            "Error simulado"
        )

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "ERROR_VERIFICACION",
            500
        )

    def test_verificacion_sin_imagen(self):

        respuesta = self.client.post(
            self.url_verificacion,
            {
                "reserva_id": self.reserva.id
            },
            format="multipart"
        )

        self.comprobar_error(
            respuesta,
            "IMAGEN_REQUERIDA"
        )

        self.verificador.assert_not_called()

    def test_verificacion_sin_reserva_id(self):

        respuesta = self.client.post(
            self.url_verificacion,
            {
                "imagen": self.crear_imagen()
            },
            format="multipart"
        )

        self.comprobar_error(
            respuesta,
            "RESERVA_REQUERIDA"
        )

        self.verificador.assert_not_called()

    def test_verificacion_reserva_id_invalido(self):

        respuesta = self.verificar("abc")

        self.comprobar_error(
            respuesta,
            "RESERVA_REQUERIDA"
        )

        self.verificador.assert_not_called()

    def test_verificacion_reserva_inexistente(self):

        respuesta = self.verificar(999999)

        self.comprobar_error(
            respuesta,
            "RESERVA_NO_VALIDA",
            404
        )

        self.verificador.assert_not_called()

    def test_verificacion_reserva_usuario_no_socio(self):

        self.reserva.socio = self.coach
        self.reserva.save()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "SOCIO_NO_VALIDO"
        )

        self.verificador.assert_not_called()

    def test_verificacion_reserva_cancelada(self):

        self.reserva.estado = Reserva.Estado.CANCELADA
        self.reserva.save()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "RESERVA_NO_CONFIRMADA"
        )

        self.verificador.assert_not_called()

    def test_verificacion_sin_registro(self):

        self.registro.delete()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "SIN_REGISTRO_FACIAL"
        )

        self.verificador.assert_not_called()

    def test_verificacion_sin_consentimiento(self):

        self.registro.consentimiento_otorgado = False
        self.registro.save()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "SIN_CONSENTIMIENTO"
        )

        self.verificador.assert_not_called()

    def test_verificacion_consentimiento_revocado(self):

        self.registro.fecha_revocacion = (
            self.ahora + timedelta(minutes=1)
        )

        self.registro.save()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "SIN_CONSENTIMIENTO"
        )

        self.verificador.assert_not_called()

    def test_verificacion_registro_inactivo(self):

        self.registro.activo = False
        self.registro.save()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "RECONOCIMIENTO_INACTIVO"
        )

        self.verificador.assert_not_called()

    def test_verificacion_sesion_deshabilitada(self):

        self.sesion.habilitada = False
        self.sesion.save()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "SESION_NO_DISPONIBLE"
        )

        self.verificador.assert_not_called()

    def test_verificacion_fuera_de_horario(self):

        with patch(
            "django.utils.timezone.now",
            return_value=self.ahora + timedelta(hours=3)
        ):

            respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "SESION_NO_DISPONIBLE"
        )

        self.verificador.assert_not_called()

    def test_verificacion_asistencia_resuelta(self):

        self.reserva.asistencia = Reserva.Asistencia.ASISTIO
        self.reserva.save()

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "ASISTENCIA_RESUELTA",
            409
        )

        self.verificador.assert_not_called()

    def test_verificacion_no_registra_asistencia(self):

        respuesta = self.verificar()

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
            self.reserva.registrado_por
        )

    def test_verificacion_no_expone_datos_biometricos(self):

        respuesta = self.verificar()

        self.assertEqual(respuesta.status_code, 200)

        campos_prohibidos = [
            "distancia",
            "tolerancia",
            "vector",
            "datos_biometricos_cifrados",
            "imagen"
        ]

        for campo in campos_prohibidos:

            self.assertNotIn(
                campo,
                respuesta.data
            )

    def test_verificacion_socio_no_autorizado(self):

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.verificar()

        self.assertEqual(
            respuesta.status_code,
            403
        )

        self.verificador.assert_not_called()

    def test_verificacion_coach_autorizado(self):

        self.client.force_authenticate(
            user=self.coach
        )

        respuesta = self.verificar()

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        self.assertTrue(
            respuesta.data["verificado"]
        )

        self.assertFalse(
            respuesta.data["asistencia_registrada"]
        )

        self.verificador.assert_called_once()

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

    def test_verificacion_sin_autenticacion(self):

        self.client.force_authenticate(
            user=None
        )

        respuesta = self.verificar()

        self.assertEqual(respuesta.status_code, 401)
        self.verificador.assert_not_called()

    def test_verificacion_limite_de_intentos(self):

        for intento in range(5):

            respuesta = self.verificar()

            self.assertEqual(
                respuesta.status_code,
                200
            )

        respuesta = self.verificar()

        self.assertEqual(
            respuesta.status_code,
            429
        )

        self.assertEqual(
            self.verificador.call_count,
            5
        )

    def test_otro_coach_no_puede_verificar(self):

        self.client.force_authenticate(
            user=self.otro_coach
        )

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "RESERVA_NO_VALIDA",
            404
        )

        self.verificador.assert_not_called()

    def test_verificacion_clase_inactiva(self):

        self.clase.activa = False

        self.clase.save(
            update_fields=["activa"]
        )

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "CLASE_INACTIVA"
        )

        self.verificador.assert_not_called()

    def test_verificacion_fecha_no_valida(self):

        self.clase.fecha += timedelta(days=1)

        self.clase.save(
            update_fields=["fecha"]
        )

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "FECHA_NO_VALIDA"
        )

        self.verificador.assert_not_called()

    def test_verificacion_socio_inactivo(self):

        self.socio.is_active = False

        self.socio.save(
            update_fields=["is_active"]
        )

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "SOCIO_NO_VALIDO"
        )

        self.verificador.assert_not_called()

    def test_verificacion_sin_datos_biometricos(self):

        self.registro.datos_biometricos_cifrados = None

        self.registro.save(
            update_fields=[
                "datos_biometricos_cifrados"
            ]
        )

        respuesta = self.verificar()

        self.comprobar_error(
            respuesta,
            "RECONOCIMIENTO_INACTIVO"
        )

        self.verificador.assert_not_called()

    def test_verificacion_identificadores_correctos(self):

        respuesta = self.verificar()

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        self.assertEqual(
            respuesta.data["reserva_id"],
            self.reserva.id
        )

        self.assertEqual(
            respuesta.data["clase_id"],
            self.clase.id
        )

        self.assertEqual(
            respuesta.data["socio_id"],
            self.socio.id
        )

        self.assertFalse(
            respuesta.data["asistencia_registrada"]
        )
