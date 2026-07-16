#!/usr/bin/env python3

import json
from pathlib import Path
from typing import List, Tuple


DIRECTORIO_SCRIPTS = Path(__file__).resolve().parents[1]
DIRECTORIO_CONFIGURACION = DIRECTORIO_SCRIPTS / "configuracion"

RUTA_CATALOGO = DIRECTORIO_CONFIGURACION / "catalogo_poses_es.json"
RUTA_INTENCIONES = DIRECTORIO_CONFIGURACION / "intenciones_es.json"


def crear_intencion(
    identificador: str,
    prioridad: int,
    palabras_bandera: List[str],
    respuestas: List[Tuple[str, str]],
    poses_candidatas: List[str],
    ejecutar_pose: bool = True,
    modo_ejecucion: str = "hablar_y_posar",
    desfase_pose_segundos: float = 0.8,
):
    return {
        "id": identificador,
        "habilitada": True,
        "prioridad": prioridad,
        "palabras_bandera": palabras_bandera,
        "respuestas": [
            {
                "texto": texto,
                "archivo_audio": archivo_audio,
            }
            for texto, archivo_audio in respuestas
        ],
        "poses_candidatas": poses_candidatas,
        "ejecutar_pose": ejecutar_pose,
        "permitida_en_fisico": True,
        "modo_ejecucion": modo_ejecucion,
        "desfase_pose_segundos": desfase_pose_segundos,
    }


catalogo_poses = {
    "version_esquema": 1,
    "descripcion": (
        "Catálogo de poses permitidas para la interacción por palabras "
        "bandera del Unitree G1 23 DoF."
    ),
    "poses": {
        "sin_pose": {
            "archivo": None,
            "descripcion": "No ejecutar movimiento físico.",
            "permitida_en_fisico": True,
        },
        "pose_segura": {
            "archivo": "0_pose_segura.json",
            "descripcion": "Pose segura de referencia.",
            "permitida_en_fisico": True,
        },
        "saludo_derecha": {
            "archivo": "1_saludo_derecha.json",
            "descripcion": "Saludo con el brazo derecho.",
            "permitida_en_fisico": True,
        },
        "saludo_formal": {
            "archivo": "2_saludo_formal.json",
            "descripcion": "Saludo formal.",
            "permitida_en_fisico": True,
        },
        "saludo_izquierda": {
            "archivo": "3_saludo_izq.json",
            "descripcion": "Saludo con el brazo izquierdo.",
            "permitida_en_fisico": True,
        },
        "boxeo": {
            "archivo": "4_boxeo.json",
            "descripcion": "Demostración de boxeo.",
            "permitida_en_fisico": True,
        },
        "dab": {
            "archivo": "5_dab.json",
            "descripcion": "Pose dab.",
            "permitida_en_fisico": True,
        },
        "saludo_arriba_derecha": {
            "archivo": "6_saludo_arriba_der.json",
            "descripcion": "Saludo elevado con el brazo derecho.",
            "permitida_en_fisico": True,
        },
        "hablar": {
            "archivo": "7_hablar.json",
            "descripcion": "Gesticulación asociada al habla.",
            "permitida_en_fisico": True,
        },
        "fuerza": {
            "archivo": "8_fuerza.json",
            "descripcion": "Pose de fuerza.",
            "permitida_en_fisico": True,
        },
        "despejar_espacio": {
            "archivo": "9_quitense.json",
            "descripcion": "Gesto para solicitar que despejen el área.",
            "permitida_en_fisico": True,
        },
        "chocar_cinco": {
            "archivo": "10_chocar_cinco_der.json",
            "descripcion": "Gesto para chocar los cinco.",
            "permitida_en_fisico": True,
        },
        "confusion": {
            "archivo": "11_confusion.json",
            "descripcion": "Gesto de confusión.",
            "permitida_en_fisico": True,
        },
        "siu": {
            "archivo": "12_siu.json",
            "descripcion": "Pose de celebración siu.",
            "permitida_en_fisico": True,
        },
    },
}


