#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List


DIRECTORIO_TOOLS = Path(__file__).resolve().parent
DIRECTORIO_SCRIPTS = DIRECTORIO_TOOLS.parent
DIRECTORIO_INTERACCION = DIRECTORIO_SCRIPTS.parent

if str(DIRECTORIO_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(DIRECTORIO_SCRIPTS))


from agente_banderas.motor_intenciones import MotorIntenciones
from agente_banderas.normalizador_texto import normalizar_texto
from stt.motor_whisper_cpp import limpiar_transcripcion


RUTA_WHISPER = (
    DIRECTORIO_INTERACCION
    / "externos"
    / "whisper.cpp"
    / "build"
    / "bin"
    / "whisper-cli"
)

DIRECTORIO_MODELOS = (
    DIRECTORIO_SCRIPTS
    / "recursos"
    / "modelos"
)

DIRECTORIO_AUDIOS = (
    DIRECTORIO_SCRIPTS
    / "recursos"
    / "benchmark_stt"
)

DIRECTORIO_LOGS = (
    DIRECTORIO_SCRIPTS
    / "logs"
)

RUTA_CONFIGURACION_BENCHMARK = (
    DIRECTORIO_SCRIPTS
    / "configuracion"
    / "benchmark_stt_es.json"
)

RUTA_INTENCIONES = (
    DIRECTORIO_SCRIPTS
    / "configuracion"
    / "intenciones_es.json"
)

RUTA_CATALOGO = (
    DIRECTORIO_SCRIPTS
    / "configuracion"
    / "catalogo_poses_es.json"
)


@dataclass(frozen=True)
class PerfilSTT:
    nombre: str
    modelo: str
    contexto_audio: int


@dataclass
class ResultadoCaso:
    perfil: str
    caso: int
    archivo: str
    texto_esperado: str
    texto_reconocido: str
    intencion_esperada: str
    intencion_detectada: str
    intencion_correcta: bool
    similitud: float
    tiempo_segundos: float
    codigo_retorno: int


def cargar_json(ruta: Path) -> Dict:
    with ruta.open("r", encoding="utf-8") as archivo:
        return json.load(archivo)


def obtener_audios(cantidad: int) -> List[Path]:
    archivos = sorted(
        DIRECTORIO_AUDIOS.glob("*.wav"),
        key=lambda ruta: ruta.stat().st_mtime,
    )

    if len(archivos) != cantidad:
        raise RuntimeError(
            f"Se esperaban {cantidad} WAV y se encontraron "
            f"{len(archivos)} en {DIRECTORIO_AUDIOS}."
        )

    return archivos


def construir_comando(
    perfil: PerfilSTT,
    audio: Path,
    prompt: str,
) -> List[str]:
    ruta_modelo = DIRECTORIO_MODELOS / perfil.modelo

    if not ruta_modelo.is_file():
        raise FileNotFoundError(
            f"No existe el modelo: {ruta_modelo}"
        )

    hilos = max(
        1,
        min(os.cpu_count() or 1, 8),
    )

    comando = [
        str(RUTA_WHISPER),
        "-m",
        str(ruta_modelo),
        "-f",
        str(audio),
        "-l",
        "es",
        "-t",
        str(hilos),
        "-nt",
        "-np",
        "-ng",
        "-bs",
        "1",
        "-bo",
        "1",
        "-nf",
        "--prompt",
        prompt,
    ]

    if perfil.contexto_audio > 0:
        comando.extend(
            [
                "-ac",
                str(perfil.contexto_audio),
            ]
        )

    return comando


def transcribir(
    perfil: PerfilSTT,
    audio: Path,
    prompt: str,
):
    comando = construir_comando(
        perfil=perfil,
        audio=audio,
        prompt=prompt,
    )

    inicio = time.perf_counter()

    proceso = subprocess.run(
        comando,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60,
        check=False,
    )

    tiempo = time.perf_counter() - inicio

    texto = limpiar_transcripcion(
        proceso.stdout
    )

    if proceso.returncode != 0:
        detalle = (
            proceso.stderr.strip()
            or proceso.stdout.strip()
        )

        raise RuntimeError(
            f"Error en perfil {perfil.nombre}: "
            f"{detalle[-1500:]}"
        )

    return texto, tiempo, proceso.returncode


def calcular_similitud(
    esperado: str,
    reconocido: str,
) -> float:
    esperado_normalizado = normalizar_texto(
        esperado
    )

    reconocido_normalizado = normalizar_texto(
        reconocido
    )

    return SequenceMatcher(
        None,
        esperado_normalizado,
        reconocido_normalizado,
    ).ratio()


