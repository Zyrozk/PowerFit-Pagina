
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Clase, TipoClase, HorarioClase


class ClaseSerializer(serializers.ModelSerializer):
    tipo = serializers.CharField(max_length=50)
    coach_nombre = serializers.SerializerMethodField()
    cupos_ocupados = serializers.IntegerField(read_only=True)
    cupos_disponibles = serializers.SerializerMethodField()
    tipo_nombre = serializers.CharField(
        source="get_tipo_display",
        read_only=True
    )

    class Meta:
        model = Clase
        fields = [
            "id",
            "tipo",
            "tipo_nombre",
            "fecha",
            "hora_inicio",
            "hora_fin",
            "coach",
            "coach_nombre",
            "cupos",
            "cupos_ocupados",
            "cupos_disponibles",
            "descripcion",
            "activa"
        ]
        read_only_fields = [
            "id",
            "coach_nombre",
            "tipo_nombre",
            "cupos_ocupados",
            "cupos_disponibles"
        ]

    def get_cupos_disponibles(self, obj):
        ocupados = getattr(obj, "cupos_ocupados", None)

        if ocupados is None:
            ocupados = obj.reservas.filter(
                estado__in=["CONFIRMADA", "PENDIENTE"]
            ).count()

        return max(0, obj.cupos - ocupados)

    def get_coach_nombre(self, obj):
        return obj.coach.get_full_name() or obj.coach.username

    def validate_tipo(self, value):
        tipo = TipoClase.objects.filter(
            codigo=value
        ).first()

        if not tipo:
            raise serializers.ValidationError(
                "El tipo de clase seleccionado no existe."
            )

        if not tipo.activa:
            if not self.instance or self.instance.tipo != value:
                raise serializers.ValidationError(
                    "Este tipo de clase está desactivado."
                )

        return value

    def validate(self, attrs):
        instancia = self.instance

        tipo_codigo = attrs.get(
            "tipo",
            getattr(instancia, "tipo", None)
        )

        fecha = attrs.get(
            "fecha",
            getattr(instancia, "fecha", None)
        )

        inicio = attrs.get(
            "hora_inicio",
            getattr(instancia, "hora_inicio", None)
        )

        fin = attrs.get(
            "hora_fin",
            getattr(instancia, "hora_fin", None)
        )

        coach = attrs.get(
            "coach",
            getattr(instancia, "coach", None)
        )

        activa = attrs.get(
            "activa",
            getattr(instancia, "activa", True)
        )

        if inicio and fin and fin <= inicio:
            raise serializers.ValidationError({
                "hora_fin": "La hora de término debe ser posterior al inicio."
            })

        if coach and coach.rol != "COACH":
            raise serializers.ValidationError({
                "coach": "Debe seleccionar un usuario COACH."
            })

        tipo = TipoClase.objects.filter(
            codigo=tipo_codigo
        ).first()

        if not tipo:
            raise serializers.ValidationError({
                "tipo": "El tipo de clase seleccionado no existe."
            })

        cambio_tipo = (
            instancia is None
            or instancia.tipo != tipo_codigo
        )

        if cambio_tipo and not tipo.activa:
            raise serializers.ValidationError({
                "tipo": "Este tipo de clase está desactivado."
            })

        cambio_horario = (
            instancia is None
            or instancia.hora_inicio != inicio
            or instancia.hora_fin != fin
        )

        reactivacion = (
            instancia is not None
            and not instancia.activa
            and activa
        )

        if inicio and fin and (cambio_horario or reactivacion):
            horario = HorarioClase.objects.filter(
                hora_inicio=inicio,
                hora_fin=fin
            ).first()

            if not horario:
                raise serializers.ValidationError({
                    "hora_inicio": "El horario seleccionado no está registrado."
                })

            if not horario.activo:
                raise serializers.ValidationError({
                    "hora_inicio": "Este horario está desactivado."
                })

        if fecha and inicio and fin and activa:
            superpuestas = Clase.objects.filter(
                fecha=fecha,
                activa=True,
                hora_inicio__lt=fin,
                hora_fin__gt=inicio
            )

            if instancia:
                superpuestas = superpuestas.exclude(pk=instancia.pk)

            if superpuestas.exists():
                raise serializers.ValidationError({
                    "hora_inicio": "Ya existe una clase programada en este horario."
                })

        if instancia is None and "cupos" not in attrs:
            attrs["cupos"] = tipo.cupos_predeterminados

        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                error.message_dict if hasattr(error, "message_dict")
                else error.messages
            )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                error.message_dict if hasattr(error, "message_dict")
                else error.messages
            )


class TipoClaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoClase
        fields = [
            "id",
            "codigo",
            "nombre",
            "cupos_predeterminados",
            "activa"
        ]
        read_only_fields = [
            "id",
            "codigo"
        ]

    def validate_nombre(self, value):
        nombre = value.strip()

        if not nombre:
            raise serializers.ValidationError(
                "El nombre de la clase es obligatorio."
            )

        duplicado = TipoClase.objects.filter(
            nombre__iexact=nombre
        )

        if self.instance:
            duplicado = duplicado.exclude(pk=self.instance.pk)

        if duplicado.exists():
            raise serializers.ValidationError(
                "Ya existe un tipo de clase con ese nombre."
            )

        return nombre

    def validate_cupos_predeterminados(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Debe haber al menos un cupo."
            )

        return value

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                error.message_dict if hasattr(error, "message_dict")
                else error.messages
            )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                error.message_dict if hasattr(error, "message_dict")
                else error.messages
            )


class HorarioClaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = HorarioClase
        fields = [
            "id",
            "hora_inicio",
            "hora_fin",
            "activo"
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        inicio = attrs.get(
            "hora_inicio",
            getattr(self.instance, "hora_inicio", None)
        )

        fin = attrs.get(
            "hora_fin",
            getattr(self.instance, "hora_fin", None)
        )

        if inicio and fin:
            if fin <= inicio:
                raise serializers.ValidationError({
                    "hora_fin": "La hora de término debe ser posterior al inicio."
                })

            superpuestos = HorarioClase.objects.filter(
                hora_inicio__lt=fin,
                hora_fin__gt=inicio
            )

            if self.instance:
                superpuestos = superpuestos.exclude(
                    pk=self.instance.pk
                )

            if superpuestos.exists():
                raise serializers.ValidationError({
                    "hora_inicio": "Este horario se superpone con otro existente."
                })

        return attrs

    def create(self, validated_data):
        try:
            return super().create(validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                error.message_dict if hasattr(error, "message_dict")
                else error.messages
            )

    def update(self, instance, validated_data):
        try:
            return super().update(instance, validated_data)
        except DjangoValidationError as error:
            raise serializers.ValidationError(
                error.message_dict if hasattr(error, "message_dict")
                else error.messages
            )
