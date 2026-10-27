
from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def obtener_cifrador_facial():
    clave = settings.POWERFIT_FERNET_KEY

    if not clave:
        raise ValueError(
            "No se ha configurado la clave de cifrado facial."
        )

    try:
        return Fernet(clave.encode("utf-8"))
    except (ValueError, TypeError) as error:
        raise ValueError(
            "La clave de cifrado facial no es válida."
        ) from error


def cifrar_datos_faciales(datos):
    if not isinstance(datos, bytes):
        raise TypeError(
            "Los datos faciales deben estar en formato bytes."
        )

    if not datos:
        raise ValueError(
            "No se pueden cifrar datos faciales vacíos."
        )

    cifrador = obtener_cifrador_facial()

    return cifrador.encrypt(datos)


def descifrar_datos_faciales(datos_cifrados):
    if not isinstance(datos_cifrados, bytes):
        raise TypeError(
            "Los datos cifrados deben estar en formato bytes."
        )

    if not datos_cifrados:
        raise ValueError(
            "No existen datos faciales para descifrar."
        )

    cifrador = obtener_cifrador_facial()

    try:
        return cifrador.decrypt(datos_cifrados)
    except InvalidToken as error:
        raise ValueError(
            "No se pudieron descifrar los datos faciales."
        ) from error
