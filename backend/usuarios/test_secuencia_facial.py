
from unittest.mock import patch

import numpy as np

from django.test import SimpleTestCase

from usuarios.servicios_secuencia_facial import (
    obtener_secuencia_requerida,
    validar_cantidad_fotogramas,
    validar_secuencia_movimientos,
    validar_secuencia_fotogramas,
)


class SecuenciaFacialTest(SimpleTestCase):

    def setUp(self):

        self.frente = {
            "estado_ojos": "ABIERTOS",
            "estado_cabeza": "FRENTE",
        }

        self.parpadeo = {
            "estado_ojos": "CERRADOS",
            "estado_cabeza": "FRENTE",
        }

        self.izquierda = {
            "estado_ojos": "ABIERTOS",
            "estado_cabeza": "IZQUIERDA_IMAGEN",
        }

        self.derecha = {
            "estado_ojos": "ABIERTOS",
            "estado_cabeza": "DERECHA_IMAGEN",
        }

        self.indeterminado = {
            "estado_ojos": "INDETERMINADO",
            "estado_cabeza": "INDETERMINADO",
        }

        self.secuencia_izquierda = [
            self.frente,
            self.parpadeo,
            self.frente,
            self.izquierda,
            self.frente,
        ]

        self.secuencia_derecha = [
            self.frente,
            self.parpadeo,
            self.frente,
            self.derecha,
            self.frente,
        ]

        self.imagen = np.zeros(
            (100, 100, 3),
            dtype=np.uint8
        )

    def test_secuencia_requerida_izquierda(self):

        resultado = obtener_secuencia_requerida(
            "IZQUIERDA_IMAGEN"
        )

        self.assertEqual(len(resultado), 5)

        self.assertEqual(
            resultado[3]["cabeza"],
            "IZQUIERDA_IMAGEN"
        )

    def test_secuencia_requerida_derecha(self):

        resultado = obtener_secuencia_requerida(
            "DERECHA_IMAGEN"
        )

        self.assertEqual(len(resultado), 5)

        self.assertEqual(
            resultado[3]["cabeza"],
            "DERECHA_IMAGEN"
        )

    def test_direccion_invalida(self):

        with self.assertRaises(ValueError):

            obtener_secuencia_requerida(
                "INVALIDA"
            )

    def test_secuencia_correcta_izquierda(self):

        resultado = validar_secuencia_movimientos(
            self.secuencia_izquierda,
            "IZQUIERDA_IMAGEN"
        )

        self.assertTrue(resultado["superada"])

        self.assertEqual(
            resultado["codigo"],
            "SECUENCIA_COMPLETA"
        )

        self.assertEqual(
            resultado["pasos_completados"],
            5
        )

    def test_secuencia_correcta_derecha(self):

        resultado = validar_secuencia_movimientos(
            self.secuencia_derecha,
            "DERECHA_IMAGEN"
        )

        self.assertTrue(resultado["superada"])

    def test_secuencia_sin_parpadeo(self):

        secuencia = [
            self.frente,
            self.frente,
            self.frente,
            self.izquierda,
            self.frente,
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    def test_secuencia_sin_reabrir_ojos(self):

        secuencia = [
            self.frente,
            self.parpadeo,
            self.parpadeo,
            self.izquierda,
            self.frente,
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    def test_secuencia_sin_giro(self):

        secuencia = [
            self.frente,
            self.parpadeo,
            self.frente,
            self.frente,
            self.frente,
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    def test_secuencia_giro_incorrecto(self):

        resultado = validar_secuencia_movimientos(
            self.secuencia_derecha,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    def test_secuencia_sin_regreso_frontal(self):

        secuencia = [
            self.frente,
            self.parpadeo,
            self.frente,
            self.izquierda,
            self.izquierda,
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

        self.assertEqual(
            resultado["pasos_completados"],
            4
        )

    def test_secuencia_orden_incorrecto(self):

        secuencia = [
            self.frente,
            self.izquierda,
            self.frente,
            self.parpadeo,
            self.frente,
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    def test_secuencia_fotografia_estatica(self):

        secuencia = [
            self.frente.copy()
            for _ in range(10)
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    def test_secuencia_ojos_siempre_cerrados(self):

        secuencia = [
            self.parpadeo.copy()
            for _ in range(10)
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    def test_secuencia_con_fotogramas_intermedios(self):

        secuencia = [
            self.frente,
            self.frente,
            self.indeterminado,
            self.parpadeo,
            self.parpadeo,
            self.indeterminado,
            self.frente,
            self.izquierda,
            self.izquierda,
            self.frente,
        ]

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertTrue(resultado["superada"])

    def test_secuencia_con_fotogramas_adicionales(self):

        secuencia = (
            self.secuencia_izquierda
            + [
                self.frente,
                self.frente,
            ]
        )

        resultado = validar_secuencia_movimientos(
            secuencia,
            "IZQUIERDA_IMAGEN"
        )

        self.assertTrue(resultado["superada"])

    def test_secuencia_vacia(self):

        with self.assertRaises(ValueError):

            validar_cantidad_fotogramas([])

    def test_fotogramas_insuficientes(self):

        with self.assertRaises(ValueError):

            validar_cantidad_fotogramas(
                [self.imagen] * 4
            )

    def test_cantidad_maxima_permitida(self):

        validar_cantidad_fotogramas(
            [self.imagen] * 30
        )

    def test_demasiados_fotogramas(self):

        with self.assertRaises(ValueError):

            validar_cantidad_fotogramas(
                [self.imagen] * 31
            )

    def test_formato_secuencia_invalido(self):

        with self.assertRaises(ValueError):

            validar_cantidad_fotogramas(
                "secuencia_invalida"
            )

    def test_resultado_facial_invalido(self):

        secuencia = [
            None,
            self.parpadeo,
            self.frente,
            self.izquierda,
            self.frente,
        ]

        with self.assertRaises(ValueError):

            validar_secuencia_movimientos(
                secuencia,
                "IZQUIERDA_IMAGEN"
            )

    def test_estado_ojos_invalido(self):

        secuencia = self.secuencia_izquierda.copy()

        secuencia[0] = {
            "estado_ojos": "INVALIDO",
            "estado_cabeza": "FRENTE",
        }

        with self.assertRaises(ValueError):

            validar_secuencia_movimientos(
                secuencia,
                "IZQUIERDA_IMAGEN"
            )

    def test_estado_cabeza_invalido(self):

        secuencia = self.secuencia_izquierda.copy()

        secuencia[0] = {
            "estado_ojos": "ABIERTOS",
            "estado_cabeza": "INVALIDO",
        }

        with self.assertRaises(ValueError):

            validar_secuencia_movimientos(
                secuencia,
                "IZQUIERDA_IMAGEN"
            )

    @patch(
        "usuarios.servicios_secuencia_facial."
        "analizar_fotograma_facial"
    )
    def test_validacion_fotogramas_correcta(
        self,
        analizador
    ):

        analizador.side_effect = (
            self.secuencia_izquierda
        )

        resultado = validar_secuencia_fotogramas(
            [self.imagen] * 5,
            "IZQUIERDA_IMAGEN"
        )

        self.assertTrue(resultado["superada"])

        self.assertEqual(
            analizador.call_count,
            5
        )

    @patch(
        "usuarios.servicios_secuencia_facial."
        "analizar_fotograma_facial"
    )
    def test_validacion_fotogramas_sin_movimientos(
        self,
        analizador
    ):

        analizador.return_value = self.frente

        resultado = validar_secuencia_fotogramas(
            [self.imagen] * 5,
            "IZQUIERDA_IMAGEN"
        )

        self.assertFalse(resultado["superada"])

    @patch(
        "usuarios.servicios_secuencia_facial."
        "analizar_fotograma_facial"
    )
    def test_fotograma_sin_rostro(
        self,
        analizador
    ):

        analizador.side_effect = ValueError(
            "No se detectó ningún rostro."
        )

        with self.assertRaisesMessage(
            ValueError,
            "No se detectó ningún rostro."
        ):

            validar_secuencia_fotogramas(
                [self.imagen] * 5,
                "IZQUIERDA_IMAGEN"
            )

    @patch(
        "usuarios.servicios_secuencia_facial."
        "analizar_fotograma_facial"
    )
    def test_fotograma_varios_rostros(
        self,
        analizador
    ):

        analizador.side_effect = ValueError(
            "Debe aparecer solamente un rostro."
        )

        with self.assertRaisesMessage(
            ValueError,
            "Debe aparecer solamente un rostro."
        ):

            validar_secuencia_fotogramas(
                [self.imagen] * 5,
                "IZQUIERDA_IMAGEN"
            )
