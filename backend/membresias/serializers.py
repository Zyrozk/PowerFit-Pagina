
from rest_framework import serializers
from .models import Membresia, Reserva


class MembresiaSerializer(serializers.ModelSerializer):
    vigente = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membresia
        fields = [
            'id',
            'socio',
            'pago',
            'plan',
            'estado',
            'clases_totales',
            'clases_restantes',
            'fecha_solicitud',
            'fecha_aprobacion',
            'fecha_vencimiento',
            'vigente'
        ]
        read_only_fields = fields


class ReservaSerializer(serializers.ModelSerializer):
    nombre_socio = serializers.SerializerMethodField()

    nombre_clase = serializers.CharField(
        source='clase.get_tipo_display',
        read_only=True
    )

    fecha_clase = serializers.DateField(
        source='clase.fecha',
        read_only=True
    )

    hora_inicio = serializers.TimeField(
        source='clase.hora_inicio',
        format='%H:%M',
        read_only=True
    )

    hora_fin = serializers.TimeField(
        source='clase.hora_fin',
        format='%H:%M',
        read_only=True
    )

    coach_id = serializers.IntegerField(
        source='clase.coach_id',
        read_only=True
    )

    coach_nombre = serializers.SerializerMethodField()

    clases_restantes = serializers.IntegerField(
        source='membresia.clases_restantes',
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Reserva
        fields = [
            'id',
            'socio',
            'nombre_socio',
            'clase',
            'membresia',
            'pago',
            'estado',
            'fecha_creacion',
            'asistencia',
            'fecha_registro_asistencia',
            'registrado_por',
            'clase_devuelta',
            'nombre_clase',
            'fecha_clase',
            'hora_inicio',
            'hora_fin',
            'coach_id',
            'coach_nombre',
            'clases_restantes'
        ]
        read_only_fields = fields

    def get_nombre_socio(self, obj):
        socio = obj.socio
        nombre = socio.get_full_name().strip()

        if nombre:
            return nombre

        return socio.username

    def get_coach_nombre(self, obj):
        coach = obj.clase.coach
        nombre = coach.get_full_name().strip()

        if nombre:
            return nombre

        return coach.username
