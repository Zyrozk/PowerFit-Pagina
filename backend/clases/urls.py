from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ClaseViewSet,
    TipoClaseViewSet,
    HorarioClaseViewSet,
)

router = DefaultRouter()

router.register(
    "tipos",
    TipoClaseViewSet,
    basename="tipo-clase"
)

router.register(
    "horarios",
    HorarioClaseViewSet,
    basename="horario-clase"
)

router.register(
    "",
    ClaseViewSet,
    basename="clase"
)

urlpatterns = [
    path("", include(router.urls))
]