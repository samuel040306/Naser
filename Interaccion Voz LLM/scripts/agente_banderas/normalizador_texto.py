#!/usr/bin/env python3

import re
import unicodedata
from typing import Dict


REEMPLAZOS_CANONICOS: Dict[str, str] = {
    "g uno": "g1",
    "ge uno": "g1",
    "gee uno": "g1",
    "si u": "siu",
    "si uu": "siu",
    "siuuu": "siu",
    "highfive": "high five",
}


def eliminar_tildes(texto: str) -> str:
    """
    Convierte caracteres acentuados a su representación base.

    Ejemplos:
        cómo -> como
        adiós -> adios
        qué -> que
    """
    descompuesto = unicodedata.normalize("NFD", texto)

    return "".join(
        caracter
        for caracter in descompuesto
        if unicodedata.category(caracter) != "Mn"
    )


def normalizar_texto(texto: str) -> str:
    """
    Normaliza texto para realizar comparaciones deterministas.

    La salida:
    - queda en minúsculas;
    - no contiene tildes;
    - conserva letras y números;
    - no contiene puntuación;
    - no contiene espacios repetidos.
    """
    if not isinstance(texto, str):
        raise TypeError("El texto que se desea normalizar debe ser una cadena.")

    texto_normalizado = eliminar_tildes(texto.lower().strip())

    # Sustituir cualquier carácter que no sea letra o número por un espacio.
    texto_normalizado = re.sub(
        r"[^a-z0-9]+",
        " ",
        texto_normalizado,
    )

    texto_normalizado = " ".join(texto_normalizado.split())

    # Aplicar sustituciones sobre frases completas.
    for variante, forma_canonica in REEMPLAZOS_CANONICOS.items():
        patron = (
            r"(?<![a-z0-9])"
            + re.escape(variante)
            + r"(?![a-z0-9])"
        )

        texto_normalizado = re.sub(
            patron,
            forma_canonica,
            texto_normalizado,
        )

    return " ".join(texto_normalizado.split())


def contiene_frase(
    texto_normalizado: str,
    frase_normalizada: str,
) -> bool:
    """
    Verifica una coincidencia por palabras o frases completas.

    Evita falsos positivos como:
        alto dentro de asfalto
        siu dentro de residuos
    """
    if not texto_normalizado or not frase_normalizada:
        return False

    patron = (
        r"(?<![a-z0-9])"
        + re.escape(frase_normalizada)
        + r"(?![a-z0-9])"
    )

    return re.search(patron, texto_normalizado) is not None


def contar_palabras(texto_normalizado: str) -> int:
    if not texto_normalizado:
        return 0

    return len(texto_normalizado.split())
