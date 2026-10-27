from calendar import monthrange
from datetime import date
from django.conf import settings
from django.db import models
from django.utils import timezone


def sumar_mes(fecha):
    anio = fecha.year + (fecha.month // 12)
    mes = (fecha.month % 12) + 1
    return date(anio, mes, min(fecha.day, monthrange(anio, mes)[1]))


class Membresia(models.Model):
    class Plan(models.TextChoices):
        PLAN_1 = 'PLAN_1', 'Plan 1'
        PLAN_2 = 'PLAN_2', 'Plan 2'
        PLAN_3 = 'PLAN_3', 'Plan 3'

    class Estado(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ACTIVA = 'ACTIVA', 'Activa'
        RECHAZADA = 'RECHAZADA', 'Rechazada'

    PRECIOS = {'PLAN_1': 30000, 'PLAN_2': 45000, 'PLAN_3': 65000}
    CUPOS = {'PLAN_1': 10, 'PLAN_2': 15, 'PLAN_3': 24}

    socio = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='membresias')
    pago = models.OneToOneField('pagos.Pago', on_delete=models.PROTECT, related_name='membresia')
    plan = models.CharField(max_length=10, choices=Plan.choices)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    clases_totales = models.PositiveSmallIntegerField()
    clases_restantes = models.PositiveSmallIntegerField()
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    @property
    def vigente(self):
        return self.estado == self.Estado.ACTIVA and self.fecha_vencimiento is not None and timezone.localdate() < self.fecha_vencimiento


class Reserva(models.Model):
    class Estado(models.TextChoices):
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        PENDIENTE = 'PENDIENTE', 'Pendiente de pago'

    socio = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='reservas')
    clase = models.ForeignKey('clases.Clase', on_delete=models.PROTECT, related_name='reservas')
    membresia = models.ForeignKey(Membresia, on_delete=models.PROTECT, null=True, blank=True, related_name='reservas')
    pago = models.OneToOneField('pagos.Pago', on_delete=models.PROTECT, null=True, blank=True, related_name='reserva')
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.CONFIRMADA)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['socio', 'clase'], condition=models.Q(estado__in=['CONFIRMADA', 'PENDIENTE']), name='reserva_unica_socio_clase_activa')]
