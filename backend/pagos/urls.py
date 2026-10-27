from django.urls import path
from .views import HistorialPagosView, ExportarPagosExcelView

urlpatterns = [
    path("historial/", HistorialPagosView.as_view(), name="historial-pagos"),
    path("exportar-excel/", ExportarPagosExcelView.as_view(), name="exportar-pagos-excel"),
]