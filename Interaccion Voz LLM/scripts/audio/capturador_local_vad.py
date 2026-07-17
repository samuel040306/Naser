#!/usr/bin/env python3

import audioop
import json
import queue
import statistics
import threading
import wave
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional, Union

import sounddevice as sd
import webrtcvad

from audio.segmentador_intervenciones import (
    ConfiguracionSegmentador,
    SegmentadorIntervenciones,
)


DispositivoAudio = Optional[Union[int, str]]


@dataclass(frozen=True)
class ConfiguracionAudioLocal:
    frecuencia_muestreo: int
    canales: int
    ancho_muestra_bytes: int
    duracion_trama_ms: int
    modo_vad: int
    duracion_calibracion_segundos: float
    multiplicador_ruido: float
    umbral_rms_minimo: int
    tramas_voz_consecutivas_inicio: int
    pre_audio_ms: int
    silencio_final_ms: int
    duracion_minima_voz_segundos: float
    duracion_maxima_intervencion_segundos: float
    tamano_cola_audio: int

    def __post_init__(self) -> None:
        if self.frecuencia_muestreo not in {
            8000,
            16000,
            32000,
            48000,
        }:
            raise ValueError(
                "WebRTC VAD requiere una frecuencia de "
                "8000, 16000, 32000 o 48000 Hz."
            )

        if self.canales != 1:
            raise ValueError(
                "La captura para WebRTC VAD debe ser mono."
            )

        if self.ancho_muestra_bytes != 2:
            raise ValueError(
                "La captura debe utilizar PCM de 16 bits."
            )

        if self.duracion_trama_ms not in {10, 20, 30}:
            raise ValueError(
                "WebRTC VAD solo admite tramas de 10, 20 o 30 ms."
            )

        if self.modo_vad not in {0, 1, 2, 3}:
            raise ValueError(
                "El modo VAD debe estar entre 0 y 3."
            )

        if self.duracion_calibracion_segundos <= 0:
            raise ValueError(
                "La calibración debe durar más de cero segundos."
            )

        if self.multiplicador_ruido <= 0:
            raise ValueError(
                "El multiplicador de ruido debe ser positivo."
            )

        if self.umbral_rms_minimo < 0:
            raise ValueError(
                "El umbral RMS mínimo no puede ser negativo."
            )

        if self.tamano_cola_audio <= 0:
            raise ValueError(
                "El tamaño de la cola debe ser mayor que cero."
            )

    @property
    def muestras_por_trama(self) -> int:
        return int(
            self.frecuencia_muestreo
            * self.duracion_trama_ms
            / 1000
        )

    @property
    def bytes_por_trama(self) -> int:
        return (
            self.muestras_por_trama
            * self.canales
            * self.ancho_muestra_bytes
        )

    @property
    def configuracion_segmentador(
        self,
    ) -> ConfiguracionSegmentador:
        return ConfiguracionSegmentador(
            duracion_trama_ms=self.duracion_trama_ms,
            tramas_voz_consecutivas_inicio=(
                self.tramas_voz_consecutivas_inicio
            ),
            pre_audio_ms=self.pre_audio_ms,
            silencio_final_ms=self.silencio_final_ms,
            duracion_minima_voz_segundos=(
                self.duracion_minima_voz_segundos
            ),
            duracion_maxima_intervencion_segundos=(
                self.duracion_maxima_intervencion_segundos
            ),
        )

    @classmethod
    def desde_json(
        cls,
        ruta: Path,
    ) -> "ConfiguracionAudioLocal":
        ruta = Path(ruta)

        if not ruta.is_file():
            raise FileNotFoundError(
                f"No existe la configuración de audio: {ruta}"
            )

        with ruta.open("r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)

        if not isinstance(contenido, dict):
            raise ValueError(
                "La configuración de audio debe ser un objeto JSON."
            )

        return cls(**contenido)


@dataclass(frozen=True)
class CapturaAudio:
    ruta_wav: Path
    motivo_finalizacion: str
    duracion_total_segundos: float
    duracion_voz_segundos: float
    umbral_rms: int
    fragmentos_descartados_cola: int


def resolver_dispositivo(
    valor: Optional[str],
) -> DispositivoAudio:
    if valor is None or valor.strip() == "":
        return None

    valor = valor.strip()

    try:
        return int(valor)
    except ValueError:
        return valor


def listar_dispositivos_audio() -> None:
    dispositivos = sd.query_devices()
    dispositivo_predeterminado = sd.default.device

    try:
        indice_entrada_predeterminado = int(
            dispositivo_predeterminado[0]
        )
    except Exception:
        indice_entrada_predeterminado = None

    print("\nDISPOSITIVOS DE ENTRADA DISPONIBLES")
    print("=" * 78)

    encontrados = 0

    for indice, dispositivo in enumerate(dispositivos):
        canales_entrada = int(
            dispositivo.get("max_input_channels", 0)
        )

        if canales_entrada <= 0:
            continue

        encontrados += 1

        marca = (
            " [PREDETERMINADO]"
            if indice == indice_entrada_predeterminado
            else ""
        )

        print(
            f"{indice:02d}. {dispositivo['name']}{marca}\n"
            f"    Canales de entrada: {canales_entrada}\n"
            f"    Frecuencia predeterminada: "
            f"{dispositivo['default_samplerate']:.0f} Hz"
        )

    if encontrados == 0:
        print("No se encontraron dispositivos de entrada.")

    print("=" * 78)


def guardar_pcm_como_wav(
    ruta: Path,
    pcm: bytes,
    frecuencia_muestreo: int,
    canales: int,
    ancho_muestra_bytes: int,
) -> None:
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)

    if not pcm:
        raise ValueError(
            "No se puede guardar un WAV con audio vacío."
        )

    tamano_bloque = canales * ancho_muestra_bytes

    if len(pcm) % tamano_bloque != 0:
        raise ValueError(
            "El número de bytes PCM no coincide con "
            "el formato de audio."
        )

    with wave.open(str(ruta), "wb") as archivo_wav:
        archivo_wav.setnchannels(canales)
        archivo_wav.setsampwidth(ancho_muestra_bytes)
        archivo_wav.setframerate(frecuencia_muestreo)
        archivo_wav.writeframes(pcm)


