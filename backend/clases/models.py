from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class Clase(models.Model):
    class Tipo(models.TextChoices):
        BAILE_ENTRETENIDO = 'BAILE_ENTRETENIDO', 'Baile entretenido'
        LOCALIZADO = 'LOCALIZADO', 'Localizado'
        STEP = 'STEP', 'Step'
        SALSA_FIT = 'SALSA_FIT', 'Salsa fit'
        BACHATA = 'BACHATA', 'Bachata'
        SALSA = 'SALSA', 'Salsa'

    tipo = models.CharField(max_length=30, choices=Tipo.choices)
    fecha = models.DateField()
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    coach = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='clases_asignadas')
    cupos = models.PositiveSmallIntegerField(default=17)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)

    class Meta:
        ordering = ['fecha', 'hora_inicio', 'id']
        constraints = [models.UniqueConstraint(fields=['fecha', 'hora_inicio'], name='clase_fecha_hora_unica')]

    def clean(self):
        if self.hora_inicio and self.hora_fin and self.hora_fin <= self.hora_inicio:
            raise ValidationError({'hora_fin': 'La hora de término debe ser posterior al inicio.'})
        if self.coach_id and self.coach.rol != 'COACH':
            raise ValidationError({'coach': 'El usuario seleccionado debe tener rol COACH.'})
        if self.cupos is not None and self.cupos < 1:
            raise ValidationError({'cupos': 'Debe haber al menos un cupo.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.fecha} {self.hora_inicio}'
