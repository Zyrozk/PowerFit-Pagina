from concurrent.futures import ThreadPoolExecutor
from threading import Event, Barrier
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection, connections
from django.test import TransactionTestCase

from rest_framework.test import APIClient

from membresias import test_asistencia_facial_personal

from membresias.models import (
    Reserva,
    DesafioPruebaVida,
)


class ConcurrenciaFacialTest(TransactionTestCase):

    crear_usuario = (
        test_asistencia_facial_personal
        .AsistenciaFacialPersonalTest.crear_usuario
    )

    def setUp(self):

        self.assertEqual(
            connection.vendor,
            "postgresql",
            "Esta prueba requiere PostgreSQL."
        )

        test_asistencia_facial_personal.AsistenciaFacialPersonalTest.setUp(
            self
        )

        cache.clear()
        self.addCleanup(cache.clear)

        self.client.force_authenticate(
            user=self.duena
        )

        respuesta = self.client.post(
            "/api/membresias/asistencia-facial/desafio/",
            {"reserva_id": self.reserva.id},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        self.token = respuesta.data["token_desafio"]

        self.url_validacion = (
            "/api/membresias/asistencia-facial/"
            "validar-vida/"
        )

    def enviar_validacion(self):

        try:

            cliente = APIClient()

            cliente.force_authenticate(
                user=self.duena
            )

            fotogramas = [
                SimpleUploadedFile(
                    f"fotograma_{i}.jpg",
                    b"imagen_de_prueba",
                    content_type="image/jpeg"
                )
                for i in range(5)
            ]

            respuesta = cliente.post(
                self.url_validacion,
                {
                    "token_desafio": self.token,
                    "fotogramas": fotogramas
                },
                format="multipart"
            )

            return (
                respuesta.status_code,
                dict(respuesta.data)
            )

        finally:

            connections.close_all()

    def test_validaciones_simultaneas_mismo_desafio(self):

        procesamiento_iniciado = Event()
        permitir_finalizacion = Event()

        def procesar(*args, **kwargs):

            procesamiento_iniciado.set()

            if not permitir_finalizacion.wait(timeout=30):

                raise RuntimeError(
                    "Tiempo de espera agotado."
                )

            return {
                "superada": True,
                "identidad_verificada": True,
                "codigo": "PRUEBA_VIDA_SUPERADA",
                "mensaje": "Validación correcta."
            }

        with patch(
            "membresias.views_validacion_vida."
            "validar_prueba_vida_con_identidad",
            side_effect=procesar
        ) as validador:

            with ThreadPoolExecutor(
                max_workers=2
            ) as ejecutor:

                primera = ejecutor.submit(
                    self.enviar_validacion
                )

                try:

                    self.assertTrue(
                        procesamiento_iniciado.wait(
                            timeout=30
                        ),
                        "La primera solicitud no inició."
                    )

                    segunda = ejecutor.submit(
                        self.enviar_validacion
                    )

                    estado_segunda, datos_segunda = (
                        segunda.result(timeout=30)
                    )

                    self.assertEqual(
                        estado_segunda,
                        409,
                        datos_segunda
                    )

                    self.assertEqual(
                        datos_segunda["codigo"],
                        "DESAFIO_NO_DISPONIBLE"
                    )

                finally:

                    permitir_finalizacion.set()

                estado_primera, datos_primera = (
                    primera.result(timeout=30)
                )

            self.assertEqual(
                estado_primera,
                200,
                datos_primera
            )

            validador.assert_called_once()

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.ASISTIO
        )

        self.assertEqual(
            self.reserva.registrado_por_id,
            self.duena.id
        )

        self.assertIsNotNone(
            self.reserva.fecha_registro_asistencia
        )

        desafio = DesafioPruebaVida.objects.get(
            token=self.token
        )

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.SUPERADO
        )

        self.assertEqual(
            DesafioPruebaVida.objects.filter(
                reserva=self.reserva,
                estado=DesafioPruebaVida.Estado.SUPERADO
            ).count(),
            1
        )

    def preparar_qr(self):

        self.client.force_authenticate(
            user=self.duena
        )

        respuesta = self.client.post(
            f"/api/membresias/clases/{self.clase.id}/qr/",
            {},
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        self.assertTrue(
            respuesta.data["habilitada"]
        )

        self.assertTrue(
            respuesta.data["vigente"]
        )

        self.token_qr = respuesta.data["token"]

    def enviar_qr(self, barrera=None):

        try:

            cliente = APIClient()

            cliente.force_authenticate(
                user=self.socio
            )

            if barrera is not None:

                barrera.wait(timeout=30)

            respuesta = cliente.post(
                "/api/membresias/qr/escanear/",
                {"token": self.token_qr},
                format="json"
            )

            return (
                respuesta.status_code,
                dict(respuesta.data)
            )

        finally:

            connections.close_all()

    def resultado_facial_correcto(self):

        return {
            "superada": True,
            "identidad_verificada": True,
            "codigo": "PRUEBA_VIDA_SUPERADA",
            "mensaje": "Validación correcta."
        }

    def test_qr_registra_durante_validacion_facial(self):

        self.preparar_qr()

        procesamiento_iniciado = Event()
        permitir_finalizacion = Event()

        def procesar(*args, **kwargs):

            procesamiento_iniciado.set()

            if not permitir_finalizacion.wait(timeout=30):

                raise RuntimeError(
                    "Tiempo de espera agotado."
                )

            return self.resultado_facial_correcto()

        with patch(
            "membresias.views_validacion_vida."
            "validar_prueba_vida_con_identidad",
            side_effect=procesar
        ) as validador:

            with ThreadPoolExecutor(
                max_workers=2
            ) as ejecutor:

                facial = ejecutor.submit(
                    self.enviar_validacion
                )

                try:

                    self.assertTrue(
                        procesamiento_iniciado.wait(
                            timeout=30
                        )
                    )

                    qr = ejecutor.submit(
                        self.enviar_qr
                    )

                    estado_qr, datos_qr = (
                        qr.result(timeout=30)
                    )

                    self.assertEqual(
                        estado_qr,
                        200,
                        datos_qr
                    )

                    self.assertEqual(
                        datos_qr["codigo"],
                        "ASISTENCIA_REGISTRADA"
                    )

                    self.reserva.refresh_from_db()

                    fecha_original = (
                        self.reserva.fecha_registro_asistencia
                    )

                    self.assertIsNotNone(
                        fecha_original
                    )

                    self.assertEqual(
                        self.reserva.registrado_por_id,
                        self.socio.id
                    )

                finally:

                    permitir_finalizacion.set()

                estado_facial, datos_facial = (
                    facial.result(timeout=30)
                )

            self.assertEqual(
                estado_facial,
                409,
                datos_facial
            )

            self.assertEqual(
                datos_facial["codigo"],
                "ASISTENCIA_RESUELTA"
            )

            self.assertFalse(
                datos_facial["asistencia_registrada"]
            )

            validador.assert_called_once()

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.ASISTIO
        )

        self.assertEqual(
            self.reserva.registrado_por_id,
            self.socio.id
        )

        self.assertEqual(
            self.reserva.fecha_registro_asistencia,
            fecha_original
        )

        desafio = DesafioPruebaVida.objects.get(
            token=self.token
        )

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.CANCELADO
        )

    def test_facial_registra_antes_del_qr(self):

        self.preparar_qr()

        with patch(
            "membresias.views_validacion_vida."
            "validar_prueba_vida_con_identidad",
            return_value=self.resultado_facial_correcto()
        ) as validador:

            with ThreadPoolExecutor(
                max_workers=2
            ) as ejecutor:

                facial = ejecutor.submit(
                    self.enviar_validacion
                )

                estado_facial, datos_facial = (
                    facial.result(timeout=30)
                )

                self.assertEqual(
                    estado_facial,
                    200,
                    datos_facial
                )

                self.assertTrue(
                    datos_facial["asistencia_registrada"]
                )

                self.reserva.refresh_from_db()

                fecha_original = (
                    self.reserva.fecha_registro_asistencia
                )

                self.assertIsNotNone(
                    fecha_original
                )

                qr = ejecutor.submit(
                    self.enviar_qr
                )

                estado_qr, datos_qr = (
                    qr.result(timeout=30)
                )

                self.assertEqual(
                    estado_qr,
                    200,
                    datos_qr
                )

                self.assertEqual(
                    datos_qr["codigo"],
                    "ASISTENCIA_YA_REGISTRADA"
                )

            validador.assert_called_once()

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.ASISTIO
        )

        self.assertEqual(
            self.reserva.registrado_por_id,
            self.duena.id
        )

        self.assertEqual(
            self.reserva.fecha_registro_asistencia,
            fecha_original
        )

        desafio = DesafioPruebaVida.objects.get(
            token=self.token
        )

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.SUPERADO
        )

    def test_dos_escaneos_qr_simultaneos(self):

        self.preparar_qr()

        barrera = Barrier(2)

        with ThreadPoolExecutor(
            max_workers=2
        ) as ejecutor:

            primera = ejecutor.submit(
                self.enviar_qr,
                barrera
            )

            segunda = ejecutor.submit(
                self.enviar_qr,
                barrera
            )

            estado_primera, datos_primera = (
                primera.result(timeout=30)
            )

            estado_segunda, datos_segunda = (
                segunda.result(timeout=30)
            )

        self.assertEqual(
            estado_primera,
            200,
            datos_primera
        )

        self.assertEqual(
            estado_segunda,
            200,
            datos_segunda
        )

        codigos = [
            datos_primera["codigo"],
            datos_segunda["codigo"]
        ]

        self.assertEqual(
            codigos.count("ASISTENCIA_REGISTRADA"),
            1
        )

        self.assertEqual(
            codigos.count("ASISTENCIA_YA_REGISTRADA"),
            1
        )

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.ASISTIO
        )

        self.assertEqual(
            self.reserva.registrado_por_id,
            self.socio.id
        )

        self.assertIsNotNone(
            self.reserva.fecha_registro_asistencia
        )

        self.assertEqual(
            Reserva.objects.filter(
                socio=self.socio,
                clase=self.clase,
                estado=Reserva.Estado.CONFIRMADA,
                asistencia=Reserva.Asistencia.ASISTIO
            ).count(),
            1
        )