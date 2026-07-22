#!/usr/bin/env python3

import argparse
from pathlib import Path

from agente_banderas.motor_intenciones import (
    MotorIntenciones,
)
from audio.capturador_local_vad import (
    CapturadorLocalVAD,
    ConfiguracionAudioLocal,
    resolver_dispositivo,
)
from stt.motor_whisper_cpp import (
    ConfiguracionWhisperCpp,
    MotorWhisperCpp,
)


DIRECTORIO_SCRIPTS = Path(__file__).resolve().parent
DIRECTORIO_INTERACCION = DIRECTORIO_SCRIPTS.parent

DIRECTORIO_CONFIGURACION = (
    DIRECTORIO_SCRIPTS / "configuracion"
)

DIRECTORIO_CAPTURAS = (
    DIRECTORIO_SCRIPTS
    / "recursos"
    / "capturas_locales"
)


def imprimir_resultado(
    numero: int,
    captura,
    stt,
    interaccion,
) -> None:
    print("\n" + "=" * 78)
    print(f"INTERACCIÓN LOCAL #{numero}")
    print("=" * 78)
    print(f"Audio:               {captura.ruta_wav.name}")
    print(f"Texto reconocido:    {stt.texto}")
    print(
        f"Tiempo STT:          "
        f"{stt.tiempo_transcripcion_segundos:.2f} s"
    )
    print(f"Intención:           {interaccion.intencion}")
    print(
        f"Bandera activadora:  "
        f"{interaccion.bandera_activadora}"
    )
    print(f"Respuesta:           {interaccion.respuesta}")
    print(
        f"Audio de respuesta:  "
        f"{interaccion.archivo_audio}"
    )
    print(f"Pose:                {interaccion.clave_pose}")
    print(
        f"Archivo de pose:     "
        f"{interaccion.archivo_pose}"
    )
    print(
        f"Ejecutar pose:       "
        f"{interaccion.ejecutar_pose}"
    )
    print(
        f"Desfase de pose:     "
        f"{interaccion.desfase_pose_segundos:.2f} s"
    )
    print(
        "Acción física:       "
        "SIMULADA. No se envían comandos al robot."
    )
    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Agente local continuo: micrófono, VAD, "
            "whisper.cpp e intenciones."
        )
    )

    parser.add_argument(
        "--dispositivo",
        default=None,
        help="Índice o nombre del micrófono.",
    )

    parser.add_argument(
        "--max-intervenciones",
        type=int,
        default=0,
        help=(
            "Número máximo de interacciones. "
            "Cero significa ejecución continua."
        ),
    )

    args = parser.parse_args()

    if args.max_intervenciones < 0:
        raise SystemExit(
            "--max-intervenciones no puede ser negativo."
        )

    configuracion_audio = (
        ConfiguracionAudioLocal.desde_json(
            DIRECTORIO_CONFIGURACION
            / "audio_local.json"
        )
    )

    configuracion_stt = (
        ConfiguracionWhisperCpp.desde_json(
            DIRECTORIO_CONFIGURACION
            / "stt_whisper_cpp.json"
        )
    )

    motor_stt = MotorWhisperCpp(
        configuracion=configuracion_stt,
        directorio_interaccion=(
            DIRECTORIO_INTERACCION
        ),
    )

    motor_intenciones = MotorIntenciones(
        ruta_intenciones=(
            DIRECTORIO_CONFIGURACION
            / "intenciones_es.json"
        ),
        ruta_catalogo=(
            DIRECTORIO_CONFIGURACION
            / "catalogo_poses_es.json"
        ),
    )

    capturador = CapturadorLocalVAD(
        configuracion=configuracion_audio,
        directorio_salida=DIRECTORIO_CAPTURAS,
        dispositivo=resolver_dispositivo(
            args.dispositivo
        ),
    )

    print("\nAGENTE LOCAL STT + PALABRAS BANDERA")
    print("=" * 78)
    print("Este modo no controla el robot físico.")
    print("Las poses únicamente se imprimen en terminal.")
    print("Presiona Ctrl+C para finalizar.")
    print("=" * 78)

    numero_interacciones = 0

    try:
        for captura in capturador.escuchar():
            print("\n[STT] Transcribiendo intervención...")

            try:
                resultado_stt = motor_stt.transcribir(
                    captura.ruta_wav
                )
            except Exception as error:
                print(
                    f"[ERROR][STT] {error}"
                )
                eliminados = (
                    capturador.descartar_audio_pendiente()
                )
                print(
                    "[AUDIO] Fragmentos pendientes "
                    f"eliminados: {eliminados}"
                )
                continue

            if not resultado_stt.texto:
                print(
                    "[ADVERTENCIA] El STT retornó texto vacío."
                )
                eliminados = (
                    capturador.descartar_audio_pendiente()
                )
                print(
                    "[AUDIO] Fragmentos pendientes "
                    f"eliminados: {eliminados}"
                )
                continue

            resultado_interaccion = (
                motor_intenciones.resolver(
                    resultado_stt.texto
                )
            )

            numero_interacciones += 1

            imprimir_resultado(
                numero=numero_interacciones,
                captura=captura,
                stt=resultado_stt,
                interaccion=resultado_interaccion,
            )

            eliminados = (
                capturador.descartar_audio_pendiente()
            )

            print(
                "[AUDIO] Fragmentos acumulados durante "
                f"el procesamiento eliminados: {eliminados}"
            )

            print(
                "\n[ESCUCHA] Reactivando escucha..."
            )

            if (
                args.max_intervenciones > 0
                and numero_interacciones
                >= args.max_intervenciones
            ):
                capturador.detener()
                break

    except KeyboardInterrupt:
        print(
            "\n[INFORMACIÓN] Ctrl+C detectado. "
            "Cerrando agente."
        )
        capturador.detener()

    print(
        "[INFORMACIÓN] Interacciones completadas: "
        f"{numero_interacciones}"
    )


if __name__ == "__main__":
    main()
