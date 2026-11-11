
from datetime import timedelta

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from membresias.models import Membresia
from .models import Notificacion


class NotificacionesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self, request):
        return Notificacion.objects.filter(
            socio=request.user
        )

    def get(self, request):
        qs = self.get_queryset(request)

        if request.user.rol == 'SOCIO':
            hoy = timezone.localdate()
            limite = hoy + timedelta(days=3)

            membresias = Membresia.objects.filter(
                socio=request.user,
                estado=Membresia.Estado.ACTIVA,
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=limite
            )

            for membresia in membresias:
                Notificacion.objects.get_or_create(
                    clave_evento=f'vence:{membresia.pk}',
                    defaults={
                        'socio': request.user,
                        'tipo': 'MEMBRESIA_POR_VENCER',
                        'titulo': 'Tu membresía está por vencer',
                        'descripcion': (
                            f'Tu {membresia.get_plan_display()} '
                            f'vence el '
                            f'{membresia.fecha_vencimiento:%d/%m/%Y}.'
                        ),
                        'membresia_id_referencia': membresia.pk
                    }
                )

        notificaciones = self.get_queryset(request)

        return Response([
            {
                'id': notificacion.id,
                'tipo': notificacion.tipo,
                'titulo': notificacion.titulo,
                'descripcion': notificacion.descripcion,
                'membresia_id': notificacion.membresia_id_referencia,
                'motivo_rechazo': notificacion.motivo_rechazo,
                'creada': notificacion.creada.isoformat(),
                'nueva': not notificacion.leida
            }
            for notificacion in notificaciones
        ])

    def delete(self, request):
        self.get_queryset(request).delete()

        return Response(
            status=status.HTTP_204_NO_CONTENT
        )


class NotificacionDetalleView(NotificacionesView):

    def delete(self, request, pk):
        cantidad, _ = self.get_queryset(request).filter(
            pk=pk
        ).delete()

        return Response(
            status=(
                status.HTTP_204_NO_CONTENT
                if cantidad
                else status.HTTP_404_NOT_FOUND
            )
        )
