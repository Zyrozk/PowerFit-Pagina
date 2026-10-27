from rest_framework import permissions, viewsets
from .models import Clase
from .serializers import ClaseSerializer


class SoloDuenaPuedeModificar(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.method in permissions.SAFE_METHODS or request.user.rol == 'DUENA'


class ClaseViewSet(viewsets.ModelViewSet):
    serializer_class = ClaseSerializer
    permission_classes = [SoloDuenaPuedeModificar]

    def get_queryset(self):
        qs = Clase.objects.select_related('coach').all()
        if self.request.user.rol != 'DUENA':
            qs = qs.filter(activa=True)
        fecha = self.request.query_params.get('fecha')
        if fecha:
            qs = qs.filter(fecha=fecha)
        return qs
