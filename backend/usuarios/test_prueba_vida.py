
from unittest.mock import patch

import numpy as np

from django.test import SimpleTestCase

from usuarios.servicios_prueba_vida import (
    distancia_puntos,
    calcular_apertura_ojo,
    calcular_orientacion_cabeza,
    analizar_puntos_faciales,
    analizar_fotograma_facial,
)


class PruebaVidaTest(SimpleTestCase):

    def setUp(self):

        self.ojo_abierto = [
            (0, 0),
            (2, -3),
            (8, -3),
            (10, 0),
            (8, 3),
            (2, 3)
        ]

        self.ojo_cerrado = [
            (0, 0),
            (2, -0.5),
            (8, -0.5),
            (10, 0),
            (8, 0.5),
            (2, 0.5)
        ]

        self.ojo_intermedio = [
            (0, 0),
            (2, -1),
            (8, -1),
            (10, 0),
            (8, 1),
            (2, 1)
        ]

        self.imagen = np.zeros(
            (100, 100, 3),
            dtype=np.uint8
        )

    def crear_puntos(
        self,
        ojo_izquierdo=None,
        ojo_derecho=None,
        desplazamiento_nariz=0
    ):

        if ojo_izquierdo is None:
            ojo_izquierdo = self.ojo_abierto

        if ojo_derecho is None:
            ojo_derecho = self.ojo_abierto

        menton = [
            (0, 0)
            for _ in range(17)
        ]

        menton[0] = (0, 0)
        menton[16] = (100, 0)

        centro_nariz = (
            50 + desplazamiento_nariz,
            30
        )

        nariz = [
            centro_nariz
            for _ in range(5)
        ]

        return {
            "left_eye": ojo_izquierdo,
            "right_eye": ojo_derecho,
            "chin": menton,
            "nose_tip": nariz,
        }

    def test_distancia_entre_puntos(self):

        resultado = distancia_puntos(
            (0, 0),
            (3, 4)
        )

        self.assertAlmostEqual(
            resultado,
            5.0
        )

    def test_apertura_ojo_abierto(self):

        resultado = calcular_apertura_ojo(
            self.ojo_abierto
        )

        self.assertAlmostEqual(
            resultado,
            0.60
        )

    def test_apertura_ojo_cerrado(self):

        resultado = calcular_apertura_ojo(
            self.ojo_cerrado
        )

        self.assertAlmostEqual(
            resultado,
            0.10
        )

    def test_ojo_con_puntos_insuficientes(self):

        with self.assertRaises(ValueError):

            calcular_apertura_ojo([
                (0, 0),
                (1, 1)
            ])

    def test_ojo_con_ancho_invalido(self):

        puntos = [
            (0, 0)
            for _ in range(6)
        ]

        with self.assertRaises(ValueError):

            calcular_apertura_ojo(puntos)

    def test_ambos_ojos_abiertos(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos()
        )

        self.assertEqual(
            resultado["estado_ojos"],
            "ABIERTOS"
        )

    def test_ambos_ojos_cerrados(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos(
                ojo_izquierdo=self.ojo_cerrado,
                ojo_derecho=self.ojo_cerrado
            )
        )

        self.assertEqual(
            resultado["estado_ojos"],
            "CERRADOS"
        )

    def test_ojos_intermedios(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos(
                ojo_izquierdo=self.ojo_intermedio,
                ojo_derecho=self.ojo_intermedio
            )
        )

        self.assertEqual(
            resultado["estado_ojos"],
            "INDETERMINADO"
        )

    def test_solo_un_ojo_cerrado(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos(
                ojo_izquierdo=self.ojo_cerrado,
                ojo_derecho=self.ojo_abierto
            )
        )

        self.assertEqual(
            resultado["estado_ojos"],
            "INDETERMINADO"
        )

    def test_cabeza_frontal(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos()
        )

        self.assertEqual(
            resultado["estado_cabeza"],
            "FRENTE"
        )

        self.assertAlmostEqual(
            resultado["orientacion_cabeza"],
            0.0
        )

    def test_cabeza_girada_izquierda(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos(
                desplazamiento_nariz=-20
            )
        )

        self.assertEqual(
            resultado["estado_cabeza"],
            "IZQUIERDA_IMAGEN"
        )

    def test_cabeza_girada_derecha(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos(
                desplazamiento_nariz=20
            )
        )

        self.assertEqual(
            resultado["estado_cabeza"],
            "DERECHA_IMAGEN"
        )

    def test_giro_insuficiente(self):

        resultado = analizar_puntos_faciales(
            self.crear_puntos(
                desplazamiento_nariz=10
            )
        )

        self.assertEqual(
            resultado["estado_cabeza"],
            "INDETERMINADO"
        )

    def test_orientacion_con_menton_invalido(self):

        puntos = self.crear_puntos()
        puntos["chin"] = [(0, 0)]

        with self.assertRaises(ValueError):

            calcular_orientacion_cabeza(
                puntos
            )

    def test_orientacion_con_ancho_invalido(self):

        puntos = self.crear_puntos()

        puntos["chin"][16] = (
            puntos["chin"][0]
        )

        with self.assertRaises(ValueError):

            calcular_orientacion_cabeza(
                puntos
            )

    def test_puntos_faciales_incompletos(self):

        puntos = self.crear_puntos()

        del puntos["left_eye"]

        with self.assertRaises(ValueError):

            analizar_puntos_faciales(
                puntos
            )

    def test_fotograma_no_es_numpy(self):

        with self.assertRaises(ValueError):

            analizar_fotograma_facial(
                "imagen_invalida"
            )

    def test_fotograma_sin_formato_rgb(self):

        imagen = np.zeros(
            (100, 100),
            dtype=np.uint8
        )

        with self.assertRaises(ValueError):

            analizar_fotograma_facial(
                imagen
            )

    def test_fotograma_tipo_dato_invalido(self):

        imagen = np.zeros(
            (100, 100, 3),
            dtype=np.float64
        )

        with self.assertRaises(ValueError):

            analizar_fotograma_facial(
                imagen
            )

    def test_fotograma_vacio(self):

        imagen = np.zeros(
            (0, 0, 3),
            dtype=np.uint8
        )

        with self.assertRaises(ValueError):

            analizar_fotograma_facial(
                imagen
            )

    @patch(
        "usuarios.servicios_prueba_vida."
        "face_recognition.face_locations"
    )
    def test_fotograma_sin_rostro(
        self,
        detector
    ):

        detector.return_value = []

        with self.assertRaisesMessage(
            ValueError,
            "No se detectó ningún rostro."
        ):

            analizar_fotograma_facial(
                self.imagen
            )

    @patch(
        "usuarios.servicios_prueba_vida."
        "face_recognition.face_locations"
    )
    def test_fotograma_con_varios_rostros(
        self,
        detector
    ):

        detector.return_value = [
            (10, 50, 50, 10),
            (20, 90, 80, 60)
        ]

        with self.assertRaisesMessage(
            ValueError,
            "Debe aparecer solamente un rostro."
        ):

            analizar_fotograma_facial(
                self.imagen
            )

    @patch(
        "usuarios.servicios_prueba_vida."
        "face_recognition.face_landmarks"
    )
    @patch(
        "usuarios.servicios_prueba_vida."
        "face_recognition.face_locations"
    )
    def test_fotograma_con_rostro_valido(
        self,
        detector,
        landmarks
    ):

        detector.return_value = [
            (10, 50, 50, 10)
        ]

        landmarks.return_value = [
            self.crear_puntos()
        ]

        resultado = analizar_fotograma_facial(
            self.imagen
        )

        self.assertEqual(
            resultado["estado_ojos"],
            "ABIERTOS"
        )

        self.assertEqual(
            resultado["estado_cabeza"],
            "FRENTE"
        )

    @patch(
        "usuarios.servicios_prueba_vida."
        "face_recognition.face_landmarks"
    )
    @patch(
        "usuarios.servicios_prueba_vida."
        "face_recognition.face_locations"
    )
    def test_fotograma_sin_puntos_faciales(
        self,
        detector,
        landmarks
    ):

        detector.return_value = [
            (10, 50, 50, 10)
        ]

        landmarks.return_value = []

        with self.assertRaisesMessage(
            ValueError,
            "No fue posible analizar el rostro."
        ):

            analizar_fotograma_facial(
                self.imagen
            )
