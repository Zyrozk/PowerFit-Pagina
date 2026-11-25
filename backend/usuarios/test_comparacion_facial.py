
import os
from pathlib import Path
from unittest import skipUnless

from django.test import SimpleTestCase

from .servicios_faciales import (
    generar_vector_facial,
    comparar_vectores_faciales,
)


@skipUnless(
    all(
        os.environ.get(variable)
        for variable in (
            "POWERFIT_IMAGEN_PRUEBA",
            "POWERFIT_IMAGEN_PRUEBA_2",
            "POWERFIT_IMAGEN_PRUEBA_3",
        )
    ),
    "Las fotografías de prueba no están configuradas."
)
class PruebasComparacionFacial(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.vector_1 = cls.cargar_vector(
            "POWERFIT_IMAGEN_PRUEBA"
        )

        cls.vector_2 = cls.cargar_vector(
            "POWERFIT_IMAGEN_PRUEBA_2"
        )

        cls.vector_3 = cls.cargar_vector(
            "POWERFIT_IMAGEN_PRUEBA_3"
        )

    @staticmethod
    def cargar_vector(variable):
        ruta = Path(os.environ[variable])

        if not ruta.is_file():
            raise FileNotFoundError(
                f"No se encontró la fotografía: {ruta}"
            )

        with ruta.open("rb") as imagen:
            return generar_vector_facial(imagen)

    def mostrar_resultado(self, nombre, resultado):
        print("\n")
        print("=" * 50)
        print(nombre)
        print("=" * 50)
        print(
            "Coincidencia facial:",
            resultado["coincidencia"]
        )
        print(
            "Distancia facial:",
            round(resultado["distancia"], 6)
        )
        print(
            "Tolerancia:",
            resultado["tolerancia"]
        )

    def test_01_misma_fotografia(self):
        resultado = comparar_vectores_faciales(
            self.vector_1,
            self.vector_1,
        )

        self.mostrar_resultado(
            "PRUEBA 1: MISMA FOTOGRAFIA",
            resultado,
        )

        self.assertTrue(
            resultado["coincidencia"],
            resultado,
        )

    def test_02_misma_persona_fotografias_diferentes(self):
        resultado = comparar_vectores_faciales(
            self.vector_1,
            self.vector_2,
        )

        self.mostrar_resultado(
            "PRUEBA 2: MISMA PERSONA",
            resultado,
        )

        self.assertTrue(
            resultado["coincidencia"],
            resultado,
        )

    def test_03_personas_diferentes(self):
        resultado = comparar_vectores_faciales(
            self.vector_1,
            self.vector_3,
        )

        self.mostrar_resultado(
            "PRUEBA 3: PERSONAS DIFERENTES",
            resultado,
        )

        self.assertFalse(
            resultado["coincidencia"],
            resultado,
        )

    def test_04_segunda_fotografia_persona_diferente(self):
        resultado = comparar_vectores_faciales(
            self.vector_2,
            self.vector_3,
        )

        self.mostrar_resultado(
            "PRUEBA 4: SEGUNDA FOTO Y PERSONA DIFERENTE",
            resultado,
        )

        self.assertFalse(
            resultado["coincidencia"],
            resultado,
        )
