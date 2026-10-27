
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient
from usuarios.models import RegistroFacial

Usuario = get_user_model()

socio = Usuario.objects.get(
    email="camila.prueba@example.com",
    rol="SOCIO"
)

registro, creado = RegistroFacial.objects.get_or_create(
    socio=socio
)

if registro.datos_biometricos_cifrados is not None:
    raise ValueError(
        "La prueba se detuvo porque existen datos biométricos. "
        "No se sobrescribirán."
    )

registro.datos_biometricos_cifrados = b"DATOS_FICTICIOS_API"
registro.activo = True
registro.consentimiento_otorgado = True
registro.consentimiento_confirmado_por_socio = True
registro.save()

socio.reconocimiento_facial_habilitado = True
socio.save(
    update_fields=["reconocimiento_facial_habilitado"]
)

cliente = APIClient()
cliente.force_authenticate(user=socio)

with override_settings(ALLOWED_HOSTS=["testserver", "127.0.0.1", "localhost"]):
    respuesta = cliente.post(
        "/api/usuarios/consentimiento-facial/",
        {"aceptar": False},
        format="json"
    )

registro.refresh_from_db()
socio.refresh_from_db()

print("Código HTTP:", respuesta.status_code)
print("Respuesta API:", respuesta.data)

assert respuesta.status_code == 200
assert registro.datos_biometricos_cifrados is None
assert registro.fecha_enrolamiento is None
assert registro.activo is False
assert registro.consentimiento_otorgado is False
assert registro.consentimiento_confirmado_por_socio is False
assert socio.reconocimiento_facial_habilitado is False
assert registro.fecha_revocacion is not None

print("PRUEBA EXITOSA: la API revocó el consentimiento y limpió los datos faciales.")
