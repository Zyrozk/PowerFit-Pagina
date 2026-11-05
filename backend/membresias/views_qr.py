
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import (
    NotFound,
    PermissionDenied,
    ValidationError,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from clases.models import Clase
from .models import (
    CambioExcepcionalAsistencia,
    Membresia,
    Reserva,
    SesionQRAsistencia,
    generar_token_qr,
)
from .serializers import ReservaSerializer


def verificar_administrador_clase(usuario, clase):
    if usuario.rol == 'DUENA':
        return

    if usuario.rol == 'COACH' and clase.coach_id == usuario.pk:
        return

    raise PermissionDenied(
        'No tienes permiso para administrar esta clase.'
    )


def obtener_clase(clase_id):
    try:
        return Clase.objects.get(pk=clase_id)
    except Clase.DoesNotExist:
        raise NotFound('Clase no encontrada.')


def datos_sesion(sesion):
    return {
        'clase_id': sesion.clase_id,
        'habilitada': sesion.habilitada,
        'vigente': sesion.vigente,
        'token': sesion.token,
        'inicio_validez': sesion.inicio_validez,
        'fin_validez': sesion.fin_validez,
    }


class SesionQRClaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, clase_id):
        clase = obtener_clase(clase_id)
        verificar_administrador_clase(request.user, clase)

        try:
            sesion = SesionQRAsistencia.objects.get(clase=clase)
        except SesionQRAsistencia.DoesNotExist:
            return Response({
                'clase_id': clase.id,
                'habilitada': False,
                'vigente': False,
                'token': None,
            })

        return Response(datos_sesion(sesion))

    def post(self, request, clase_id):
        with transaction.atomic():
            try:
                clase = Clase.objects.select_for_update().get(
                    pk=clase_id
                )
            except Clase.DoesNotExist:
                raise NotFound('Clase no encontrada.')

            verificar_administrador_clase(request.user, clase)

            if not clase.activa:
                raise ValidationError(
                    'No puedes habilitar QR en una clase desactivada.'
                )

            sesion, creada = (
                SesionQRAsistencia.objects.select_for_update()
                .get_or_create(
                    clase=clase,
                    defaults={
                        'generada_por': request.user,
                        'habilitada': True,
                    }
                )
            )

            if not creada:
                sesion.token = generar_token_qr()
                sesion.habilitada = True
                sesion.generada_por = request.user
                sesion.save()

        return Response(datos_sesion(sesion))


class DeshabilitarQRClaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, clase_id):
        with transaction.atomic():
            try:
                sesion = (
                    SesionQRAsistencia.objects
                    .select_for_update()
                    .select_related('clase')
                    .get(clase_id=clase_id)
                )
            except SesionQRAsistencia.DoesNotExist:
                raise NotFound('Esta clase no tiene una sesión QR.')

            verificar_administrador_clase(
                request.user,
                sesion.clase
            )

            sesion.habilitada = False
            sesion.save(update_fields=[
                'habilitada',
                'fecha_actualizacion',
            ])

        return Response({
            'mensaje': 'QR deshabilitado correctamente.',
            'clase_id': clase_id,
            'habilitada': False,
        })


class EscanearQRAsistenciaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.rol != 'SOCIO':
            raise PermissionDenied(
                'Solo los socios pueden registrar asistencia mediante QR.'
            )

        token = request.data.get('token')

        if not isinstance(token, str) or not token.strip():
            raise ValidationError({
                'token': 'Debes proporcionar un código QR válido.'
            })

        with transaction.atomic():
            try:
                sesion = (
                    SesionQRAsistencia.objects
                    .select_related('clase')
                    .get(token=token.strip())
                )
            except SesionQRAsistencia.DoesNotExist:
                raise ValidationError({
                    'codigo': 'QR_INVALIDO',
                    'mensaje': 'El código QR no es válido.'
                })

            if not sesion.vigente:
                raise ValidationError({
                    'codigo': 'QR_NO_DISPONIBLE',
                    'mensaje': (
                        'El QR está deshabilitado o fuera '
                        'del horario permitido.'
                    )
                })

            try:
                reserva = (
                    Reserva.objects
                    .select_for_update()
                    .select_related('clase', 'membresia')
                    .get(
                        clase_id=sesion.clase_id,
                        socio=request.user,
                        estado=Reserva.Estado.CONFIRMADA,
                    )
                )
            except Reserva.DoesNotExist:
                raise ValidationError({
                    'codigo': 'SIN_RESERVA',
                    'mensaje': (
                        'No tienes una reserva confirmada '
                        'para esta clase.'
                    )
                })

            if reserva.asistencia != Reserva.Asistencia.PENDIENTE:
                return Response({
                    'codigo': 'ASISTENCIA_YA_REGISTRADA',
                    'mensaje': 'Tu asistencia ya fue registrada.',
                    'reserva': ReservaSerializer(reserva).data,
                })

            reserva.asistencia = Reserva.Asistencia.ASISTIO
            reserva.fecha_registro_asistencia = timezone.now()
            reserva.registrado_por = request.user
            reserva.save(update_fields=[
                'asistencia',
                'fecha_registro_asistencia',
                'registrado_por',
            ])

        return Response({
            'codigo': 'ASISTENCIA_REGISTRADA',
            'mensaje': 'Tu asistencia fue registrada correctamente.',
            'reserva': ReservaSerializer(reserva).data,
        }, status=status.HTTP_200_OK)


class CambioExcepcionalAsistenciaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, reserva_id):
        nueva_asistencia = request.data.get('asistencia')
        motivo = request.data.get('motivo', '')

        if nueva_asistencia not in (
            Reserva.Asistencia.ASISTIO,
            Reserva.Asistencia.NO_ASISTIO,
        ):
            raise ValidationError({
                'asistencia': 'Usa ASISTIO o NO_ASISTIO.'
            })

        if not isinstance(motivo, str) or not motivo.strip():
            raise ValidationError({
                'motivo': 'Debes indicar el motivo del cambio excepcional.'
            })

        if len(motivo.strip()) > 1000:
            raise ValidationError({
                'motivo': 'El motivo no puede superar los 1000 caracteres.'
            })

        with transaction.atomic():
            try:
                reserva = (
                    Reserva.objects
                    .select_for_update()
                    .select_related('clase', 'membresia')
                    .get(pk=reserva_id)
                )
            except Reserva.DoesNotExist:
                raise NotFound('Reserva no encontrada.')

            if request.user.rol != 'DUENA':
             raise PermissionDenied(
                'Solo la dueña puede realizar cambios excepcionales de asistencia.'
    )

            if reserva.estado != Reserva.Estado.CONFIRMADA:
                raise ValidationError(
                    'Solo puedes corregir reservas confirmadas.'
                )

            fin_clase = timezone.make_aware(
                datetime.combine(
                    reserva.clase.fecha,
                    reserva.clase.hora_fin,
                ),
                timezone.get_current_timezone(),
            )

            if timezone.now() < fin_clase:
                raise ValidationError(
                    'El cambio excepcional se permite después '
                    'de finalizar la clase.'
                )

            asistencia_anterior = reserva.asistencia

            if asistencia_anterior == nueva_asistencia:
                raise ValidationError(
                    'La asistencia ya tiene el estado solicitado.'
                )

            membresia = None
            clases_antes = None
            clases_despues = None

            if reserva.membresia_id:
                membresia = (
                    Membresia.objects
                    .select_for_update()
                    .get(pk=reserva.membresia_id)
                )
                clases_antes = membresia.clases_restantes

                if nueva_asistencia == Reserva.Asistencia.ASISTIO:
                    if reserva.clase_devuelta:
                        if membresia.clases_restantes < 1:
                            raise ValidationError(
                                'No se puede revertir la devolución: '
                                'la membresía no tiene clases disponibles.'
                            )

                        membresia.clases_restantes -= 1
                        reserva.clase_devuelta = False
                        membresia.save(
                            update_fields=['clases_restantes']
                        )

                elif nueva_asistencia == Reserva.Asistencia.NO_ASISTIO:
                    if (
                        not reserva.clase_devuelta
                        and membresia.vigente
                        and membresia.clases_restantes
                        < membresia.clases_totales
                    ):
                        membresia.clases_restantes += 1
                        reserva.clase_devuelta = True
                        membresia.save(
                            update_fields=['clases_restantes']
                        )

                clases_despues = membresia.clases_restantes

            reserva.asistencia = nueva_asistencia
            reserva.fecha_registro_asistencia = timezone.now()
            reserva.registrado_por = request.user
            reserva.save(update_fields=[
                'asistencia',
                'fecha_registro_asistencia',
                'registrado_por',
                'clase_devuelta',
            ])

            cambio = CambioExcepcionalAsistencia.objects.create(
                reserva=reserva,
                asistencia_anterior=asistencia_anterior,
                asistencia_nueva=nueva_asistencia,
                motivo=motivo.strip(),
                realizado_por=request.user,
                clases_restantes_antes=clases_antes,
                clases_restantes_despues=clases_despues,
            )

        return Response({
            'codigo': 'CAMBIO_EXCEPCIONAL_REGISTRADO',
            'mensaje': 'La asistencia fue corregida correctamente.',
            'cambio_id': cambio.id,
            'reserva': ReservaSerializer(reserva).data,
        })
