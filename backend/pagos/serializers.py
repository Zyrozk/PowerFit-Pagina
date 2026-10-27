from rest_framework import serializers
from .models import Pago


class PagoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.SerializerMethodField()
    tipo_pago_nombre = serializers.CharField(
        source="get_tipo_pago_display",
        read_only=True
    )
    metodo_pago_nombre = serializers.CharField(
        source="get_metodo_pago_display",
        read_only=True
    )
    estado_nombre = serializers.CharField(
        source="get_estado_display",
        read_only=True
    )

    class Meta:
        model = Pago
        fields = [
            "id",
            "socio",
            "socio_nombre",
            "tipo_pago",
            "tipo_pago_nombre",
            "metodo_pago",
            "metodo_pago_nombre",
            "monto",
            "estado",
            "estado_nombre",
            "fecha_pago",
        ]
        read_only_fields = fields

    def get_socio_nombre(self, obj):
        nombre = obj.socio.get_full_name()
        return nombre if nombre else obj.socio.username