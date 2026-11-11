from django.urls import path
from .views import EstadisticasDuenaView

urlpatterns = [
    path(
        "duena/",
        EstadisticasDuenaView.as_view(),
        name="estadisticas-duena"
    ),
]