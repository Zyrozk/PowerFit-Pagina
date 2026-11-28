import logging

from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

from usuarios.models import RegistroFacial
from usuarios.servicios_faciales import (
    validar_consentimiento_facial,
    verificar_imagen_facial,
)

from .models import Reserva, SesionAsistenciaFacial

from .views_disponibilidad_facial import (
    PersonalAsistenciaFacial,
    puede_administrar_clase,
)


logger = logging.getLogger(__name__)


class VerificacionFacialThrottle(UserRateThrottle):

    scope = "verificacion_facial"
    rate = "5/min"


class VerificacionAsistenciaFacialView(APIView):

    permission_classes = [
        permissions.IsAuthenticated,
        PersonalAsistenciaFacial,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    throttle_classes = [
        VerificacionFacialThrottle,
    ]

    def error(self, codigo, mensaje, estado=400):

        return Response(
            {
                "verificado": False,
                "asistencia_registrada": False,
                "codigo": codigo,
                "mensaje": mensaje,
            },
            status=estado
        )

    def post(self, request):

        responsable = request.user

        reserva_id = request.data.get("reserva_id")
        imagen = request.FILES.get("imagen")

        try:

            reserva_id = int(reserva_id)

            if reserva_id <= 0:
                raise ValueError

        except (TypeError, ValueError):

            return self.error(
                "RESERVA_REQUERIDA",
                "Debes seleccionar una reserva válida."
            )

        reservas = Reserva.objects.filter(
            pk=reserva_id
        ).select_related(
            "clase",
            "socio"
        )

        if responsable.rol == "COACH":

            reservas = reservas.filter(
                clase__coach_id=responsable.id
            )

        reserva = reservas.first()

        if reserva is None:

            return self.error(
                "RESERVA_NO_VALIDA",
                "La reserva no existe o no tienes "
                "permiso para administrarla.",
                status.HTTP_404_NOT_FOUND
            )

        if not puede_administrar_clase(
            responsable,
            reserva.clase
        ):

            return self.error(
                "SIN_PERMISOS",
                "No tienes permiso para administrar "
                "la asistencia de esta clase.",
                status.HTTP_403_FORBIDDEN
            )

        if reserva.estado != Reserva.Estado.CONFIRMADA:

            return self.error(
                "RESERVA_NO_CONFIRMADA",
                "La reserva del socio no está confirmada."
            )

        if not reserva.clase.activa:

            return self.error(
                "CLASE_INACTIVA",
                "La clase seleccionada no está activa."
            )

        if reserva.clase.fecha != timezone.localdate():

            return self.error(
                "FECHA_NO_VALIDA",
                "Solo puedes verificar la asistencia "
                "de clases correspondientes al día de hoy."
            )

        if reserva.asistencia != Reserva.Asistencia.PENDIENTE:

            return self.error(
                "ASISTENCIA_RESUELTA",
                "La asistencia de este socio ya fue resuelta.",
                status.HTTP_409_CONFLICT
            )

        sesion = SesionAsistenciaFacial.objects.filter(
            clase_id=reserva.clase_id
        ).select_related(
            "clase"
        ).first()

        if sesion is None or not sesion.vigente:

            return self.error(
                "SESION_NO_DISPONIBLE",
                "El reconocimiento facial no está disponible "
                "para esta clase en este momento."
            )

        socio = reserva.socio

        if not socio.is_active or socio.rol != "SOCIO":

            return self.error(
                "SOCIO_NO_VALIDO",
                "La cuenta del socio no está activa "
                "o no corresponde a un socio válido."
            )

        registro = RegistroFacial.objects.filter(
            socio=socio
        ).select_related(
            "socio"
        ).first()

        if registro is None:

            return self.error(
                "SIN_REGISTRO_FACIAL",
                "El socio no tiene un registro facial. "
                "Puedes utilizar el registro mediante QR."
            )

        try:

            validar_consentimiento_facial(registro)

        except ValueError:

            return self.error(
                "SIN_CONSENTIMIENTO",
                "El socio no ha autorizado el uso "
                "del reconocimiento facial."
            )

        if (
            not registro.activo
            or not registro.socio.reconocimiento_facial_habilitado
            or not registro.datos_biometricos_cifrados
        ):

            return self.error(
                "RECONOCIMIENTO_INACTIVO",
                "El socio no tiene el reconocimiento facial activo."
            )

        if imagen is None:

            return self.error(
                "IMAGEN_REQUERIDA",
                "Debes capturar una fotografía "
                "del rostro del socio."
            )

        try:

            resultado = verificar_imagen_facial(
                registro,
                imagen
            )

        except ValueError:

            return self.error(
                "IMAGEN_NO_VALIDA",
                "No fue posible verificar el rostro. "
                "Captura una fotografía clara donde aparezca "
                "solamente el rostro del socio."
            )

        except Exception:

            logger.error(
                "Error interno durante la verificación facial."
            )

            return self.error(
                "ERROR_VERIFICACION",
                "No fue posible completar la verificación facial.",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        if not resultado["coincidencia"]:

            return self.error(
                "ROSTRO_NO_COINCIDE",
                "El rostro capturado no coincide "
                "con el registro facial del socio."
            )

        return Response(
            {
                "verificado": True,
                "asistencia_registrada": False,
                "codigo": "ROSTRO_VERIFICADO",
                "mensaje": (
                    "El rostro coincide con el registro facial "
                    "del socio. Debes completar la prueba de vida."
                ),
                "reserva_id": reserva.id,
                "clase_id": reserva.clase_id,
                "socio_id": socio.id,
            },
            status=status.HTTP_200_OK
        )