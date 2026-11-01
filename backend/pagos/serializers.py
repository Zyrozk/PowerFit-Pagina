from rest_framework import serializers
from .models import Pago
from membresias.models import Membresia, Reserva


class PagoSerializer(serializers.ModelSerializer):
    socio_nombre = serializers.SerializerMethodField()
    tiene_boleta = serializers.SerializerMethodField()
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
            "motivo_rechazo",
            "fecha_pago",
            "tiene_boleta",
        ]
        read_only_fields = fields

    def get_socio_nombre(self, obj):
        nombre = obj.socio.get_full_name()
        return nombre if nombre else obj.socio.username
    def get_tiene_boleta(self, obj):
        return obj.estado == "APROBADO" and bool(obj.boleta)

class PagoDuenaSerializer(serializers.ModelSerializer):
    nombre_socio = serializers.SerializerMethodField()
    concepto = serializers.SerializerMethodField()
    objeto_id = serializers.SerializerMethodField()
    tiene_comprobante = serializers.SerializerMethodField()
    tiene_boleta = serializers.SerializerMethodField()

    
    class Meta:
        model = Pago
        fields = [
            "id",
            "nombre_socio",
            "tipo_pago",
            "concepto",
            "objeto_id",
            "metodo_pago",
            "monto",
            "estado",
            "fecha_pago",
            "tiene_comprobante",
            "tiene_boleta",
            "motivo_rechazo"
        ]
        read_only_fields = fields


    def get_nombre_socio(self, obj):
        nombre = obj.socio.get_full_name().strip()
        return nombre or obj.socio.username

    def get_concepto(self, obj):
        if obj.tipo_pago == Pago.TipoPago.MEMBRESIA:
            membresia = Membresia.objects.filter(pago=obj).first()
            if membresia:
                return membresia.get_plan_display()
            return "Membresía"

        return "Clase particular"

    def get_objeto_id(self, obj):
        if obj.tipo_pago == Pago.TipoPago.MEMBRESIA:
            membresia = Membresia.objects.filter(pago=obj).first()
            return membresia.id if membresia else None

        reserva = Reserva.objects.filter(pago=obj).first()
        return reserva.id if reserva else None

    def get_tiene_comprobante(self, obj):
        return bool(obj.comprobante)
    
    def get_tiene_boleta(self, obj):
        return bool(obj.boleta)
