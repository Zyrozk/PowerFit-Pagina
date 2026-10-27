from rest_framework import serializers
from .models import Clase


class ClaseSerializer(serializers.ModelSerializer):
    coach_nombre = serializers.SerializerMethodField()
    tipo_nombre = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = Clase
        fields = ['id', 'tipo', 'tipo_nombre', 'fecha', 'hora_inicio', 'hora_fin', 'coach', 'coach_nombre', 'cupos', 'descripcion', 'activa']
        read_only_fields = ['id', 'coach_nombre', 'tipo_nombre']

    def get_coach_nombre(self, obj):
        return obj.coach.get_full_name() or obj.coach.username

    def validate(self, attrs):
        inicio = attrs.get('hora_inicio', getattr(self.instance, 'hora_inicio', None))
        fin = attrs.get('hora_fin', getattr(self.instance, 'hora_fin', None))
        if inicio and fin and fin <= inicio:
            raise serializers.ValidationError({'hora_fin': 'Debe ser posterior a la hora de inicio.'})
        coach = attrs.get('coach', getattr(self.instance, 'coach', None))
        if coach and coach.rol != 'COACH':
            raise serializers.ValidationError({'coach': 'Debe seleccionar un usuario COACH.'})
        tipo = attrs.get('tipo', getattr(self.instance, 'tipo', None))
        if not self.instance and 'cupos' not in attrs:
            attrs['cupos'] = 25 if tipo == Clase.Tipo.STEP else 17
        return attrs
