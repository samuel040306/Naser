#!/usr/bin/env python3

import argparse
from pathlib import Path

from stt.motor_whisper_cpp import (
    ConfiguracionWhisperCpp,
    MotorWhisperCpp,
)


DIRECTORIO_SCRIPTS = Path(__file__).resolve().parent
DIRECTORIO_INTERACCION = DIRECTORIO_SCRIPTS.parent

RUTA_CONFIGURACION = (
    DIRECTORIO_SCRIPTS
    / "configuracion"
    / "stt_whisper_cpp.json"
)


def buscar_ultimo_wav() -> Path:
    directorio = (
        DIRECTORIO_SCRIPTS
        / "recursos"
        / "capturas_locales"
    )

    archivos = sorted(
        directorio.glob("*.wav"),
        key=lambda ruta: ruta.stat().st_mtime,
        reverse=True,
    )

    if not archivos:
        raise FileNotFoundError(
            f"No hay archivos WAV en {directorio}"
        )

    return archivos[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba local del motor STT basado en whisper.cpp."
        )
    )

    parser.add_argument(
        "--audio",
        type=Path,
        default=None,
        help=(
            "Archivo WAV. Si se omite, se utiliza "
            "la captura más reciente."
        ),
    )

    args = parser.parse_args()

    ruta_audio = (
        args.audio.resolve()
        if args.audio
        else buscar_ultimo_wav()
    )

    configuracion = (
        ConfiguracionWhisperCpp.desde_json(
            RUTA_CONFIGURACION
        )
    )

    motor = MotorWhisperCpp(
        configuracion=configuracion,
        directorio_interaccion=(
            DIRECTORIO_INTERACCION
        ),
    )

    print("\nPRUEBA DE WHISPER.CPP")
    print("=" * 72)
    print(f"Audio:   {ruta_audio}")
    print(f"Modelo:  {motor.ruta_modelo}")
    print(
        "Hilos:   "
        f"{configuracion.resolver_hilos()}"
    )
    print("=" * 72)

    resultado = motor.transcribir(
        ruta_audio
    )

    print("\nRESULTADO")
    print("=" * 72)
    print(
        f"Texto:               {resultado.texto}"
    )
    print(
        "Duración del audio:  "
        f"{resultado.duracion_audio_segundos:.2f} s"
    )
    print(
        "Tiempo de STT:       "
        f"{resultado.tiempo_transcripcion_segundos:.2f} s"
    )
    print(
        "Factor tiempo real:  "
        f"{resultado.factor_tiempo_real:.2f}x"
    )
    print("=" * 72)


if __name__ == "__main__":
    main()
