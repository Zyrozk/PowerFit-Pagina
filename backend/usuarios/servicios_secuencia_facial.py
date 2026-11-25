
from .servicios_prueba_vida import (
    analizar_fotograma_facial,
)


MINIMO_FOTOGRAMAS = 5
MAXIMO_FOTOGRAMAS = 30

DIRECCIONES_VALIDAS = (
    "IZQUIERDA_IMAGEN",
    "DERECHA_IMAGEN",
)


def obtener_secuencia_requerida(direccion):

    if direccion not in DIRECCIONES_VALIDAS:

        raise ValueError(
            "La dirección del desafío no es válida."
        )

    return [
        {
            "ojos": "ABIERTOS",
            "cabeza": "FRENTE",
        },
        {
            "ojos": "CERRADOS",
            "cabeza": "FRENTE",
        },
        {
            "ojos": "ABIERTOS",
            "cabeza": "FRENTE",
        },
        {
            "ojos": "ABIERTOS",
            "cabeza": direccion,
        },
        {
            "ojos": "ABIERTOS",
            "cabeza": "FRENTE",
        },
    ]


def validar_cantidad_fotogramas(fotogramas):

    if not isinstance(fotogramas, (list, tuple)):

        raise ValueError(
            "La secuencia de fotogramas no es válida."
        )

    cantidad = len(fotogramas)

    if cantidad < MINIMO_FOTOGRAMAS:

        raise ValueError(
            "No hay suficientes fotogramas "
            "para validar la prueba de vida."
        )

    if cantidad > MAXIMO_FOTOGRAMAS:

        raise ValueError(
            "La cantidad de fotogramas "
            "supera el máximo permitido."
        )


def validar_secuencia_movimientos(
    resultados,
    direccion
):

    validar_cantidad_fotogramas(resultados)

    secuencia = obtener_secuencia_requerida(
        direccion
    )

    paso_actual = 0

    for resultado in resultados:

        if not isinstance(resultado, dict):

            raise ValueError(
                "El resultado facial no es válido."
            )

        estado_ojos = resultado.get(
            "estado_ojos"
        )

        estado_cabeza = resultado.get(
            "estado_cabeza"
        )

        if estado_ojos not in (
            "ABIERTOS",
            "CERRADOS",
            "INDETERMINADO",
        ):

            raise ValueError(
                "El estado de los ojos no es válido."
            )

        if estado_cabeza not in (
            "FRENTE",
            "IZQUIERDA_IMAGEN",
            "DERECHA_IMAGEN",
            "INDETERMINADO",
        ):

            raise ValueError(
                "La orientación de la cabeza "
                "no es válida."
            )

        if paso_actual >= len(secuencia):

            continue

        movimiento_esperado = secuencia[
            paso_actual
        ]

        if (
            estado_ojos == movimiento_esperado["ojos"]
            and estado_cabeza
            == movimiento_esperado["cabeza"]
        ):

            paso_actual += 1

    secuencia_completa = (
        paso_actual == len(secuencia)
    )

    if secuencia_completa:

        return {
            "superada": True,
            "codigo": "SECUENCIA_COMPLETA",
            "mensaje": (
                "Los movimientos faciales "
                "fueron realizados correctamente."
            ),
            "pasos_completados": paso_actual,
            "pasos_requeridos": len(secuencia),
        }

    return {
        "superada": False,
        "codigo": "SECUENCIA_INCOMPLETA",
        "mensaje": (
            "No se completaron todos los "
            "movimientos faciales solicitados."
        ),
        "pasos_completados": paso_actual,
        "pasos_requeridos": len(secuencia),
    }


def validar_secuencia_fotogramas(
    fotogramas,
    direccion
):

    validar_cantidad_fotogramas(fotogramas)

    obtener_secuencia_requerida(direccion)

    resultados = []

    for fotograma in fotogramas:

        resultado = analizar_fotograma_facial(
            fotograma
        )

        resultados.append(resultado)

    return validar_secuencia_movimientos(
        resultados,
        direccion
    )
