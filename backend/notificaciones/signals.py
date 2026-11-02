from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from membresias.models import Membresia, Reserva
from .models import Notificacion

@receiver(pre_save, sender=Membresia)
def estado_anterior_membresia(sender, instance, **kwargs):
    instance._estado_anterior_aviso = sender.objects.filter(pk=instance.pk).values_list('estado', flat=True).first() if instance.pk else None

@receiver(post_save, sender=Membresia)
def aviso_membresia(sender, instance, created, **kwargs):
    if created or instance._estado_anterior_aviso == instance.estado or instance.estado not in ('ACTIVA', 'RECHAZADA'):
        return
    def crear():
        aprobada = instance.estado == 'ACTIVA'
        motivo = instance.pago.motivo_rechazo if not aprobada else ''
        Notificacion.objects.get_or_create(clave_evento=f'membresia:{instance.pk}:{instance.estado}', defaults=dict(
            socio=instance.socio, tipo='MEMBRESIA_APROBADA' if aprobada else 'MEMBRESIA_RECHAZADA',
            titulo='Membresía aprobada' if aprobada else 'Membresía rechazada',
            descripcion=f'Tu {instance.get_plan_display()} fue activado.' if aprobada else f'Tu solicitud de {instance.get_plan_display()} fue rechazada. {motivo}',
            membresia_id_referencia=instance.pk, motivo_rechazo=motivo))
    transaction.on_commit(crear)

@receiver(pre_save, sender=Reserva)
def estado_anterior_reserva(sender, instance, **kwargs):
    instance._estado_anterior_aviso = sender.objects.filter(pk=instance.pk).values_list('estado', flat=True).first() if instance.pk else None

@receiver(post_save, sender=Reserva)
def aviso_reserva(sender, instance, created, **kwargs):
    if not ((created and instance.estado in ('PENDIENTE','CONFIRMADA')) or (not created and instance._estado_anterior_aviso != instance.estado and instance.estado == 'CONFIRMADA')):
        return
    def crear():
        es_confirmada = instance.estado == 'CONFIRMADA'
        Notificacion.objects.get_or_create(clave_evento=f'reserva:{instance.pk}:{instance.estado}', defaults=dict(
            socio=instance.socio, tipo='RESERVA_CONFIRMADA' if es_confirmada else 'CLASE_AGENDADA',
            titulo='Reserva confirmada' if es_confirmada else 'Clase agendada',
            descripcion=f'Tu reserva para {instance.clase} está confirmada.' if es_confirmada else f'Registramos tu solicitud para {instance.clase}. Pendiente de aprobación del pago.'))
    transaction.on_commit(crear)
