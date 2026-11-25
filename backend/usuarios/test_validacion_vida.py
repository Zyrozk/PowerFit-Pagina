
from unittest.mock import patch, Mock

import numpy as np

from django.test import SimpleTestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from usuarios.servicios_validacion_vida import (
    validar_archivos_fotogramas,
    analizar_fotograma_con_identidad,
    validar_prueba_vida_con_identidad,
)


class ValidacionVidaTest(SimpleTestCase):

    def setUp(self):

        self.registro = Mock()

        self.vector = np.zeros(
            128,
            dtype=np.float64
        )

        self.imagen = np.zeros(
            (100, 100, 3),
            dtype=np.uint8
        )

        self.frente = {
            "coincidencia": True,
            "estado_ojos": "ABIERTOS",
            "estado_cabeza": "FRENTE",
        }

        self.parpadeo = {
            "coincidencia": True,
            "estado_ojos": "CERRADOS",
            "estado_cabeza": "FRENTE",
        }

        self.izquierda = {
            "coincidencia": True,
            "estado_ojos": "ABIERTOS",
            "estado_cabeza": "IZQUIERDA_IMAGEN",
        }

        self.derecha = {
            "coincidencia": True,
            "estado_ojos": "ABIERTOS",
            "estado_cabeza": "DERECHA_IMAGEN",
        }

        self.secuencia = [
            self.frente,
            self.parpadeo,
            self.frente,
            self.izquierda,
            self.frente,
        ]

        self.archivos = self.crear_archivos()

    def crear_archivos(
        self,
        cantidad=5,
        contenido=b"imagen_de_prueba"
    ):

        return [
            SimpleUploadedFile(
                f"fotograma_{i}.jpg",
                contenido,
                content_type="image/jpeg"
            )
            for i in range(cantidad)
        ]

    def ejecutar_validacion(
        self,
        resultados,
        direccion="IZQUIERDA_IMAGEN"
    ):

        ruta = "usuarios.servicios_validacion_vida."

        with patch(
            ruta + "obtener_vector_facial",
            return_value=self.vector
        ), patch(
            ruta + "procesar_imagen_facial",
            return_value=self.imagen
        ), patch(
            ruta + "analizar_fotograma_con_identidad",
            side_effect=resultados
        ) as analizador:

            resultado = validar_prueba_vida_con_identidad(
                self.registro,
                self.archivos,
                direccion
            )

            return resultado, analizador.call_count

    def test_archivos_validos(self):

        validar_archivos_fotogramas(
            self.archivos
        )

    def test_archivos_insuficientes(self):

        with self.assertRaises(ValueError):

            validar_archivos_fotogramas(
                self.crear_archivos(cantidad=4)
            )

    def test_demasiados_archivos(self):

        with self.assertRaises(ValueError):

            validar_archivos_fotogramas(
                self.crear_archivos(cantidad=31)
            )

    def test_archivo_sin_tamano(self):

        archivos = [
            object()
            for _ in range(5)
        ]

        with self.assertRaisesMessage(
            ValueError,
            "El archivo facial no es válido."
        ):

            validar_archivos_fotogramas(
                archivos
            )

    def test_archivo_vacio(self):

        archivos = self.crear_archivos(
            contenido=b""
        )

        with self.assertRaisesMessage(
            ValueError,
            "Uno de los fotogramas está vacío."
        ):

            validar_archivos_fotogramas(
                archivos
            )

    def test_archivo_demasiado_grande(self):

        archivos = self.crear_archivos()

        archivos[0] = Mock(
            size=(1024 * 1024) + 1
        )

        with self.assertRaisesMessage(
            ValueError,
            "Cada fotograma debe pesar como máximo 1 MB."
        ):

            validar_archivos_fotogramas(
                archivos
            )

    def test_tamano_total_excedido(self):

        archivos = [
            Mock(size=1024 * 1024)
            for _ in range(16)
        ]

        with self.assertRaisesMessage(
            ValueError,
            "La secuencia facial supera "
            "el tamaño máximo permitido."
        ):

            validar_archivos_fotogramas(
                archivos
            )

    def test_tamano_total_maximo_permitido(self):

        archivos = [
            Mock(size=1024 * 1024)
            for _ in range(15)
        ]

        validar_archivos_fotogramas(
            archivos
        )

    def test_prueba_vida_superada_izquierda(self):

        resultado, llamadas = self.ejecutar_validacion(
            self.secuencia
        )

        self.assertTrue(
            resultado["superada"]
        )

        self.assertTrue(
            resultado["identidad_verificada"]
        )

        self.assertEqual(
            resultado["codigo"],
            "PRUEBA_VIDA_SUPERADA"
        )

        self.assertEqual(llamadas, 5)

    def test_prueba_vida_superada_derecha(self):

        secuencia = [
            self.frente,
            self.parpadeo,
            self.frente,
            self.derecha,
            self.frente,
        ]

        resultado, llamadas = self.ejecutar_validacion(
            secuencia,
            direccion="DERECHA_IMAGEN"
        )

        self.assertTrue(
            resultado["superada"]
        )

        self.assertEqual(llamadas, 5)

    def test_rostro_incorrecto_primer_fotograma(self):

        resultado, llamadas = self.ejecutar_validacion([
            {"coincidencia": False}
        ])

        self.assertFalse(
            resultado["superada"]
        )

        self.assertFalse(
            resultado["identidad_verificada"]
        )

        self.assertEqual(
            resultado["codigo"],
            "ROSTRO_NO_COINCIDE"
        )

        self.assertEqual(llamadas, 1)

    def test_cambio_persona_durante_secuencia(self):

        secuencia = [
            self.frente,
            self.parpadeo,
            {"coincidencia": False},
            self.izquierda,
            self.frente,
        ]

        resultado, llamadas = self.ejecutar_validacion(
            secuencia
        )

        self.assertFalse(
            resultado["superada"]
        )

        self.assertFalse(
            resultado["identidad_verificada"]
        )

        self.assertEqual(llamadas, 3)

    def test_rostro_incorrecto_ultimo_fotograma(self):

        secuencia = self.secuencia.copy()

        secuencia[4] = {
            "coincidencia": False
        }

        resultado, llamadas = self.ejecutar_validacion(
            secuencia
        )

        self.assertFalse(
            resultado["superada"]
        )

        self.assertFalse(
            resultado["identidad_verificada"]
        )

        self.assertEqual(llamadas, 5)

    def test_identidad_correcta_sin_movimientos(self):

        resultado, llamadas = self.ejecutar_validacion(
            [self.frente] * 5
        )

        self.assertFalse(
            resultado["superada"]
        )

        self.assertTrue(
            resultado["identidad_verificada"]
        )

        self.assertEqual(
            resultado["codigo"],
            "SECUENCIA_INCOMPLETA"
        )

    def test_identidad_correcta_giro_incorrecto(self):

        secuencia = [
            self.frente,
            self.parpadeo,
            self.frente,
            self.derecha,
            self.frente,
        ]

        resultado, llamadas = self.ejecutar_validacion(
            secuencia
        )

        self.assertFalse(
            resultado["superada"]
        )

        self.assertTrue(
            resultado["identidad_verificada"]
        )

    def test_direccion_invalida(self):

        with self.assertRaises(ValueError):

            validar_prueba_vida_con_identidad(
                self.registro,
                self.archivos,
                "INVALIDA"
            )

    @patch(
        "usuarios.servicios_validacion_vida."
        "obtener_vector_facial"
    )
    def test_registro_facial_no_disponible(
        self,
        obtener_vector
    ):

        obtener_vector.side_effect = ValueError(
            "Registro facial no disponible."
        )

        with self.assertRaisesMessage(
            ValueError,
            "Registro facial no disponible."
        ):

            validar_prueba_vida_con_identidad(
                self.registro,
                self.archivos,
                "IZQUIERDA_IMAGEN"
            )

    @patch(
        "usuarios.servicios_validacion_vida."
        "procesar_imagen_facial"
    )
    @patch(
        "usuarios.servicios_validacion_vida."
        "obtener_vector_facial"
    )
    def test_imagen_invalida(
        self,
        obtener_vector,
        procesar_imagen
    ):

        obtener_vector.return_value = self.vector

        procesar_imagen.side_effect = ValueError(
            "Imagen facial no válida."
        )

        with self.assertRaisesMessage(
            ValueError,
            "Imagen facial no válida."
        ):

            validar_prueba_vida_con_identidad(
                self.registro,
                self.archivos,
                "IZQUIERDA_IMAGEN"
            )

    @patch(
        "usuarios.servicios_validacion_vida."
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

            analizar_fotograma_con_identidad(
                self.imagen,
                self.vector
            )

    @patch(
        "usuarios.servicios_validacion_vida."
        "face_recognition.face_locations"
    )
    def test_fotograma_varios_rostros(
        self,
        detector
    ):

        detector.return_value = [
            (10, 50, 50, 10),
            (20, 90, 80, 60),
        ]

        with self.assertRaisesMessage(
            ValueError,
            "Debe aparecer solamente un rostro."
        ):

            analizar_fotograma_con_identidad(
                self.imagen,
                self.vector
            )

    @patch(
        "usuarios.servicios_validacion_vida."
        "face_recognition.face_encodings"
    )
    @patch(
        "usuarios.servicios_validacion_vida."
        "face_recognition.face_locations"
    )
    def test_fotograma_sin_vector(
        self,
        detector,
        codificador
    ):

        detector.return_value = [
            (10, 50, 50, 10)
        ]

        codificador.return_value = []

        with self.assertRaisesMessage(
            ValueError,
            "No fue posible verificar el rostro."
        ):

            analizar_fotograma_con_identidad(
                self.imagen,
                self.vector
            )

    def test_fotograma_identidad_correcta(self):

        ruta = "usuarios.servicios_validacion_vida."

        with patch(
            ruta + "face_recognition.face_locations",
            return_value=[(10, 50, 50, 10)]
        ), patch(
            ruta + "face_recognition.face_encodings",
            return_value=[self.vector]
        ), patch(
            ruta + "face_recognition.face_landmarks",
            return_value=[{}]
        ), patch(
            ruta + "analizar_puntos_faciales",
            return_value={
                "estado_ojos": "ABIERTOS",
                "estado_cabeza": "FRENTE",
            }
        ):

            resultado = analizar_fotograma_con_identidad(
                self.imagen,
                self.vector
            )

        self.assertTrue(
            resultado["coincidencia"]
        )

        self.assertEqual(
            resultado["estado_ojos"],
            "ABIERTOS"
        )

    def test_fotograma_identidad_incorrecta(self):

        ruta = "usuarios.servicios_validacion_vida."

        with patch(
            ruta + "face_recognition.face_locations",
            return_value=[(10, 50, 50, 10)]
        ), patch(
            ruta + "face_recognition.face_encodings",
            return_value=[np.ones(128)]
        ), patch(
            ruta + "face_recognition.face_landmarks"
        ) as landmarks:

            resultado = analizar_fotograma_con_identidad(
                self.imagen,
                self.vector
            )

        self.assertFalse(
            resultado["coincidencia"]
        )

        landmarks.assert_not_called()

    def test_fotograma_sin_puntos_faciales(self):

        ruta = "usuarios.servicios_validacion_vida."

        with patch(
            ruta + "face_recognition.face_locations",
            return_value=[(10, 50, 50, 10)]
        ), patch(
            ruta + "face_recognition.face_encodings",
            return_value=[self.vector]
        ), patch(
            ruta + "face_recognition.face_landmarks",
            return_value=[]
        ):

            with self.assertRaisesMessage(
                ValueError,
                "No fue posible analizar "
                "los movimientos faciales."
            ):

                analizar_fotograma_con_identidad(
                    self.imagen,
                    self.vector
                )

    def test_resultado_no_expone_datos_biometricos(self):

        resultado, llamadas = self.ejecutar_validacion(
            self.secuencia
        )

        for campo in [
            "vector",
            "distancia",
            "imagen",
            "fotogramas",
            "datos_biometricos_cifrados",
        ]:

            self.assertNotIn(
                campo,
                resultado
            )
