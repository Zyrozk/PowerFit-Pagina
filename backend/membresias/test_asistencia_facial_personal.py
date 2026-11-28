from datetime import time, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from django.core.cache import cache

from rest_framework.test import APIClient

from clases.models import Clase
from usuarios.models import RegistroFacial

from .models import (
    Reserva,
    SesionAsistenciaFacial,
    DesafioPruebaVida,
)
from django.core.files.uploadedfile import SimpleUploadedFile



Usuario = get_user_model()


class AsistenciaFacialPersonalTest(TestCase):

    def setUp(self):

        cache.clear()

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

        self.duena = self.crear_usuario(
            "duena", "DUENA"
        )

        self.coach = self.crear_usuario(
            "coach", "COACH"
        )

        self.otro_coach = self.crear_usuario(
            "otro_coach", "COACH"
        )

        self.socio = self.crear_usuario(
            "socio", "SOCIO"
        )

        self.socio.reconocimiento_facial_habilitado = True

        self.socio.save(
            update_fields=[
                "reconocimiento_facial_habilitado"
            ]
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

        self.url_disponibilidad = (
            "/api/membresias/"
            "asistencia-facial/disponibilidad/"
        )

        self.url_desafio = (
            "/api/membresias/"
            "asistencia-facial/desafio/"
        )

    def crear_usuario(self, nombre, rol):

        return Usuario.objects.create_user(
            username=nombre,
            email=f"{nombre}@prueba.cl",
            password="Prueba123456",
            rol=rol
        )

    def consultar_disponibilidad(self, usuario):

        self.client.force_authenticate(
            user=usuario
        )

        return self.client.get(
            self.url_disponibilidad,
            {"clase_id": self.clase.id}
        )

    def crear_desafio(self, usuario):

        self.client.force_authenticate(
            user=usuario
        )

        return self.client.post(
            self.url_desafio,
            {"reserva_id": self.reserva.id},
            format="json"
        )

    def test_01_duena_consulta_disponibilidad(self):

        respuesta = self.consultar_disponibilidad(
            self.duena
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["disponible"])

        self.assertEqual(
            respuesta.data["reservas"][0]["reserva_id"],
            self.reserva.id
        )

    def test_02_coach_consulta_su_clase(self):

        respuesta = self.consultar_disponibilidad(
            self.coach
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["disponible"])

    def test_03_coach_no_consulta_clase_ajena(self):

        respuesta = self.consultar_disponibilidad(
            self.otro_coach
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_04_socio_no_consulta_disponibilidad(self):

        respuesta = self.consultar_disponibilidad(
            self.socio
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_05_usuario_no_autenticado(self):

        respuesta = self.client.get(
            self.url_disponibilidad,
            {"clase_id": self.clase.id}
        )

        self.assertIn(
            respuesta.status_code,
            [401, 403]
        )

    def test_06_socio_sin_registro_facial(self):

        self.registro.delete()

        respuesta = self.consultar_disponibilidad(
            self.duena
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["disponible"])

        self.assertEqual(
            respuesta.data["codigo"],
            "SIN_SOCIOS_HABILITADOS"
        )

    def test_07_socio_sin_consentimiento(self):

        self.registro.consentimiento_otorgado = False
        self.registro.save()

        respuesta = self.consultar_disponibilidad(
            self.duena
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["disponible"])

    def test_08_registro_facial_inactivo(self):

        self.registro.activo = False
        self.registro.save()

        respuesta = self.consultar_disponibilidad(
            self.coach
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["disponible"])

    def test_09_sesion_facial_deshabilitada(self):

        self.sesion.habilitada = False
        self.sesion.save()

        respuesta = self.consultar_disponibilidad(
            self.duena
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["disponible"])

        self.assertEqual(
            respuesta.data["codigo"],
            "SESION_NO_DISPONIBLE"
        )

    def test_10_asistencia_previamente_registrada(self):

        self.reserva.asistencia = Reserva.Asistencia.ASISTIO
        self.reserva.save()

        respuesta = self.consultar_disponibilidad(
            self.coach
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["disponible"])

        self.assertEqual(
            respuesta.data["codigo"],
            "ASISTENCIA_RESUELTA"
        )

    def test_11_duena_genera_desafio(self):

        respuesta = self.crear_desafio(
            self.duena
        )

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

        self.assertEqual(
            desafio.reserva_id,
            self.reserva.id
        )

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.PENDIENTE
        )

    def test_12_coach_genera_desafio(self):

        respuesta = self.crear_desafio(
            self.coach
        )

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

    def test_13_coach_no_genera_desafio_ajeno(self):

        respuesta = self.crear_desafio(
            self.otro_coach
        )

        self.assertEqual(respuesta.status_code, 404)

        self.assertEqual(
            DesafioPruebaVida.objects.count(),
            0
        )

    def test_14_socio_no_genera_desafio(self):

        respuesta = self.crear_desafio(
            self.socio
        )

        self.assertEqual(respuesta.status_code, 403)

        self.assertEqual(
            DesafioPruebaVida.objects.count(),
            0
        )

    def test_15_otro_responsable_no_interfiere(self):

        primera = self.crear_desafio(
            self.duena
        )

        self.assertEqual(
            primera.status_code,
            201,
            primera.data
        )

        segunda = self.crear_desafio(
            self.coach
        )

        self.assertEqual(segunda.status_code, 409)

        self.assertEqual(
            segunda.data["codigo"],
            "DESAFIO_EN_CURSO"
        )

        self.assertEqual(
            DesafioPruebaVida.objects.count(),
            1
        )

    def test_16_generar_desafio_no_registra_asistencia(self):

        respuesta = self.crear_desafio(
            self.duena
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

        self.assertIsNone(
            self.reserva.registrado_por_id
        )

    def enviar_prueba_vida(
        self,
        usuario,
        token,
        superada=True,
        identidad_verificada=True
    ):

        self.client.force_authenticate(user=usuario)

        fotogramas = [
            SimpleUploadedFile(
                f"fotograma_{i}.jpg",
                b"imagen_de_prueba",
                content_type="image/jpeg"
            )
            for i in range(5)
        ]

        resultado = {
            "superada": superada,
            "identidad_verificada": identidad_verificada,
            "codigo": (
                "PRUEBA_VIDA_SUPERADA"
                if superada and identidad_verificada
                else "PRUEBA_VIDA_FALLIDA"
            ),
            "mensaje": "Resultado de prueba automatizada."
        }

        with patch(
            "membresias.views_validacion_vida."
            "validar_prueba_vida_con_identidad",
            return_value=resultado
        ):

            return self.client.post(
                "/api/membresias/"
                "asistencia-facial/validar-vida/",
                {
                    "token_desafio": token,
                    "fotogramas": fotogramas
                },
                format="multipart"
            )

    def obtener_token_desafio(self, usuario):

        respuesta = self.crear_desafio(usuario)

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        return respuesta.data["token_desafio"]

    def comprobar_asistencia_pendiente(self):

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.PENDIENTE
        )

        self.assertIsNone(
            self.reserva.registrado_por_id
        )

    def comprobar_asistencia_registrada(
        self,
        responsable,
        token
    ):

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.asistencia,
            Reserva.Asistencia.ASISTIO
        )

        self.assertEqual(
            self.reserva.registrado_por_id,
            responsable.id
        )

        self.assertIsNotNone(
            self.reserva.fecha_registro_asistencia
        )

        desafio = DesafioPruebaVida.objects.get(
            token=token
        )

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.SUPERADO
        )

    def test_17_duena_registra_asistencia_facial(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        respuesta = self.enviar_prueba_vida(
            self.duena,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        self.assertTrue(
            respuesta.data["asistencia_registrada"]
        )

        self.comprobar_asistencia_registrada(
            self.duena,
            token
        )

    def test_18_coach_registra_asistencia_facial(self):

        token = self.obtener_token_desafio(
            self.coach
        )

        respuesta = self.enviar_prueba_vida(
            self.coach,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            200,
            respuesta.data
        )

        self.assertTrue(
            respuesta.data["asistencia_registrada"]
        )

        self.comprobar_asistencia_registrada(
            self.coach,
            token
        )

    def test_19_otro_responsable_no_valida_desafio(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        respuesta = self.enviar_prueba_vida(
            self.coach,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            404,
            respuesta.data
        )

        self.comprobar_asistencia_pendiente()

    def test_20_socio_no_valida_desafio(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        respuesta = self.enviar_prueba_vida(
            self.socio,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            403
        )

        self.comprobar_asistencia_pendiente()

    def test_21_rostro_incorrecto_no_registra(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        respuesta = self.enviar_prueba_vida(
            self.duena,
            token,
            superada=False,
            identidad_verificada=False
        )

        self.assertEqual(
            respuesta.status_code,
            400,
            respuesta.data
        )

        self.comprobar_asistencia_pendiente()

        desafio = DesafioPruebaVida.objects.get(
            token=token
        )

        self.assertEqual(
            desafio.estado,
            DesafioPruebaVida.Estado.FALLIDO
        )

    def test_22_prueba_vida_incorrecta_no_registra(self):

        token = self.obtener_token_desafio(
            self.coach
        )

        respuesta = self.enviar_prueba_vida(
            self.coach,
            token,
            superada=False,
            identidad_verificada=True
        )

        self.assertEqual(
            respuesta.status_code,
            400,
            respuesta.data
        )

        self.comprobar_asistencia_pendiente()

    def test_23_desafio_no_puede_reutilizarse(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        primera = self.enviar_prueba_vida(
            self.duena,
            token
        )

        self.assertEqual(
            primera.status_code,
            200,
            primera.data
        )

        self.reserva.refresh_from_db()

        fecha_original = (
            self.reserva.fecha_registro_asistencia
        )

        segunda = self.enviar_prueba_vida(
            self.duena,
            token
        )

        self.assertEqual(
            segunda.status_code,
            409
        )

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.fecha_registro_asistencia,
            fecha_original
        )

    def test_24_desafio_expirado_no_registra(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        DesafioPruebaVida.objects.filter(
            token=token
        ).update(
            fecha_expiracion=(
                self.ahora - timedelta(seconds=1)
            )
        )

        respuesta = self.enviar_prueba_vida(
            self.duena,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            409,
            respuesta.data
        )

        self.assertEqual(
            respuesta.data["codigo"],
            "DESAFIO_EXPIRADO"
        )

        self.comprobar_asistencia_pendiente()

    def test_25_consentimiento_revocado_no_registra(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        self.registro.consentimiento_otorgado = False

        self.registro.save(
            update_fields=[
                "consentimiento_otorgado"
            ]
        )

        respuesta = self.enviar_prueba_vida(
            self.duena,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            409,
            respuesta.data
        )

        self.comprobar_asistencia_pendiente()

    def test_26_sesion_deshabilitada_no_registra(self):

        token = self.obtener_token_desafio(
            self.coach
        )

        self.sesion.habilitada = False

        self.sesion.save(
            update_fields=["habilitada"]
        )

        respuesta = self.enviar_prueba_vida(
            self.coach,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            409,
            respuesta.data
        )

        self.comprobar_asistencia_pendiente()

    def test_27_asistencia_qr_previa_no_duplica(self):

        token = self.obtener_token_desafio(
            self.duena
        )

        self.reserva.asistencia = (
            Reserva.Asistencia.ASISTIO
        )

        self.reserva.registrado_por = self.socio

        self.reserva.fecha_registro_asistencia = (
            self.ahora
        )

        self.reserva.save()

        respuesta = self.enviar_prueba_vida(
            self.duena,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            409,
            respuesta.data
        )

        self.reserva.refresh_from_db()

        self.assertEqual(
            self.reserva.registrado_por_id,
            self.socio.id
        )

        self.assertEqual(
            self.reserva.fecha_registro_asistencia,
            self.ahora
        )

    def test_28_coach_pierde_asignacion_no_registra(self):

        token = self.obtener_token_desafio(
            self.coach
        )

        self.clase.coach = self.otro_coach

        self.clase.save(
            update_fields=["coach"]
        )

        respuesta = self.enviar_prueba_vida(
            self.coach,
            token
        )

        self.assertEqual(
            respuesta.status_code,
            403,
            respuesta.data
        )

        self.comprobar_asistencia_pendiente()