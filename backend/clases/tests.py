from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from rest_framework.test import APITestCase

from .models import Clase, TipoClase, HorarioClase


class ClaseAPITests(APITestCase):

    def setUp(self):

        Usuario = get_user_model()

        self.duena = Usuario.objects.create_user(
            username="duena_test",
            email="duena_test@example.com",
            password="ClaveSegura123!",
            rol="DUENA"
        )

        self.socio = Usuario.objects.create_user(
            username="socio_test",
            email="socio_test@example.com",
            password="ClaveSegura123!",
            rol="SOCIO"
        )

        self.coach = Usuario.objects.create_user(
            username="coach_test",
            email="coach_test@example.com",
            password="ClaveSegura123!",
            rol="COACH"
        )

        self.tipo_step = TipoClase.objects.create(
            nombre="Step",
            cupos_predeterminados=17,
            activa=True
        )

        self.horario = HorarioClase.objects.create(
            hora_inicio=time(18, 0),
            hora_fin=time(19, 0),
            activo=True
        )

        self.fecha = (
            timezone.localdate() + timedelta(days=1)
        )

        self.datos = {
            "tipo": self.tipo_step.codigo,
            "fecha": self.fecha.isoformat(),
            "hora_inicio": "18:00:00",
            "hora_fin": "19:00:00",
            "coach": self.coach.pk
        }

    def test_socio_no_puede_crear(self):

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.client.post(
            "/api/clases/",
            self.datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            403
        )

    def test_duena_puede_crear_step_con_17_cupos(self):

        self.client.force_authenticate(
            user=self.duena
        )

        respuesta = self.client.post(
            "/api/clases/",
            self.datos,
            format="json"
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data
        )

        self.assertEqual(
            respuesta.data["cupos"],
            17
        )

        self.assertEqual(
            respuesta.data["tipo"],
            self.tipo_step.codigo
        )

        self.assertEqual(
            respuesta.data["tipo_nombre"],
            "Step"
        )

        clase = Clase.objects.get(
            pk=respuesta.data["id"]
        )

        self.assertEqual(
            clase.cupos,
            17
        )

        self.assertEqual(
            clase.coach_id,
            self.coach.id
        )

    def test_socio_puede_consultar_clases_activas(self):

        Clase.objects.create(
            tipo=self.tipo_step.codigo,
            fecha=self.fecha,
            hora_inicio=time(18, 0),
            hora_fin=time(19, 0),
            coach=self.coach,
            cupos=17,
            activa=True
        )

        self.client.force_authenticate(
            user=self.socio
        )

        respuesta = self.client.get(
            "/api/clases/",
            {"fecha": self.fecha.isoformat()}
        )

        self.assertEqual(
            respuesta.status_code,
            200
        )

        self.assertEqual(
            len(respuesta.data),
            1
        )

    def test_sin_autenticacion_no_puede_consultar(self):

        respuesta = self.client.get(
            "/api/clases/"
        )

        self.assertEqual(
            respuesta.status_code,
            401
        )