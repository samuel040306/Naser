#!/usr/bin/env python3

import math
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Tuple


@dataclass(frozen=True)
class ConfiguracionSegmentador:
    duracion_trama_ms: int
    tramas_voz_consecutivas_inicio: int
    pre_audio_ms: int
    silencio_final_ms: int
    duracion_minima_voz_segundos: float
    duracion_maxima_intervencion_segundos: float

    def __post_init__(self) -> None:
        if self.duracion_trama_ms <= 0:
            raise ValueError(
                "La duración de cada trama debe ser mayor que cero."
            )

        if self.tramas_voz_consecutivas_inicio <= 0:
            raise ValueError(
                "Las tramas requeridas para iniciar deben ser mayores que cero."
            )

        if self.pre_audio_ms < 0:
            raise ValueError("El preaudio no puede ser negativo.")

        if self.silencio_final_ms <= 0:
            raise ValueError(
                "El silencio final debe ser mayor que cero."
            )

        if self.duracion_minima_voz_segundos < 0:
            raise ValueError(
                "La duración mínima de voz no puede ser negativa."
            )

        if self.duracion_maxima_intervencion_segundos <= 0:
            raise ValueError(
                "La duración máxima debe ser mayor que cero."
            )

    @property
    def tramas_pre_audio(self) -> int:
        return max(
            1,
            math.ceil(
                self.pre_audio_ms / self.duracion_trama_ms
            ),
        )

    @property
    def tramas_silencio_final(self) -> int:
        return max(
            1,
            math.ceil(
                self.silencio_final_ms / self.duracion_trama_ms
            ),
        )

    @property
    def tramas_maximas(self) -> int:
        return max(
            1,
            math.ceil(
                self.duracion_maxima_intervencion_segundos
                * 1000
                / self.duracion_trama_ms
            ),
        )

    @property
    def tramas_minimas_voz(self) -> int:
        return max(
            1,
            math.ceil(
                self.duracion_minima_voz_segundos
                * 1000
                / self.duracion_trama_ms
            ),
        )


@dataclass(frozen=True)
class ResultadoSegmentacion:
    pcm: bytes
    motivo_finalizacion: str
    numero_tramas: int
    numero_tramas_voz: int
    duracion_total_segundos: float
    duracion_voz_segundos: float
    descartada: bool


class SegmentadorIntervenciones:
    """
    Máquina de estados para delimitar intervenciones de voz.

    Estados:
        ESPERANDO_VOZ
        CAPTURANDO

    El preaudio conserva algunas tramas anteriores al inicio detectado
    para no cortar la primera sílaba de la intervención.
    """

    def __init__(
        self,
        configuracion: ConfiguracionSegmentador,
    ):
        self.configuracion = configuracion

        self._pre_audio: Deque[Tuple[bytes, bool]] = deque(
            maxlen=configuracion.tramas_pre_audio
        )

        self._capturando = False
        self._tramas_voz_consecutivas = 0
        self._tramas_silencio = 0
        self._numero_tramas_voz = 0
        self._buffer: List[bytes] = []

    @property
    def capturando(self) -> bool:
        return self._capturando

    def reiniciar(self) -> None:
        self._pre_audio.clear()
        self._capturando = False
        self._tramas_voz_consecutivas = 0
        self._tramas_silencio = 0
        self._numero_tramas_voz = 0
        self._buffer = []

    def _crear_resultado(
        self,
        motivo_finalizacion: str,
    ) -> ResultadoSegmentacion:
        numero_tramas = len(self._buffer)

        duracion_total = (
            numero_tramas
            * self.configuracion.duracion_trama_ms
            / 1000.0
        )

        duracion_voz = (
            self._numero_tramas_voz
            * self.configuracion.duracion_trama_ms
            / 1000.0
        )

        descartada = (
            self._numero_tramas_voz
            < self.configuracion.tramas_minimas_voz
        )

        resultado = ResultadoSegmentacion(
            pcm=b"".join(self._buffer),
            motivo_finalizacion=motivo_finalizacion,
            numero_tramas=numero_tramas,
            numero_tramas_voz=self._numero_tramas_voz,
            duracion_total_segundos=duracion_total,
            duracion_voz_segundos=duracion_voz,
            descartada=descartada,
        )

        self.reiniciar()
        return resultado

    def procesar_trama(
        self,
        trama: bytes,
        es_voz: bool,
    ) -> Optional[ResultadoSegmentacion]:
        if not trama:
            raise ValueError("La trama de audio está vacía.")

        if not self._capturando:
            self._pre_audio.append((trama, es_voz))

            if es_voz:
                self._tramas_voz_consecutivas += 1
            else:
                self._tramas_voz_consecutivas = 0

            if (
                self._tramas_voz_consecutivas
                >= self.configuracion.tramas_voz_consecutivas_inicio
            ):
                self._capturando = True

                self._buffer = [
                    trama_previa
                    for trama_previa, _ in self._pre_audio
                ]

                self._numero_tramas_voz = sum(
                    1
                    for _, era_voz in self._pre_audio
                    if era_voz
                )

                self._tramas_silencio = 0
                self._pre_audio.clear()

            return None

        self._buffer.append(trama)

        if es_voz:
            self._numero_tramas_voz += 1
            self._tramas_silencio = 0
        else:
            self._tramas_silencio += 1

        if (
            self._tramas_silencio
            >= self.configuracion.tramas_silencio_final
        ):
            return self._crear_resultado("silencio_final")

        if (
            len(self._buffer)
            >= self.configuracion.tramas_maximas
        ):
            return self._crear_resultado("duracion_maxima")

        return None

    def finalizar_pendiente(
        self,
    ) -> Optional[ResultadoSegmentacion]:
        if not self._capturando or not self._buffer:
            self.reiniciar()
            return None

        return self._crear_resultado("cierre_manual")
