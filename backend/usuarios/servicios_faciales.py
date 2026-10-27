from .cifrado_facial import cifrar_datos_faciales
from django.utils import timezone


def eliminar_datos_faciales(registro):
    """
    Elimina los datos biométricos asociados a un registro facial
    y desactiva el reconocimiento facial del socio.
    """

    registro.datos_biometricos_cifrados = None
    registro.fecha_enrolamiento = None
    registro.activo = False
    registro.registrado_por = None

    registro.consentimiento_otorgado = False
    registro.consentimiento_confirmado_por_socio = False
    registro.fecha_revocacion = timezone.now()

    registro.save()

    socio = registro.socio
    socio.reconocimiento_facial_habilitado = False
    socio.save(
        update_fields=["reconocimiento_facial_habilitado"]
    )



def guardar_datos_faciales_cifrados(registro, datos_biometricos):
    from django.db import transaction
    from .models import RegistroFacial

    if not isinstance(datos_biometricos, bytes):
        raise TypeError(
            "Los datos biométricos deben estar en formato bytes."
        )

    if not datos_biometricos:
        raise ValueError(
            "No se pueden guardar datos biométricos vacíos."
        )

    with transaction.atomic():
        registro_actual = RegistroFacial.objects.select_for_update().get(
            pk=registro.pk
        )

        if not registro_actual.consentimiento_otorgado:
            raise ValueError(
                "El socio no ha autorizado el reconocimiento facial."
            )

        if not registro_actual.consentimiento_confirmado_por_socio:
            raise ValueError(
                "El socio no ha confirmado su consentimiento."
            )

        if registro_actual.fecha_revocacion is not None:
            if (
                registro_actual.fecha_confirmacion_socio is None
                or registro_actual.fecha_confirmacion_socio
                <= registro_actual.fecha_revocacion
            ):
                raise ValueError(
                    "El consentimiento fue revocado. "
                    "Se requiere una nueva autorización."
                )

        if registro_actual.datos_biometricos_cifrados is not None:
            raise ValueError(
                "Este socio ya tiene datos biométricos almacenados."
            )

        datos_cifrados = cifrar_datos_faciales(datos_biometricos)

        registro_actual.datos_biometricos_cifrados = datos_cifrados

        registro_actual.save(
            update_fields=[
                "datos_biometricos_cifrados",
                "fecha_actualizacion"
            ]
        )

        return registro_actual