class CapturadorLocalVAD:
    def __init__(
        self,
        configuracion: ConfiguracionAudioLocal,
        directorio_salida: Path,
        dispositivo: DispositivoAudio = None,
    ):
        self.configuracion = configuracion
        self.directorio_salida = Path(directorio_salida)
        self.dispositivo = dispositivo

        self.vad = webrtcvad.Vad(
            self.configuracion.modo_vad
        )

        self._evento_detencion = threading.Event()
        self._cola_audio: queue.Queue = queue.Queue(
            maxsize=self.configuracion.tamano_cola_audio
        )

        self._buffer_entrada = bytearray()
        self._fragmentos_descartados_cola = 0
        self._estado_stream_pendiente = None

    def detener(self) -> None:
        self._evento_detencion.set()

    def _callback_audio(
        self,
        datos_entrada,
        numero_tramas,
        informacion_tiempo,
        estado,
    ) -> None:
        del numero_tramas
        del informacion_tiempo

        if estado:
            self._estado_stream_pendiente = str(estado)

        try:
            self._cola_audio.put_nowait(bytes(datos_entrada))
        except queue.Full:
            self._fragmentos_descartados_cola += 1

    def _leer_trama(
        self,
        timeout: float = 1.0,
    ) -> bytes:
        bytes_necesarios = self.configuracion.bytes_por_trama

        while len(self._buffer_entrada) < bytes_necesarios:
            fragmento = self._cola_audio.get(
                timeout=timeout
            )

            self._buffer_entrada.extend(fragmento)

        trama = bytes(
            self._buffer_entrada[:bytes_necesarios]
        )

        del self._buffer_entrada[:bytes_necesarios]

        return trama

    def _calibrar_umbral_rms(self) -> int:
        numero_tramas = max(
            1,
            round(
                self.configuracion.duracion_calibracion_segundos
                * 1000
                / self.configuracion.duracion_trama_ms
            ),
        )

        print(
            "\n[CALIBRACIÓN] Permanece en silencio durante "
            f"{self.configuracion.duracion_calibracion_segundos:.1f} "
            "segundos..."
        )

        valores_rms = []

        for _ in range(numero_tramas):
            trama = self._leer_trama(timeout=2.0)

            rms = audioop.rms(
                trama,
                self.configuracion.ancho_muestra_bytes,
            )

            valores_rms.append(rms)

        rms_ambiente = int(
            statistics.median(valores_rms)
        )

        umbral_calculado = int(
            rms_ambiente
            * self.configuracion.multiplicador_ruido
        )

        umbral_final = max(
            self.configuracion.umbral_rms_minimo,
            umbral_calculado,
        )

        print(
            f"[CALIBRACIÓN] RMS ambiente: {rms_ambiente}"
        )
        print(
            f"[CALIBRACIÓN] Umbral RMS utilizado: "
            f"{umbral_final}"
        )

        return umbral_final

    def _clasificar_trama(
        self,
        trama: bytes,
        umbral_rms: int,
    ):
        rms = audioop.rms(
            trama,
            self.configuracion.ancho_muestra_bytes,
        )

        decision_vad = self.vad.is_speech(
            trama,
            self.configuracion.frecuencia_muestreo,
        )

        es_voz = bool(
            decision_vad
            and rms >= umbral_rms
        )

        return es_voz, rms, decision_vad

    def _crear_ruta_captura(self) -> Path:
        marca_tiempo = datetime.now().strftime(
            "%Y%m%d_%H%M%S_%f"
        )[:-3]

        return (
            self.directorio_salida
            / f"intervencion_{marca_tiempo}.wav"
        )

    def escuchar(
        self,
    ) -> Generator[CapturaAudio, None, None]:
        self._evento_detencion.clear()
        self._fragmentos_descartados_cola = 0
        self._buffer_entrada.clear()

        self.directorio_salida.mkdir(
            parents=True,
            exist_ok=True,
        )

        sd.check_input_settings(
            device=self.dispositivo,
            channels=self.configuracion.canales,
            dtype="int16",
            samplerate=self.configuracion.frecuencia_muestreo,
        )

        segmentador = SegmentadorIntervenciones(
            self.configuracion.configuracion_segmentador
        )

        print("\n[INFORMACIÓN] Abriendo micrófono local.")
        print(
            f"[INFORMACIÓN] Dispositivo: "
            f"{self.dispositivo if self.dispositivo is not None else 'predeterminado'}"
        )
        print(
            f"[INFORMACIÓN] Formato: "
            f"{self.configuracion.frecuencia_muestreo} Hz, "
            "mono, PCM16"
        )

        with sd.RawInputStream(
            samplerate=self.configuracion.frecuencia_muestreo,
            blocksize=self.configuracion.muestras_por_trama,
            device=self.dispositivo,
            channels=self.configuracion.canales,
            dtype="int16",
            callback=self._callback_audio,
        ):
            umbral_rms = self._calibrar_umbral_rms()

            print("\n[ESCUCHA] Sistema listo.")
            print(
                "[ESCUCHA] Habla normalmente. "
                "Presiona Ctrl+C para cerrar.\n"
            )

            while not self._evento_detencion.is_set():
                try:
                    trama = self._leer_trama(timeout=1.5)
                except queue.Empty:
                    print(
                        "[ADVERTENCIA] No se están recibiendo "
                        "datos del micrófono."
                    )
                    continue

                if self._estado_stream_pendiente:
                    print(
                        "[ADVERTENCIA][AUDIO] "
                        f"{self._estado_stream_pendiente}"
                    )
                    self._estado_stream_pendiente = None

                es_voz, rms, decision_vad = (
                    self._clasificar_trama(
                        trama,
                        umbral_rms,
                    )
                )

                del rms
                del decision_vad

                estaba_capturando = segmentador.capturando

                resultado = segmentador.procesar_trama(
                    trama,
                    es_voz,
                )

                if (
                    not estaba_capturando
                    and segmentador.capturando
                ):
                    print(
                        "[VOZ] Inicio de intervención detectado."
                    )

                if resultado is None:
                    continue

                if resultado.descartada:
                    print(
                        "[DESCARTADA] Fragmento demasiado corto: "
                        f"{resultado.duracion_voz_segundos:.2f} s "
                        "de voz."
                    )
                    continue

                ruta_wav = self._crear_ruta_captura()

                guardar_pcm_como_wav(
                    ruta=ruta_wav,
                    pcm=resultado.pcm,
                    frecuencia_muestreo=(
                        self.configuracion.frecuencia_muestreo
                    ),
                    canales=self.configuracion.canales,
                    ancho_muestra_bytes=(
                        self.configuracion.ancho_muestra_bytes
                    ),
                )

                print(
                    "[GUARDADO] Intervención completada."
                )
                print(
                    f"           Archivo: {ruta_wav}"
                )
                print(
                    f"           Duración total: "
                    f"{resultado.duracion_total_segundos:.2f} s"
                )
                print(
                    f"           Voz detectada: "
                    f"{resultado.duracion_voz_segundos:.2f} s"
                )
                print(
                    f"           Motivo de cierre: "
                    f"{resultado.motivo_finalizacion}"
                )
                print("\n[ESCUCHA] Esperando nueva intervención.")

                yield CapturaAudio(
                    ruta_wav=ruta_wav,
                    motivo_finalizacion=(
                        resultado.motivo_finalizacion
                    ),
                    duracion_total_segundos=(
                        resultado.duracion_total_segundos
                    ),
                    duracion_voz_segundos=(
                        resultado.duracion_voz_segundos
                    ),
                    umbral_rms=umbral_rms,
                    fragmentos_descartados_cola=(
                        self._fragmentos_descartados_cola
                    ),
                )

        print("[INFORMACIÓN] Micrófono cerrado.")
