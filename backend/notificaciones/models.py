from django.conf import settings
from django.db import models

class Notificacion(models.Model):
    socio = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='avisos_powerfit')
    tipo = models.CharField(max_length=40)
    titulo = models.CharField(max_length=120)
    descripcion = models.TextField()
    membresia_id_referencia = models.PositiveIntegerField(null=True, blank=True)
    motivo_rechazo = models.TextField(blank=True, default='')
    leida = models.BooleanField(default=False)
    creada = models.DateTimeField(auto_now_add=True)
    clave_evento = models.CharField(max_length=120, unique=True, null=True, blank=True)

    class Meta:
        ordering = ['-creada', '-id']
