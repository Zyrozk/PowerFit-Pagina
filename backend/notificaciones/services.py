
from django.contrib.auth import get_user_model
from django.db import transaction

from .models import Notificacion


def notificar_coach(
    coach,
    tipo,
    titulo,
    descripcion,
    clave_evento
):
    if coach is None:
        return

    coach_id = getattr(coach, "pk", None)

    if coach_id is None:
        return

    Usuario = get_user_model()

    def crear_notificacion():
        usuario_coach = Usuario.objects.filter(
            pk=coach_id,
            rol="COACH",
            is_active=True
        ).first()

        if usuario_coach is None:
            return

        Notificacion.objects.get_or_create(
            clave_evento=f"{clave_evento}:coach:{usuario_coach.pk}",
            defaults={
                "socio": usuario_coach,
                "tipo": tipo,
                "titulo": titulo,
                "descripcion": descripcion
            }
        )

    transaction.on_commit(crear_notificacion)

def notificar_duenas(tipo, titulo, descripcion, clave_evento):
    Usuario = get_user_model()

    def crear_notificaciones():
        duenas = Usuario.objects.filter(
            rol="DUENA",
            is_active=True
        )

        for duena in duenas:
            Notificacion.objects.get_or_create(
                clave_evento=f"{clave_evento}:duena:{duena.pk}",
                defaults={
                    "socio": duena,
                    "tipo": tipo,
                    "titulo": titulo,
                    "descripcion": descripcion
                }
            )

    transaction.on_commit(crear_notificaciones)


def notificar_socio(
    socio,
    tipo,
    titulo,
    descripcion,
    clave_evento,
    membresia_id=None,
    motivo_rechazo=""
):
    def crear_notificacion():
        Notificacion.objects.get_or_create(
            clave_evento=f"{clave_evento}:socio:{socio.pk}",
            defaults={
                "socio": socio,
                "tipo": tipo,
                "titulo": titulo,
                "descripcion": descripcion,
                "membresia_id_referencia": membresia_id,
                "motivo_rechazo": motivo_rechazo
            }
        )

    transaction.on_commit(crear_notificacion)


def notificar_solicitud_membresia(membresia):
    metodo = membresia.pago.metodo_pago

    if metodo == "TRANSFERENCIA":
        titulo = "Nueva membresía por validar"
        descripcion = (
            f"El socio {membresia.socio.get_full_name() or membresia.socio.username} "
            f"solicitó una membresía y adjuntó un comprobante de transferencia."
        )
    else:
        titulo = "Nueva membresía pendiente de pago"
        descripcion = (
            f"El socio {membresia.socio.get_full_name() or membresia.socio.username} "
            f"solicitó una membresía con pago presencial."
        )

    notificar_duenas(
        tipo="MEMBRESIA_PENDIENTE",
        titulo=titulo,
        descripcion=descripcion,
        clave_evento=f"solicitud_membresia:{membresia.pk}"
    )


def notificar_reserva_particular(reserva):
    metodo = reserva.pago.metodo_pago

    if metodo == "TRANSFERENCIA":
        titulo = "Nueva clase particular por validar"
        descripcion = (
            f"El socio {reserva.socio.get_full_name() or reserva.socio.username} "
            f"reservó una clase particular y adjuntó un comprobante de transferencia."
        )
    else:
        titulo = "Nueva clase particular pendiente de pago"
        descripcion = (
            f"El socio {reserva.socio.get_full_name() or reserva.socio.username} "
            f"reservó una clase particular con pago presencial."
        )

    notificar_duenas(
        tipo="CLASE_PARTICULAR_PENDIENTE",
        titulo=titulo,
        descripcion=descripcion,
        clave_evento=f"reserva_particular:{reserva.pk}"
    )


def notificar_resultado_membresia(membresia, aprobada, motivo=""):
    nombre_plan = membresia.get_plan_display()

    if aprobada:
        notificar_socio(
            socio=membresia.socio,
            tipo="MEMBRESIA_APROBADA",
            titulo="Membresía aprobada",
            descripcion=(
                f"Tu {nombre_plan} fue aprobado y ya se encuentra activo. "
                f"Puedes revisar tu membresía y comenzar a reservar clases."
            ),
            clave_evento=f"membresia_aprobada:{membresia.pk}",
            membresia_id=membresia.pk
        )
    else:
        notificar_socio(
            socio=membresia.socio,
            tipo="MEMBRESIA_RECHAZADA",
            titulo="Membresía rechazada",
            descripcion=(
                f"Tu solicitud de {nombre_plan} fue rechazada. "
                f"Revisa el motivo indicado."
            ),
            clave_evento=f"membresia_rechazada:{membresia.pk}",
            membresia_id=membresia.pk,
            motivo_rechazo=motivo
        )


def notificar_resultado_reserva_particular(reserva, aprobada, motivo=""):
    nombre_clase = str(reserva.clase)

    if aprobada:
        notificar_socio(
            socio=reserva.socio,
            tipo="RESERVA_CONFIRMADA",
            titulo="Clase particular aprobada",
            descripcion=(
                f"Tu reserva particular para {nombre_clase} fue aprobada. "
                f"Ya puedes consultar tu clase en el historial."
            ),
            clave_evento=f"reserva_particular_aprobada:{reserva.pk}"
        )
    else:
        notificar_socio(
            socio=reserva.socio,
            tipo="CLASE_PARTICULAR_RECHAZADA",
            titulo="Clase particular rechazada",
            descripcion=(
                f"Tu reserva particular para {nombre_clase} fue rechazada. "
                f"Motivo: {motivo}"
            ),
            clave_evento=f"reserva_particular_rechazada:{reserva.pk}",
            motivo_rechazo=motivo
        )
