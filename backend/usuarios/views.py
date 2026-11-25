
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser


from .models import RegistroFacial, RegistroIMC, FichaSalud
from .permisos_faciales import EsDuenaParaEnrolamientoFacial
from .serializers import (
    UsuarioSerializer,
    RegistroSocioSerializer,
    RegistroFacialSerializer,
    GestionCoachSerializer,
    GestionSocioSerializer,
    MiPerfilSerializer,
    RegistroIMCSerializer,
    FichaSaludSerializer,
)
from .servicios_faciales import (
    eliminar_datos_faciales,
    generar_vector_facial,
    serializar_vector_facial,
    guardar_datos_faciales_cifrados,
)

from django.core.exceptions import ValidationError


Usuario = get_user_model()


class EsDuena(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.rol == "DUENA"
        )




class MiPerfilView(generics.RetrieveUpdateAPIView):
    serializer_class = MiPerfilSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]
    http_method_names = [
        "get",
        "patch",
        "head",
        "options",
    ]

    def get_object(self):
        return self.request.user

    def perform_update(self, serializer):
        usuario = self.get_object()

        foto_anterior = (
            usuario.foto_perfil.name
            if usuario.foto_perfil
            else None
        )

        foto_nueva = serializer.validated_data.get(
            "foto_perfil"
        )

        usuario_actualizado = serializer.save()

        if foto_nueva is not None and foto_anterior:
            nombre_nuevo = (
                usuario_actualizado.foto_perfil.name
                if usuario_actualizado.foto_perfil
                else None
            )

            if foto_anterior != nombre_nuevo:
                almacenamiento = (
                    usuario_actualizado.foto_perfil.storage
                )

                transaction.on_commit(
                    lambda: almacenamiento.delete(
                        foto_anterior
                    )
                )




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


class GestionCoachesView(generics.ListCreateAPIView):
    serializer_class = GestionCoachSerializer
    permission_classes = [permissions.IsAuthenticated, EsDuena]

    def get_queryset(self):
        return Usuario.objects.filter(
            rol=Usuario.Rol.COACH
        ).order_by("first_name", "last_name", "id")


class DetalleGestionCoachView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GestionCoachSerializer
    permission_classes = [permissions.IsAuthenticated, EsDuena]

    def get_queryset(self):
        return Usuario.objects.filter(
            rol=Usuario.Rol.COACH
        )


class GestionSociosView(generics.ListCreateAPIView):
    serializer_class = GestionSocioSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        EsDuena,
    ]

    def get_queryset(self):
        return Usuario.objects.filter(
            rol=Usuario.Rol.SOCIO
        ).order_by("first_name", "last_name", "id")


