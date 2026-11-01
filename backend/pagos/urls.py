
from django.urls import path
from .views import (
    HistorialPagosView,
    ExportarPagosExcelView,
    PagosDuenaView,
    DocumentoPagoDuenaView,
    BoletaPagoSocioView,
)

urlpatterns = [
    path(
        "historial/",
        HistorialPagosView.as_view(),
        name="historial-pagos"
    ),
    path(
        "exportar-excel/",
        ExportarPagosExcelView.as_view(),
        name="exportar-pagos-excel"
    ),
    path(
        "duena/",
        PagosDuenaView.as_view(),
        name="pagos-duena"
    ),
    path(
        "duena/<int:pago_id>/documento/",
        DocumentoPagoDuenaView.as_view(),
        name="documento-pago-duena"
    ),
    path(
        "socio/<int:pago_id>/boleta/",
        BoletaPagoSocioView.as_view(),
        name="boleta-pago-socio"
    ),

]
