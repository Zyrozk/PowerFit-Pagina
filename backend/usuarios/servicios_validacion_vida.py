
import face_recognition
import numpy as np

from .servicios_faciales import (
    procesar_imagen_facial,
    obtener_vector_facial,
    validar_vector_facial,
    comparar_vectores_faciales,
)

from .servicios_prueba_vida import (
    analizar_puntos_faciales,
)

from .servicios_secuencia_facial import (
    validar_cantidad_fotogramas,
    obtener_secuencia_requerida,
    validar_secuencia_movimientos,
)


TAMANO_MAXIMO_FOTOGRAMA = 1024 * 1024

TAMANO_MAXIMO_SECUENCIA = 15 * 1024 * 1024


def validar_archivos_fotogramas(archivos):

    validar_cantidad_fotogramas(archivos)

    tamano_total = 0

    for archivo in archivos:

        tamano = getattr(
            archivo,
            "size",
            None
        )

        if tamano is None:

            raise ValueError(
                "El archivo facial no es válido."
            )

        if tamano <= 0:

            raise ValueError(
                "Uno de los fotogramas está vacío."
            )

        if tamano > TAMANO_MAXIMO_FOTOGRAMA:

            raise ValueError(
                "Cada fotograma debe pesar "
                "como máximo 1 MB."
            )

        tamano_total += tamano

        if tamano_total > TAMANO_MAXIMO_SECUENCIA:

            raise ValueError(
                "La secuencia facial supera "
                "el tamaño máximo permitido."
            )


def analizar_fotograma_con_identidad(
    imagen,
    vector_registrado
):

    imagen = np.ascontiguousarray(imagen)

    rostros = face_recognition.face_locations(
        imagen,
        model="hog"
    )

    if len(rostros) == 0:

        raise ValueError(
            "No se detectó ningún rostro."
        )

    if len(rostros) > 1:

        raise ValueError(
            "Debe aparecer solamente un rostro."
        )

    vectores = face_recognition.face_encodings(
        imagen,
        known_face_locations=rostros,
        num_jitters=1,
        model="small"
    )

    if len(vectores) != 1:

        raise ValueError(
            "No fue posible verificar el rostro."
        )

    vector_capturado = validar_vector_facial(
        vectores[0]
    )

    comparacion = comparar_vectores_faciales(
        vector_registrado,
        vector_capturado
    )

    if not comparacion["coincidencia"]:

        return {
            "coincidencia": False,
        }

    puntos_faciales = face_recognition.face_landmarks(
        imagen,
        face_locations=rostros,
        model="large"
    )

    if len(puntos_faciales) != 1:

        raise ValueError(
            "No fue posible analizar "
            "los movimientos faciales."
        )

    movimientos = analizar_puntos_faciales(
        puntos_faciales[0]
    )

    return {
        "coincidencia": True,
        "estado_ojos": movimientos["estado_ojos"],
        "estado_cabeza": movimientos["estado_cabeza"],
    }


def validar_prueba_vida_con_identidad(
    registro,
    archivos,
    direccion
):

    validar_archivos_fotogramas(archivos)

    obtener_secuencia_requerida(direccion)

    vector_registrado = obtener_vector_facial(
        registro
    )

    resultados = []

    for archivo in archivos:

        imagen = procesar_imagen_facial(
            archivo
        )

        resultado = analizar_fotograma_con_identidad(
            imagen,
            vector_registrado
        )

        if not resultado["coincidencia"]:

            return {
                "superada": False,
                "identidad_verificada": False,
                "codigo": "ROSTRO_NO_COINCIDE",
                "mensaje": (
                    "El rostro no coincide con "
                    "el registro facial del socio."
                ),
            }

        resultados.append({
            "estado_ojos": resultado["estado_ojos"],
            "estado_cabeza": resultado["estado_cabeza"],
        })

    secuencia = validar_secuencia_movimientos(
        resultados,
        direccion
    )

    if not secuencia["superada"]:

        return {
            "superada": False,
            "identidad_verificada": True,
            "codigo": "SECUENCIA_INCOMPLETA",
            "mensaje": (
                "No se completaron correctamente "
                "los movimientos solicitados."
            ),
            "pasos_completados": (
                secuencia["pasos_completados"]
            ),
            "pasos_requeridos": (
                secuencia["pasos_requeridos"]
            ),
        }

    return {
        "superada": True,
        "identidad_verificada": True,
        "codigo": "PRUEBA_VIDA_SUPERADA",
        "mensaje": (
            "La identidad y los movimientos "
            "faciales fueron verificados correctamente."
        ),
        "pasos_completados": (
            secuencia["pasos_completados"]
        ),
        "pasos_requeridos": (
            secuencia["pasos_requeridos"]
        ),
    }
