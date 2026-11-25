
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import permissions, status
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from clases.models import Clase

from .models import SesionAsistenciaFacial


class PermisoGestionAsistenciaFacial(BasePermission):

    message = (
        "No tienes permiso para gestionar "
        "la asistencia facial de esta clase."
    )

    def has_permission(self, request, view):

        usuario = request.user

        return (
            usuario.is_authenticated
            and usuario.is_active
            and usuario.rol in ["DUENA", "COACH"]
        )

    def has_object_permission(self, request, view, obj):

        usuario = request.user

        if usuario.rol == "DUENA":
            return True

        if usuario.rol == "COACH":
            return obj.coach_id == usuario.id

        return False


def datos_sesion_facial(clase, sesion):

    if sesion is None:
        return {
            "clase_id": clase.id,
            "tiene_sesion": False,
            "habilitada": False,
            "vigente": False,
            "habilitada_por": None,
            "fecha_habilitacion": None,
            "fecha_desactivacion": None,
            "inicio_validez": None,
            "fin_validez": None,
        }

    return {
        "clase_id": clase.id,
        "tiene_sesion": True,
        "habilitada": sesion.habilitada,
        "vigente": sesion.vigente,
        "habilitada_por": sesion.habilitada_por_id,
        "fecha_habilitacion": sesion.fecha_habilitacion,
        "fecha_desactivacion": sesion.fecha_desactivacion,
        "inicio_validez": sesion.inicio_validez,
        "fin_validez": sesion.fin_validez,
    }


class SesionAsistenciaFacialView(APIView):

    permission_classes = [
        permissions.IsAuthenticated,
        PermisoGestionAsistenciaFacial,
    ]

    def get(self, request, clase_id):

        clase = get_object_or_404(
            Clase,
            pk=clase_id
        )

        self.check_object_permissions(
            request,
            clase
        )

        sesion = SesionAsistenciaFacial.objects.filter(
            clase=clase
        ).first()

        return Response(
            datos_sesion_facial(clase, sesion),
            status=status.HTTP_200_OK
        )

    @transaction.atomic
    def post(self, request, clase_id):

        clase = get_object_or_404(
            Clase.objects.select_for_update(),
            pk=clase_id
        )

        self.check_object_permissions(
            request,
            clase
        )

        if not clase.activa:
            return Response(
                {
                    "error": (
                        "No se puede habilitar el reconocimiento "
                        "facial de una clase inactiva."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        sesion = (
            SesionAsistenciaFacial.objects
            .select_for_update()
            .filter(clase=clase)
            .first()
        )

        if sesion is None:
            sesion = SesionAsistenciaFacial(
                clase=clase
            )

        ahora = timezone.now()

        if ahora > sesion.fin_validez:
            return Response(
                {
                    "error": (
                        "El período de registro de asistencia "
                        "de esta clase ha finalizado."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if sesion.habilitada:
            return Response(
                {
                    "mensaje": (
                        "El reconocimiento facial "
                        "ya está habilitado."
                    ),
                    **datos_sesion_facial(clase, sesion),
                },
                status=status.HTTP_200_OK
            )

        sesion.habilitada = True
        sesion.habilitada_por = request.user
        sesion.fecha_habilitacion = ahora
        sesion.fecha_desactivacion = None

        sesion.save()

        return Response(
            {
                "mensaje": (
                    "Reconocimiento facial "
                    "habilitado correctamente."
                ),
                **datos_sesion_facial(clase, sesion),
            },
            status=status.HTTP_200_OK
        )


class DeshabilitarAsistenciaFacialView(APIView):

    permission_classes = [
        permissions.IsAuthenticated,
        PermisoGestionAsistenciaFacial,
    ]

    @transaction.atomic
    def post(self, request, clase_id):

        clase = get_object_or_404(
            Clase.objects.select_for_update(),
            pk=clase_id
        )

        self.check_object_permissions(
            request,
            clase
        )

        sesion = (
            SesionAsistenciaFacial.objects
            .select_for_update()
            .filter(clase=clase)
            .first()
        )

        if sesion is None or not sesion.habilitada:
            return Response(
                {
                    "mensaje": (
                        "El reconocimiento facial "
                        "ya está deshabilitado."
                    ),
                    **datos_sesion_facial(clase, sesion),
                },
                status=status.HTTP_200_OK
            )

        sesion.habilitada = False
        sesion.fecha_desactivacion = timezone.now()

        sesion.save(
            update_fields=[
                "habilitada",
                "fecha_desactivacion",
                "fecha_actualizacion",
            ]
        )

        return Response(
            {
                "mensaje": (
                    "Reconocimiento facial "
                    "deshabilitado correctamente."
                ),
                **datos_sesion_facial(clase, sesion),
            },
            status=status.HTTP_200_OK
        )
