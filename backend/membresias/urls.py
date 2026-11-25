
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

from .views_configuracion import (
    PlanesConfigurablesView,
    PlanConfigurableDetalleView,
    PrecioParticularView,
)

from .views_qr import (
    SesionQRClaseView,
    DeshabilitarQRClaseView,
    EscanearQRAsistenciaView,
    CambioExcepcionalAsistenciaView,
)

from .views_asistencia_facial import (
    SesionAsistenciaFacialView,
    DeshabilitarAsistenciaFacialView,
)

from .views_disponibilidad_facial import (
    DisponibilidadAsistenciaFacialView,
)

from .views_verificacion_facial import (
    VerificacionAsistenciaFacialView,
)

from .views_desafio_facial import (
    CrearDesafioFacialView,
)

from .views_validacion_vida import (
    ValidarPruebaVidaView,
)

urlpatterns = [
    path(
        "planes/",
        PlanesView.as_view(),
        name="planes"
    ),
    path(
        "planes/configuracion/",
        PlanesConfigurablesView.as_view(),
        name="planes-configuracion"
    ),
    path(
        "planes/configuracion/<int:pk>/",
        PlanConfigurableDetalleView.as_view(),
        name="plan-configuracion-detalle"
    ),
    path(
        "precios/clase-particular/",
        PrecioParticularView.as_view(),
        name="precio-clase-particular"
    ),
    path(
        "",
        MembresiasView.as_view(),
        name="membresias"
    ),
    path(
        "comprar/",
        ComprarPlanView.as_view(),
        name="comprar-plan"
    ),
    path(
        "<int:pk>/resolver/",
        ResolverMembresiaView.as_view(),
        name="resolver-membresia"
    ),
    path(
        "reservas/",
        ReservasView.as_view(),
        name="reservas"
    ),
    path(
        "reservas/crear/",
        ReservarClaseView.as_view(),
        name="reservar-clase"
    ),
    path(
        "reservas/<int:pk>/resolver/",
        ResolverReservaParticularView.as_view(),
        name="resolver-reserva"
    ),
    path(
        "reservas/<int:pk>/asistencia/",
        RegistrarAsistenciaView.as_view(),
        name="registrar-asistencia"
    ),
    path(
        "clases/<int:clase_id>/qr/",
        SesionQRClaseView.as_view(),
        name="sesion-qr-clase"
    ),
    path(
        "clases/<int:clase_id>/qr/deshabilitar/",
        DeshabilitarQRClaseView.as_view(),
        name="deshabilitar-qr-clase"
    ),
    path(
        "qr/escanear/",
        EscanearQRAsistenciaView.as_view(),
        name="escanear-qr-asistencia"
    ),
    path(
        "reservas/<int:reserva_id>/cambio-excepcional/",
        CambioExcepcionalAsistenciaView.as_view(),
        name="cambio-excepcional-asistencia"
    ),
    path(
        "clases/<int:clase_id>/asistencia-facial/",
        SesionAsistenciaFacialView.as_view(),
        name="sesion-asistencia-facial"
    ),
    path(
        "clases/<int:clase_id>/asistencia-facial/deshabilitar/",
        DeshabilitarAsistenciaFacialView.as_view(),
        name="deshabilitar-asistencia-facial"
    ),
    path(
        "asistencia-facial/disponibilidad/",
        DisponibilidadAsistenciaFacialView.as_view(),
        name="disponibilidad-asistencia-facial"
    ),
    path(
        "asistencia-facial/verificar/",
        VerificacionAsistenciaFacialView.as_view(),
        name="verificacion-asistencia-facial"
    ),
    path(
        "asistencia-facial/desafio/",
        CrearDesafioFacialView.as_view(),
        name="crear-desafio-facial"
    ),
    path(
        "asistencia-facial/validar-vida/",
        ValidarPruebaVidaView.as_view(),
        name="validar-prueba-vida"
    ),
]
