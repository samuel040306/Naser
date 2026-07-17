#!/usr/bin/env python3

import argparse
from pathlib import Path

from audio.capturador_local_vad import (
    CapturadorLocalVAD,
    ConfiguracionAudioLocal,
    listar_dispositivos_audio,
    resolver_dispositivo,
)


DIRECTORIO_SCRIPTS = Path(__file__).resolve().parent

RUTA_CONFIGURACION_PREDETERMINADA = (
    DIRECTORIO_SCRIPTS
    / "configuracion"
    / "audio_local.json"
)

DIRECTORIO_SALIDA_PREDETERMINADO = (
    DIRECTORIO_SCRIPTS
    / "recursos"
    / "capturas_locales"
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Captura continua de voz desde el micrófono local "
            "mediante WebRTC VAD."
        )
    )

    parser.add_argument(
        "--listar-dispositivos",
        action="store_true",
        help="Mostrar los dispositivos de entrada disponibles.",
    )

    parser.add_argument(
        "--dispositivo",
        default=None,
        help=(
            "Índice o nombre del dispositivo de entrada. "
            "Si se omite, se utiliza el predeterminado."
        ),
    )

    parser.add_argument(
        "--configuracion",
        type=Path,
        default=RUTA_CONFIGURACION_PREDETERMINADA,
        help="Ruta del archivo de configuración JSON.",
    )

    parser.add_argument(
        "--salida",
        type=Path,
        default=DIRECTORIO_SALIDA_PREDETERMINADO,
        help="Directorio donde se guardarán los WAV.",
    )

    parser.add_argument(
        "--max-intervenciones",
        type=int,
        default=0,
        help=(
            "Finalizar después de N intervenciones. "
            "Cero significa ejecución continua."
        ),
    )

    args = parser.parse_args()

    if args.listar_dispositivos:
        listar_dispositivos_audio()
        return

    if args.max_intervenciones < 0:
        raise SystemExit(
            "--max-intervenciones no puede ser negativo."
        )

    configuracion = ConfiguracionAudioLocal.desde_json(
        args.configuracion
    )

    dispositivo = resolver_dispositivo(
        args.dispositivo
    )

    capturador = CapturadorLocalVAD(
        configuracion=configuracion,
        directorio_salida=args.salida,
        dispositivo=dispositivo,
    )

    numero_capturas = 0

    try:
        for captura in capturador.escuchar():
            numero_capturas += 1

            print(
                f"[RESUMEN] Intervención #{numero_capturas}: "
                f"{captura.ruta_wav.name}"
            )

            if (
                args.max_intervenciones > 0
                and numero_capturas
                >= args.max_intervenciones
            ):
                print(
                    "[INFORMACIÓN] Se alcanzó el máximo "
                    "de intervenciones."
                )
                capturador.detener()
                break

    except KeyboardInterrupt:
        print(
            "\n[INFORMACIÓN] Ctrl+C detectado. "
            "Cerrando captura local."
        )
        capturador.detener()

    print(
        f"[INFORMACIÓN] Total de intervenciones "
        f"guardadas: {numero_capturas}"
    )


if __name__ == "__main__":
    main()