intenciones = [
    crear_intencion(
        "siu",
        120,
        [
            "siu",
            "siuu",
            "siiu",
            "ciu",
            "cristiano",
            "ronaldo",
            "celebración de ronaldo",
            "pose de ronaldo",
        ],
        [
            ("Claro. Haré la celebración siu.", "siu_01.wav"),
            ("Activando la celebración siu.", "siu_02.wav"),
        ],
        ["siu"],
        desfase_pose_segundos=1.0,
    ),
    crear_intencion(
        "boxeo",
        120,
        [
            "boxeo",
            "boxear",
            "pose de boxeo",
            "posición de boxeo",
            "ponte en guardia",
            "tira golpes",
            "modo boxeo",
        ],
        [
            (
                "Claro. Haré una demostración de boxeo.",
                "boxeo_01.wav",
            ),
            ("Activando la pose de boxeo.", "boxeo_02.wav"),
        ],
        ["boxeo"],
        desfase_pose_segundos=1.0,
    ),
    crear_intencion(
        "dab",
        120,
        [
            "dab",
            "pose dab",
            "hacer el dab",
            "hacer un dab",
        ],
        [
            ("Claro. Haré un dab.", "dab_01.wav"),
            ("Activando la pose dab.", "dab_02.wav"),
        ],
        ["dab"],
        desfase_pose_segundos=1.0,
    ),
    crear_intencion(
        "fuerza",
        120,
        [
            "fuerza",
            "pose de fuerza",
            "mostrar fuerza",
            "muestra tus músculos",
            "haz músculos",
            "modo fuerza",
            "fisicoculturista",
            "qué tan fuerte eres",
        ],
        [
            (
                "Claro. Mostraré mi pose de fuerza.",
                "fuerza_01.wav",
            ),
            ("Activando la pose de fuerza.", "fuerza_02.wav"),
        ],
        ["fuerza"],
        desfase_pose_segundos=1.0,
    ),
    crear_intencion(
        "chocar_cinco",
        115,
        [
            "choca esos cinco",
            "chócala",
            "dame esos cinco",
            "dame cinco",
            "choca los cinco",
            "high five",
        ],
        [
            ("Claro. Choca esos cinco.", "chocar_cinco_01.wav"),
            (
                "Adelante. Estoy listo para chocar los cinco.",
                "chocar_cinco_02.wav",
            ),
        ],
        ["chocar_cinco"],
    ),
    crear_intencion(
        "despejar_espacio",
        110,
        [
            "quítense",
            "hazte a un lado",
            "háganse a un lado",
            "despejen el área",
            "hagan espacio",
            "dejen espacio",
            "retrocedan",
            "aléjense",
            "mantengan distancia",
            "necesito espacio",
        ],
        [
            (
                "Por favor, mantengan una distancia segura.",
                "despejar_espacio_01.wav",
            ),
            (
                "Por favor, despejen el área y permitan el paso.",
                "despejar_espacio_02.wav",
            ),
        ],
        ["despejar_espacio"],
    ),
    crear_intencion(
        "saludo_formal",
        100,
        [
            "saludo formal",
            "saluda formalmente",
            "preséntate formalmente",
            "mucho gusto",
            "es un placer conocerte",
            "encantado de conocerte",
        ],
        [
            (
                "Mucho gusto. Soy el robot G1 de Robotics 4.0.",
                "saludo_formal_01.wav",
            ),
            (
                "Reciba un cordial saludo de Robotics 4.0.",
                "saludo_formal_02.wav",
            ),
        ],
        ["saludo_formal"],
        desfase_pose_segundos=1.0,
    ),
    crear_intencion(
        "pose_aleatoria",
        90,
        [
            "haz una pose",
            "hacer una pose",
            "muéstrame una pose",
            "quiero ver una pose",
            "sorpréndeme",
            "haz algo divertido",
            "haz algo chévere",
            "haz un movimiento",
            "haz una demostración",
            "enséñame algo",
        ],
        [
            (
                "Claro. Elegiré una pose para mostrarte.",
                "pose_aleatoria_01.wav",
            ),
            (
                "De acuerdo. Haré una pose de demostración.",
                "pose_aleatoria_02.wav",
            ),
        ],
        [
            "boxeo",
            "dab",
            "fuerza",
            "siu",
        ],
        desfase_pose_segundos=1.0,
    ),
    crear_intencion(
        "presentacion_robot",
        85,
        [
            "quién eres",
            "cómo te llamas",
            "cuál es tu nombre",
            "preséntate",
            "dime quién eres",
            "qué eres",
            "de qué empresa eres",
            "quién te creó",
            "eres el robot g1",
        ],
        [
            (
                "Soy el robot humanoide G1 de Robotics 4.0, preparado "
                "para interacción y demostraciones en entornos de seguridad.",
                "presentacion_01.wav",
            ),
            (
                "Soy G1, un robot humanoide de Robotics 4.0. En esta "
                "prueba puedo reconocer instrucciones, responder y "
                "ejecutar poses.",
                "presentacion_02.wav",
            ),
        ],
        ["hablar"],
    ),
    crear_intencion(
        "capacidades",
        84,
        [
            "qué puedes hacer",
            "cuáles son tus funciones",
            "qué sabes hacer",
            "para qué sirves",
            "qué funciones tienes",
            "qué movimientos haces",
            "qué poses tienes",
        ],
        [
            (
                "Puedo reconocer instrucciones en español, responder "
                "por voz y ejecutar varias poses de demostración. La "
                "navegación permanece desactivada durante esta prueba.",
                "capacidades_01.wav",
            ),
            (
                "En este modo puedo responder mediante palabras bandera "
                "y realizar poses autorizadas mientras permanezco detenido.",
                "capacidades_02.wav",
            ),
        ],
        ["hablar"],
    ),
    crear_intencion(
        "hablar",
        82,
        [
            "puedes hablar",
            "di algo",
            "dime algo",
            "quiero escucharte",
            "cuéntame algo",
            "movimiento de hablar",
            "mueve los brazos mientras hablas",
        ],
        [
            (
                "Claro. Estoy listo para interactuar contigo.",
                "hablar_01.wav",
            ),
            (
                "Puedo escucharte y responder mediante mi sistema "
                "local de interacción.",
                "hablar_02.wav",
            ),
        ],
        ["hablar"],
    ),
    crear_intencion(
        "contactar_operador",
        81,
        [
            "llama al operador",
            "contacta al operador",
            "necesito un operador",
            "llama a seguridad",
            "contacta a seguridad",
            "necesito seguridad",
            "necesito un guardia",
            "ayuda humana",
            "hablar con una persona",
            "llama al encargado",
        ],
        [
            (
                "La llamada automática al operador aún no está habilitada. "
                "Por favor, comunícate directamente con el personal de "
                "seguridad.",
                "contactar_operador_01.wav",
            ),
        ],
        ["hablar"],
    ),
    crear_intencion(
        "ubicacion_no_configurada",
        80,
        [
            "dónde está",
            "dónde queda",
            "cómo llego",
            "me puedes indicar",
            "dónde están los baños",
            "dónde está el baño",
            "dónde está la salida",
            "dónde puedo comer",
            "dónde está recepción",
        ],
        [
            (
                "Esa ubicación todavía no está registrada. Un integrante "
                "del personal puede orientarte.",
                "ubicacion_no_configurada_01.wav",
            ),
            (
                "Aún no tengo habilitada la información de rutas del "
                "lugar. Por favor, consulta al personal de seguridad.",
                "ubicacion_no_configurada_02.wav",
            ),
        ],
        ["hablar"],
    ),
    crear_intencion(
        "acompanar_no_disponible",
        80,
        [
            "acompáñame",
            "ven conmigo",
            "sígueme",
            "puedes acompañarme",
            "llévame",
            "guíame",
            "muéstrame el camino",
            "camina conmigo",
        ],
        [
            (
                "La navegación está desactivada durante esta prueba, "
                "por lo que permaneceré detenido.",
                "navegacion_desactivada_01.wav",
            ),
        ],
        ["sin_pose"],
        ejecutar_pose=False,
        modo_ejecucion="solo_hablar",
        desfase_pose_segundos=0.0,
    ),
    crear_intencion(
        "detenerse",
        80,
        [
            "alto",
            "detente",
            "párate",
            "no te muevas",
            "quédate quieto",
            "permanece quieto",
            "deja de moverte",
            "frena",
            "stop",
        ],
        [
            (
                "Entendido. Permaneceré detenido.",
                "detenerse_01.wav",
            ),
        ],
        ["sin_pose"],
        ejecutar_pose=False,
        modo_ejecucion="solo_hablar",
        desfase_pose_segundos=0.0,
    ),
    crear_intencion(
        "esperar",
        79,
        [
            "espera",
            "espera un momento",
            "un momento",
            "aguarda",
            "dame un segundo",
            "dame un momento",
            "pausa",
            "quédate ahí",
        ],
        [
            (
                "De acuerdo. Esperaré aquí.",
                "esperar_01.wav",
            ),
        ],
        ["sin_pose"],
        ejecutar_pose=False,
        modo_ejecucion="solo_hablar",
        desfase_pose_segundos=0.0,
    ),
    crear_intencion(
        "estado_robot",
        75,
        [
            "cómo estás",
            "cómo te encuentras",
            "cómo te va",
            "estás bien",
            "estás funcionando",
            "funcionas bien",
            "cómo están tus sistemas",
            "estás listo",
        ],
        [
            (
                "Estoy funcionando correctamente y listo para interactuar.",
                "estado_01.wav",
            ),
            (
                "Mis sistemas de interacción están activos y permanezco "
                "detenido de forma segura.",
                "estado_02.wav",
            ),
        ],
        ["hablar"],
    ),
    crear_intencion(
        "agradecimiento",
        70,
        [
            "gracias",
            "muchas gracias",
            "te agradezco",
            "muy amable",
            "bien hecho",
            "buen trabajo",
        ],
        [
            (
                "Con gusto. Estoy aquí para ayudarte.",
                "agradecimiento_01.wav",
            ),
            (
                "Es un placer ayudarte.",
                "agradecimiento_02.wav",
            ),
        ],
        ["saludo_formal"],
    ),
    crear_intencion(
        "despedida",
        68,
        [
            "adiós",
            "hasta luego",
            "nos vemos",
            "chao",
            "chau",
            "hasta pronto",
            "me voy",
            "hasta la próxima",
        ],
        [
            (
                "Hasta luego. Que tengas un buen día.",
                "despedida_01.wav",
            ),
            (
                "Nos vemos pronto. Mantente seguro.",
                "despedida_02.wav",
            ),
        ],
        [
            "saludo_izquierda",
            "saludo_formal",
        ],
    ),
    crear_intencion(
        "saludo",
        60,
        [
            "hola",
            "buenos días",
            "buenas tardes",
            "buenas noches",
            "qué tal",
            "cómo vas",
            "hey",
            "oye robot",
            "oye g1",
            "un saludo",
            "salúdame",
            "di hola",
        ],
        [
            (
                "Hola. Soy el robot G1 de Robotics 4.0. ¿Cómo estás?",
                "saludo_01.wav",
            ),
            (
                "Hola. Es un gusto saludarte.",
                "saludo_02.wav",
            ),
            (
                "Buenos días. Estoy listo para interactuar contigo.",
                "saludo_03.wav",
            ),
        ],
        [
            "saludo_derecha",
            "saludo_arriba_derecha",
        ],
    ),
]


