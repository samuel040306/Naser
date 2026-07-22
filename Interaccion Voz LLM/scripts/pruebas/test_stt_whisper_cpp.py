#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


DIRECTORIO_PRUEBAS = Path(__file__).resolve().parent
DIRECTORIO_SCRIPTS = DIRECTORIO_PRUEBAS.parent

if str(DIRECTORIO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIRECTORIO_SCRIPTS))


from stt.motor_whisper_cpp import (
    ConfiguracionWhisperCpp,
    MotorWhisperCpp,
    limpiar_transcripcion,
)


def crear_configuracion(**cambios):
    valores = {
        "motor": "whisper.cpp",
        "idioma": "es",
        "ruta_ejecutable": "whisper-cli",
        "ruta_modelo": "modelo.bin",
        "hilos": 0,
        "maximo_hilos": 8,
        "timeout_segundos": 30,
        "temperatura": 0.0,
        "contexto_audio": 0,
        "beam_size": 1,
        "best_of": 1,
        "sin_fallback": True,
        "usar_gpu": True,
        "conservar_temporales": False,
        "prompt_inicial": "Robot G1. Pose de siu. Dab.",
    }

    valores.update(cambios)

    return ConfiguracionWhisperCpp(**valores)


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
        configuracion = crear_configuracion()

        with patch(
            "stt.motor_whisper_cpp.os.cpu_count",
            return_value=12,
        ):
            self.assertEqual(
                configuracion.resolver_hilos(),
                8,
            )

    def test_respeta_hilos_configurados(self):
        configuracion = crear_configuracion(
            hilos=4
        )

        self.assertEqual(
            configuracion.resolver_hilos(),
            4,
        )

    def test_comando_optimizado_con_gpu_permitida(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)

            ejecutable = raiz / "whisper-cli"
            ejecutable.write_text(
                "#!/bin/sh\nexit 0\n",
                encoding="utf-8",
            )
            ejecutable.chmod(0o755)

            modelo = raiz / "modelo.bin"
            modelo.write_bytes(b"modelo")

            configuracion = crear_configuracion(
                usar_gpu=True,
                contexto_audio=0,
            )

            motor = MotorWhisperCpp(
                configuracion=configuracion,
                directorio_interaccion=raiz,
            )

            comando = motor.construir_comando(
                ruta_audio=raiz / "audio.wav",
                base_salida=raiz / "salida",
            )

            self.assertIn("-bs", comando)
            self.assertIn("-bo", comando)
            self.assertIn("-nf", comando)
            self.assertIn("-np", comando)
            self.assertNotIn("-ng", comando)
            self.assertNotIn("-ac", comando)

    def test_comando_permite_cpu_y_contexto_reducido(self):
        with tempfile.TemporaryDirectory() as temporal:
            raiz = Path(temporal)

            ejecutable = raiz / "whisper-cli"
            ejecutable.write_text(
                "#!/bin/sh\nexit 0\n",
                encoding="utf-8",
            )
            ejecutable.chmod(0o755)

            modelo = raiz / "modelo.bin"
            modelo.write_bytes(b"modelo")

            configuracion = crear_configuracion(
                usar_gpu=False,
                contexto_audio=512,
            )

            motor = MotorWhisperCpp(
                configuracion=configuracion,
                directorio_interaccion=raiz,
            )

            comando = motor.construir_comando(
                ruta_audio=raiz / "audio.wav",
                base_salida=raiz / "salida",
            )

            self.assertIn("-ng", comando)
            self.assertIn("-ac", comando)

            indice = comando.index("-ac")

            self.assertEqual(
                comando[indice + 1],
                "512",
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
