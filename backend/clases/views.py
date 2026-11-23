
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import permissions, viewsets

from .models import (
    Clase,
    TipoClase,
    HorarioClase,
    HistorialEspecialidadCoach
)
from .serializers import (
    ClaseSerializer,
    TipoClaseSerializer,
    HorarioClaseSerializer
)
from notificaciones.services import notificar_coach


class SoloDuenaPuedeModificar(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        return (
            request.method in permissions.SAFE_METHODS
            or request.user.rol == "DUENA"
        )


class ClaseViewSet(viewsets.ModelViewSet):
    serializer_class = ClaseSerializer
    permission_classes = [SoloDuenaPuedeModificar]

    def perform_create(self, serializer):
        clase = serializer.save()

        nombre_clase = clase.get_tipo_display()
        fecha = clase.fecha.strftime("%d/%m/%Y")
        inicio = clase.hora_inicio.strftime("%H:%M")
        fin = clase.hora_fin.strftime("%H:%M")

        notificar_coach(
            coach=clase.coach,
            tipo="CLASE_ASIGNADA",
            titulo="Nueva clase asignada",
            descripcion=(
                f"Se te asignó la clase {nombre_clase} "
                f"para el {fecha}, de {inicio} a {fin}."
            ),
            clave_evento=f"clase_asignada:{clase.pk}"
        )

    def get_queryset(self):
        qs = Clase.objects.select_related("coach").annotate(
            cupos_ocupados=Count(
                "reservas",
                filter=Q(
                    reservas__estado__in=[
                        "CONFIRMADA",
                        "PENDIENTE"
                    ]
                )
            )
        )

        if self.request.user.rol != "DUENA":
            qs = qs.filter(activa=True)

        fecha = self.request.query_params.get("fecha")

        if fecha:
            qs = qs.filter(fecha=fecha)

        return qs


class SoloDuenaAdministraCatalogos(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.method in permissions.SAFE_METHODS:
            return request.user.rol in ["DUENA", "COACH"]

        return request.user.rol == "DUENA"


class TipoClaseViewSet(viewsets.ModelViewSet):
    queryset = TipoClase.objects.all()
    serializer_class = TipoClaseSerializer
    permission_classes = [SoloDuenaAdministraCatalogos]
    http_method_names = [
        "get", "post", "put", "patch", "head", "options"
    ]

    @transaction.atomic
    def perform_update(self, serializer):
        tipo = TipoClase.objects.select_for_update().get(
            pk=serializer.instance.pk
        )
        estaba_activa = tipo.activa
        tipo = serializer.save()

        if estaba_activa and not tipo.activa:
            Usuario = get_user_model()

            coaches = Usuario.objects.select_for_update().filter(
                rol="COACH"
            )

            for coach in coaches:
                especialidades = coach.especialidades or []

                if tipo.codigo not in especialidades:
                    continue

                HistorialEspecialidadCoach.objects.create(
                    coach=coach,
                    tipo_clase=tipo,
                    codigo=tipo.codigo,
                    nombre=tipo.nombre,
                    desactivada_por=self.request.user
                )

                coach.especialidades = [
                    codigo
                    for codigo in especialidades
                    if codigo != tipo.codigo
                ]

                coach.save(
                    update_fields=["especialidades"]
                )

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.rol != "DUENA":
            queryset = queryset.filter(activa=True)

        return queryset


class HorarioClaseViewSet(viewsets.ModelViewSet):
    queryset = HorarioClase.objects.all()
    serializer_class = HorarioClaseSerializer
    permission_classes = [SoloDuenaAdministraCatalogos]
    http_method_names = [
        "get", "post", "put", "patch", "head", "options"
    ]

    def get_queryset(self):
        queryset = super().get_queryset()

        if self.request.user.rol != "DUENA":
            queryset = queryset.filter(activo=True)

        return queryset
