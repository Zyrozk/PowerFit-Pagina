from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = (
        "username",
        "first_name",
        "last_name",
        "email",
        "rol",
        "reconocimiento_facial_habilitado",
        "is_active",
    )

    list_filter = (
        "rol",
        "reconocimiento_facial_habilitado",
        "is_active",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "Información de PowerFit Copiapó",
            {
                "fields": (
                    "rol",
                    "reconocimiento_facial_habilitado",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Información de PowerFit Copiapó",
            {
                "fields": (
                    "rol",
                    "reconocimiento_facial_habilitado",
                )
            },
        ),
    )