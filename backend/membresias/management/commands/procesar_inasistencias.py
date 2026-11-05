
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from membresias.models import Membresia, Reserva


class Command(BaseCommand):
    help = "Registra automáticamente las inasistencias y devuelve clases cuando corresponde."

    def handle(self, *args, **options):
        ahora = timezone.now()
        zona_horaria = timezone.get_current_timezone()

        reservas = (
            Reserva.objects
            .filter(
                estado=Reserva.Estado.CONFIRMADA,
                asistencia=Reserva.Asistencia.PENDIENTE,
                clase__fecha__lte=timezone.localdate(ahora)
            )
            .select_related("clase")
            .order_by("id")
        )

        procesadas = 0
        devueltas = 0

        for reserva_pendiente in reservas:
            clase = reserva_pendiente.clase

            cierre_qr = timezone.make_aware(
                datetime.combine(
                    clase.fecha,
                    clase.hora_fin
                ),
                zona_horaria
            ) + timedelta(hours=1)

            if ahora <= cierre_qr:
                continue

            with transaction.atomic():
                reserva = (
                    Reserva.objects
                    .select_for_update()
                    .get(pk=reserva_pendiente.pk)
                )

                if (
                    reserva.estado != Reserva.Estado.CONFIRMADA
                    or reserva.asistencia != Reserva.Asistencia.PENDIENTE
                ):
                    continue

                if reserva.membresia_id and not reserva.clase_devuelta:
                    membresia = (
                        Membresia.objects
                        .select_for_update()
                        .get(pk=reserva.membresia_id)
                    )

                    if (
                        membresia.vigente
                        and membresia.clases_restantes < membresia.clases_totales
                    ):
                        membresia.clases_restantes += 1
                        membresia.save(
                            update_fields=["clases_restantes"]
                        )

                        reserva.clase_devuelta = True
                        devueltas += 1

                reserva.asistencia = Reserva.Asistencia.NO_ASISTIO
                reserva.fecha_registro_asistencia = timezone.now()
                reserva.registrado_por = None

                reserva.save(
                    update_fields=[
                        "asistencia",
                        "fecha_registro_asistencia",
                        "registrado_por",
                        "clase_devuelta"
                    ]
                )

                procesadas += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Inasistencias registradas: {procesadas}. "
                f"Clases devueltas: {devueltas}."
            )
        )
