#!/usr/bin/env python3

import sys
import tempfile
import unittest
import wave
from pathlib import Path


DIRECTORIO_PRUEBAS = Path(__file__).resolve().parent
DIRECTORIO_SCRIPTS = DIRECTORIO_PRUEBAS.parent

if str(DIRECTORIO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIRECTORIO_SCRIPTS))


from audio.capturador_local_vad import (
    ConfiguracionAudioLocal,
    guardar_pcm_como_wav,
)
from audio.segmentador_intervenciones import (
    ConfiguracionSegmentador,
    SegmentadorIntervenciones,
)


class PruebasSegmentador(unittest.TestCase):
    def crear_segmentador(
        self,
        duracion_minima_voz=0.06,
        duracion_maxima=2.0,
    ):
        configuracion = ConfiguracionSegmentador(
            duracion_trama_ms=30,
            tramas_voz_consecutivas_inicio=2,
            pre_audio_ms=60,
            silencio_final_ms=90,
            duracion_minima_voz_segundos=(
                duracion_minima_voz
            ),
            duracion_maxima_intervencion_segundos=(
                duracion_maxima
            ),
        )

        return SegmentadorIntervenciones(
            configuracion
        )

    def test_detecta_inicio_y_silencio_final(self):
        segmentador = self.crear_segmentador()
        trama = b"\x00\x00" * 480

        for _ in range(3):
            self.assertIsNone(
                segmentador.procesar_trama(
                    trama,
                    False,
                )
            )

        for _ in range(4):
            resultado = segmentador.procesar_trama(
                trama,
                True,
            )

            self.assertIsNone(resultado)

        resultado = None

        for _ in range(3):
            resultado = segmentador.procesar_trama(
                trama,
                False,
            )

        self.assertIsNotNone(resultado)
        self.assertFalse(resultado.descartada)
        self.assertEqual(
            resultado.motivo_finalizacion,
            "silencio_final",
        )
        self.assertGreater(
            resultado.duracion_voz_segundos,
            0,
        )

    def test_descarta_intervencion_demasiado_corta(self):
        segmentador = self.crear_segmentador(
            duracion_minima_voz=0.15
        )

        trama = b"\x00\x00" * 480

        segmentador.procesar_trama(
            trama,
            True,
        )

        segmentador.procesar_trama(
            trama,
            True,
        )

        resultado = None

        for _ in range(3):
            resultado = segmentador.procesar_trama(
                trama,
                False,
            )

        self.assertIsNotNone(resultado)
        self.assertTrue(resultado.descartada)

    def test_finaliza_por_duracion_maxima(self):
        segmentador = self.crear_segmentador(
            duracion_minima_voz=0.03,
            duracion_maxima=0.18,
        )

        trama = b"\x00\x00" * 480
        resultado = None

        for _ in range(20):
            resultado = segmentador.procesar_trama(
                trama,
                True,
            )

            if resultado is not None:
                break

        self.assertIsNotNone(resultado)
        self.assertEqual(
            resultado.motivo_finalizacion,
            "duracion_maxima",
        )


class PruebasConfiguracionAudio(unittest.TestCase):
    def test_configuracion_json(self):
        ruta = (
            DIRECTORIO_SCRIPTS
            / "configuracion"
            / "audio_local.json"
        )

        configuracion = (
            ConfiguracionAudioLocal.desde_json(ruta)
        )

        self.assertEqual(
            configuracion.frecuencia_muestreo,
            16000,
        )

        self.assertEqual(
            configuracion.bytes_por_trama,
            960,
        )

        self.assertEqual(
            configuracion.muestras_por_trama,
            480,
        )

    def test_escritura_wav_pcm16(self):
        frecuencia = 16000
        pcm = b"\x00\x00" * frecuencia

        with tempfile.TemporaryDirectory() as temporal:
            ruta = Path(temporal) / "prueba.wav"

            guardar_pcm_como_wav(
                ruta=ruta,
                pcm=pcm,
                frecuencia_muestreo=frecuencia,
                canales=1,
                ancho_muestra_bytes=2,
            )

            with wave.open(str(ruta), "rb") as archivo:
                self.assertEqual(
                    archivo.getnchannels(),
                    1,
                )

                self.assertEqual(
                    archivo.getsampwidth(),
                    2,
                )

                self.assertEqual(
                    archivo.getframerate(),
                    16000,
                )

                self.assertEqual(
                    archivo.getnframes(),
                    frecuencia,
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
