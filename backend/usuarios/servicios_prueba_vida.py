
import face_recognition
import numpy as np


UMBRAL_OJOS_CERRADOS = 0.18
UMBRAL_OJOS_ABIERTOS = 0.23

UMBRAL_GIRO_CABEZA = 0.12
UMBRAL_ROSTRO_FRONTAL = 0.08


def distancia_puntos(punto_a, punto_b):

    punto_a = np.asarray(
        punto_a,
        dtype=np.float64
    )

    punto_b = np.asarray(
        punto_b,
        dtype=np.float64
    )

    return float(
        np.linalg.norm(punto_a - punto_b)
    )


def calcular_apertura_ojo(puntos):

    if len(puntos) != 6:

        raise ValueError(
            "No fue posible identificar el ojo."
        )

    vertical_1 = distancia_puntos(
        puntos[1],
        puntos[5]
    )

    vertical_2 = distancia_puntos(
        puntos[2],
        puntos[4]
    )

    horizontal = distancia_puntos(
        puntos[0],
        puntos[3]
    )

    if horizontal <= 0:

        raise ValueError(
            "Las dimensiones del ojo no son válidas."
        )

    return (
        vertical_1 + vertical_2
    ) / (2.0 * horizontal)


def calcular_orientacion_cabeza(puntos_faciales):

    menton = puntos_faciales["chin"]
    nariz = puntos_faciales["nose_tip"]

    if len(menton) != 17 or len(nariz) != 5:

        raise ValueError(
            "No fue posible determinar "
            "la orientación del rostro."
        )

    extremo_izquierdo = np.asarray(
        menton[0],
        dtype=np.float64
    )

    extremo_derecho = np.asarray(
        menton[16],
        dtype=np.float64
    )

    centro_nariz = np.asarray(
        nariz[2],
        dtype=np.float64
    )

    eje_horizontal = (
        extremo_derecho - extremo_izquierdo
    )

    ancho_rostro = float(
        np.linalg.norm(eje_horizontal)
    )

    if ancho_rostro <= 0:

        raise ValueError(
            "Las dimensiones del rostro no son válidas."
        )

    eje_unitario = (
        eje_horizontal / ancho_rostro
    )

    centro_rostro = (
        extremo_izquierdo + extremo_derecho
    ) / 2.0

    desplazamiento = float(
        np.dot(
            centro_nariz - centro_rostro,
            eje_unitario
        )
    )

    return desplazamiento / ancho_rostro


def analizar_puntos_faciales(puntos_faciales):

    campos_requeridos = [
        "left_eye",
        "right_eye",
        "chin",
        "nose_tip"
    ]

    for campo in campos_requeridos:

        if campo not in puntos_faciales:

            raise ValueError(
                "No fue posible identificar "
                "todos los puntos faciales."
            )

    apertura_izquierda = calcular_apertura_ojo(
        puntos_faciales["left_eye"]
    )

    apertura_derecha = calcular_apertura_ojo(
        puntos_faciales["right_eye"]
    )

    apertura_promedio = (
        apertura_izquierda + apertura_derecha
    ) / 2.0

    orientacion = calcular_orientacion_cabeza(
        puntos_faciales
    )

    if (
        apertura_izquierda <= UMBRAL_OJOS_CERRADOS
        and apertura_derecha <= UMBRAL_OJOS_CERRADOS
    ):

        estado_ojos = "CERRADOS"

    elif (
        apertura_izquierda >= UMBRAL_OJOS_ABIERTOS
        and apertura_derecha >= UMBRAL_OJOS_ABIERTOS
    ):

        estado_ojos = "ABIERTOS"

    else:

        estado_ojos = "INDETERMINADO"

    if orientacion <= -UMBRAL_GIRO_CABEZA:

        estado_cabeza = "IZQUIERDA_IMAGEN"

    elif orientacion >= UMBRAL_GIRO_CABEZA:

        estado_cabeza = "DERECHA_IMAGEN"

    elif abs(orientacion) <= UMBRAL_ROSTRO_FRONTAL:

        estado_cabeza = "FRENTE"

    else:

        estado_cabeza = "INDETERMINADO"

    return {
        "apertura_ojo_izquierdo": apertura_izquierda,
        "apertura_ojo_derecho": apertura_derecha,
        "apertura_promedio": apertura_promedio,
        "estado_ojos": estado_ojos,
        "orientacion_cabeza": orientacion,
        "estado_cabeza": estado_cabeza,
    }


def analizar_fotograma_facial(imagen_rgb):

    if not isinstance(imagen_rgb, np.ndarray):

        raise ValueError(
            "El fotograma facial no es válido."
        )

    if (
        imagen_rgb.ndim != 3
        or imagen_rgb.shape[2] != 3
        or imagen_rgb.dtype != np.uint8
        or imagen_rgb.size == 0
    ):

        raise ValueError(
            "El fotograma debe tener formato RGB."
        )

    imagen_rgb = np.ascontiguousarray(
        imagen_rgb
    )

    rostros = face_recognition.face_locations(
        imagen_rgb,
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

    puntos_faciales = face_recognition.face_landmarks(
        imagen_rgb,
        face_locations=rostros,
        model="large"
    )

    if len(puntos_faciales) != 1:

        raise ValueError(
            "No fue posible analizar el rostro."
        )

    return analizar_puntos_faciales(
        puntos_faciales[0]
    )
