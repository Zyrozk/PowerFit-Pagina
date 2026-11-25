
import io

import face_recognition
import numpy as np

from PIL import Image, ImageOps, UnidentifiedImageError
from django.db import transaction
from django.utils import timezone

from .cifrado_facial import (
    cifrar_datos_faciales,
    descifrar_datos_faciales
)


DIMENSIONES_VECTOR_FACIAL = 128
TOLERANCIA_FACIAL = 0.50
TAMANO_MAXIMO_IMAGEN = 5 * 1024 * 1024
MAXIMO_PIXELES_IMAGEN = 12000000


def procesar_imagen_facial(archivo_imagen):
    if archivo_imagen is None:
        raise ValueError(
            "Debe proporcionar una imagen facial."
        )

    if hasattr(archivo_imagen, "read"):
        if hasattr(archivo_imagen, "seek"):
            archivo_imagen.seek(0)

        contenido = archivo_imagen.read(
            TAMANO_MAXIMO_IMAGEN + 1
        )
    elif isinstance(archivo_imagen, bytes):
        contenido = archivo_imagen
    else:
        raise ValueError(
            "El formato de la imagen no es válido."
        )

    if not contenido:
        raise ValueError(
            "La imagen está vacía."
        )

    if len(contenido) > TAMANO_MAXIMO_IMAGEN:
        raise ValueError(
            "La imagen no puede superar los 5 MB."
        )

    try:
        with Image.open(io.BytesIO(contenido)) as imagen:
            if imagen.format not in ("JPEG", "PNG"):
                raise ValueError(
                    "Solo se permiten imágenes JPG, JPEG o PNG."
                )

            ancho, alto = imagen.size

            if ancho * alto > MAXIMO_PIXELES_IMAGEN:
                raise ValueError(
                    "La resolución de la imagen es demasiado alta."
                )

            imagen = ImageOps.exif_transpose(imagen)
            imagen = imagen.convert("RGB")
            imagen.thumbnail((1600, 1600))

            return np.ascontiguousarray(
                np.array(imagen, dtype=np.uint8)
            )

    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError
    ) as error:
        raise ValueError(
            "No se pudo procesar la imagen facial."
        ) from error


def generar_vector_facial(archivo_imagen):
    imagen = procesar_imagen_facial(archivo_imagen)

    rostros = face_recognition.face_locations(
        imagen,
        model="hog"
    )

    if len(rostros) == 0:
        raise ValueError(
            "No se detectó ningún rostro en la imagen."
        )

    if len(rostros) > 1:
        raise ValueError(
            "Se detectó más de un rostro en la imagen."
        )

    vectores = face_recognition.face_encodings(
        imagen,
        known_face_locations=rostros,
        num_jitters=1,
        model="small"
    )

    if len(vectores) != 1:
        raise ValueError(
            "No se pudo generar el vector facial."
        )

    return validar_vector_facial(vectores[0])


def validar_vector_facial(vector):
    vector = np.asarray(vector, dtype=np.float64)

    if vector.shape != (DIMENSIONES_VECTOR_FACIAL,):
        raise ValueError(
            "El vector facial debe contener 128 dimensiones."
        )

    if not np.all(np.isfinite(vector)):
        raise ValueError(
            "El vector facial contiene valores no válidos."
        )

    return vector


def serializar_vector_facial(vector):
    vector = validar_vector_facial(vector)

    return vector.astype("<f8").tobytes()


def deserializar_vector_facial(datos):
    if not isinstance(datos, bytes):
        raise TypeError(
            "Los datos biométricos deben estar en formato bytes."
        )

    if len(datos) != DIMENSIONES_VECTOR_FACIAL * 8:
        raise ValueError(
            "Los datos biométricos almacenados no son válidos."
        )

    vector = np.frombuffer(
        datos,
        dtype="<f8"
    ).copy()

    return validar_vector_facial(vector)


def validar_consentimiento_facial(registro):
    if not registro.consentimiento_otorgado:
        raise ValueError(
            "El socio no ha autorizado el reconocimiento facial."
        )

    if not registro.consentimiento_confirmado_por_socio:
        raise ValueError(
            "El socio no ha confirmado su consentimiento."
        )

    if registro.fecha_revocacion is not None:
        if (
            registro.fecha_confirmacion_socio is None
            or registro.fecha_confirmacion_socio
            <= registro.fecha_revocacion
        ):
            raise ValueError(
                "El consentimiento fue revocado. "
                "Se requiere una nueva autorización."
            )


def obtener_vector_facial(registro):
    validar_consentimiento_facial(registro)

    if not registro.activo:
        raise ValueError(
            "El reconocimiento facial no está activo."
        )

    if not registro.socio.reconocimiento_facial_habilitado:
        raise ValueError(
            "El socio no tiene habilitado el reconocimiento facial."
        )

    if not registro.datos_biometricos_cifrados:
        raise ValueError(
            "El socio no tiene datos biométricos registrados."
        )

    datos_descifrados = descifrar_datos_faciales(
        bytes(registro.datos_biometricos_cifrados)
    )

    return deserializar_vector_facial(
        datos_descifrados
    )


def comparar_vectores_faciales(
    vector_registrado,
    vector_capturado
):
    vector_registrado = validar_vector_facial(
        vector_registrado
    )

    vector_capturado = validar_vector_facial(
        vector_capturado
    )

    distancias = face_recognition.face_distance(
        [vector_registrado],
        vector_capturado
    )

    distancia = float(distancias[0])

    coincidencia = distancia <= TOLERANCIA_FACIAL

    return {
        "coincidencia": coincidencia,
        "distancia": distancia,
        "tolerancia": TOLERANCIA_FACIAL
    }


def verificar_imagen_facial(registro, archivo_imagen):
    vector_registrado = obtener_vector_facial(
        registro
    )

    vector_capturado = generar_vector_facial(
        archivo_imagen
    )

    return comparar_vectores_faciales(
        vector_registrado,
        vector_capturado
    )


def eliminar_datos_faciales(registro):
    from .models import RegistroFacial

    with transaction.atomic():
        registro = RegistroFacial.objects.select_for_update().get(
            pk=registro.pk
        )

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
            update_fields=[
                "reconocimiento_facial_habilitado"
            ]
        )


def guardar_datos_faciales_cifrados(
    registro,
    datos_biometricos
):
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

        validar_consentimiento_facial(
            registro_actual
        )

        if registro_actual.datos_biometricos_cifrados is not None:
            raise ValueError(
                "Este socio ya tiene datos biométricos almacenados."
            )

        datos_cifrados = cifrar_datos_faciales(
            datos_biometricos
        )

        registro_actual.datos_biometricos_cifrados = datos_cifrados

        registro_actual.save(
            update_fields=[
                "datos_biometricos_cifrados",
                "fecha_actualizacion"
            ]
        )

        return registro_actual
