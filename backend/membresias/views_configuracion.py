
from django.db import transaction
from rest_framework import permissions, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PlanMembresia, ConfiguracionPrecio
from .serializers import (
    PlanMembresiaSerializer,
    ConfiguracionPrecioSerializer
)


class SoloDuena(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.rol == "DUENA"
        )


class PlanesConfigurablesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        planes = PlanMembresia.objects.all().order_by("id")

        datos = PlanMembresiaSerializer(
            planes,
            many=True
        ).data

        return Response(datos)

    def post(self, request):
        if request.user.rol != "DUENA":
            return Response(
                {"detail": "Solo la dueña puede crear membresías."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = PlanMembresiaSerializer(
            data=request.data
        )

        serializer.is_valid(raise_exception=True)
        plan = serializer.save()

        return Response(
            PlanMembresiaSerializer(plan).data,
            status=status.HTTP_201_CREATED
        )


class PlanConfigurableDetalleView(APIView):
    permission_classes = [SoloDuena]

    def patch(self, request, pk):
        with transaction.atomic():
            try:
                plan = (
                    PlanMembresia.objects
                    .select_for_update()
                    .get(pk=pk)
                )
            except PlanMembresia.DoesNotExist:
                raise NotFound("Membresía no encontrada.")

            serializer = PlanMembresiaSerializer(
                plan,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)
            plan = serializer.save()

        return Response(
            PlanMembresiaSerializer(plan).data
        )


class PrecioParticularView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        configuracion, _ = (
            ConfiguracionPrecio.objects.get_or_create(
                clave="CLASE_PARTICULAR",
                defaults={"precio_clp": 3500}
            )
        )

        return Response(
            ConfiguracionPrecioSerializer(configuracion).data
        )

    def patch(self, request):
        if request.user.rol != "DUENA":
            return Response(
                {"detail": "Solo la dueña puede modificar el precio."},
                status=status.HTTP_403_FORBIDDEN
            )

        with transaction.atomic():
            configuracion, _ = (
                ConfiguracionPrecio.objects.get_or_create(
                    clave="CLASE_PARTICULAR",
                    defaults={"precio_clp": 3500}
                )
            )

            configuracion = (
                ConfiguracionPrecio.objects
                .select_for_update()
                .get(pk=configuracion.pk)
            )

            serializer = ConfiguracionPrecioSerializer(
                configuracion,
                data=request.data,
                partial=True
            )

            serializer.is_valid(raise_exception=True)
            configuracion = serializer.save()

        return Response(
            ConfiguracionPrecioSerializer(configuracion).data
        )
