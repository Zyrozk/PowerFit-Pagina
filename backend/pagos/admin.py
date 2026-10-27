from django.contrib import admin
from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "socio",
        "tipo_pago",
        "metodo_pago",
        "monto",
        "estado",
        "fecha_pago",
    )

    list_filter = (
        "tipo_pago",
        "metodo_pago",
        "estado",
        "fecha_pago",
    )

    search_fields = (
        "socio__username",
        "socio__first_name",
        "socio__last_name",
    )

    readonly_fields = (
        "fecha_pago",
    )

    ordering = (
        "-fecha_pago",
    )