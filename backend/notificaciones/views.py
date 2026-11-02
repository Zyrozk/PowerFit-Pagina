from datetime import timedelta
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from membresias.models import Membresia
from .models import Notificacion

class NotificacionesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def get_queryset(self, request):
        if request.user.rol != 'SOCIO':
            raise PermissionDenied('Solo socios.')
        return Notificacion.objects.filter(socio=request.user)

    def get(self, request):
        qs = self.get_queryset(request)
        hoy = timezone.localdate()
        limite = hoy + timedelta(days=3)
        for m in Membresia.objects.filter(socio=request.user, estado=Membresia.Estado.ACTIVA, fecha_vencimiento__gte=hoy, fecha_vencimiento__lte=limite):
            Notificacion.objects.get_or_create(clave_evento=f'vence:{m.pk}', defaults=dict(socio=request.user, tipo='MEMBRESIA_POR_VENCER', titulo='Tu membresía está por vencer', descripcion=f'Tu {m.get_plan_display()} vence el {m.fecha_vencimiento:%d/%m/%Y}.', membresia_id_referencia=m.pk))
        return Response([dict(id=n.id, tipo=n.tipo, titulo=n.titulo, descripcion=n.descripcion, membresia_id=n.membresia_id_referencia, motivo_rechazo=n.motivo_rechazo, creada=n.creada.isoformat(), nueva=not n.leida) for n in qs])

    def delete(self, request):
        self.get_queryset(request).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class NotificacionDetalleView(NotificacionesView):
    def delete(self, request, pk):
        count, _ = self.get_queryset(request).filter(pk=pk).delete()
        return Response(status=status.HTTP_204_NO_CONTENT if count else status.HTTP_404_NOT_FOUND)
