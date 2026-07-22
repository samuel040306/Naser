#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


DIRECTORIO_PRUEBAS = Path(__file__).resolve().parent
DIRECTORIO_SCRIPTS = DIRECTORIO_PRUEBAS.parent

if str(DIRECTORIO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIRECTORIO_SCRIPTS))


from stt.motor_whisper_cpp import (
    ConfiguracionWhisperCpp,
    limpiar_transcripcion,
)


class PruebasWhisperCpp(unittest.TestCase):
    def test_limpia_espacios_y_saltos(self):
        texto = "  Hola,\n  robot.   Buenos días.  "

        self.assertEqual(
            limpiar_transcripcion(texto),
            "Hola, robot. Buenos días.",
        )

    def test_elimina_marcas_entre_corchetes(self):
        texto = "[Música] Hola robot [Ruido]"

        self.assertEqual(
            limpiar_transcripcion(texto),
            "Hola robot",
        )

    def test_resuelve_hilos_automaticos(self):
        configuracion = ConfiguracionWhisperCpp(
            motor="whisper.cpp",
            idioma="es",
            ruta_ejecutable="whisper-cli",
            ruta_modelo="modelo.bin",
            hilos=0,
            maximo_hilos=8,
            timeout_segundos=30,
            temperatura=0.0,
            conservar_temporales=False,
            prompt_inicial=None,
        )

        with patch(
            "stt.motor_whisper_cpp.os.cpu_count",
            return_value=12,
        ):
            self.assertEqual(
                configuracion.resolver_hilos(),
                8,
            )

    def test_respeta_hilos_configurados(self):
        configuracion = ConfiguracionWhisperCpp(
            motor="whisper.cpp",
            idioma="es",
            ruta_ejecutable="whisper-cli",
            ruta_modelo="modelo.bin",
            hilos=4,
            maximo_hilos=8,
            timeout_segundos=30,
            temperatura=0.0,
            conservar_temporales=False,
            prompt_inicial=None,
        )

        self.assertEqual(
            configuracion.resolver_hilos(),
            4,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
