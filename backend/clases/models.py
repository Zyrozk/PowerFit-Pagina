
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class TipoClase(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        editable=False
    )
    cupos_predeterminados = models.PositiveSmallIntegerField(default=17)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "Tipo de clase"
        verbose_name_plural = "Tipos de clases"

    def clean(self):
        self.nombre = (self.nombre or "").strip()

        if not self.nombre:
            raise ValidationError({
                "nombre": "El nombre de la clase es obligatorio."
            })

        if self.cupos_predeterminados < 1:
            raise ValidationError({
                "cupos_predeterminados": "Debe haber al menos un cupo."
            })

        duplicado = TipoClase.objects.filter(
            nombre__iexact=self.nombre
        ).exclude(pk=self.pk).exists()

        if duplicado:
            raise ValidationError({
                "nombre": "Ya existe un tipo de clase con ese nombre."
            })

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = f"TC_{uuid.uuid4().hex[:20].upper()}"

        if self.pk:
            codigo_original = TipoClase.objects.filter(
                pk=self.pk
            ).values_list("codigo", flat=True).first()

            if codigo_original:
                self.codigo = codigo_original

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre


class HorarioClase(models.Model):
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["hora_inicio", "hora_fin"]
        verbose_name = "Horario de clase"
        verbose_name_plural = "Horarios de clases"
        constraints = [
            models.UniqueConstraint(
                fields=["hora_inicio", "hora_fin"],
                name="horario_clase_unico"
            )
        ]

    def clean(self):
        if self.hora_inicio and self.hora_fin:
            if self.hora_fin <= self.hora_inicio:
                raise ValidationError({
                    "hora_fin": "La hora de término debe ser posterior al inicio."
                })

            superpuestos = HorarioClase.objects.filter(
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio
            ).exclude(pk=self.pk)

            if superpuestos.exists():
                raise ValidationError({
                    "hora_inicio": "Este horario se superpone con otro existente."
                })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.hora_inicio.strftime('%H:%M')} - "
            f"{self.hora_fin.strftime('%H:%M')}"
        )


class Clase(models.Model):
    class Tipo(models.TextChoices):
        BAILE_ENTRETENIDO = "BAILE_ENTRETENIDO", "Baile entretenido"
        LOCALIZADO = "LOCALIZADO", "Localizado"
        STEP = "STEP", "Step"
        SALSA_FIT = "SALSA_FIT", "Salsa fit"
        BACHATA = "BACHATA", "Bachata"
        SALSA = "SALSA", "Salsa"

    tipo = models.CharField(max_length=50)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="clases_asignadas"
    )
    cupos = models.PositiveSmallIntegerField(default=17)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ["fecha", "hora_inicio", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["fecha", "hora_inicio"],
                name="clase_fecha_hora_unica"
            )
        ]

    def get_tipo_display(self):
        tipo = TipoClase.objects.filter(
            codigo=self.tipo
        ).first()

        if tipo:
            return tipo.nombre

        return dict(self.Tipo.choices).get(self.tipo, self.tipo)

    def clean(self):
        if self.hora_inicio and self.hora_fin:
            if self.hora_fin <= self.hora_inicio:
                raise ValidationError({
                    "hora_fin": "La hora de término debe ser posterior al inicio."
                })

            superpuestas = Clase.objects.filter(
                fecha=self.fecha,
                activa=True,
                hora_inicio__lt=self.hora_fin,
                hora_fin__gt=self.hora_inicio
            ).exclude(pk=self.pk)

            if self.activa and superpuestas.exists():
                raise ValidationError({
                    "hora_inicio": "Ya existe una clase en este horario."
                })

        if self.coach_id and self.coach.rol != "COACH":
            raise ValidationError({
                "coach": "El usuario seleccionado debe tener rol COACH."
            })

        if self.cupos is not None and self.cupos < 1:
            raise ValidationError({
                "cupos": "Debe haber al menos un cupo."
            })

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.get_tipo_display()} - "
            f"{self.fecha} {self.hora_inicio}"
        )


class HistorialEspecialidadCoach(models.Model):
    coach = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="historial_especialidades"
    )
    tipo_clase = models.ForeignKey(
        TipoClase,
        on_delete=models.PROTECT,
        related_name="historial_coaches"
    )
    codigo = models.CharField(max_length=50)
    nombre = models.CharField(max_length=100)
    fecha_desactivacion = models.DateTimeField(auto_now_add=True)
    desactivada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="desactivaciones_especialidades"
    )

    class Meta:
        ordering = ["-fecha_desactivacion", "-id"]

    def __str__(self):
        return f"{self.coach_id} - {self.nombre}"
