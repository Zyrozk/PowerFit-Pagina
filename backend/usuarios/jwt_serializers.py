
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate
from rest_framework import serializers


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):

    username_field = "email"

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get("email", "").strip()
        password = attrs.get("password", "")

        usuario = authenticate(
            request=self.context.get("request"),
            email=email,
            password=password
        )

        if usuario is None or not usuario.is_active:
            raise AuthenticationFailed(
                "Correo electrónico o contraseña incorrectos."
            )

        refresh = self.get_token(usuario)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token)
        }
