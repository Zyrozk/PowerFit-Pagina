from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from clases.models import Clase
from usuarios.models import RegistroFacial
from usuarios.servicios_faciales import validar_consentimiento_facial

from .models import Reserva, SesionAsistenciaFacial


class SoloSocioAsistenciaFacial(permissions.BasePermission):

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.rol == "SOCIO"
        )


class PersonalAsistenciaFacial(permissions.BasePermission):

    message = (
        "Solo la dueña y los coaches pueden "
        "administrar la asistencia facial."
    )

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.rol in ["DUENA", "COACH"]
        )


def puede_administrar_clase(usuario, clase):

    if not usuario.is_authenticated or not usuario.is_active:
        return False

    if usuario.rol == "DUENA":
        return True

    if usuario.rol == "COACH":
        return clase.coach_id == usuario.id

    return False


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
        PersonalAsistenciaFacial,
    ]

    def get(self, request):

        clase_id = request.query_params.get("clase_id")

        try:
            clase_id = int(clase_id)

            if clase_id <= 0:
                raise ValueError

        except (TypeError, ValueError):

            return Response(
                {
                    "detail": "Debes indicar una clase válida."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        clases = Clase.objects.filter(pk=clase_id)

        if request.user.rol == "COACH":
            clases = clases.filter(
                coach_id=request.user.id
            )

        clase = clases.first()

        if clase is None:

            return Response(
                {
                    "detail": (
                        "La clase no existe o no tienes "
                        "permiso para administrarla."
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )

        if not clase.activa:

            return respuesta_no_disponible(
                "CLASE_INACTIVA",
                "La clase seleccionada no está activa."
            )

        if clase.fecha != timezone.localdate():

            return respuesta_no_disponible(
                "FECHA_NO_VALIDA",
                "Solo puedes registrar asistencia facial "
                "en clases correspondientes al día de hoy."
            )

        sesion = SesionAsistenciaFacial.objects.filter(
            clase=clase
        ).select_related(
            "clase"
        ).first()

        if sesion is None or not sesion.vigente:

            return respuesta_no_disponible(
                "SESION_NO_DISPONIBLE",
                "La sesión de reconocimiento facial "
                "no está habilitada o no se encuentra vigente."
            )

        reservas = list(
            Reserva.objects.filter(
                clase=clase,
                estado=Reserva.Estado.CONFIRMADA
            ).select_related(
                "socio"
            ).order_by(
                "socio__first_name",
                "socio__last_name",
                "id"
            )
        )

        if not reservas:

            return respuesta_no_disponible(
                "SIN_RESERVAS",
                "No hay socios con reservas confirmadas "
                "para esta clase."
            )

        reservas_pendientes = [
            reserva
            for reserva in reservas
            if reserva.asistencia == Reserva.Asistencia.PENDIENTE
        ]

        if not reservas_pendientes:

            return respuesta_no_disponible(
                "ASISTENCIA_RESUELTA",
                "No quedan asistencias pendientes "
                "para esta clase."
            )

        registros = {
            registro.socio_id: registro
            for registro in RegistroFacial.objects.filter(
                socio_id__in=[
                    reserva.socio_id
                    for reserva in reservas_pendientes
                ]
            ).select_related("socio")
        }

        reservas_disponibles = []

        for reserva in reservas_pendientes:

            socio = reserva.socio

            if not socio.is_active:
                continue

            if socio.rol != "SOCIO":
                continue

            registro = registros.get(socio.id)

            if registro is None:
                continue

            try:
                validar_consentimiento_facial(registro)

            except ValueError:
                continue

            if (
                not registro.activo
                or not socio.reconocimiento_facial_habilitado
                or not registro.datos_biometricos_cifrados
            ):
                continue

            reservas_disponibles.append({
                "reserva_id": reserva.id,
                "socio_id": socio.id,
                "nombre_socio": socio.get_full_name().strip(),
                "clase_id": clase.id,
                "nombre_clase": clase.get_tipo_display(),
                "fecha": clase.fecha.isoformat(),
                "hora_inicio": clase.hora_inicio.strftime("%H:%M"),
                "hora_fin": clase.hora_fin.strftime("%H:%M"),
                "asistencia": reserva.asistencia,
                "inicio_validez": sesion.inicio_validez,
                "fin_validez": sesion.fin_validez,
            })

        if not reservas_disponibles:

            return respuesta_no_disponible(
                "SIN_SOCIOS_HABILITADOS",
                "No hay socios pendientes con "
                "reconocimiento facial habilitado. "
                "Puedes utilizar el registro mediante QR."
            )

        return Response(
            {
                "disponible": True,
                "codigo": "DISPONIBLE",
                "mensaje": (
                    "Hay socios disponibles para "
                    "el reconocimiento facial."
                ),
                "clase_id": clase.id,
                "total_inscritos": len(reservas),
                "total_registrados": sum(
                    reserva.asistencia == Reserva.Asistencia.ASISTIO
                    for reserva in reservas
                ),
                "total_pendientes": len(reservas_pendientes),
                "total_disponibles": len(reservas_disponibles),
                "reservas": reservas_disponibles,
            },
            status=status.HTTP_200_OK
        )