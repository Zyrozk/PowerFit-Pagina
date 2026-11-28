
from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from django.test import TestCase
from membresias import test_asistencia_facial_personal

from membresias.models import (
    Reserva,
    SesionAsistenciaFacial,
    DesafioPruebaVida,
)


class DesafioFacialTest(TestCase):

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

        self.url_desafio = (
            "/api/membresias/"
            "asistencia-facial/desafio/"
        )

    def crear_desafio(self, datos=None):

        if datos is None:

            datos = {
                "reserva_id": self.reserva.id
            }

        return self.client.post(
            self.url_desafio,
            datos,
            format="json"
        )

    def comprobar_error(
        self,
        respuesta,
        estado,
        codigo
    ):

        self.assertEqual(
            respuesta.status_code,
            estado
        )

        self.assertFalse(
            respuesta.data["creado"]
        )

        self.assertEqual(
            respuesta.data["codigo"],
            codigo
        )

    def test_desafio_creado_correctamente(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        self.assertTrue(
            respuesta.data["creado"]
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "DESAFIO_CREADO"
        )

        desafio = DesafioPruebaVida.objects.get(
            token=respuesta.data["token_desafio"]
        )

        self.assertEqual(
            desafio.reserva_id,
            self.reserva.id
        )

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.PENDIENTE
        )

        self.assertTrue(
            desafio.vigente
        )

    def test_token_tiene_64_caracteres(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        token = respuesta.data["token_desafio"]

        self.assertEqual(
            len(token),
            64
        )

        self.assertEqual(
            len(bytes.fromhex(token)),
            32
        )

    def test_direccion_valida(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        self.assertIn(
            respuesta.data["direccion"],
            [
                "IZQUIERDA_IMAGEN",
                "DERECHA_IMAGEN",
            ]
        )

    def test_secuencia_correcta(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        direccion = respuesta.data["direccion"]

        self.assertEqual(
            respuesta.data["secuencia"],
            [
                "MIRAR_FRENTE",
                "CERRAR_OJOS",
                "ABRIR_OJOS",
                direccion,
                "MIRAR_FRENTE",
            ]
        )

    def test_duracion_maxima_desafio(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        self.assertGreater(
            respuesta.data["duracion_segundos"],
            0
        )

        self.assertLessEqual(
            respuesta.data["duracion_segundos"],
            60
        )

    def test_desafio_expirado_no_vigente(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        desafio = DesafioPruebaVida.objects.get(
            token=respuesta.data["token_desafio"]
        )

        desafio.fecha_expiracion = (
            timezone.now() - timedelta(seconds=1)
        )

        desafio.save(
            update_fields=["fecha_expiracion"]
        )

        self.assertFalse(
            desafio.vigente
        )

    def test_nuevo_desafio_cancela_anterior(self):

        primera = self.crear_desafio()
        segunda = self.crear_desafio()

        self.assertEqual(
            primera.status_code,
            201
        )

        self.assertEqual(
            segunda.status_code,
            201
        )

        anterior = DesafioPruebaVida.objects.get(
            token=primera.data["token_desafio"]
        )

        nuevo = DesafioPruebaVida.objects.get(
            token=segunda.data["token_desafio"]
        )

        self.assertEqual(
            anterior.estado,
            DesafioPruebaVida.Estado.CANCELADO
        )

        self.assertIsNotNone(
            anterior.fecha_resolucion
        )

        self.assertFalse(
            anterior.vigente
        )

        self.assertTrue(
            nuevo.vigente
        )

        self.assertNotEqual(
            anterior.token,
            nuevo.token
        )

    def test_nuevo_desafio_marca_expirado_anterior(self):

        primera = self.crear_desafio()

        self.assertEqual(
            primera.status_code,
            201
        )

        anterior = DesafioPruebaVida.objects.get(
            token=primera.data["token_desafio"]
        )

        anterior.fecha_expiracion = (
            timezone.now() - timedelta(seconds=1)
        )

        anterior.save(
            update_fields=["fecha_expiracion"]
        )

        segunda = self.crear_desafio()

        self.assertEqual(
            segunda.status_code,
            201
        )

        anterior.refresh_from_db()

        self.assertEqual(
            anterior.estado,
            DesafioPruebaVida.Estado.EXPIRADO
        )

        self.assertIsNotNone(
            anterior.fecha_resolucion
        )

    def test_desafio_en_validacion_bloquea_nuevo(self):

        primera = self.crear_desafio()

        self.assertEqual(
            primera.status_code,
            201
        )

        desafio = DesafioPruebaVida.objects.get(
            token=primera.data["token_desafio"]
        )

        desafio.estado = (
            DesafioPruebaVida.Estado.VALIDANDO
        )

        desafio.save(
            update_fields=["estado"]
        )

        respuesta = self.crear_desafio()

        self.comprobar_error(
            respuesta,
            409,
            "DESAFIO_EN_VALIDACION"
        )

    def test_reserva_no_enviada(self):

        respuesta = self.crear_desafio({})

        self.comprobar_error(
            respuesta,
            400,
            "RESERVA_REQUERIDA"
        )

    def test_reserva_id_invalido(self):

        respuesta = self.crear_desafio({
            "reserva_id": "invalido"
        })

        self.comprobar_error(
            respuesta,
            400,
            "RESERVA_REQUERIDA"
        )

    def test_reserva_id_negativo(self):

        respuesta = self.crear_desafio({
            "reserva_id": -1
        })

        self.comprobar_error(
            respuesta,
            400,
            "RESERVA_REQUERIDA"
        )

    def test_reserva_inexistente(self):

        respuesta = self.crear_desafio({
            "reserva_id": 999999
        })

        self.comprobar_error(
            respuesta,
            404,
            "RESERVA_NO_VALIDA"
        )

    def test_reserva_de_otro_usuario(self):

        self.reserva.socio = self.coach

        self.reserva.save(
            update_fields=["socio"]
        )

        respuesta = self.crear_desafio()

        self.assertIn(
            respuesta.status_code,
            [400, 403, 404]
        )

        self.assertFalse(
            DesafioPruebaVida.objects.filter(
                reserva=self.reserva
            ).exists()
        )

    def test_reserva_cancelada(self):

        self.reserva.estado = (
            Reserva.Estado.CANCELADA
        )

        self.reserva.save(
            update_fields=["estado"]
        )

        respuesta = self.crear_desafio()

        self.comprobar_error(
            respuesta,
            404,
            "RESERVA_NO_VALIDA"
        )

    def test_asistencia_ya_registrada(self):

        self.reserva.asistencia = (
            Reserva.Asistencia.ASISTIO
        )

        self.reserva.save(
            update_fields=["asistencia"]
        )

        respuesta = self.crear_desafio()

        self.comprobar_error(
            respuesta,
            409,
            "ASISTENCIA_RESUELTA"
        )

    def test_sesion_deshabilitada(self):

        SesionAsistenciaFacial.objects.filter(
            clase_id=self.reserva.clase_id
        ).update(
            habilitada=False
        )

        respuesta = self.crear_desafio()

        self.comprobar_error(
            respuesta,
            400,
            "SESION_NO_DISPONIBLE"
        )

    def test_deshabilitar_sesion_invalida_desafio(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        SesionAsistenciaFacial.objects.filter(
            clase_id=self.reserva.clase_id
        ).update(
            habilitada=False
        )

        desafio = DesafioPruebaVida.objects.get(
            token=respuesta.data["token_desafio"]
        )

        self.assertFalse(
            desafio.vigente
        )

    def test_rehabilitar_sesion_no_reactiva_desafio(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        desafio = DesafioPruebaVida.objects.get(
            token=respuesta.data["token_desafio"]
        )

        SesionAsistenciaFacial.objects.filter(
            clase_id=self.reserva.clase_id
        ).update(
            habilitada=True,
            fecha_habilitacion=(
                desafio.fecha_habilitacion_sesion
                + timedelta(seconds=1)
            )
        )

        desafio.refresh_from_db()

        self.assertFalse(
            desafio.vigente
        )

    def test_crear_desafio_no_registra_asistencia(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

    def test_respuesta_no_expone_datos_biometricos(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        campos_prohibidos = [
            "datos_biometricos_cifrados",
            "vector",
            "imagen",
            "fotogramas",
            "distancia",
        ]

        for campo in campos_prohibidos:

            self.assertNotIn(
                campo,
                respuesta.data
            )

    def test_duena_puede_solicitar_desafio(self):

        self.client.force_authenticate(
            user=self.duena
        )

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        desafio = DesafioPruebaVida.objects.get(
            token=respuesta.data["token_desafio"]
        )

        self.assertEqual(
            desafio.generado_por_id,
            self.duena.id
        )

    def test_coach_puede_solicitar_desafio(self):

        self.client.force_authenticate(
            user=self.coach
        )

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        desafio = DesafioPruebaVida.objects.get(
            token=respuesta.data["token_desafio"]
        )

        self.assertEqual(
            desafio.generado_por_id,
            self.coach.id
        )

    def test_usuario_no_autenticado(self):

        self.client.force_authenticate(
            user=None
        )

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            401
        )

    def test_limite_solicitudes_por_minuto(self):

        for _ in range(5):

            respuesta = self.crear_desafio()

            self.assertEqual(
                respuesta.status_code,
                201
            )

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            429
        )

    def test_socio_no_puede_solicitar_desafio(self):

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            403
        )

        self.assertFalse(
            DesafioPruebaVida.objects.filter(
                reserva=self.reserva
            ).exists()
        )

    def test_otro_coach_no_puede_solicitar_desafio(self):

        self.client.force_authenticate(
            user=self.otro_coach
        )

        respuesta = self.crear_desafio()

        self.comprobar_error(
            respuesta,
            404,
            "RESERVA_NO_VALIDA"
        )

        self.assertFalse(
            DesafioPruebaVida.objects.filter(
                reserva=self.reserva
            ).exists()
        )

    def test_otro_responsable_no_cancela_desafio(self):

        primera = self.crear_desafio()

        self.assertEqual(
            primera.status_code,
            201
        )

        desafio = DesafioPruebaVida.objects.get(
            token=primera.data["token_desafio"]
        )

        self.client.force_authenticate(
            user=self.coach
        )

        segunda = self.crear_desafio()

        self.comprobar_error(
            segunda,
            409,
            "DESAFIO_EN_CURSO"
        )

        desafio.refresh_from_db()

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.PENDIENTE
        )

        self.assertEqual(
            desafio.generado_por_id,
            self.duena.id
        )

        self.assertTrue(desafio.vigente)

    def test_desafio_identificadores_correctos(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201,
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

        self.assertEqual(
            respuesta.data["generado_por"],
            self.duena.id
        )

    def test_desafio_no_modifica_responsable_asistencia(self):

        respuesta = self.crear_desafio()

        self.assertEqual(
            respuesta.status_code,
            201
        )

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

        self.assertIsNone(
            self.reserva.registrado_por_id
        )

        self.assertIsNone(
            self.reserva.fecha_registro_asistencia
        )

    def test_desafio_no_supera_fin_sesion(self):

        ahora = (
            self.sesion.fin_validez
            - timedelta(seconds=30)
        )

        from unittest.mock import patch

        with patch(
            "django.utils.timezone.now",
            return_value=ahora
        ):

            respuesta = self.crear_desafio()

            self.assertEqual(
                respuesta.status_code,
                201,
                respuesta.data
            )

            desafio = DesafioPruebaVida.objects.get(
                token=respuesta.data["token_desafio"]
            )

            self.assertLessEqual(
                desafio.fecha_expiracion,
                self.sesion.fin_validez
            )

            self.assertGreater(
                desafio.fecha_expiracion,
                ahora
            )

            self.assertLessEqual(
                respuesta.data["duracion_segundos"],
                30
            )