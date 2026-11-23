
from rest_framework import serializers

from .models import (
    Membresia,
    Reserva,
    PlanMembresia,
    ConfiguracionPrecio
)


class PlanMembresiaSerializer(serializers.ModelSerializer):

    class Meta:
        model = PlanMembresia

        fields = [
            "id",
            "codigo",
            "nombre",
            "precio_clp",
            "clases",
            "fecha_creacion",
            "fecha_actualizacion"
        ]

        read_only_fields = [
            "id",
            "codigo",
            "fecha_creacion",
            "fecha_actualizacion"
        ]

    def validate_nombre(self, value):
        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError(
                "Debes ingresar el nombre de la membresía."
            )

        if len(nombre) > 100:
            raise serializers.ValidationError(
                "El nombre no puede superar los 100 caracteres."
            )

        return nombre

    def validate_precio_clp(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El precio debe ser mayor a $0."
            )

        return value

    def validate_clases(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La membresía debe incluir al menos una clase."
            )

        return value

    def validate(self, attrs):
        nombre = attrs.get(
            "nombre",
            getattr(self.instance, "nombre", None)
        )

        if nombre:
            planes = PlanMembresia.objects.filter(
                nombre__iexact=nombre
            )

            if self.instance:
                planes = planes.exclude(
                    pk=self.instance.pk
                )

            if planes.exists():
                raise serializers.ValidationError({
                    "nombre": (
                        "Ya existe una membresía con ese nombre."
                    )
                })

        return attrs


class ConfiguracionPrecioSerializer(serializers.ModelSerializer):

    class Meta:
        model = ConfiguracionPrecio

        fields = [
            "id",
            "clave",
            "precio_clp",
            "fecha_actualizacion"
        ]

        read_only_fields = [
            "id",
            "clave",
            "fecha_actualizacion"
        ]

    def validate_precio_clp(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "El precio debe ser mayor a $0."
            )

        return value


class MembresiaSerializer(serializers.ModelSerializer):

    vigente = serializers.BooleanField(
        read_only=True
    )

    nombre_socio = serializers.SerializerMethodField()

    nombre_plan = serializers.CharField(
        source="nombre_plan_mostrado",
        read_only=True
    )

    class Meta:
        model = Membresia

        fields = [
            "id",
            "socio",
            "nombre_socio",
            "pago",
            "plan",
            "nombre_plan",
            "estado",
            "clases_totales",
            "clases_restantes",
            "fecha_solicitud",
            "fecha_aprobacion",
            "fecha_vencimiento",
            "vigente"
        ]

        read_only_fields = fields

    def get_nombre_socio(self, obj):
        socio = obj.socio

        nombre = socio.get_full_name().strip()

        if nombre:
            return nombre

        return socio.username


class ReservaSerializer(serializers.ModelSerializer):

    nombre_socio = serializers.SerializerMethodField()

    nombre_clase = serializers.CharField(
        source="clase.get_tipo_display",
        read_only=True
    )

    fecha_clase = serializers.DateField(
        source="clase.fecha",
        read_only=True
    )

    hora_inicio = serializers.TimeField(
        source="clase.hora_inicio",
        format="%H:%M",
        read_only=True
    )

    hora_fin = serializers.TimeField(
        source="clase.hora_fin",
        format="%H:%M",
        read_only=True
    )

    coach_id = serializers.IntegerField(
        source="clase.coach_id",
        read_only=True
    )

    coach_nombre = serializers.SerializerMethodField()

    clases_restantes = serializers.IntegerField(
        source="membresia.clases_restantes",
        read_only=True,
        allow_null=True
    )

    class Meta:
        model = Reserva

        fields = [
            "id",
            "socio",
            "nombre_socio",
            "clase",
            "membresia",
            "pago",
            "estado",
            "fecha_creacion",
            "asistencia",
            "fecha_registro_asistencia",
            "registrado_por",
            "clase_devuelta",
            "nombre_clase",
            "fecha_clase",
            "hora_inicio",
            "hora_fin",
            "coach_id",
            "coach_nombre",
            "clases_restantes"
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
