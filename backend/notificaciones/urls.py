from django.urls import path
from .views import NotificacionesView, NotificacionDetalleView
urlpatterns = [path('', NotificacionesView.as_view()), path('<int:pk>/', NotificacionDetalleView.as_view())]