class DetalleGestionSocioView(
    generics.RetrieveUpdateAPIView
):
    serializer_class = GestionSocioSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        EsDuena,
    ]

    def get_queryset(self):
        return Usuario.objects.filter(
            rol=Usuario.Rol.SOCIO
        )


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

    parser_classes = [
        JSONParser,
        MultiPartParser,
        FormParser,
    ]

    def obtener_motivos(self, registro):
        motivos = []

        if registro is None:
            motivos.append(
                "El socio todavía no tiene un registro de consentimiento."
            )
            return motivos

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

        return motivos

    def get(self, request):
        socio_id = request.query_params.get("socio_id")

        if not socio_id:
            return Response(
                {
                    "mensaje": (
                        "Acceso autorizado para la dueña "
                        "de PowerFit Copiapó."
                    ),
                    "enrolamiento_disponible": True,
                    "detalle": (
                        "Selecciona un socio para consultar "
                        "las condiciones del enrolamiento facial."
                    ),
                },
                status=status.HTTP_200_OK
            )

        if not socio_id.isdecimal():
            return Response(
                {
                    "error": (
                        "El socio_id debe ser un número válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        socio = Usuario.objects.filter(
            pk=int(socio_id),
            rol="SOCIO",
            is_active=True,
        ).first()

        if socio is None:
            raise NotFound(
                "No se encontró un socio activo con ese ID."
            )

        registro = RegistroFacial.objects.filter(
            socio=socio
        ).first()

        motivos = self.obtener_motivos(registro)

        disponible = len(motivos) == 0

        return Response(
            {
                "socio_id": socio.id,
                "socio": (
                    socio.get_full_name()
                    or socio.username
                ),
                "tiene_registro": registro is not None,
                "consentimiento_valido": disponible,
                "cumple_condiciones_previas": disponible,
                "enrolamiento_disponible": disponible,
                "activo": (
                    registro.activo
                    if registro is not None
                    else False
                ),
                "motivos": motivos,
                "detalle": (
                    "El socio cumple las condiciones "
                    "para realizar el enrolamiento facial."
                    if disponible
                    else
                    "El socio no cumple las condiciones "
                    "para realizar el enrolamiento facial."
                ),
            },
            status=status.HTTP_200_OK
        )

    def post(self, request):
        socio_id = request.data.get("socio_id")
        imagen = request.FILES.get("imagen")

        if (
            socio_id is None
            or not str(socio_id).isdecimal()
        ):
            return Response(
                {
                    "error": (
                        "Debe proporcionar un socio_id válido."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        socio = Usuario.objects.filter(
            pk=int(socio_id),
            rol="SOCIO",
            is_active=True,
        ).first()

        if socio is None:
            raise NotFound(
                "No se encontró un socio activo con ese ID."
            )

        registro = RegistroFacial.objects.filter(
            socio=socio
        ).first()

        motivos = self.obtener_motivos(registro)

        if motivos:
            return Response(
                {
                    "error": (
                        "El socio no cumple las condiciones "
                        "para realizar el enrolamiento facial."
                    ),
                    "motivos": motivos,
                    "enrolamiento_disponible": False,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if imagen is None:
            return Response(
                {
                    "error": (
                        "Debe proporcionar una imagen facial."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            vector = generar_vector_facial(imagen)
            datos_biometricos = serializar_vector_facial(
                vector
            )

        except ValueError as error:
            return Response(
                {"error": str(error)},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                registro_actual = (
                    RegistroFacial.objects
                    .select_for_update()
                    .get(pk=registro.pk)
                )

                socio_actual = (
                    Usuario.objects
                    .select_for_update()
                    .filter(
                        pk=socio.pk,
                        rol="SOCIO",
                        is_active=True,
                    )
                    .first()
                )

                if socio_actual is None:
                    raise NotFound(
                        "El socio ya no se encuentra activo."
                    )

                motivos = self.obtener_motivos(
                    registro_actual
                )

                if motivos:
                    return Response(
                        {
                            "error": (
                                "Las condiciones del enrolamiento "
                                "facial han cambiado."
                            ),
                            "motivos": motivos,
                            "enrolamiento_disponible": False,
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                registro_actual = (
                    guardar_datos_faciales_cifrados(
                        registro_actual,
                        datos_biometricos
                    )
                )

                registro_actual.activo = True
                registro_actual.fecha_enrolamiento = (
                    timezone.now()
                )
                registro_actual.registrado_por = (
                    request.user
                )

                registro_actual.save(
                    update_fields=[
                        "activo",
                        "fecha_enrolamiento",
                        "registrado_por",
                        "fecha_actualizacion",
                    ]
                )

                socio_actual.reconocimiento_facial_habilitado = True

                socio_actual.save(
                    update_fields=[
                        "reconocimiento_facial_habilitado"
                    ]
                )

        except RegistroFacial.DoesNotExist:
            return Response(
                {
                    "error": (
                        "El registro de consentimiento "
                        "ya no se encuentra disponible."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except ValueError:
            return Response(
                {
                    "error": (
                        "No se pudo almacenar el registro facial. "
                        "Verifica la configuración del servidor."
                    )
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {
                "mensaje": (
                    "Enrolamiento facial realizado correctamente."
                ),
                "socio_id": socio_actual.id,
                "socio": (
                    socio_actual.get_full_name()
                    or socio_actual.username
                ),
                "activo": True,
                "reconocimiento_facial_habilitado": True,
                "fecha_enrolamiento": (
                    registro_actual.fecha_enrolamiento
                ),
                "enrolamiento_disponible": False,
            },
            status=status.HTTP_201_CREATED
        )


class CambiarContrasenaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        usuario = request.user

        actual = request.data.get("contrasena_actual", "")
        nueva = request.data.get("contrasena_nueva", "")
        confirmacion = request.data.get("confirmacion", "")

        if not usuario.check_password(actual):
            return Response(
                {
                    "detail": "La contraseña actual es incorrecta."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if not nueva or not confirmacion:
            return Response(
                {
                    "detail": "Debes completar todos los campos."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if nueva != confirmacion:
            return Response(
                {
                    "detail": "Las contraseñas nuevas no coinciden."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_password(nueva, user=usuario)

        except ValidationError as error:
            return Response(
                {
                    "detail": error.messages
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        usuario.set_password(nueva)
        usuario.save(update_fields=["password"])

        return Response(
            {
                "detail": "Contraseña actualizada correctamente."
            },
            status=status.HTTP_200_OK
        )


class RegistroIMCView(generics.ListCreateAPIView):
    serializer_class = RegistroIMCSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        usuario = self.request.user

        if usuario.rol != "SOCIO":
            return RegistroIMC.objects.none()

        return RegistroIMC.objects.filter(
            socio=usuario
        )

    def perform_create(self, serializer):
        if self.request.user.rol != "SOCIO":
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied(
                "Solo los socios pueden registrar mediciones de IMC."
            )

        serializer.save(socio=self.request.user)


class MiFichaSaludView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.rol != "SOCIO":
            return Response(
                {"detail": "Solo los socios pueden consultar su ficha de salud."},
                status=status.HTTP_403_FORBIDDEN
            )

        ficha = FichaSalud.objects.filter(
            socio=request.user
        ).first()

        if ficha is None:
            return Response(
                {"tiene_ficha": False},
                status=status.HTTP_200_OK
            )

        datos = FichaSaludSerializer(ficha).data

        return Response(
            {"tiene_ficha": True, **datos},
            status=status.HTTP_200_OK
        )

    def put(self, request):
        if request.user.rol != "SOCIO":
            return Response(
                {"detail": "Solo los socios pueden modificar su ficha de salud."},
                status=status.HTTP_403_FORBIDDEN
            )

        ficha = FichaSalud.objects.filter(
            socio=request.user
        ).first()

        serializer = FichaSaludSerializer(
            ficha,
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        serializer.save(socio=request.user)

        return Response(
            {"tiene_ficha": True, **serializer.data},
            status=status.HTTP_200_OK
        )


class FichaSaludSocioDuenaView(APIView):
    permission_classes = [
        permissions.IsAuthenticated,
        EsDuena,
    ]

    def get(self, request, socio_id):
        socio = Usuario.objects.filter(
            id=socio_id,
            rol=Usuario.Rol.SOCIO
        ).first()

        if socio is None:
            raise NotFound("No se encontró el socio.")

        ficha = FichaSalud.objects.filter(
            socio=socio
        ).first()

        if ficha is None:
            return Response(
                {
                    "socio_id": socio.id,
                    "tiene_ficha": False
                },
                status=status.HTTP_200_OK
            )

        datos = FichaSaludSerializer(ficha).data

        return Response(
            {
                "socio_id": socio.id,
                "tiene_ficha": True,
                **datos
            },
            status=status.HTTP_200_OK
        )

