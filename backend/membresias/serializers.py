from rest_framework import serializers
from .models import Membresia, Reserva


class MembresiaSerializer(serializers.ModelSerializer):
    vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membresia
        fields = ['id', 'socio', 'pago', 'plan', 'estado', 'clases_totales', 'clases_restantes', 'fecha_solicitud', 'fecha_aprobacion', 'fecha_vencimiento', 'vigente']
        read_only_fields = fields


class ReservaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserva
        fields = ['id', 'socio', 'clase', 'membresia', 'pago', 'estado', 'fecha_creacion']
        read_only_fields = fields
