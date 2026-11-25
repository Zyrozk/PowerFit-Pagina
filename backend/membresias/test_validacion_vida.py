
from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from membresias import test_disponibilidad_facial

from membresias.models import (
    Reserva,
    DesafioPruebaVida,
)


class ValidacionVidaEndpointTest(
    test_disponibilidad_facial.DisponibilidadFacialTest
):

    def setUp(self):

        super().setUp()

        cache.clear()
        self.addCleanup(cache.clear)

        self.url_validacion = (
            "/api/membresias/asistencia-facial/"
            "validar-vida/"
        )

        self.url_desafio = (
            "/api/membresias/asistencia-facial/"
            "desafio/"
        )

        respuesta = self.client.post(
            self.url_desafio,
            {"reserva_id": self.reserva.id},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        self.token = respuesta.data["token_desafio"]

        self.desafio = DesafioPruebaVida.objects.get(
            token=self.token
        )

        parche = patch(
            "membresias.views_validacion_vida."
            "validar_prueba_vida_con_identidad"
        )

        self.validador = parche.start()

        self.addCleanup(parche.stop)

        self.validador.return_value = {
            "superada": True,
            "identidad_verificada": True,
            "codigo": "PRUEBA_VIDA_SUPERADA",
            "mensaje": "Validación correcta.",
            "pasos_completados": 5,
            "pasos_requeridos": 5,
        }

    def crear_fotogramas(self, cantidad=5):

        return [
            SimpleUploadedFile(
                f"fotograma_{i}.jpg",
                b"imagen_de_prueba",
                content_type="image/jpeg"
            )
            for i in range(cantidad)
        ]

    def validar(self, token=None, cantidad=5):

        return self.client.post(
            self.url_validacion,
            {
                "token_desafio": (
                    self.token
                    if token is None
                    else token
                ),
                "fotogramas": self.crear_fotogramas(
                    cantidad
                ),
            },
            format="multipart"
        )

    def comprobar_estado(self, estado):

        self.desafio.refresh_from_db()

        self.assertEqual(
            self.desafio.estado,
            estado
        )

    def test_validacion_correcta(self):

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            200
        )

        self.assertTrue(
            respuesta.data["superada"]
        )

        self.assertTrue(
            respuesta.data["identidad_verificada"]
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.SUPERADO
        )

    
    def test_validacion_registra_asistencia(self):

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            200
        )

        self.assertTrue(
            respuesta.data["asistencia_registrada"]
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "ASISTENCIA_REGISTRADA"
        )

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.ASISTIO
        )

        self.assertIsNotNone(
            self.reserva.fecha_registro_asistencia
        )

        self.assertEqual(
            self.reserva.registrado_por_id,
            self.socio.id
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.SUPERADO
        )


    def test_desafio_no_puede_reutilizarse(self):

        primera = self.validar()

        segunda = self.validar()

        self.assertEqual(
            primera.status_code,
            200
        )

        self.assertEqual(
            segunda.status_code,
            409
        )

        self.assertEqual(
            segunda.data["codigo"],
            "DESAFIO_NO_DISPONIBLE"
        )

        self.validador.assert_called_once()

    def test_token_ausente(self):

        respuesta = self.client.post(
            self.url_validacion,
            {
                "fotogramas": self.crear_fotogramas()
            },
            format="multipart"
        )

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "TOKEN_REQUERIDO"
        )

    def test_token_invalido(self):

        respuesta = self.validar(
            token="incorrecto"
        )

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "TOKEN_INVALIDO"
        )

    def test_token_no_hexadecimal(self):

        respuesta = self.validar(
            token="z" * 64
        )

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "TOKEN_INVALIDO"
        )

    def test_token_inexistente(self):

        respuesta = self.validar(
            token="a" * 64
        )

        self.assertEqual(
            respuesta.status_code,
            404
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "DESAFIO_NO_ENCONTRADO"
        )

    def test_fotogramas_insuficientes(self):

        respuesta = self.validar(
            cantidad=4
        )

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "FOTOGRAMAS_INVALIDOS"
        )

        self.validador.assert_not_called()

    def test_demasiados_fotogramas(self):

        respuesta = self.validar(
            cantidad=31
        )

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.validador.assert_not_called()

    def test_desafio_expirado(self):

        self.desafio.fecha_expiracion = (
            timezone.now() - timedelta(seconds=1)
        )

        self.desafio.save(
            update_fields=["fecha_expiracion"]
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "DESAFIO_EXPIRADO"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.EXPIRADO
        )

        self.validador.assert_not_called()

    def test_desafio_cancelado(self):

        self.desafio.estado = (
            DesafioPruebaVida.Estado.CANCELADO
        )

        self.desafio.save(
            update_fields=["estado"]
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.validador.assert_not_called()

    def test_desafio_en_validacion(self):

        self.desafio.estado = (
            DesafioPruebaVida.Estado.VALIDANDO
        )

        self.desafio.save(
            update_fields=["estado"]
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.validador.assert_not_called()

    def test_rostro_no_coincide(self):

        self.validador.return_value = {
            "superada": False,
            "identidad_verificada": False,
            "codigo": "ROSTRO_NO_COINCIDE",
            "mensaje": "El rostro no coincide.",
        }

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "ROSTRO_NO_COINCIDE"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.FALLIDO
        )

    def test_secuencia_incompleta(self):

        self.validador.return_value = {
            "superada": False,
            "identidad_verificada": True,
            "codigo": "SECUENCIA_INCOMPLETA",
            "mensaje": "Movimientos incompletos.",
        }

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "SECUENCIA_INCOMPLETA"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.FALLIDO
        )

    def test_error_procesamiento_imagen(self):

        self.validador.side_effect = ValueError(
            "Imagen inválida."
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            400
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "FOTOGRAMAS_NO_VALIDOS"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.FALLIDO
        )

    def test_error_interno(self):

        self.validador.side_effect = RuntimeError(
            "Error interno de prueba."
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            500
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "ERROR_VALIDACION"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.FALLIDO
        )

    def test_reserva_cancelada(self):

        self.reserva.estado = (
            Reserva.Estado.CANCELADA
        )

        self.reserva.save(
            update_fields=["estado"]
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "RESERVA_NO_VALIDA"
        )

        self.validador.assert_not_called()

    def test_asistencia_previamente_registrada(self):

        self.reserva.asistencia = (
            Reserva.Asistencia.ASISTIO
        )

        self.reserva.save(
            update_fields=["asistencia"]
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "ASISTENCIA_RESUELTA"
        )

        self.validador.assert_not_called()

    def test_sesion_deshabilitada(self):

        sesion = self.desafio.sesion

        sesion.habilitada = False

        sesion.save(
            update_fields=["habilitada"]
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "SESION_NO_DISPONIBLE"
        )

        self.validador.assert_not_called()

    def test_sesion_deshabilitada_durante_validacion(self):

        resultado = self.validador.return_value

        def procesar(*args, **kwargs):

            sesion = self.desafio.sesion

            sesion.habilitada = False

            sesion.save(
                update_fields=["habilitada"]
            )

            return resultado

        self.validador.side_effect = procesar

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "SESION_NO_DISPONIBLE"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.CANCELADO
        )

    def test_reserva_cancelada_durante_validacion(self):

        resultado = self.validador.return_value

        def procesar(*args, **kwargs):

            Reserva.objects.filter(
                pk=self.reserva.pk
            ).update(
                estado=Reserva.Estado.CANCELADA
            )

            return resultado

        self.validador.side_effect = procesar

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "RESERVA_NO_VALIDA"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.CANCELADO
        )

    def test_expiracion_durante_validacion(self):

        resultado = self.validador.return_value

        def procesar(*args, **kwargs):

            DesafioPruebaVida.objects.filter(
                pk=self.desafio.pk
            ).update(
                fecha_expiracion=(
                    timezone.now()
                    - timedelta(seconds=1)
                )
            )

            return resultado

        self.validador.side_effect = procesar

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            409
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "DESAFIO_EXPIRADO"
        )

        self.comprobar_estado(
            DesafioPruebaVida.Estado.EXPIRADO
        )

    def test_duena_no_autorizada(self):

        self.client.force_authenticate(
            user=self.duena
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            403
        )

    def test_coach_no_autorizado(self):

        self.client.force_authenticate(
            user=self.coach
        )

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            403
        )

    def test_usuario_no_autenticado(self):

        self.client.force_authenticate(
            user=None
        )

        respuesta = self.validar()

        self.assertIn(
            respuesta.status_code,
            [401, 403]
        )

    def test_respuesta_no_expone_datos_biometricos(self):

        respuesta = self.validar()

        self.assertEqual(
            respuesta.status_code,
            200
        )

        for campo in [
            "vector",
            "distancia",
            "imagen",
            "fotogramas",
            "datos_biometricos_cifrados",
            "token_desafio",
        ]:

            self.assertNotIn(
                campo,
                respuesta.data
            )


    def crear_membresia_prueba(self):
        from membresias.models import Membresia, sumar_mes
        from pagos.models import Pago

        pago = Pago.objects.create(
            socio=self.socio,
            tipo_pago=Pago.TipoPago.MEMBRESIA,
            metodo_pago=Pago.MetodoPago.EFECTIVO,
            monto=30000,
            estado=Pago.EstadoPago.APROBADO
        )

        membresia = Membresia.objects.create(
            socio=self.socio,
            pago=pago,
            plan=Membresia.Plan.PLAN_1,
            nombre_plan="Plan 1",
            estado=Membresia.Estado.ACTIVA,
            clases_totales=10,
            clases_restantes=9,
            fecha_aprobacion=timezone.now(),
            fecha_vencimiento=sumar_mes(
                timezone.localdate()
            )
        )

        self.reserva.membresia = membresia

        self.reserva.save(
            update_fields=["membresia"]
        )

        return membresia

    def test_asistencia_no_descuenta_membresia(self):
        membresia = self.crear_membresia_prueba()

        respuesta = self.validar()

        self.assertEqual(respuesta.status_code, 200)

        membresia.refresh_from_db()
        self.reserva.refresh_from_db()

        self.assertEqual(membresia.clases_restantes, 9)

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.ASISTIO
        )

    def test_asistencia_duplicada_no_descuenta_membresia(self):
        membresia = self.crear_membresia_prueba()

        primera = self.validar()
        segunda = self.validar()

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 409)

        membresia.refresh_from_db()

        self.assertEqual(membresia.clases_restantes, 9)

    def test_rostro_incorrecto_no_modifica_membresia(self):
        membresia = self.crear_membresia_prueba()

        self.validador.return_value = {
            "superada": False,
            "identidad_verificada": False,
            "codigo": "ROSTRO_NO_COINCIDE",
            "mensaje": "El rostro no coincide.",
        }

        respuesta = self.validar()

        self.assertEqual(respuesta.status_code, 400)

        membresia.refresh_from_db()
        self.reserva.refresh_from_db()

        self.assertEqual(membresia.clases_restantes, 9)

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

        self.assertIsNone(
            self.reserva.fecha_registro_asistencia
        )

    def test_secuencia_incorrecta_no_modifica_membresia(self):
        membresia = self.crear_membresia_prueba()

        self.validador.return_value = {
            "superada": False,
            "identidad_verificada": True,
            "codigo": "SECUENCIA_INCOMPLETA",
            "mensaje": "Movimientos incompletos.",
        }

        respuesta = self.validar()

        self.assertEqual(respuesta.status_code, 400)

        membresia.refresh_from_db()
        self.reserva.refresh_from_db()

        self.assertEqual(membresia.clases_restantes, 9)

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

    def test_asistencia_duplicada_no_modifica_fecha(self):
        primera = self.validar()

        self.assertEqual(primera.status_code, 200)

        self.reserva.refresh_from_db()

        fecha_original = (
            self.reserva.fecha_registro_asistencia
        )

        segunda = self.validar()

        self.assertEqual(segunda.status_code, 409)

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.fecha_registro_asistencia,
            fecha_original
        )

    def test_nuevo_desafio_con_asistencia_registrada(self):
        primera = self.validar()

        self.assertEqual(primera.status_code, 200)

        respuesta = self.client.post(
            self.url_desafio,
            {
                "reserva_id": self.reserva.id
            },
            format="json"
        )

        self.assertEqual(respuesta.status_code, 409)

        self.assertEqual(
            respuesta.data["codigo"],
            "ASISTENCIA_RESUELTA"
        )
