#!/usr/bin/env python3

import argparse
from pathlib import Path

from agente_banderas.motor_intenciones import MotorIntenciones
from agente_banderas.validador_configuracion import validar_configuracion


DIRECTORIO_SCRIPTS = Path(__file__).resolve().parent
DIRECTORIO_CONFIGURACION = DIRECTORIO_SCRIPTS / "configuracion"

RUTA_INTENCIONES = (
    DIRECTORIO_CONFIGURACION / "intenciones_es.json"
)
RUTA_CATALOGO = (
    DIRECTORIO_CONFIGURACION / "catalogo_poses_es.json"
)


def imprimir_resultado(resultado) -> None:
    print("\n" + "=" * 72)
    print("RESULTADO DEL MOTOR DE PALABRAS BANDERA")
    print("=" * 72)
    print(f"Texto original:       {resultado.texto_original}")
    print(f"Texto normalizado:    {resultado.texto_normalizado}")
    print(f"Intención:            {resultado.intencion}")
    print(f"Bandera activadora:   {resultado.bandera_activadora}")
    print(f"Respuesta:            {resultado.respuesta}")
    print(f"Archivo de audio:     {resultado.archivo_audio}")
    print(f"Clave de pose:        {resultado.clave_pose}")
    print(f"Archivo de pose:      {resultado.archivo_pose}")
    print(f"Ejecutar pose:        {resultado.ejecutar_pose}")
    print(f"Permitida en físico:  {resultado.permitida_en_fisico}")
    print(f"Modo de ejecución:    {resultado.modo_ejecucion}")
    print(
        "Desfase de pose:     "
        f"{resultado.desfase_pose_segundos:.2f} s"
    )
    print(f"Es fallback:          {resultado.es_fallback}")

    if resultado.detecciones:
        print("\nCoincidencias encontradas:")

        for posicion, deteccion in enumerate(
            resultado.detecciones,
            start=1,
        ):
            print(
                f"  {posicion:02d}. "
                f"{deteccion.identificador} | "
                f"bandera='{deteccion.bandera_original}' | "
                f"prioridad={deteccion.prioridad} | "
                f"palabras={deteccion.numero_palabras}"
            )
    else:
        print("\nCoincidencias encontradas: ninguna")

    print("=" * 72)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Prueba local por texto del motor de palabras bandera."
        )
    )
    parser.add_argument(
        "--frase",
        default=None,
        help="Procesar una sola frase y finalizar.",
    )
    parser.add_argument(
        "--semilla",
        type=int,
        default=None,
        help=(
            "Semilla opcional para hacer determinista la selección "
            "aleatoria de poses y respuestas."
        ),
    )
    args = parser.parse_args()

    validacion = validar_configuracion(
        RUTA_INTENCIONES,
        RUTA_CATALOGO,
    )

    if validacion.errores:
        print("[ERROR] La configuración no es válida:")

        for error in validacion.errores:
            print(f"  - {error}")

        raise SystemExit(1)

    print("[OK] Configuración válida.")
    print(
        "[OK] Advertencias: "
        f"{len(validacion.advertencias)}"
    )

    for advertencia in validacion.advertencias:
        print(f"  [ADVERTENCIA] {advertencia}")

    motor = MotorIntenciones(
        ruta_intenciones=RUTA_INTENCIONES,
        ruta_catalogo=RUTA_CATALOGO,
        semilla=args.semilla,
    )

    if args.frase is not None:
        imprimir_resultado(motor.resolver(args.frase))
        return

    print("\nMOTOR LOCAL DE PALABRAS BANDERA")
    print("Escribe una frase para procesarla.")
    print("Escribe 'x', 'q' o 'salir' para cerrar.")

    while True:
        try:
            frase = input("\nUsuario > ").strip()
        except EOFError:
            print("\n[INFO] Entrada finalizada.")
            break
        except KeyboardInterrupt:
            print("\n[INFO] Interrupción detectada.")
            break

        if frase.lower() in {"x", "q", "salir", "exit"}:
            print("[INFO] Cerrando motor.")
            break

        if not frase:
            print("[ADVERTENCIA] La frase está vacía.")
            continue

        imprimir_resultado(motor.resolver(frase))


if __name__ == "__main__":
    main()
