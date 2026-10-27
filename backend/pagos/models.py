from django.conf import settings
from django.db import models


class Pago(models.Model):

    class TipoPago(models.TextChoices):
        MEMBRESIA = "MEMBRESIA", "Membresía"
        CLASE_PARTICULAR = "CLASE_PARTICULAR", "Clase particular"

    class MetodoPago(models.TextChoices):
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia bancaria"
        EFECTIVO = "EFECTIVO", "Efectivo"
        TARJETA = "TARJETA", "Tarjeta"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADO = "APROBADO", "Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    socio = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pagos"
    )

    tipo_pago = models.CharField(
        max_length=20,
        choices=TipoPago.choices
    )

    metodo_pago = models.CharField(
        max_length=20,
        choices=MetodoPago.choices
    )

    monto = models.PositiveIntegerField()

    estado = models.CharField(
        max_length=10,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE
    )

    fecha_pago = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Pago #{self.id} - {self.socio.username} - ${self.monto}"