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
    PersonalAsistenciaFacial,
    puede_administrar_clase,
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


def obtener_contexto_bloqueado(responsable_id, token):

    referencia = (
        DesafioPruebaVida.objects
        .filter(
            token=token,
            generado_por_id=responsable_id
        )
        .values(
            "id",
            "reserva_id",
            "reserva__socio_id",
            "reserva__clase_id",
            "sesion_id",
        )
        .first()
    )

    if referencia is None:
        return None

    responsable = Usuario.objects.filter(
        pk=responsable_id
    ).first()

    if responsable is None:
        return None

    socio = (
        Usuario.objects
        .select_for_update()
        .filter(
            pk=referencia["reserva__socio_id"]
        )
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
            sesion=sesion,
            generado_por=responsable
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
        "responsable": responsable,
        "socio": socio,
        "registro": registro,
        "clase": clase,
        "sesion": sesion,
        "reserva": reserva,
        "desafio": desafio,
    }


def validar_contexto(contexto):

    responsable = contexto["responsable"]
    socio = contexto["socio"]
    registro = contexto["registro"]
    clase = contexto["clase"]
    sesion = contexto["sesion"]
    reserva = contexto["reserva"]
    desafio = contexto["desafio"]

    if not puede_administrar_clase(
        responsable,
        clase
    ):

        return (
            "SIN_PERMISOS",
            "No tienes permiso para administrar "
            "la asistencia de esta clase."
        )

    if desafio.generado_por_id != responsable.id:

        return (
            "RESPONSABLE_NO_VALIDO",
            "El desafío pertenece a otro responsable."
        )

    if not socio.is_active or socio.rol != "SOCIO":

        return (
            "SOCIO_NO_AUTORIZADO",
            "El socio no tiene una cuenta activa válida."
        )

    if registro is None:

        return (
            "SIN_REGISTRO_FACIAL",
            "El socio no tiene un registro facial."
        )

    try:

        validar_consentimiento_facial(registro)

    except ValueError:

        return (
            "SIN_CONSENTIMIENTO",
            "El socio no ha autorizado "
            "el reconocimiento facial."
        )

    if (
        not registro.activo
        or not socio.reconocimiento_facial_habilitado
        or not registro.datos_biometricos_cifrados
    ):

        return (
            "RECONOCIMIENTO_INACTIVO",
            "El socio no tiene el "
            "reconocimiento facial activo."
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
            "La asistencia de este socio ya fue resuelta."
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
        PersonalAsistenciaFacial,
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

        estado_http = (
            status.HTTP_403_FORBIDDEN
            if codigo in [
                "SIN_PERMISOS",
                "RESPONSABLE_NO_VALIDO",
            ]
            else status.HTTP_409_CONFLICT
        )

        return self.error(
            codigo,
            mensaje,
            estado_http
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
                    "No se encontró un desafío válido "
                    "para este responsable.",
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

        except ValueError as e:

            print(
                "ERROR REAL DE FOTOGRAMAS:",
                repr(e),
                flush=True
            )

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
            responsable = contexto["responsable"]
            socio = contexto["socio"]

            reserva.asistencia = (
                Reserva.Asistencia.ASISTIO
            )

            reserva.fecha_registro_asistencia = (
                timezone.now()
            )

            reserva.registrado_por = responsable

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
                        "La identidad del socio fue verificada "
                        "y su asistencia se registró correctamente."
                    ),
                    "reserva_id": reserva.id,
                    "clase_id": contexto["clase"].id,
                    "socio_id": socio.id,
                    "nombre_socio": socio.get_full_name().strip(),
                    "registrado_por": responsable.id,
                    "rol_responsable": responsable.rol,
                    "asistencia": reserva.asistencia,
                    "fecha_registro_asistencia": (
                        reserva.fecha_registro_asistencia
                    ),
                },
                status=status.HTTP_200_OK
            )