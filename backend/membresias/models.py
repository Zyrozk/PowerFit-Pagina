
import secrets
from calendar import monthrange
from datetime import date, datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


def sumar_mes(fecha):
    anio = fecha.year + (fecha.month // 12)
    mes = (fecha.month % 12) + 1
    return date(anio, mes, min(fecha.day, monthrange(anio, mes)[1]))


def generar_token_qr():
    return secrets.token_urlsafe(32)


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

    socio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='membresias'
    )
    pago = models.OneToOneField(
        'pagos.Pago',
        on_delete=models.PROTECT,
        related_name='membresia'
    )
    plan = models.CharField(max_length=10, choices=Plan.choices)
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE
    )
    clases_totales = models.PositiveSmallIntegerField()
    clases_restantes = models.PositiveSmallIntegerField()
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True)

    @property
    def vigente(self):
        return (
            self.estado == self.Estado.ACTIVA
            and self.fecha_vencimiento is not None
            and timezone.localdate() < self.fecha_vencimiento
        )


class Reserva(models.Model):
    class Estado(models.TextChoices):
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'
        CANCELADA = 'CANCELADA', 'Cancelada'
        PENDIENTE = 'PENDIENTE', 'Pendiente de pago'

    class Asistencia(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        ASISTIO = 'ASISTIO', 'Asistió'
        NO_ASISTIO = 'NO_ASISTIO', 'No asistió'

    asistencia = models.CharField(
        max_length=12,
        choices=Asistencia.choices,
        default=Asistencia.PENDIENTE
    )
    fecha_registro_asistencia = models.DateTimeField(
        null=True,
        blank=True
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='asistencias_registradas'
    )
    clase_devuelta = models.BooleanField(default=False)

    socio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reservas'
    )
    clase = models.ForeignKey(
        'clases.Clase',
        on_delete=models.PROTECT,
        related_name='reservas'
    )
    membresia = models.ForeignKey(
        Membresia,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reservas'
    )
    pago = models.OneToOneField(
        'pagos.Pago',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reserva'
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.CONFIRMADA
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['socio', 'clase'],
                condition=models.Q(
                    estado__in=['CONFIRMADA', 'PENDIENTE']
                ),
                name='reserva_unica_socio_clase_activa'
            )
        ]


class SesionQRAsistencia(models.Model):
    clase = models.OneToOneField(
        'clases.Clase',
        on_delete=models.CASCADE,
        related_name='sesion_qr_asistencia'
    )
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generar_token_qr,
        editable=False
    )
    habilitada = models.BooleanField(default=True)
    generada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='sesiones_qr_generadas'
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    @property
    def inicio_validez(self):
        inicio = datetime.combine(
            self.clase.fecha,
            self.clase.hora_inicio
        )
        inicio = timezone.make_aware(
            inicio,
            timezone.get_current_timezone()
        )
        return inicio - timedelta(hours=1)

    @property
    def fin_validez(self):
        fin = datetime.combine(
            self.clase.fecha,
            self.clase.hora_fin
        )
        fin = timezone.make_aware(
            fin,
            timezone.get_current_timezone()
        )
        return fin + timedelta(hours=1)

    @property
    def vigente(self):
        ahora = timezone.now()
        return (
            self.habilitada
            and self.clase.activa
            and self.inicio_validez <= ahora <= self.fin_validez
        )

    def __str__(self):
        return f'QR de clase {self.clase_id}'


class CambioExcepcionalAsistencia(models.Model):
    reserva = models.ForeignKey(
        Reserva,
        on_delete=models.PROTECT,
        related_name='cambios_excepcionales'
    )
    asistencia_anterior = models.CharField(
        max_length=12,
        choices=Reserva.Asistencia.choices
    )
    asistencia_nueva = models.CharField(
        max_length=12,
        choices=Reserva.Asistencia.choices
    )
    motivo = models.TextField()
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='cambios_excepcionales_realizados'
    )
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    clases_restantes_antes = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )
    clases_restantes_despues = models.PositiveSmallIntegerField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-fecha_cambio']

    def __str__(self):
        return f'Cambio excepcional de reserva {self.reserva_id}'
