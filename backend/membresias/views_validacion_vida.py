
import logging

from django.db import transaction
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle

from clases.models import Clase

from usuarios.models import Usuario, RegistroFacial

from usuarios.servicios_faciales import (
    validar_consentimiento_facial,
)

from usuarios.servicios_validacion_vida import (
    validar_archivos_fotogramas,
    validar_prueba_vida_con_identidad,
)

from .models import (
    Reserva,
    SesionAsistenciaFacial,
    DesafioPruebaVida,
)

from .views_disponibilidad_facial import (
    SoloSocioAsistenciaFacial,
)


logger = logging.getLogger(__name__)


class ValidacionVidaThrottle(UserRateThrottle):

    scope = "validacion_vida"
    rate = "5/min"


def resolver_desafio(desafio, estado):

    desafio.estado = estado
    desafio.fecha_resolucion = timezone.now()

    desafio.save(
        update_fields=[
            "estado",
            "fecha_resolucion",
        ]
    )


def obtener_contexto_bloqueado(socio_id, token):

    socio = (
        Usuario.objects
        .select_for_update()
        .filter(pk=socio_id)
        .first()
    )

    if socio is None:
        return None

    registro = (
        RegistroFacial.objects
        .select_for_update()
        .filter(socio=socio)
        .first()
    )

    referencia = (
        DesafioPruebaVida.objects
        .filter(
            token=token,
            reserva__socio=socio
        )
        .values(
            "id",
            "reserva_id",
            "reserva__clase_id",
            "sesion_id",
        )
        .first()
    )

    if referencia is None:
        return None

    clase = (
        Clase.objects
        .select_for_update()
        .filter(
            pk=referencia["reserva__clase_id"]
        )
        .first()
    )

    if clase is None:
        return None

    sesion = (
        SesionAsistenciaFacial.objects
        .select_for_update()
        .filter(
            pk=referencia["sesion_id"],
            clase=clase
        )
        .first()
    )

    reserva = (
        Reserva.objects
        .select_for_update()
        .filter(
            pk=referencia["reserva_id"],
            socio=socio,
            clase=clase
        )
        .first()
    )

    if sesion is None or reserva is None:
        return None

    desafio = (
        DesafioPruebaVida.objects
        .select_for_update()
        .filter(
            pk=referencia["id"],
            token=token,
            reserva=reserva,
            sesion=sesion
        )
        .first()
    )

    if desafio is None:
        return None

    sesion.clase = clase
    desafio.sesion = sesion

    if registro is not None:
        registro.socio = socio

    return {
        "socio": socio,
        "registro": registro,
        "clase": clase,
        "sesion": sesion,
        "reserva": reserva,
        "desafio": desafio,
    }


def validar_contexto(contexto):

    socio = contexto["socio"]
    registro = contexto["registro"]
    clase = contexto["clase"]
    sesion = contexto["sesion"]
    reserva = contexto["reserva"]
    desafio = contexto["desafio"]

    if not socio.is_active or socio.rol != "SOCIO":

        return (
            "SOCIO_NO_AUTORIZADO",
            "No puedes utilizar el reconocimiento facial."
        )

    if registro is None:

        return (
            "SIN_REGISTRO_FACIAL",
            "No tienes un registro facial."
        )

    try:

        validar_consentimiento_facial(registro)

    except ValueError:

        return (
            "SIN_CONSENTIMIENTO",
            "Debes autorizar el reconocimiento facial."
        )

    if (
        not registro.activo
        or not socio.reconocimiento_facial_habilitado
        or not registro.datos_biometricos_cifrados
    ):

        return (
            "RECONOCIMIENTO_INACTIVO",
            "No tienes el reconocimiento facial activo."
        )

    if (
        not clase.activa
        or clase.fecha != timezone.localdate()
        or reserva.estado != Reserva.Estado.CONFIRMADA
    ):

        return (
            "RESERVA_NO_VALIDA",
            "La reserva seleccionada ya no es válida."
        )

    if reserva.asistencia != Reserva.Asistencia.PENDIENTE:

        return (
            "ASISTENCIA_RESUELTA",
            "La asistencia de esta clase ya fue resuelta."
        )

    if timezone.now() >= desafio.fecha_expiracion:

        return (
            "DESAFIO_EXPIRADO",
            "El tiempo de la prueba de vida ha finalizado."
        )

    if (
        not sesion.vigente
        or sesion.fecha_habilitacion
        != desafio.fecha_habilitacion_sesion
    ):

        return (
            "SESION_NO_DISPONIBLE",
            "La sesión de reconocimiento facial "
            "ya no está disponible."
        )

    return None


