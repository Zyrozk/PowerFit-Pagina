from rest_framework import serializers
from .models import Usuario, RegistroFacial
from django.contrib.auth.password_validation import validate_password


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "rol",
            "reconocimiento_facial_habilitado",
        ]

        read_only_fields = fields


class RegistroSocioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password]
    )

    class Meta:
        model = Usuario
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "password",
        ]

    def create(self, validated_data):
        return Usuario.objects.create_user(
            **validated_data,
            rol=Usuario.Rol.SOCIO,
            reconocimiento_facial_habilitado=False
        )

class RegistroFacialSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroFacial
        fields = [
            "id",
            "socio",
            "activo",
            "consentimiento_otorgado",
            "fecha_consentimiento",
            "fecha_registro",
            "fecha_actualizacion",
        ]
        read_only_fields = fields