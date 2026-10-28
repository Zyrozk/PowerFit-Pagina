
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import RegistroFacial
from .permisos_faciales import EsDuenaParaEnrolamientoFacial
from .serializers import (
    UsuarioSerializer,
    RegistroSocioSerializer,
    RegistroFacialSerializer,
)
from .servicios_faciales import eliminar_datos_faciales


Usuario = get_user_model()


class EsDuena(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.rol == "DUENA"
        )


class MiPerfilView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class RegistroSocioView(generics.CreateAPIView):
    serializer_class = RegistroSocioSerializer
    permission_classes = [permissions.AllowAny]


class BuscarSociosView(generics.ListAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        EsDuena,
    ]

    def get_queryset(self):
        queryset = Usuario.objects.filter(
            rol="SOCIO"
        ).order_by("first_name", "last_name")

        busqueda = self.request.query_params.get(
            "buscar", ""
        ).strip()

        if busqueda:
            queryset = queryset.filter(
                Q(first_name__icontains=busqueda)
                | Q(last_name__icontains=busqueda)
                | Q(username__icontains=busqueda)
            )

        return queryset


class BuscarCoachesView(generics.ListAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        EsDuena,
    ]

    def get_queryset(self):
        return Usuario.objects.filter(
            rol="COACH",
            is_active=True
        ).order_by("first_name", "last_name", "id")



class EstadoRegistroFacialView(generics.GenericAPIView):
    permission_classes = [
        permissions.IsAuthenticated,
        EsDuena,
    ]

    def get(self, request, socio_id):
        socio = Usuario.objects.filter(
            id=socio_id,
            rol="SOCIO"
        ).first()

        if socio is None:
            raise NotFound("No se encontró el socio.")

        registro = RegistroFacial.objects.filter(
            socio=socio
        ).first()

        if registro is None:
            return Response({
                "socio_id": socio.id,
                "tiene_registro": False,
                "activo": False,
                "consentimiento_otorgado": False,
                "fecha_consentimiento": None,
            })

        datos = RegistroFacialSerializer(registro).data

        return Response({
            "socio_id": socio.id,
            "tiene_registro": True,
            **datos,
        })


