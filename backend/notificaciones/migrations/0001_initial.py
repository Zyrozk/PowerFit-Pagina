from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='Notificacion', fields=[
        ('id', models.BigAutoField(primary_key=True, serialize=False)),
        ('tipo', models.CharField(max_length=40)),
        ('titulo', models.CharField(max_length=120)),
        ('descripcion', models.TextField()),
        ('membresia_id_referencia', models.PositiveIntegerField(blank=True, null=True)),
        ('motivo_rechazo', models.TextField(blank=True, default='')),
        ('leida', models.BooleanField(default=False)),
        ('creada', models.DateTimeField(auto_now_add=True)),
        ('clave_evento', models.CharField(max_length=120, unique=True, blank=True, null=True)),
        ('socio', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.CASCADE, related_name='avisos_powerfit')),
    ], options={'ordering':['-creada','-id']})]
