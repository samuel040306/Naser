#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


DIRECTORIO_PRUEBAS = Path(__file__).resolve().parent
DIRECTORIO_SCRIPTS = DIRECTORIO_PRUEBAS.parent

if str(DIRECTORIO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIRECTORIO_SCRIPTS))


from agente_banderas.motor_intenciones import MotorIntenciones
from agente_banderas.normalizador_texto import (
    contiene_frase,
    normalizar_texto,
)


class PruebasMotorIntenciones(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        directorio_configuracion = (
            DIRECTORIO_SCRIPTS / "configuracion"
        )

        cls.motor = MotorIntenciones(
            ruta_intenciones=(
                directorio_configuracion / "intenciones_es.json"
            ),
            ruta_catalogo=(
                directorio_configuracion / "catalogo_poses_es.json"
            ),
            semilla=40,
        )

    def test_normalizacion(self):
        self.assertEqual(
            normalizar_texto("¡Buenos DÍAS, Robot!"),
            "buenos dias robot",
        )

    def test_limites_de_palabra(self):
        self.assertTrue(
            contiene_frase("robot detente", "detente")
        )
        self.assertFalse(
            contiene_frase("el asfalto esta seco", "alto")
        )

    def test_siu_especifico_supera_pose_general(self):
        resultado = self.motor.resolver(
            "Robot, ¿puedes hacer una pose de siu?"
        )

        self.assertEqual(resultado.intencion, "siu")
        self.assertEqual(resultado.clave_pose, "siu")
        self.assertEqual(resultado.archivo_pose, "12_siu.json")

    def test_boxeo_especifico_supera_pose_general(self):
        resultado = self.motor.resolver(
            "Puedes hacer una pose de boxeo"
        )

        self.assertEqual(resultado.intencion, "boxeo")
        self.assertEqual(resultado.clave_pose, "boxeo")

    def test_pose_general_selecciona_pose_recreativa(self):
        resultado = self.motor.resolver(
            "Robot, puedes hacer una pose"
        )

        self.assertEqual(resultado.intencion, "pose_aleatoria")
        self.assertIn(
            resultado.clave_pose,
            {"boxeo", "dab", "fuerza", "siu"},
        )

    def test_saludo(self):
        resultado = self.motor.resolver(
            "Hola robot, buenos días"
        )

        self.assertEqual(resultado.intencion, "saludo")
        self.assertIn(
            resultado.clave_pose,
            {"saludo_derecha", "saludo_arriba_derecha"},
        )

    def test_agradecimiento(self):
        resultado = self.motor.resolver(
            "Muchas gracias por tu ayuda"
        )

        self.assertEqual(
            resultado.intencion,
            "agradecimiento",
        )

    def test_navegacion_desactivada_no_mueve_pose(self):
        resultado = self.motor.resolver(
            "Robot, acompáñame hasta la salida"
        )

        self.assertEqual(
            resultado.intencion,
            "acompanar_no_disponible",
        )
        self.assertFalse(resultado.ejecutar_pose)
        self.assertEqual(resultado.clave_pose, "sin_pose")

    def test_fallback_ejecuta_confusion(self):
        resultado = self.motor.resolver(
            "La ecuación diferencial necesita otra condición"
        )

        self.assertTrue(resultado.es_fallback)
        self.assertEqual(resultado.intencion, "no_entendido")
        self.assertEqual(resultado.clave_pose, "confusion")
        self.assertEqual(
            resultado.archivo_pose,
            "11_confusion.json",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
