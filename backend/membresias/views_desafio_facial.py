
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

from clases.models import Clase
from usuarios.models import Usuario, RegistroFacial

from usuarios.servicios_faciales import (
    validar_consentimiento_facial,
)

from .models import (
    Reserva,
    SesionAsistenciaFacial,
    DesafioPruebaVida,
)

from .views_disponibilidad_facial import (
    SoloSocioAsistenciaFacial,
)


DURACION_DESAFIO_SEGUNDOS = 60


class DesafioFacialThrottle(UserRateThrottle):

    scope = "desafio_facial"
    rate = "5/min"


class CrearDesafioFacialView(APIView):

    permission_classes = [
        permissions.IsAuthenticated,
        SoloSocioAsistenciaFacial,
    ]

    throttle_classes = [
        DesafioFacialThrottle,
    ]

    def error(self, codigo, mensaje, estado=400):

        return Response(
            {
                "creado": False,
                "codigo": codigo,
                "mensaje": mensaje,
            },
            status=estado
        )

    @transaction.atomic
    def post(self, request):

        try:

            reserva_id = int(
                request.data.get("reserva_id")
            )

            if reserva_id <= 0:
                raise ValueError

        except (TypeError, ValueError):

            return self.error(
                "RESERVA_REQUERIDA",
                "Debes seleccionar una reserva válida."
            )

        socio = Usuario.objects.select_for_update().get(
            pk=request.user.pk
        )

        if not socio.is_active or socio.rol != "SOCIO":

            return self.error(
                "SOCIO_NO_AUTORIZADO",
                "No puedes utilizar el reconocimiento facial.",
                status.HTTP_403_FORBIDDEN
            )

        registro = (
            RegistroFacial.objects
            .select_for_update()
            .filter(socio=socio)
            .first()
        )

        if registro is None:

            return self.error(
                "SIN_REGISTRO_FACIAL",
                "No tienes un registro de reconocimiento facial."
            )

        try:

            validar_consentimiento_facial(registro)

        except ValueError:

            return self.error(
                "SIN_CONSENTIMIENTO",
                "Debes autorizar el reconocimiento facial."
            )

        if (
            not registro.activo
            or not socio.reconocimiento_facial_habilitado
            or not registro.datos_biometricos_cifrados
        ):

            return self.error(
                "RECONOCIMIENTO_INACTIVO",
                "No tienes el reconocimiento facial activo."
            )

        referencia = Reserva.objects.filter(
            pk=reserva_id,
            socio=socio
        ).values(
            "clase_id"
        ).first()

        if referencia is None:

            return self.error(
                "RESERVA_NO_VALIDA",
                "No tienes una reserva confirmada válida.",
                status.HTTP_404_NOT_FOUND
            )

        clase = Clase.objects.select_for_update().filter(
            pk=referencia["clase_id"],
            activa=True,
            fecha=timezone.localdate()
        ).first()

        if clase is None:

            return self.error(
                "RESERVA_NO_VALIDA",
                "La clase seleccionada no está disponible.",
                status.HTTP_404_NOT_FOUND
            )

        sesion = (
            SesionAsistenciaFacial.objects
            .select_for_update()
            .filter(clase=clase)
            .first()
        )

        reserva = (
            Reserva.objects
            .select_for_update()
            .filter(
                pk=reserva_id,
                socio=socio,
                clase=clase,
                estado=Reserva.Estado.CONFIRMADA
            )
            .first()
        )

        if reserva is None:

            return self.error(
                "RESERVA_NO_VALIDA",
                "No tienes una reserva confirmada válida.",
                status.HTTP_404_NOT_FOUND
            )

        if reserva.asistencia != Reserva.Asistencia.PENDIENTE:

            return self.error(
                "ASISTENCIA_RESUELTA",
                "La asistencia de esta clase ya fue resuelta.",
                status.HTTP_409_CONFLICT
            )

        if (
            sesion is None
            or not sesion.vigente
            or sesion.fecha_habilitacion is None
        ):

            return self.error(
                "SESION_NO_DISPONIBLE",
                "El reconocimiento facial no está disponible "
                "para esta clase en este momento."
            )

        ahora = timezone.now()

        DesafioPruebaVida.objects.filter(
            reserva__socio=socio,
            estado__in=[
                DesafioPruebaVida.Estado.PENDIENTE,
                DesafioPruebaVida.Estado.VALIDANDO,
            ],
            fecha_expiracion__lte=ahora
        ).update(
            estado=DesafioPruebaVida.Estado.EXPIRADO,
            fecha_resolucion=ahora
        )

        if DesafioPruebaVida.objects.filter(
            reserva__socio=socio,
            estado=DesafioPruebaVida.Estado.VALIDANDO
        ).exists():

            return self.error(
                "DESAFIO_EN_VALIDACION",
                "Ya tienes una prueba de vida en procesamiento.",
                status.HTTP_409_CONFLICT
            )

        DesafioPruebaVida.objects.filter(
            reserva__socio=socio,
            estado=DesafioPruebaVida.Estado.PENDIENTE
        ).update(
            estado=DesafioPruebaVida.Estado.CANCELADO,
            fecha_resolucion=ahora
        )

        direccion = secrets.choice([
            DesafioPruebaVida.Direccion.IZQUIERDA,
            DesafioPruebaVida.Direccion.DERECHA,
        ])

        fecha_expiracion = min(
            ahora + timedelta(
                seconds=DURACION_DESAFIO_SEGUNDOS
            ),
            sesion.fin_validez
        )

        if fecha_expiracion <= ahora:

            return self.error(
                "SESION_NO_DISPONIBLE",
                "El período de asistencia ha finalizado."
            )

        desafio = DesafioPruebaVida.objects.create(
            reserva=reserva,
            sesion=sesion,
            token=secrets.token_hex(32),
            direccion=direccion,
            estado=DesafioPruebaVida.Estado.PENDIENTE,
            fecha_habilitacion_sesion=sesion.fecha_habilitacion,
            fecha_expiracion=fecha_expiracion
        )

        segundos_disponibles = int(
            (fecha_expiracion - ahora).total_seconds()
        )

        return Response(
            {
                "creado": True,
                "codigo": "DESAFIO_CREADO",
                "mensaje": (
                    "Realiza los movimientos faciales solicitados."
                ),
                "token_desafio": desafio.token,
                "reserva_id": reserva.id,
                "clase_id": clase.id,
                "direccion": desafio.direccion,
                "duracion_segundos": segundos_disponibles,
                "fecha_expiracion": desafio.fecha_expiracion,
                "secuencia": [
                    "MIRAR_FRENTE",
                    "CERRAR_OJOS",
                    "ABRIR_OJOS",
                    desafio.direccion,
                    "MIRAR_FRENTE",
                ],
            },
            status=status.HTTP_201_CREATED
        )
