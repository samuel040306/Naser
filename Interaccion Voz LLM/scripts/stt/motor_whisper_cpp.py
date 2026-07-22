#!/usr/bin/env python3

import json
import os
import re
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass(frozen=True)
class ConfiguracionWhisperCpp:
    motor: str
    idioma: str
    ruta_ejecutable: str
    ruta_modelo: str
    hilos: int
    maximo_hilos: int
    timeout_segundos: float
    temperatura: float
    contexto_audio: int
    beam_size: int
    best_of: int
    sin_fallback: bool
    usar_gpu: bool
    conservar_temporales: bool
    prompt_inicial: Optional[str]

    @classmethod
    def desde_json(
        cls,
        ruta: Path,
    ) -> "ConfiguracionWhisperCpp":
        ruta = Path(ruta)

        if not ruta.is_file():
            raise FileNotFoundError(
                f"No existe la configuración STT: {ruta}"
            )

        with ruta.open("r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)

        if not isinstance(contenido, dict):
            raise ValueError(
                "La configuración STT debe ser un objeto JSON."
            )

        configuracion = cls(**contenido)
        configuracion.validar()

        return configuracion

    def validar(self) -> None:
        if self.motor != "whisper.cpp":
            raise ValueError(
                "El campo 'motor' debe ser 'whisper.cpp'."
            )

        if not self.idioma:
            raise ValueError(
                "El idioma del STT no puede estar vacío."
            )

        if self.hilos < 0:
            raise ValueError(
                "El número de hilos no puede ser negativo."
            )

        if self.maximo_hilos <= 0:
            raise ValueError(
                "'maximo_hilos' debe ser mayor que cero."
            )

        if self.timeout_segundos <= 0:
            raise ValueError(
                "El timeout debe ser mayor que cero."
            )

        if self.temperatura < 0:
            raise ValueError(
                "La temperatura no puede ser negativa."
            )

        if self.contexto_audio < 0:
            raise ValueError(
                "El contexto de audio no puede ser negativo."
            )

        if self.beam_size <= 0:
            raise ValueError(
                "El beam size debe ser mayor que cero."
            )

        if self.best_of <= 0:
            raise ValueError(
                "Best-of debe ser mayor que cero."
            )

    def resolver_hilos(self) -> int:
        if self.hilos > 0:
            return self.hilos

        disponibles = os.cpu_count() or 1

        return max(
            1,
            min(disponibles, self.maximo_hilos),
        )


@dataclass(frozen=True)
class ResultadoSTT:
    texto: str
    ruta_audio: Path
    duracion_audio_segundos: float
    tiempo_transcripcion_segundos: float
    factor_tiempo_real: float
    codigo_retorno: int
    comando: List[str]


def limpiar_transcripcion(texto: str) -> str:
    """
    Limpia espacios, saltos de línea y marcas residuales.
    """
    if not isinstance(texto, str):
        raise TypeError(
            "La transcripción debe ser una cadena."
        )

    texto = texto.replace("\ufeff", " ")
    texto = re.sub(r"\[[^\]]+\]", " ", texto)
    texto = re.sub(r"\s+", " ", texto)

    return texto.strip()


def obtener_duracion_wav(ruta: Path) -> float:
    ruta = Path(ruta)

    with wave.open(str(ruta), "rb") as archivo:
        frecuencia = archivo.getframerate()
        tramas = archivo.getnframes()

    if frecuencia <= 0:
        raise ValueError(
            f"Frecuencia inválida en el WAV: {ruta}"
        )

    return tramas / frecuencia


class MotorWhisperCpp:
    def __init__(
        self,
        configuracion: ConfiguracionWhisperCpp,
        directorio_interaccion: Path,
    ):
        self.configuracion = configuracion
        self.directorio_interaccion = Path(
            directorio_interaccion
        ).resolve()

        self.ruta_ejecutable = (
            self.directorio_interaccion
            / self.configuracion.ruta_ejecutable
        ).resolve()

        self.ruta_modelo = (
            self.directorio_interaccion
            / self.configuracion.ruta_modelo
        ).resolve()

        self._validar_archivos()

    def _validar_archivos(self) -> None:
        if not self.ruta_ejecutable.is_file():
            raise FileNotFoundError(
                f"No existe whisper-cli: {self.ruta_ejecutable}"
            )

        if not os.access(self.ruta_ejecutable, os.X_OK):
            raise PermissionError(
                f"whisper-cli no es ejecutable: "
                f"{self.ruta_ejecutable}"
            )

        if not self.ruta_modelo.is_file():
            raise FileNotFoundError(
                f"No existe el modelo: {self.ruta_modelo}"
            )

        if self.ruta_modelo.stat().st_size <= 0:
            raise ValueError(
                f"El modelo está vacío: {self.ruta_modelo}"
            )

    def construir_comando(
        self,
        ruta_audio: Path,
        base_salida: Path,
    ) -> List[str]:
        comando = [
            str(self.ruta_ejecutable),
            "-m",
            str(self.ruta_modelo),
            "-f",
            str(Path(ruta_audio).resolve()),
            "-l",
            self.configuracion.idioma,
            "-t",
            str(self.configuracion.resolver_hilos()),
            "-otxt",
            "-of",
            str(base_salida),
            "-nt",
            "-np",
            "-bs",
            str(self.configuracion.beam_size),
            "-bo",
            str(self.configuracion.best_of),
        ]

        if self.configuracion.prompt_inicial:
            comando.extend(
                [
                    "--prompt",
                    self.configuracion.prompt_inicial,
                ]
            )

        if self.configuracion.sin_fallback:
            comando.append("-nf")

        if self.configuracion.contexto_audio > 0:
            comando.extend(
                [
                    "-ac",
                    str(self.configuracion.contexto_audio),
                ]
            )

        if not self.configuracion.usar_gpu:
            comando.append("-ng")

        return comando

    def transcribir(
        self,
        ruta_audio: Path,
    ) -> ResultadoSTT:
        ruta_audio = Path(ruta_audio).resolve()

        if not ruta_audio.is_file():
            raise FileNotFoundError(
                f"No existe el WAV: {ruta_audio}"
            )

        duracion_audio = obtener_duracion_wav(
            ruta_audio
        )

        with tempfile.TemporaryDirectory(
            prefix="nasser_stt_"
        ) as directorio_temporal:
            directorio_temporal = Path(
                directorio_temporal
            )

            base_salida = (
                directorio_temporal
                / "transcripcion"
            )

            ruta_txt = Path(
                f"{base_salida}.txt"
            )

            comando = self.construir_comando(
                ruta_audio=ruta_audio,
                base_salida=base_salida,
            )

            inicio = time.perf_counter()

            try:
                proceso = subprocess.run(
                    comando,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=self.configuracion.timeout_segundos,
                    check=False,
                )
            except subprocess.TimeoutExpired as error:
                raise TimeoutError(
                    "whisper.cpp superó el tiempo máximo de "
                    f"{self.configuracion.timeout_segundos:.1f} s."
                ) from error

            tiempo_transcripcion = (
                time.perf_counter() - inicio
            )

            if proceso.returncode != 0:
                detalle = (
                    proceso.stderr.strip()
                    or proceso.stdout.strip()
                    or "Sin información adicional."
                )

                raise RuntimeError(
                    "whisper.cpp terminó con código "
                    f"{proceso.returncode}:\n{detalle[-2000:]}"
                )

            if not ruta_txt.is_file():
                raise RuntimeError(
                    "whisper.cpp terminó sin crear el archivo "
                    f"de transcripción esperado: {ruta_txt}"
                )

            texto = limpiar_transcripcion(
                ruta_txt.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            )

            if (
                self.configuracion.conservar_temporales
            ):
                destino = (
                    ruta_audio.parent
                    / f"{ruta_audio.stem}_transcripcion.txt"
                )

                destino.write_text(
                    texto + "\n",
                    encoding="utf-8",
                )

            factor_tiempo_real = (
                tiempo_transcripcion
                / max(duracion_audio, 1e-6)
            )

            return ResultadoSTT(
                texto=texto,
                ruta_audio=ruta_audio,
                duracion_audio_segundos=duracion_audio,
                tiempo_transcripcion_segundos=(
                    tiempo_transcripcion
                ),
                factor_tiempo_real=factor_tiempo_real,
                codigo_retorno=proceso.returncode,
                comando=comando,
            )