class ValidarPruebaVidaView(APIView):

    permission_classes = [
        permissions.IsAuthenticated,
        SoloSocioAsistenciaFacial,
    ]

    parser_classes = [
        MultiPartParser,
        FormParser,
    ]

    throttle_classes = [
        ValidacionVidaThrottle,
    ]

    def error(
        self,
        codigo,
        mensaje,
        estado=400
    ):

        return Response(
            {
                "superada": False,
                "asistencia_registrada": False,
                "codigo": codigo,
                "mensaje": mensaje,
            },
            status=estado
        )

    def cancelar_por_contexto(
        self,
        desafio,
        error_contexto
    ):

        codigo, mensaje = error_contexto

        if codigo == "DESAFIO_EXPIRADO":

            estado_desafio = (
                DesafioPruebaVida.Estado.EXPIRADO
            )

        else:

            estado_desafio = (
                DesafioPruebaVida.Estado.CANCELADO
            )

        resolver_desafio(
            desafio,
            estado_desafio
        )

        return self.error(
            codigo,
            mensaje,
            status.HTTP_409_CONFLICT
        )

    def post(self, request):

        token = request.data.get(
            "token_desafio"
        )

        if not isinstance(token, str):

            return self.error(
                "TOKEN_REQUERIDO",
                "Debes proporcionar un desafío válido."
            )

        token = token.strip()

        if len(token) != 64:

            return self.error(
                "TOKEN_INVALIDO",
                "El desafío facial no es válido."
            )

        try:

            if len(bytes.fromhex(token)) != 32:
                raise ValueError

        except ValueError:

            return self.error(
                "TOKEN_INVALIDO",
                "El desafío facial no es válido."
            )

        archivos = request.FILES.getlist(
            "fotogramas"
        )

        try:

            validar_archivos_fotogramas(
                archivos
            )

        except ValueError as error:

            return self.error(
                "FOTOGRAMAS_INVALIDOS",
                str(error)
            )

        with transaction.atomic():

            contexto = obtener_contexto_bloqueado(
                request.user.pk,
                token
            )

            if contexto is None:

                return self.error(
                    "DESAFIO_NO_ENCONTRADO",
                    "No se encontró un desafío válido.",
                    status.HTTP_404_NOT_FOUND
                )

            desafio = contexto["desafio"]

            if (
                desafio.estado
                != DesafioPruebaVida.Estado.PENDIENTE
            ):

                return self.error(
                    "DESAFIO_NO_DISPONIBLE",
                    "El desafío ya fue utilizado "
                    "o no está disponible.",
                    status.HTTP_409_CONFLICT
                )

            error_contexto = validar_contexto(
                contexto
            )

            if error_contexto is not None:

                return self.cancelar_por_contexto(
                    desafio,
                    error_contexto
                )

            registro = contexto["registro"]

            registro_id = registro.pk

            fecha_enrolamiento = (
                registro.fecha_enrolamiento
            )

            datos_cifrados = bytes(
                registro.datos_biometricos_cifrados
            )

            direccion = desafio.direccion

            desafio.estado = (
                DesafioPruebaVida.Estado.VALIDANDO
            )

            desafio.save(
                update_fields=["estado"]
            )

        error_procesamiento = None
        resultado = None

        try:

            resultado = validar_prueba_vida_con_identidad(
                registro,
                archivos,
                direccion
            )

        except ValueError:

            error_procesamiento = (
                "FOTOGRAMAS_NO_VALIDOS",
                "No fue posible validar los fotogramas. "
                "Intenta nuevamente.",
                status.HTTP_400_BAD_REQUEST
            )

        except Exception:

            logger.error(
                "Error interno durante la prueba de vida."
            )

            error_procesamiento = (
                "ERROR_VALIDACION",
                "Ocurrió un error durante "
                "la validación facial.",
                status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        with transaction.atomic():

            contexto = obtener_contexto_bloqueado(
                request.user.pk,
                token
            )

            if contexto is None:

                return self.error(
                    "DESAFIO_NO_ENCONTRADO",
                    "El desafío ya no está disponible.",
                    status.HTTP_404_NOT_FOUND
                )

            desafio = contexto["desafio"]

            if (
                desafio.estado
                != DesafioPruebaVida.Estado.VALIDANDO
            ):

                return self.error(
                    "DESAFIO_NO_DISPONIBLE",
                    "El desafío ya no está disponible.",
                    status.HTTP_409_CONFLICT
                )

            error_contexto = validar_contexto(
                contexto
            )

            if error_contexto is not None:

                return self.cancelar_por_contexto(
                    desafio,
                    error_contexto
                )

            registro_actual = contexto["registro"]

            if (
                registro_actual.pk != registro_id
                or registro_actual.fecha_enrolamiento
                != fecha_enrolamiento
                or bytes(
                    registro_actual.datos_biometricos_cifrados
                ) != datos_cifrados
            ):

                resolver_desafio(
                    desafio,
                    DesafioPruebaVida.Estado.CANCELADO
                )

                return self.error(
                    "REGISTRO_FACIAL_MODIFICADO",
                    "El registro facial fue modificado. "
                    "Debes iniciar un nuevo desafío.",
                    status.HTTP_409_CONFLICT
                )

            if error_procesamiento is not None:

                resolver_desafio(
                    desafio,
                    DesafioPruebaVida.Estado.FALLIDO
                )

                codigo, mensaje, estado_http = (
                    error_procesamiento
                )

                return self.error(
                    codigo,
                    mensaje,
                    estado_http
                )

            if (
                not resultado["superada"]
                or not resultado["identidad_verificada"]
            ):

                resolver_desafio(
                    desafio,
                    DesafioPruebaVida.Estado.FALLIDO
                )

                return self.error(
                    resultado["codigo"],
                    resultado["mensaje"]
                )

            
            reserva = contexto["reserva"]

            reserva.asistencia = Reserva.Asistencia.ASISTIO

            reserva.fecha_registro_asistencia = (
                timezone.now()
            )

            reserva.registrado_por = contexto["socio"]

            reserva.save(
                update_fields=[
                    "asistencia",
                    "fecha_registro_asistencia",
                    "registrado_por",
                ]
            )

            resolver_desafio(
                desafio,
                DesafioPruebaVida.Estado.SUPERADO
            )

            return Response(
                {
                    "superada": True,
                    "identidad_verificada": True,
                    "asistencia_registrada": True,
                    "codigo": "ASISTENCIA_REGISTRADA",
                    "mensaje": (
                        "Tu identidad fue verificada "
                        "y tu asistencia se registró "
                        "correctamente."
                    ),
                    "reserva_id": reserva.id,
                    "clase_id": contexto["clase"].id,
                    "asistencia": reserva.asistencia,
                    "fecha_registro_asistencia": (
                        reserva.fecha_registro_asistencia
                    ),
                },
                status=status.HTTP_200_OK
            )