configuracion_intenciones = {
    "version_esquema": 1,
    "configuracion_general": {
        "idioma": "es",
        "intencion_fallback": "no_entendido",
        "seleccion_respuesta": "aleatoria",
        "seleccion_pose": "aleatoria",
        "modo_ejecucion_predeterminado": "hablar_y_posar",
        "desfase_pose_segundos": 1.0,
    },
    "intenciones": intenciones,
    "fallback": {
        "id": "no_entendido",
        "prioridad": 0,
        "respuestas": [
            {
                "texto": (
                    "No entendí bien. ¿Puedes repetirlo con otras palabras?"
                ),
                "archivo_audio": "no_entendido_01.wav",
            },
            {
                "texto": (
                    "No logré identificar la instrucción. Por favor, "
                    "repítela más claramente."
                ),
                "archivo_audio": "no_entendido_02.wav",
            },
        ],
        "poses_candidatas": ["confusion"],
        "ejecutar_pose": True,
        "permitida_en_fisico": True,
        "modo_ejecucion": "hablar_y_posar",
        "desfase_pose_segundos": 0.8,
    },
}


def guardar_json(ruta: Path, contenido):
    ruta.parent.mkdir(parents=True, exist_ok=True)

    with ruta.open("w", encoding="utf-8") as archivo:
        json.dump(
            contenido,
            archivo,
            ensure_ascii=False,
            indent=2,
        )
        archivo.write("\n")


def main():
    guardar_json(RUTA_CATALOGO, catalogo_poses)
    guardar_json(RUTA_INTENCIONES, configuracion_intenciones)

    print("[OK] Configuración generada.")
    print(f"[OK] Catálogo: {RUTA_CATALOGO}")
    print(f"[OK] Intenciones: {RUTA_INTENCIONES}")
    print(f"[OK] Número de poses: {len(catalogo_poses['poses'])}")
    print(f"[OK] Número de intenciones: {len(intenciones)}")


if __name__ == "__main__":
    main()
