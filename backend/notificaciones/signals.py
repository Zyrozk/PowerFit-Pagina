
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction

from membresias.models import Membresia, Reserva
from pagos.models import Pago
from .models import Notificacion
from .services import (
    notificar_resultado_membresia,
    notificar_resultado_reserva_particular
)


@receiver(pre_save, sender=Membresia)
def estado_anterior_membresia(sender, instance, **kwargs):
    instance._estado_anterior_aviso = (
        sender.objects.filter(pk=instance.pk)
        .values_list("estado", flat=True)
        .first()
        if instance.pk else None
    )


@receiver(post_save, sender=Membresia)
def aviso_membresia(sender, instance, created, **kwargs):
    estado_anterior = getattr(
        instance,
        "_estado_anterior_aviso",
        None
    )

    if (
        created
        or estado_anterior == instance.estado
        or instance.estado not in ("ACTIVA", "RECHAZADA")
    ):
        return

    aprobada = instance.estado == "ACTIVA"

    motivo = ""

    if not aprobada:
        motivo = Pago.objects.filter(
            pk=instance.pago_id
        ).values_list(
            "motivo_rechazo",
            flat=True
        ).first() or ""

    notificar_resultado_membresia(
        membresia=instance,
        aprobada=aprobada,
        motivo=motivo
    )


@receiver(pre_save, sender=Reserva)
def estado_anterior_reserva(sender, instance, **kwargs):
    instance._estado_anterior_aviso = (
        sender.objects.filter(pk=instance.pk)
        .values_list("estado", flat=True)
        .first()
        if instance.pk else None
    )


@receiver(post_save, sender=Reserva)
def aviso_reserva(sender, instance, created, **kwargs):
    estado_anterior = getattr(
        instance,
        "_estado_anterior_aviso",
        None
    )

    if not created and estado_anterior == instance.estado:
        return

    if not created and instance.pago_id:
        pago = Pago.objects.filter(
            pk=instance.pago_id
        ).first()

        if pago is None:
            return

        if instance.estado == "CONFIRMADA":
            notificar_resultado_reserva_particular(
                reserva=instance,
                aprobada=True
            )

        elif (
            instance.estado == "CANCELADA"
            and pago.estado == "RECHAZADO"
        ):
            notificar_resultado_reserva_particular(
                reserva=instance,
                aprobada=False,
                motivo=pago.motivo_rechazo
            )

        return

    if not (
        (
            created
            and instance.estado in ("PENDIENTE", "CONFIRMADA")
        )
        or (
            not created
            and instance.estado == "CONFIRMADA"
        )
    ):
        return

    es_confirmada = instance.estado == "CONFIRMADA"

    socio = instance.socio
    nombre_clase = str(instance.clase)
    estado = instance.estado
    reserva_id = instance.pk

    def crear():
        Notificacion.objects.get_or_create(
            clave_evento=f"reserva:{reserva_id}:{estado}",
            defaults={
                "socio": socio,
                "tipo": (
                    "RESERVA_CONFIRMADA"
                    if es_confirmada
                    else "CLASE_AGENDADA"
                ),
                "titulo": (
                    "Reserva confirmada"
                    if es_confirmada
                    else "Clase agendada"
                ),
                "descripcion": (
                    f"Tu reserva para {nombre_clase} está confirmada."
                    if es_confirmada
                    else (
                        f"Registramos tu solicitud para {nombre_clase}. "
                        "Pendiente de aprobación del pago."
                    )
                )
            }
        )

    transaction.on_commit(crear)
