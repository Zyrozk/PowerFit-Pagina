from django.contrib import admin
from .models import Membresia, Reserva

@admin.register(Membresia)
class MembresiaAdmin(admin.ModelAdmin):
    list_display = ('id', 'socio', 'plan', 'estado', 'clases_restantes', 'fecha_aprobacion', 'fecha_vencimiento')
    list_filter = ('plan', 'estado')

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('id', 'socio', 'clase', 'estado')
    list_filter = ('estado',)
