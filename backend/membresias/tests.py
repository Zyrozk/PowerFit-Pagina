from datetime import date
from django.test import SimpleTestCase
from .models import sumar_mes, Membresia

class ReglasMembresiasTests(SimpleTestCase):
    def test_precios(self):
        self.assertEqual(Membresia.PRECIOS, {'PLAN_1': 30000, 'PLAN_2': 45000, 'PLAN_3': 65000})

    def test_cupos(self):
        self.assertEqual(Membresia.CUPOS, {'PLAN_1': 10, 'PLAN_2': 15, 'PLAN_3': 24})

    def test_mes_siguiente(self):
        self.assertEqual(sumar_mes(date(2026, 10, 27)), date(2026, 11, 27))

    def test_fin_de_mes(self):
        self.assertEqual(sumar_mes(date(2027, 1, 31)), date(2027, 2, 28))