class ConsentimientoFacialView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    VERSION_CONSENTIMIENTO = "1.0"

    def get(self, request):
        socio = request.user

        if socio.rol != "SOCIO":
            return Response(
                {
                    "error": (
                        "Solo los socios pueden consultar "
                        "su consentimiento facial."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        registro = RegistroFacial.objects.filter(
            socio=socio
        ).first()

        if registro is None:
            return Response(
                {
                    "consentimiento_otorgado": False,
                    "consentimiento_confirmado_por_socio": False,
                    "activo": False,
                    "tiene_registro": False,
                },
                status=status.HTTP_200_OK
            )

        return Response(
            {
                "consentimiento_otorgado": registro.consentimiento_otorgado,
                "consentimiento_confirmado_por_socio": (
                    registro.consentimiento_confirmado_por_socio
                ),
                "activo": registro.activo,
                "tiene_registro": True,
                "fecha_confirmacion_socio": registro.fecha_confirmacion_socio,
                "fecha_revocacion": registro.fecha_revocacion,
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        socio = request.user

        if socio.rol != "SOCIO":
            return Response(
                {
                    "error": (
                        "Solo los socios pueden gestionar "
                        "su consentimiento facial."
                    )
                },
                status=status.HTTP_403_FORBIDDEN
            )

        aceptar = request.data.get("aceptar")

        if type(aceptar) is not bool:
            return Response(
                {
                    "error": "El campo aceptar debe ser true o false."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            registro, creado = (
                RegistroFacial.objects.select_for_update().get_or_create(
                    socio=socio
                )
            )

            if aceptar:
                if not registro.consentimiento_otorgado:
                    registro.activo = False
                    registro.datos_biometricos_cifrados = None
                    registro.fecha_enrolamiento = None
                    registro.registrado_por = None

                    socio.reconocimiento_facial_habilitado = False
                    socio.save(
                        update_fields=["reconocimiento_facial_habilitado"]
                    )

                registro.consentimiento_otorgado = True
                registro.consentimiento_confirmado_por_socio = True
                registro.fecha_consentimiento = timezone.now()
                registro.fecha_confirmacion_socio = timezone.now()
                registro.fecha_revocacion = None
                registro.version_consentimiento = self.VERSION_CONSENTIMIENTO

                mensaje = "Consentimiento facial registrado correctamente."

                registro.save()

            else:
                eliminar_datos_faciales(registro)

                mensaje = (
                    "Consentimiento facial revocado correctamente. "
                    "Los datos biométricos del registro activo "
                    "han sido eliminados."
                )

        return Response(
            {
                "mensaje": mensaje,
                "socio_id": socio.id,
                "consentimiento_otorgado": registro.consentimiento_otorgado,
                "consentimiento_confirmado_por_socio": (
                    registro.consentimiento_confirmado_por_socio
                ),
                "activo": registro.activo,
                "fecha_confirmacion_socio": registro.fecha_confirmacion_socio,
                "fecha_revocacion": registro.fecha_revocacion,
            },
            status=status.HTTP_200_OK
        )


class EnrolamientoFacialView(APIView):
    permission_classes = [EsDuenaParaEnrolamientoFacial]

    def get(self, request):
        socio_id = request.query_params.get("socio_id")

        if not socio_id:
            return Response(
                {
                    "mensaje": (
                        "Acceso autorizado para la dueña "
                        "de PowerFit Copiapó."
                    ),
                    "enrolamiento_disponible": False,
                    "detalle": (
                        "El enrolamiento facial todavía no está habilitado. "
                        "Puedes consultar el estado de un socio "
                        "enviando el parámetro socio_id."
                    ),
                },
                status=status.HTTP_200_OK
            )

        if not socio_id.isdecimal():
            return Response(
                {"error": "El socio_id debe ser un número válido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        socio = Usuario.objects.filter(
            pk=int(socio_id),
            rol="SOCIO",
            is_active=True,
        ).first()

        if socio is None:
            raise NotFound("No se encontró un socio activo con ese ID.")

        registro = RegistroFacial.objects.filter(
            socio=socio
        ).first()

        motivos = []

        if registro is None:
            motivos.append(
                "El socio todavía no tiene un registro de consentimiento."
            )
        else:
            if not registro.consentimiento_otorgado:
                motivos.append(
                    "El socio no ha autorizado el reconocimiento facial."
                )

            if not registro.consentimiento_confirmado_por_socio:
                motivos.append(
                    "El socio no ha confirmado su consentimiento."
                )

            if not registro.version_consentimiento:
                motivos.append(
                    "No existe una versión de consentimiento registrada."
                )

            if registro.fecha_confirmacion_socio is None:
                motivos.append(
                    "No existe una fecha de confirmación del consentimiento."
                )

            if registro.fecha_revocacion is not None:
                if (
                    registro.fecha_confirmacion_socio is None
                    or registro.fecha_confirmacion_socio
                    <= registro.fecha_revocacion
                ):
                    motivos.append(
                        "El consentimiento fue revocado."
                    )

            if registro.datos_biometricos_cifrados is not None:
                motivos.append(
                    "El socio ya tiene datos biométricos almacenados."
                )

            if registro.activo:
                motivos.append(
                    "El reconocimiento facial del socio ya está activo."
                )

        return Response(
            {
                "socio_id": socio.id,
                "socio": socio.get_full_name() or socio.username,
                "tiene_registro": registro is not None,
                "consentimiento_valido": len(motivos) == 0,
                "cumple_condiciones_previas": len(motivos) == 0,
                "enrolamiento_disponible": False,
                "motivos": motivos,
                "detalle": (
                    "Esta consulta solo verifica condiciones previas. "
                    "La captura y el almacenamiento biométrico "
                    "todavía no están habilitados."
                ),
            },
            status=status.HTTP_200_OK
        )
