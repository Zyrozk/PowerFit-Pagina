from django.contrib import admin
from .models import Clase


@admin.register(Clase)
class ClaseAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'fecha', 'hora_inicio', 'hora_fin', 'coach', 'cupos', 'activa')
    list_filter = ('tipo', 'fecha', 'activa')
    search_fields = ('coach__username', 'coach__first_name', 'coach__last_name')
