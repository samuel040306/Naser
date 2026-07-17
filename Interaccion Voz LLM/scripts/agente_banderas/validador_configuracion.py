#!/usr/bin/env python3

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set

from agente_banderas.normalizador_texto import normalizar_texto


MODOS_EJECUCION_VALIDOS = {
    "hablar_y_posar",
    "solo_hablar",
    "solo_pose",
}


@dataclass
class ResultadoValidacion:
    errores: List[str] = field(default_factory=list)
    advertencias: List[str] = field(default_factory=list)

    @property
    def es_valida(self) -> bool:
        return not self.errores

    def agregar_error(self, mensaje: str) -> None:
        self.errores.append(mensaje)

    def agregar_advertencia(self, mensaje: str) -> None:
        self.advertencias.append(mensaje)


def cargar_json(ruta: Path) -> Dict[str, Any]:
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo: {ruta}")

    try:
        with ruta.open("r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"JSON inválido en {ruta}: línea {error.lineno}, "
            f"columna {error.colno}: {error.msg}"
        ) from error

    if not isinstance(contenido, dict):
        raise ValueError(
            f"El contenido principal de {ruta} debe ser un objeto JSON."
        )

    return contenido


def validar_respuestas(
    respuestas: Any,
    contexto: str,
    resultado: ResultadoValidacion,
) -> None:
    if not isinstance(respuestas, list) or not respuestas:
        resultado.agregar_error(
            f"{contexto}: debe contener una lista no vacía de respuestas."
        )
        return

    for indice, respuesta in enumerate(respuestas, start=1):
        etiqueta = f"{contexto}, respuesta {indice}"

        if not isinstance(respuesta, dict):
            resultado.agregar_error(
                f"{etiqueta}: debe ser un objeto JSON."
            )
            continue

        texto = respuesta.get("texto")
        archivo_audio = respuesta.get("archivo_audio")

        if not isinstance(texto, str) or not texto.strip():
            resultado.agregar_error(
                f"{etiqueta}: el campo 'texto' está vacío o es inválido."
            )

        if (
            not isinstance(archivo_audio, str)
            or not archivo_audio.strip()
        ):
            resultado.agregar_error(
                f"{etiqueta}: 'archivo_audio' está vacío o es inválido."
            )
        elif not archivo_audio.lower().endswith(".wav"):
            resultado.agregar_error(
                f"{etiqueta}: el archivo debe terminar en .wav."
            )


def validar_poses(
    poses_candidatas: Any,
    poses_registradas: Set[str],
    contexto: str,
    resultado: ResultadoValidacion,
) -> None:
    if not isinstance(poses_candidatas, list) or not poses_candidatas:
        resultado.agregar_error(
            f"{contexto}: debe contener al menos una pose candidata."
        )
        return

    poses_vistas: Set[str] = set()

    for pose in poses_candidatas:
        if not isinstance(pose, str) or not pose.strip():
            resultado.agregar_error(
                f"{contexto}: contiene una clave de pose inválida."
            )
            continue

        if pose in poses_vistas:
            resultado.agregar_error(
                f"{contexto}: la pose '{pose}' está repetida."
            )

        poses_vistas.add(pose)

        if pose not in poses_registradas:
            resultado.agregar_error(
                f"{contexto}: la pose '{pose}' no existe en el catálogo."
            )


def validar_bloque_ejecucion(
    bloque: Dict[str, Any],
    contexto: str,
    resultado: ResultadoValidacion,
) -> None:
    prioridad = bloque.get("prioridad")

    if not isinstance(prioridad, int) or isinstance(prioridad, bool):
        resultado.agregar_error(
            f"{contexto}: 'prioridad' debe ser un número entero."
        )
    elif prioridad < 0:
        resultado.agregar_error(
            f"{contexto}: 'prioridad' no puede ser negativa."
        )

    ejecutar_pose = bloque.get("ejecutar_pose")

    if not isinstance(ejecutar_pose, bool):
        resultado.agregar_error(
            f"{contexto}: 'ejecutar_pose' debe ser true o false."
        )

    modo = bloque.get("modo_ejecucion")

    if modo not in MODOS_EJECUCION_VALIDOS:
        resultado.agregar_error(
            f"{contexto}: modo de ejecución inválido: {modo!r}."
        )

    desfase = bloque.get("desfase_pose_segundos", 0.0)

    if (
        not isinstance(desfase, (int, float))
        or isinstance(desfase, bool)
        or desfase < 0
    ):
        resultado.agregar_error(
            f"{contexto}: 'desfase_pose_segundos' debe ser "
            "un número mayor o igual a cero."
        )


