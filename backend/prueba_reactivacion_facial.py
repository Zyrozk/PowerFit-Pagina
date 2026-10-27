
from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import override_settings
from rest_framework.test import APIClient
from usuarios.models import RegistroFacial

Usuario = get_user_model()

socio = Usuario.objects.get(
    email="camila.prueba@example.com",
    rol="SOCIO"
)

with transaction.atomic():
    registro, creado = RegistroFacial.objects.select_for_update().get_or_create(
        socio=socio
    )

    if registro.datos_biometricos_cifrados is not None:
        raise ValueError(
            "La prueba se detuvo porque existen datos biométricos. "
            "No se sobrescribirán."
        )

    cliente = APIClient()
    cliente.force_authenticate(user=socio)

    with override_settings(
        ALLOWED_HOSTS=["testserver", "127.0.0.1", "localhost"]
    ):
        respuesta_revocacion = cliente.post(
            "/api/usuarios/consentimiento-facial/",
            {"aceptar": False},
            format="json"
        )

        assert respuesta_revocacion.status_code == 200

        registro.refresh_from_db()

        assert registro.datos_biometricos_cifrados is None
        assert registro.activo is False
        assert registro.consentimiento_otorgado is False

        print("PASO 1: revocación correcta.")

        respuesta_autorizacion = cliente.post(
            "/api/usuarios/consentimiento-facial/",
            {"aceptar": True},
            format="json"
        )

        assert respuesta_autorizacion.status_code == 200

        registro.refresh_from_db()
        socio.refresh_from_db()

        assert registro.consentimiento_otorgado is True
        assert registro.consentimiento_confirmado_por_socio is True
        assert registro.activo is False
        assert registro.datos_biometricos_cifrados is None
        assert registro.fecha_enrolamiento is None
        assert socio.reconocimiento_facial_habilitado is False

        print("PASO 2: nueva autorización registrada.")
        print("Consentimiento otorgado:", registro.consentimiento_otorgado)
        print("Registro facial activo:", registro.activo)
        print("Datos biométricos:", registro.datos_biometricos_cifrados)
        print("Reconocimiento habilitado:", socio.reconocimiento_facial_habilitado)

        print(
            "PRUEBA EXITOSA: una nueva autorización requiere "
            "un nuevo enrolamiento presencial."
        )

    transaction.set_rollback(True)