def imprimir_caso(resultado: ResultadoCaso) -> None:
    estado = (
        "OK"
        if resultado.intencion_correcta
        else "FALLO"
    )

    print(
        f"  Caso {resultado.caso}: "
        f"[{estado}] "
        f"{resultado.tiempo_segundos:.2f} s"
    )

    print(
        f"    Esperado:    {resultado.texto_esperado}"
    )

    print(
        f"    Reconocido:  {resultado.texto_reconocido}"
    )

    print(
        f"    Intención:   "
        f"{resultado.intencion_detectada} "
        f"(esperada: {resultado.intencion_esperada})"
    )

    print(
        f"    Similitud:   "
        f"{resultado.similitud * 100:.1f} %"
    )


def main() -> None:
    if not RUTA_WHISPER.is_file():
        raise FileNotFoundError(
            f"No existe whisper-cli: {RUTA_WHISPER}"
        )

    configuracion = cargar_json(
        RUTA_CONFIGURACION_BENCHMARK
    )

    casos = configuracion["casos"]
    prompt = configuracion["prompt"]

    audios = obtener_audios(
        len(casos)
    )

    perfiles = [
        PerfilSTT(
            nombre="base_contexto_completo",
            modelo="ggml-base-q5_0.bin",
            contexto_audio=0,
        ),
        PerfilSTT(
            nombre="base_contexto_512",
            modelo="ggml-base-q5_0.bin",
            contexto_audio=512,
        ),
        PerfilSTT(
            nombre="small_contexto_512",
            modelo="ggml-small-q5_0.bin",
            contexto_audio=512,
        ),
    ]

    motor_intenciones = MotorIntenciones(
        ruta_intenciones=RUTA_INTENCIONES,
        ruta_catalogo=RUTA_CATALOGO,
        semilla=40,
    )

    resultados: List[ResultadoCaso] = []

    print("\nBENCHMARK LOCAL DE STT")
    print("=" * 78)
    print(f"Audios:   {len(audios)}")
    print(f"Perfiles: {len(perfiles)}")
    print(
        "Total de transcripciones: "
        f"{len(audios) * len(perfiles)}"
    )
    print("=" * 78)

    for perfil in perfiles:
        print(f"\nPERFIL: {perfil.nombre}")
        print("-" * 78)

        for caso, audio in zip(casos, audios):
            texto, tiempo, codigo = transcribir(
                perfil=perfil,
                audio=audio,
                prompt=prompt,
            )

            interaccion = motor_intenciones.resolver(
                texto
            )

            resultado = ResultadoCaso(
                perfil=perfil.nombre,
                caso=int(caso["numero"]),
                archivo=audio.name,
                texto_esperado=caso["texto_esperado"],
                texto_reconocido=texto,
                intencion_esperada=(
                    caso["intencion_esperada"]
                ),
                intencion_detectada=(
                    interaccion.intencion
                ),
                intencion_correcta=(
                    interaccion.intencion
                    == caso["intencion_esperada"]
                ),
                similitud=calcular_similitud(
                    caso["texto_esperado"],
                    texto,
                ),
                tiempo_segundos=tiempo,
                codigo_retorno=codigo,
            )

            resultados.append(resultado)
            imprimir_caso(resultado)

    print("\n" + "=" * 78)
    print("RESUMEN POR PERFIL")
    print("=" * 78)

    resumen = {}

    for perfil in perfiles:
        subset = [
            resultado
            for resultado in resultados
            if resultado.perfil == perfil.nombre
        ]

        aciertos = sum(
            resultado.intencion_correcta
            for resultado in subset
        )

        tiempo_promedio = sum(
            resultado.tiempo_segundos
            for resultado in subset
        ) / len(subset)

        tiempo_maximo = max(
            resultado.tiempo_segundos
            for resultado in subset
        )

        similitud_promedio = sum(
            resultado.similitud
            for resultado in subset
        ) / len(subset)

        resumen[perfil.nombre] = {
            "aciertos_intencion": aciertos,
            "total_casos": len(subset),
            "tiempo_promedio_segundos": (
                tiempo_promedio
            ),
            "tiempo_maximo_segundos": (
                tiempo_maximo
            ),
            "similitud_promedio": (
                similitud_promedio
            ),
        }

        print(
            f"{perfil.nombre}:"
        )

        print(
            f"  Intenciones correctas: "
            f"{aciertos}/{len(subset)}"
        )

        print(
            f"  Similitud promedio:    "
            f"{similitud_promedio * 100:.1f} %"
        )

        print(
            f"  Tiempo promedio:       "
            f"{tiempo_promedio:.2f} s"
        )

        print(
            f"  Tiempo máximo:         "
            f"{tiempo_maximo:.2f} s"
        )

    DIRECTORIO_LOGS.mkdir(
        parents=True,
        exist_ok=True,
    )

    marca = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    ruta_log = (
        DIRECTORIO_LOGS
        / f"benchmark_stt_{marca}.json"
    )

    contenido_log = {
        "fecha": datetime.now().isoformat(),
        "resultados": [
            asdict(resultado)
            for resultado in resultados
        ],
        "resumen": resumen,
    }

    ruta_log.write_text(
        json.dumps(
            contenido_log,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print("\nLog guardado en:")
    print(ruta_log)


if __name__ == "__main__":
    main()
