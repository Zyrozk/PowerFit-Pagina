from django.urls import path

from .views import (
    MiPerfilView,
    RegistroSocioView,
    BuscarSociosView,
    EstadoRegistroFacialView,
    ConsentimientoFacialView,
    EnrolamientoFacialView,
    BuscarCoachesView,
)

urlpatterns = [
    path(
        "mi-perfil/",
        MiPerfilView.as_view(),
        name="mi-perfil",
    ),
    path(
        "registro/",
        RegistroSocioView.as_view(),
        name="registro-socio",
    ),
    path(
        "socios/",
        BuscarSociosView.as_view(),
        name="buscar-socios",
    ),
    path(
        "socios/<int:socio_id>/registro-facial/",
        EstadoRegistroFacialView.as_view(),
        name="estado-registro-facial",
    ),
    path(
        "consentimiento-facial/",
        ConsentimientoFacialView.as_view(),
        name="consentimiento-facial",
    ),
    path(
        "enrolamiento-facial/",
        EnrolamientoFacialView.as_view(),
        name="enrolamiento-facial"
    ),
    path(
        "coaches/",
        BuscarCoachesView.as_view(),
        name="buscar-coaches",
    ),
]