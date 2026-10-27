from django.urls import path
from .views import PlanesView, MembresiasView, ComprarPlanView, ResolverMembresiaView, ReservasView, ReservarClaseView, ResolverReservaParticularView

urlpatterns = [
    path('planes/', PlanesView.as_view(), name='planes'),
    path('', MembresiasView.as_view(), name='membresias'),
    path('comprar/', ComprarPlanView.as_view(), name='comprar-plan'),
    path('<int:pk>/resolver/', ResolverMembresiaView.as_view(), name='resolver-membresia'),
    path('reservas/', ReservasView.as_view(), name='reservas'),
    path('reservas/crear/', ReservarClaseView.as_view(), name='reservar-clase'),
    path('reservas/<int:pk>/resolver/', ResolverReservaParticularView.as_view(), name='resolver-reserva'),
]
