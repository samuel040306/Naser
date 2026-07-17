#!/usr/bin/env python3

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from agente_banderas.normalizador_texto import (
    contiene_frase,
    contar_palabras,
    normalizar_texto,
)
from agente_banderas.validador_configuracion import (
    cargar_json,
    validar_configuracion,
)


@dataclass(frozen=True)
class DeteccionIntencion:
    identificador: str
    bandera_original: str
    bandera_normalizada: str
    prioridad: int
    numero_palabras: int
    longitud: int


@dataclass
class ResultadoInteraccion:
    texto_original: str
    texto_normalizado: str
    intencion: str
    bandera_activadora: Optional[str]
    respuesta: str
    archivo_audio: str
    clave_pose: str
    archivo_pose: Optional[str]
    ejecutar_pose: bool
    permitida_en_fisico: bool
    modo_ejecucion: str
    desfase_pose_segundos: float
    es_fallback: bool
    detecciones: List[DeteccionIntencion] = field(default_factory=list)


class MotorIntenciones:
    def __init__(
        self,
        ruta_intenciones: Path,
        ruta_catalogo: Path,
        semilla: Optional[int] = None,
    ):
        self.ruta_intenciones = Path(ruta_intenciones)
        self.ruta_catalogo = Path(ruta_catalogo)
        self.aleatorio = random.Random(semilla)

        validacion = validar_configuracion(
            self.ruta_intenciones,
            self.ruta_catalogo,
        )

        if not validacion.es_valida:
            detalle = "\n".join(
                f"- {error}"
                for error in validacion.errores
            )
            raise ValueError(
                "La configuración del motor contiene errores:\n"
                f"{detalle}"
            )

        self.advertencias_configuracion = validacion.advertencias
        self.configuracion = cargar_json(self.ruta_intenciones)
        self.catalogo = cargar_json(self.ruta_catalogo)

        self.intenciones = [
            intencion
            for intencion in self.configuracion["intenciones"]
            if intencion.get("habilitada", False)
        ]

        self.fallback = self.configuracion["fallback"]
        self.poses = self.catalogo["poses"]

    def detectar(
        self,
        texto: str,
    ) -> List[DeteccionIntencion]:
        texto_normalizado = normalizar_texto(texto)
        detecciones: List[DeteccionIntencion] = []

        for intencion in self.intenciones:
            identificador = intencion["id"]
            prioridad = int(intencion["prioridad"])

            for bandera in intencion["palabras_bandera"]:
                bandera_normalizada = normalizar_texto(bandera)

                if contiene_frase(
                    texto_normalizado,
                    bandera_normalizada,
                ):
                    detecciones.append(
                        DeteccionIntencion(
                            identificador=identificador,
                            bandera_original=bandera,
                            bandera_normalizada=bandera_normalizada,
                            prioridad=prioridad,
                            numero_palabras=contar_palabras(
                                bandera_normalizada
                            ),
                            longitud=len(bandera_normalizada),
                        )
                    )

        detecciones.sort(
            key=lambda deteccion: (
                deteccion.prioridad,
                deteccion.numero_palabras,
                deteccion.longitud,
            ),
            reverse=True,
        )

        return detecciones

    def _buscar_intencion(
        self,
        identificador: str,
    ) -> Dict[str, Any]:
        for intencion in self.intenciones:
            if intencion["id"] == identificador:
                return intencion

        raise KeyError(
            f"No existe una intención habilitada llamada "
            f"'{identificador}'."
        )

    def _seleccionar_respuesta(
        self,
        bloque: Dict[str, Any],
    ) -> Dict[str, str]:
        respuestas = bloque["respuestas"]
        return self.aleatorio.choice(respuestas)

    def _seleccionar_pose(
        self,
        bloque: Dict[str, Any],
    ) -> str:
        poses_candidatas = bloque["poses_candidatas"]
        return self.aleatorio.choice(poses_candidatas)

    def _resolver_archivo_pose(
        self,
        clave_pose: str,
    ) -> Optional[str]:
        informacion_pose = self.poses.get(clave_pose)

        if informacion_pose is None:
            raise KeyError(
                f"La pose '{clave_pose}' no está registrada."
            )

        return informacion_pose.get("archivo")

    def resolver(
        self,
        texto: str,
    ) -> ResultadoInteraccion:
        texto_normalizado = normalizar_texto(texto)
        detecciones = self.detectar(texto)

        if detecciones:
            deteccion_principal = detecciones[0]
            bloque = self._buscar_intencion(
                deteccion_principal.identificador
            )
            es_fallback = False
            bandera_activadora = deteccion_principal.bandera_original
        else:
            bloque = self.fallback
            es_fallback = True
            bandera_activadora = None

        respuesta = self._seleccionar_respuesta(bloque)
        clave_pose = self._seleccionar_pose(bloque)
        archivo_pose = self._resolver_archivo_pose(clave_pose)

        ejecutar_pose = bool(bloque.get("ejecutar_pose", False))

        if clave_pose == "sin_pose":
            ejecutar_pose = False

        informacion_pose = self.poses[clave_pose]

        permitida_en_fisico = bool(
            bloque.get("permitida_en_fisico", False)
            and informacion_pose.get("permitida_en_fisico", False)
        )

        return ResultadoInteraccion(
            texto_original=texto,
            texto_normalizado=texto_normalizado,
            intencion=bloque["id"],
            bandera_activadora=bandera_activadora,
            respuesta=respuesta["texto"],
            archivo_audio=respuesta["archivo_audio"],
            clave_pose=clave_pose,
            archivo_pose=archivo_pose,
            ejecutar_pose=ejecutar_pose,
            permitida_en_fisico=permitida_en_fisico,
            modo_ejecucion=bloque["modo_ejecucion"],
            desfase_pose_segundos=float(
                bloque.get("desfase_pose_segundos", 0.0)
            ),
            es_fallback=es_fallback,
            detecciones=detecciones,
        )
