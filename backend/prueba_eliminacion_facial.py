
from django.contrib.auth import get_user_model
from django.db import transaction
from usuarios.models import RegistroFacial
from usuarios.servicios_faciales import eliminar_datos_faciales

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
            "La prueba se detuvo porque ya existen datos biométricos. "
            "No se sobrescribirán."
        )

    registro.datos_biometricos_cifrados = b"DATOS_FICTICIOS_PRUEBA"
    registro.activo = True
    registro.consentimiento_otorgado = True
    registro.consentimiento_confirmado_por_socio = True
    registro.save()

    socio.reconocimiento_facial_habilitado = True
    socio.save(
        update_fields=["reconocimiento_facial_habilitado"]
    )

    eliminar_datos_faciales(registro)

    registro.refresh_from_db()
    socio.refresh_from_db()

    assert registro.datos_biometricos_cifrados is None
    assert registro.fecha_enrolamiento is None
    assert registro.activo is False
    assert registro.consentimiento_otorgado is False
    assert registro.consentimiento_confirmado_por_socio is False
    assert socio.reconocimiento_facial_habilitado is False
    assert registro.fecha_revocacion is not None

    print("PRUEBA EXITOSA: datos faciales eliminados del registro activo.")
    print(
        "Reconocimiento facial habilitado:",
        socio.reconocimiento_facial_habilitado
    )
    print(
        "Consentimiento otorgado:",
        registro.consentimiento_otorgado
    )
    print(
        "Registro facial activo:",
        registro.activo
    )
    print(
        "Datos biométricos:",
        registro.datos_biometricos_cifrados
    )
