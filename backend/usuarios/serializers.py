from rest_framework import serializers
from .models import Usuario, RegistroFacial, RegistroIMC, FichaSalud
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


class MiPerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "telefono",
            "rol",
            "reconocimiento_facial_habilitado",
        ]
        read_only_fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "rol",
            "reconocimiento_facial_habilitado",
        ]

    def validate_email(self, value):
        email = value.strip().lower()

        if Usuario.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError(
                "Este correo ya está registrado."
            )

        return email


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


class GestionCoachSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password]
    )

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "telefono",
            "especialidades",
            "password",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({
                "password": "La contraseña es obligatoria."
            })
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        return Usuario.objects.create_user(
            password=password,
            rol=Usuario.Rol.COACH,
            **validated_data
        )

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        if password:
            instance.set_password(password)

        instance.save()
        return instance

        def validate_especialidades(self, value):
            permitidas = {
                "BAILE_ENTRETENIDO",
                "LOCALIZADO",
                "STEP",
                "SALSA_FIT",
                "BACHATA",
                "SALSA",
            }

        if not isinstance(value, list):
            raise serializers.ValidationError(
                "Las especialidades deben ser una lista."
            )

        if any(
            not isinstance(item, str) or item not in permitidas
            for item in value
        ):
            raise serializers.ValidationError(
                "Se encontraron especialidades no válidas."
            )

        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "No se permiten especialidades repetidas."
            )

        return value


class GestionSocioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=False,
        validators=[validate_password]
    )

    class Meta:
        model = Usuario
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "telefono",
            "password",
            "is_active",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        if self.instance is None and not attrs.get("password"):
            raise serializers.ValidationError({
                "password": "La contraseña es obligatoria."
            })
        return attrs

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("is_active", None)

        return Usuario.objects.create_user(
            password=password,
            rol=Usuario.Rol.SOCIO,
            is_active=True,
            reconocimiento_facial_habilitado=False,
            **validated_data
        )

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)

        for campo, valor in validated_data.items():
            setattr(instance, campo, valor)

        if password:
            instance.set_password(password)

        instance.save()
        return instance


class RegistroIMCSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroIMC
        fields = [
            "id",
            "peso",
            "altura",
            "imc",
            "clasificacion",
            "fecha_registro"
        ]
        read_only_fields = [
            "id",
            "imc",
            "clasificacion",
            "fecha_registro"
        ]

    def validate_peso(self, value):
        if value <= 0 or value > 500:
            raise serializers.ValidationError(
                "El peso debe ser mayor a 0 y no superar 500 kg."
            )
        return value

    def validate_altura(self, value):
        if value < 50 or value > 250:
            raise serializers.ValidationError(
                "La altura debe estar entre 50 y 250 cm."
            )
        return value

    def create(self, validated_data):
        peso = validated_data["peso"]
        altura_cm = validated_data["altura"]
        altura_m = altura_cm / 100

        imc = peso / (altura_m * altura_m)

        if imc < 18.5:
            clasificacion = "Bajo peso"
        elif imc < 25:
            clasificacion = "Peso normal"
        elif imc < 30:
            clasificacion = "Sobrepeso"
        else:
            clasificacion = "Obesidad"

        validated_data["imc"] = round(imc, 2)
        validated_data["clasificacion"] = clasificacion
        validated_data["socio"] = self.context["request"].user

        return super().create(validated_data)


class FichaSaludSerializer(serializers.ModelSerializer):
    class Meta:
        model = FichaSalud
        fields = [
            "id",
            "tiene_limitacion",
            "descripcion_limitacion",
            "informacion_adicional",
            "nombre_emergencia",
            "telefono_emergencia",
            "relacion_emergencia",
            "declaracion_aceptada",
            "fecha_creacion",
            "fecha_actualizacion"
        ]

        read_only_fields = [
            "id",
            "fecha_creacion",
            "fecha_actualizacion"
        ]

    def validate(self, attrs):
        tiene_limitacion = attrs.get(
            "tiene_limitacion",
            getattr(self.instance, "tiene_limitacion", None)
        )

        descripcion = attrs.get(
            "descripcion_limitacion",
            getattr(self.instance, "descripcion_limitacion", "")
        )

        if tiene_limitacion is None:
            raise serializers.ValidationError({
                "tiene_limitacion": "Debes indicar si tienes alguna limitación."
            })

        if tiene_limitacion and not descripcion.strip():
            raise serializers.ValidationError({
                "descripcion_limitacion": "Debes describir la lesión o limitación."
            })

        if not tiene_limitacion:
            attrs["descripcion_limitacion"] = ""

        for campo in [
            "nombre_emergencia",
            "telefono_emergencia",
            "relacion_emergencia"
        ]:
            valor = attrs.get(
                campo,
                getattr(self.instance, campo, "")
            )

            if not isinstance(valor, str) or not valor.strip():
                raise serializers.ValidationError({
                    campo: "Este campo es obligatorio."
                })

            attrs[campo] = valor.strip()

        aceptada = attrs.get(
            "declaracion_aceptada",
            getattr(self.instance, "declaracion_aceptada", False)
        )

        if not aceptada:
            raise serializers.ValidationError({
                "declaracion_aceptada": "Debes aceptar la declaración."
            })

        return attrs
