from datetime import date, time
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from .models import Clase


class ClaseAPITests(APITestCase):
    def setUp(self):
        Usuario = get_user_model()
        self.duena = Usuario.objects.create_user(username='duena_test', email='duena_test@example.com', password='ClaveSegura123!', rol='DUENA')
        self.socio = Usuario.objects.create_user(username='socio_test', email='socio_test@example.com', password='ClaveSegura123!', rol='SOCIO')
        self.coach = Usuario.objects.create_user(username='coach_test', email='coach_test@example.com', password='ClaveSegura123!', rol='COACH')
        self.datos = {'tipo': 'STEP', 'fecha': '2026-11-02', 'hora_inicio': '18:00:00', 'hora_fin': '19:00:00', 'coach': self.coach.pk}

    def test_socio_no_puede_crear(self):
        self.client.force_authenticate(user=self.socio)
        self.assertEqual(self.client.post('/api/clases/', self.datos).status_code, 403)

    def test_duena_puede_crear_step_con_25_cupos(self):
        self.client.force_authenticate(user=self.duena)
        respuesta = self.client.post('/api/clases/', self.datos)
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertEqual(respuesta.data['cupos'], 25)

    def test_socio_puede_consultar_clases_activas(self):
        Clase.objects.create(tipo='STEP', fecha=date(2026, 11, 2), hora_inicio=time(18), hora_fin=time(19), coach=self.coach, cupos=25)
        self.client.force_authenticate(user=self.socio)
        respuesta = self.client.get('/api/clases/?fecha=2026-11-02')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(respuesta.data), 1)

    def test_sin_autenticacion_no_puede_consultar(self):
        self.assertEqual(self.client.get('/api/clases/').status_code, 401)
