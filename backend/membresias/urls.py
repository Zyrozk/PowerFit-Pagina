
from django.urls import path

from .views import (
    PlanesView,
    MembresiasView,
    ComprarPlanView,
    ResolverMembresiaView,
    ReservasView,
    ReservarClaseView,
    ResolverReservaParticularView,
    RegistrarAsistenciaView,
)

from .views_qr import (
    SesionQRClaseView,
    DeshabilitarQRClaseView,
    EscanearQRAsistenciaView,
    CambioExcepcionalAsistenciaView,
)

urlpatterns = [
    path(
        'planes/',
        PlanesView.as_view(),
        name='planes'
    ),
    path(
        '',
        MembresiasView.as_view(),
        name='membresias'
    ),
    path(
        'comprar/',
        ComprarPlanView.as_view(),
        name='comprar-plan'
    ),
    path(
        '<int:pk>/resolver/',
        ResolverMembresiaView.as_view(),
        name='resolver-membresia'
    ),
    path(
        'reservas/',
        ReservasView.as_view(),
        name='reservas'
    ),
    path(
        'reservas/crear/',
        ReservarClaseView.as_view(),
        name='reservar-clase'
    ),
    path(
        'reservas/<int:pk>/resolver/',
        ResolverReservaParticularView.as_view(),
        name='resolver-reserva'
    ),
    path(
        'reservas/<int:pk>/asistencia/',
        RegistrarAsistenciaView.as_view(),
        name='registrar-asistencia'
    ),
    path(
        'clases/<int:clase_id>/qr/',
        SesionQRClaseView.as_view(),
        name='sesion-qr-clase'
    ),
    path(
        'clases/<int:clase_id>/qr/deshabilitar/',
        DeshabilitarQRClaseView.as_view(),
        name='deshabilitar-qr-clase'
    ),
    path(
        'qr/escanear/',
        EscanearQRAsistenciaView.as_view(),
        name='escanear-qr-asistencia'
    ),
    path(
        'reservas/<int:reserva_id>/cambio-excepcional/',
        CambioExcepcionalAsistenciaView.as_view(),
        name='cambio-excepcional-asistencia'
    ),
]
