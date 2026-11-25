
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from usuarios.models import RegistroFacial
from usuarios.servicios_faciales import validar_consentimiento_facial

from .models import Reserva, SesionAsistenciaFacial


class SoloSocioAsistenciaFacial(permissions.BasePermission):

    message = (
        "Solo los socios pueden utilizar "
        "el reconocimiento facial para asistencia."
    )

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.rol == "SOCIO"
        )


def respuesta_no_disponible(codigo, mensaje):

    return Response(
        {
            "disponible": False,
            "codigo": codigo,
            "mensaje": mensaje,
            "reservas": [],
        },
        status=status.HTTP_200_OK
    )


class DisponibilidadAsistenciaFacialView(APIView):

    permission_classes = [
        permissions.IsAuthenticated,
        SoloSocioAsistenciaFacial,
    ]

    def get(self, request):

        socio = request.user

        registro = RegistroFacial.objects.filter(
            socio=socio
        ).first()

        if registro is None:
            return respuesta_no_disponible(
                "SIN_REGISTRO_FACIAL",
                "No tienes un registro de reconocimiento facial."
            )

        try:
            validar_consentimiento_facial(registro)

        except ValueError:
            return respuesta_no_disponible(
                "SIN_CONSENTIMIENTO",
                "Debes autorizar el reconocimiento facial."
            )

        if (
            not registro.activo
            or not socio.reconocimiento_facial_habilitado
            or not registro.datos_biometricos_cifrados
        ):
            return respuesta_no_disponible(
                "RECONOCIMIENTO_INACTIVO",
                "No tienes el reconocimiento facial activo. "
                "Comunícate con la administración del gimnasio."
            )

        reservas = list(
            Reserva.objects.filter(
                socio=socio,
                estado=Reserva.Estado.CONFIRMADA,
                clase__activa=True,
                clase__fecha=timezone.localdate()
            ).select_related(
                "clase"
            ).order_by(
                "clase__hora_inicio"
            )
        )

        if not reservas:
            return respuesta_no_disponible(
                "SIN_RESERVA",
                "No tienes reservas confirmadas para hoy."
            )

        sesiones = {
            sesion.clase_id: sesion
            for sesion in (
                SesionAsistenciaFacial.objects.filter(
                    clase_id__in=[
                        reserva.clase_id
                        for reserva in reservas
                    ]
                ).select_related("clase")
            )
        }

        reservas_disponibles = []
        sesion_vigente = False

        for reserva in reservas:

            sesion = sesiones.get(
                reserva.clase_id
            )

            if sesion is None or not sesion.vigente:
                continue

            sesion_vigente = True

            if reserva.asistencia != Reserva.Asistencia.PENDIENTE:
                continue

            clase = reserva.clase

            reservas_disponibles.append({
                "reserva_id": reserva.id,
                "clase_id": clase.id,
                "nombre_clase": clase.get_tipo_display(),
                "fecha": clase.fecha.isoformat(),
                "hora_inicio": clase.hora_inicio.strftime("%H:%M"),
                "hora_fin": clase.hora_fin.strftime("%H:%M"),
                "asistencia": reserva.asistencia,
                "inicio_validez": sesion.inicio_validez,
                "fin_validez": sesion.fin_validez,
            })

        if not sesion_vigente:
            return respuesta_no_disponible(
                "SESION_NO_DISPONIBLE",
                "El reconocimiento facial no está disponible "
                "para tus clases en este momento."
            )

        if not reservas_disponibles:
            return respuesta_no_disponible(
                "ASISTENCIA_RESUELTA",
                "La asistencia de tus clases disponibles "
                "ya fue resuelta."
            )

        return Response(
            {
                "disponible": True,
                "codigo": "DISPONIBLE",
                "mensaje": (
                    "Puedes utilizar el reconocimiento facial "
                    "para registrar tu asistencia."
                ),
                "reservas": reservas_disponibles,
            },
            status=status.HTTP_200_OK
        )
