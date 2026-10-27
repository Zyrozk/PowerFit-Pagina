
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings


class Usuario(AbstractUser):

    email = models.EmailField(
        "correo electrónico",
        unique=True,
        blank=False
    )

    class Rol(models.TextChoices):
        SOCIO = "SOCIO", "Socio"
        COACH = "COACH", "Coach"
        DUENA = "DUENA", "Dueña"

    rol = models.CharField(
        max_length=10,
        choices=Rol.choices,
        default=Rol.SOCIO
    )

    reconocimiento_facial_habilitado = models.BooleanField(
        default=False
    )

    def __str__(self):
        return f"{self.username} - {self.get_rol_display()}"


class RegistroFacial(models.Model):

    socio = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registro_facial"
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True
    )

    fecha_actualizacion = models.DateTimeField(
        auto_now=True
    )

    activo = models.BooleanField(
        default=False
    )

    consentimiento_otorgado = models.BooleanField(
        default=False
    )

    fecha_consentimiento = models.DateTimeField(
        null=True,
        blank=True
    )

    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="enrolamientos_realizados"
    )

    version_consentimiento = models.CharField(
        max_length=20,
        blank=True,
        default=""
    )

    consentimiento_confirmado_por_socio = models.BooleanField(
        default=False
    )

    fecha_confirmacion_socio = models.DateTimeField(
        null=True,
        blank=True
    )

    fecha_revocacion = models.DateTimeField(
        null=True,
        blank=True
    )

    datos_biometricos_cifrados = models.BinaryField(
        null=True,
        blank=True
    )

    fecha_enrolamiento = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Registro facial de {self.socio.username}"
