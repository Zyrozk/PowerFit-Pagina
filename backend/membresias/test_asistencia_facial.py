from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from rest_framework.test import APIClient

from clases.models import Clase

from .models import SesionAsistenciaFacial


Usuario = get_user_model()


class AsistenciaFacialTest(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.duena = Usuario.objects.create_user(
            username="duena_prueba",
            email="duena@prueba.cl",
            password="Prueba123456",
            rol="DUENA"
        )

        self.socio = Usuario.objects.create_user(
            username="socio_prueba",
            email="socio@prueba.cl",
            password="Prueba123456",
            rol="SOCIO"
        )

        self.coach = Usuario.objects.create_user(
            username="coach_prueba",
            email="coach@prueba.cl",
            password="Prueba123456",
            rol="COACH"
        )

        self.otro_coach = Usuario.objects.create_user(
            username="otro_coach_prueba",
            email="otrocoach@prueba.cl",
            password="Prueba123456",
            rol="COACH"
        )

        self.clase = Clase.objects.create(
            tipo="STEP",
            fecha=timezone.localdate() + timedelta(days=1),
            hora_inicio="18:00",
            hora_fin="19:00",
            coach=self.coach,
            cupos=17,
            activa=True
        )

        self.url = (
            f"/api/membresias/clases/"
            f"{self.clase.id}/asistencia-facial/"
        )

        self.url_deshabilitar = (
            f"{self.url}deshabilitar/"
        )

    def autenticar_duena(self):

        self.client.force_authenticate(
            user=self.duena
        )

    def autenticar_coach(self):

        self.client.force_authenticate(
            user=self.coach
        )

    def test_consultar_sesion_inexistente(self):

        self.autenticar_duena()

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["tiene_sesion"])
        self.assertFalse(respuesta.data["habilitada"])
        self.assertFalse(respuesta.data["vigente"])

    def test_duena_habilita_sesion(self):

        self.autenticar_duena()

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["habilitada"])

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertTrue(sesion.habilitada)
        self.assertEqual(sesion.habilitada_por, self.duena)
        self.assertIsNotNone(sesion.fecha_habilitacion)

    def test_duena_deshabilita_sesion(self):

        self.autenticar_duena()

        self.client.post(self.url)

        respuesta = self.client.post(
            self.url_deshabilitar
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["habilitada"])

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertFalse(sesion.habilitada)
        self.assertIsNotNone(sesion.fecha_desactivacion)

    def test_socio_no_puede_habilitar(self):

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 403)

        self.assertFalse(
            SesionAsistenciaFacial.objects.filter(
                clase=self.clase
            ).exists()
        )

    def test_coach_puede_habilitar_su_clase(self):

        self.autenticar_coach()

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["habilitada"])

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertTrue(sesion.habilitada)
        self.assertEqual(sesion.habilitada_por, self.coach)
        self.assertIsNotNone(sesion.fecha_habilitacion)

    def test_usuario_no_autenticado(self):

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 401)

    def test_no_crear_sesiones_duplicadas(self):

        self.autenticar_duena()

        primera = self.client.post(self.url)
        segunda = self.client.post(self.url)

        self.assertEqual(primera.status_code, 200)
        self.assertEqual(segunda.status_code, 200)

        cantidad = SesionAsistenciaFacial.objects.filter(
            clase=self.clase
        ).count()

        self.assertEqual(cantidad, 1)

    def test_clase_inactiva(self):

        self.autenticar_duena()

        self.clase.activa = False
        self.clase.save()

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 400)

    def test_clase_finalizada(self):

        self.autenticar_duena()

        self.clase.fecha = (
            timezone.localdate() - timedelta(days=1)
        )

        self.clase.save()

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 400)

    def test_clase_inexistente(self):

        self.autenticar_duena()

        respuesta = self.client.post(
            "/api/membresias/clases/999999/asistencia-facial/"
        )

        self.assertEqual(respuesta.status_code, 404)

    def test_habilitacion_anticipada(self):

        self.autenticar_duena()

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["habilitada"])
        self.assertFalse(respuesta.data["vigente"])

    def test_rehabilitar_sesion(self):

        self.autenticar_duena()

        self.client.post(self.url)
        self.client.post(self.url_deshabilitar)

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.data["habilitada"])

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertIsNone(sesion.fecha_desactivacion)

    def test_coach_consulta_su_clase(self):

        self.autenticar_coach()

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.data["clase_id"],
            self.clase.id
        )

    def test_coach_deshabilita_su_clase(self):

        self.autenticar_coach()

        habilitacion = self.client.post(self.url)

        self.assertEqual(
            habilitacion.status_code,
            200
        )

        respuesta = self.client.post(
            self.url_deshabilitar
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["habilitada"])

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertFalse(sesion.habilitada)
        self.assertIsNotNone(sesion.fecha_desactivacion)

    def test_otro_coach_no_consulta_clase(self):

        self.client.force_authenticate(
            user=self.otro_coach
        )

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_otro_coach_no_habilita_clase(self):

        self.client.force_authenticate(
            user=self.otro_coach
        )

        respuesta = self.client.post(self.url)

        self.assertEqual(respuesta.status_code, 403)

        self.assertFalse(
            SesionAsistenciaFacial.objects.filter(
                clase=self.clase
            ).exists()
        )

    def test_otro_coach_no_deshabilita_clase(self):

        self.autenticar_duena()

        habilitacion = self.client.post(self.url)

        self.assertEqual(
            habilitacion.status_code,
            200
        )

        self.client.force_authenticate(
            user=self.otro_coach
        )

        respuesta = self.client.post(
            self.url_deshabilitar
        )

        self.assertEqual(respuesta.status_code, 403)

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertTrue(sesion.habilitada)
        self.assertIsNone(sesion.fecha_desactivacion)

    def test_socio_no_consulta_sesion(self):

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.client.get(self.url)

        self.assertEqual(respuesta.status_code, 403)

    def test_socio_no_deshabilita_sesion(self):

        self.autenticar_duena()

        habilitacion = self.client.post(self.url)

        self.assertEqual(
            habilitacion.status_code,
            200
        )

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.client.post(
            self.url_deshabilitar
        )

        self.assertEqual(respuesta.status_code, 403)

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertTrue(sesion.habilitada)

    def test_coach_inactivo_no_gestiona_sesion(self):

        self.coach.is_active = False

        self.coach.save(
            update_fields=["is_active"]
        )

        self.autenticar_coach()

        consulta = self.client.get(self.url)

        habilitacion = self.client.post(self.url)

        deshabilitacion = self.client.post(
            self.url_deshabilitar
        )

        self.assertEqual(consulta.status_code, 403)
        self.assertEqual(habilitacion.status_code, 403)
        self.assertEqual(deshabilitacion.status_code, 403)

    def test_duena_deshabilita_sesion_del_coach(self):

        self.autenticar_coach()

        habilitacion = self.client.post(self.url)

        self.assertEqual(
            habilitacion.status_code,
            200
        )

        self.autenticar_duena()

        respuesta = self.client.post(
            self.url_deshabilitar
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.data["habilitada"])

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        self.assertFalse(sesion.habilitada)
        self.assertEqual(sesion.habilitada_por, self.coach)

    def test_habilitacion_repetida_conserva_responsable(self):

        self.autenticar_duena()

        primera = self.client.post(self.url)

        self.assertEqual(primera.status_code, 200)

        sesion = SesionAsistenciaFacial.objects.get(
            clase=self.clase
        )

        fecha_original = sesion.fecha_habilitacion

        self.autenticar_coach()

        segunda = self.client.post(self.url)

        self.assertEqual(segunda.status_code, 200)

        sesion.refresh_from_db()

        self.assertTrue(sesion.habilitada)

        self.assertEqual(
            sesion.habilitada_por,
            self.duena
        )

        self.assertEqual(
            sesion.fecha_habilitacion,
            fecha_original
        )

        self.assertEqual(
            SesionAsistenciaFacial.objects.filter(
                clase=self.clase
            ).count(),
            1
        )