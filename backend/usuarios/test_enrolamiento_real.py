import os
from pathlib import Path

import numpy as np

from cryptography.fernet import Fernet

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from rest_framework.test import APIClient

from .models import RegistroFacial
from .servicios_faciales import (
    obtener_vector_facial,
    verificar_imagen_facial,
)


Usuario = get_user_model()


@override_settings(
    POWERFIT_FERNET_KEY=Fernet.generate_key().decode("utf-8")
)
class PruebaEnrolamientoReal(TestCase):

    def setUp(self):
        self.cliente = APIClient()

        self.duena = Usuario.objects.create_user(
            username="duena_prueba_real",
            email="duena_real@test.local",
            password="ClavePrueba123!",
            rol="DUENA",
        )

        self.socio = Usuario.objects.create_user(
            username="socio_prueba_real",
            email="socio_real@test.local",
            password="ClavePrueba123!",
            rol="SOCIO",
        )

        ahora = timezone.now()

        self.registro = RegistroFacial.objects.create(
            socio=self.socio,
            consentimiento_otorgado=True,
            consentimiento_confirmado_por_socio=True,
            fecha_consentimiento=ahora,
            fecha_confirmacion_socio=ahora,
            version_consentimiento="1.0",
            activo=False,
        )

        self.ruta = reverse("enrolamiento-facial")

    def cargar_imagen(self):
        ruta = os.environ.get("POWERFIT_IMAGEN_PRUEBA")

        self.assertTrue(
            ruta,
            "Debe configurar POWERFIT_IMAGEN_PRUEBA."
        )

        archivo = Path(ruta)

        self.assertTrue(
            archivo.is_file(),
            "No se encontró la fotografía de prueba."
        )

        return SimpleUploadedFile(
            archivo.name,
            archivo.read_bytes(),
            content_type="image/jpeg",
        )

    def test_enrolamiento_con_fotografia_real(self):
        self.cliente.force_authenticate(
            user=self.duena
        )

        respuesta = self.cliente.post(
            self.ruta,
            {
                "socio_id": self.socio.id,
                "imagen": self.cargar_imagen(),
            },
            format="multipart",
        )

        self.assertEqual(
            respuesta.status_code,
            201,
            respuesta.data,
        )

        self.registro.refresh_from_db()
        self.socio.refresh_from_db()

        self.assertTrue(self.registro.activo)

        self.assertTrue(
            self.socio.reconocimiento_facial_habilitado
        )

        self.assertIsNotNone(
            self.registro.datos_biometricos_cifrados
        )

        self.assertIsNotNone(
            self.registro.fecha_enrolamiento
        )

        self.assertEqual(
            self.registro.registrado_por_id,
            self.duena.id,
        )

        vector = obtener_vector_facial(
            self.registro
        )

        self.assertEqual(vector.shape, (128,))

        self.assertTrue(
            np.all(np.isfinite(vector))
        )

        resultado = verificar_imagen_facial(
            self.registro,
            self.cargar_imagen(),
        )

        self.assertTrue(
            resultado["coincidencia"]
        )

        print("\n")
        print("ENROLAMIENTO FACIAL REAL: OK")
        print("Estado HTTP:", respuesta.status_code)
        print("Registro activo:", self.registro.activo)
        print(
            "Reconocimiento habilitado:",
            self.socio.reconocimiento_facial_habilitado
        )
        print("Dimensiones del vector:", len(vector))
        print(
            "Datos cifrados:",
            bool(self.registro.datos_biometricos_cifrados)
        )
        print(
            "Coincidencia facial:",
            resultado["coincidencia"]
        )
        print(
            "Distancia facial:",
            resultado["distancia"]
        )
        print(
            "Tolerancia:",
            resultado["tolerancia"]
        )