def validar_configuracion(
    ruta_intenciones: Path,
    ruta_catalogo: Path,
) -> ResultadoValidacion:
    resultado = ResultadoValidacion()

    try:
        configuracion = cargar_json(ruta_intenciones)
    except Exception as error:
        resultado.agregar_error(str(error))
        return resultado

    try:
        catalogo = cargar_json(ruta_catalogo)
    except Exception as error:
        resultado.agregar_error(str(error))
        return resultado

    poses = catalogo.get("poses")

    if not isinstance(poses, dict) or not poses:
        resultado.agregar_error(
            "El catálogo debe contener un objeto no vacío llamado 'poses'."
        )
        return resultado

    poses_registradas = set(poses.keys())

    for clave_pose, informacion_pose in poses.items():
        contexto_pose = f"Pose '{clave_pose}'"

        if not isinstance(informacion_pose, dict):
            resultado.agregar_error(
                f"{contexto_pose}: su definición debe ser un objeto."
            )
            continue

        archivo = informacion_pose.get("archivo")

        if clave_pose == "sin_pose":
            if archivo is not None:
                resultado.agregar_error(
                    "'sin_pose' debe tener el campo 'archivo' en null."
                )
        elif not isinstance(archivo, str) or not archivo.endswith(".json"):
            resultado.agregar_error(
                f"{contexto_pose}: debe apuntar a un archivo .json."
            )

        if not isinstance(
            informacion_pose.get("permitida_en_fisico"),
            bool,
        ):
            resultado.agregar_error(
                f"{contexto_pose}: 'permitida_en_fisico' debe ser booleano."
            )

    intenciones = configuracion.get("intenciones")

    if not isinstance(intenciones, list) or not intenciones:
        resultado.agregar_error(
            "La configuración debe contener una lista no vacía "
            "llamada 'intenciones'."
        )
        return resultado

    identificadores_vistos: Set[str] = set()
    flags_globales: Dict[str, List[str]] = {}

    for indice, intencion in enumerate(intenciones, start=1):
        contexto = f"Intención {indice}"

        if not isinstance(intencion, dict):
            resultado.agregar_error(
                f"{contexto}: debe ser un objeto JSON."
            )
            continue

        identificador = intencion.get("id")

        if not isinstance(identificador, str) or not identificador.strip():
            resultado.agregar_error(
                f"{contexto}: el campo 'id' es obligatorio."
            )
            identificador = f"sin_id_{indice}"
        else:
            contexto = f"Intención '{identificador}'"

        if identificador in identificadores_vistos:
            resultado.agregar_error(
                f"{contexto}: identificador repetido."
            )

        identificadores_vistos.add(identificador)

        if not isinstance(intencion.get("habilitada"), bool):
            resultado.agregar_error(
                f"{contexto}: 'habilitada' debe ser true o false."
            )

        validar_bloque_ejecucion(
            intencion,
            contexto,
            resultado,
        )

        flags = intencion.get("palabras_bandera")

        if not isinstance(flags, list) or not flags:
            resultado.agregar_error(
                f"{contexto}: debe contener palabras bandera."
            )
        else:
            flags_locales: Set[str] = set()

            for flag in flags:
                if not isinstance(flag, str) or not flag.strip():
                    resultado.agregar_error(
                        f"{contexto}: contiene una palabra bandera vacía."
                    )
                    continue

                flag_normalizada = normalizar_texto(flag)

                if not flag_normalizada:
                    resultado.agregar_error(
                        f"{contexto}: la bandera {flag!r} queda vacía "
                        "después de normalizarla."
                    )
                    continue

                if flag_normalizada in flags_locales:
                    resultado.agregar_error(
                        f"{contexto}: bandera duplicada después de "
                        f"normalizar: {flag!r}."
                    )

                flags_locales.add(flag_normalizada)
                flags_globales.setdefault(
                    flag_normalizada,
                    [],
                ).append(identificador)

        validar_respuestas(
            intencion.get("respuestas"),
            contexto,
            resultado,
        )

        validar_poses(
            intencion.get("poses_candidatas"),
            poses_registradas,
            contexto,
            resultado,
        )

        if (
            intencion.get("ejecutar_pose") is False
            and intencion.get("poses_candidatas") != ["sin_pose"]
        ):
            resultado.agregar_advertencia(
                f"{contexto}: no ejecuta pose, pero sus poses candidatas "
                "no son exclusivamente 'sin_pose'."
            )

    for flag, identificadores in sorted(flags_globales.items()):
        identificadores_unicos = sorted(set(identificadores))

        if len(identificadores_unicos) > 1:
            resultado.agregar_advertencia(
                f"La bandera normalizada '{flag}' aparece en varias "
                f"intenciones: {', '.join(identificadores_unicos)}. "
                "La prioridad decidirá cuál gana."
            )

    fallback = configuracion.get("fallback")

    if not isinstance(fallback, dict):
        resultado.agregar_error(
            "La configuración debe contener un objeto 'fallback'."
        )
        return resultado

    identificador_fallback = fallback.get("id")

    if not isinstance(identificador_fallback, str) or not identificador_fallback:
        resultado.agregar_error(
            "El fallback debe contener un identificador válido."
        )

    validar_bloque_ejecucion(
        fallback,
        "Fallback",
        resultado,
    )

    validar_respuestas(
        fallback.get("respuestas"),
        "Fallback",
        resultado,
    )

    validar_poses(
        fallback.get("poses_candidatas"),
        poses_registradas,
        "Fallback",
        resultado,
    )

    configuracion_general = configuracion.get(
        "configuracion_general",
        {},
    )

    fallback_declarado = configuracion_general.get(
        "intencion_fallback",
    )

    if fallback_declarado != identificador_fallback:
        resultado.agregar_error(
            "La intención fallback declarada en 'configuracion_general' "
            "no coincide con el objeto 'fallback'."
        )

    return resultado
