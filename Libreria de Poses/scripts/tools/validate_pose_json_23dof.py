#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
POSES_ROOT = SCRIPT_DIR.parent
DEFAULT_JOINT_MAP = POSES_ROOT / "config" / "g1_23dof_joint_map.json"
DEFAULT_LIMITS = POSES_ROOT / "config" / "g1_23dof_pose_limits.json"


def load_json(path: Path, required=True):
    if not path.is_file() or path.stat().st_size == 0:
        if required:
            raise FileNotFoundError(str(path))
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_optional(path: Path):
    try:
        return load_json(path, required=False)
    except Exception:
        return None


def valid_indices_from_joint_map(joint_map):
    valid = set()

    if not joint_map:
        return valid

    for j in joint_map.get("joints", []):
        idx = j.get("controlled_index")
        if idx is not None:
            valid.add(int(idx))

    return valid


def limits_from_file(limits_data):
    if not limits_data:
        return {}

    return limits_data.get("limits_by_index", {})


def validate_pose(path: Path, joint_map_path: Path, limits_path: Path, max_rad_per_sec: float):
    errors = []
    warnings = []

    try:
        routine = load_json(path, required=True)
    except Exception as e:
        print(f"[ERROR] No se pudo leer JSON: {e}")
        return 1

    joint_map = load_optional(joint_map_path)
    limits_data = load_optional(limits_path)

    valid_indices = valid_indices_from_joint_map(joint_map)
    limits_by_index = limits_from_file(limits_data)

    if routine.get("modelo") != "g1_23dof":
        warnings.append("El campo modelo no es 'g1_23dof'.")

    if routine.get("requiere_robot_quieto") is not True:
        warnings.append("La rutina debería tener 'requiere_robot_quieto': true.")

    pasos = routine.get("pasos")

    if not isinstance(pasos, list) or not pasos:
        errors.append("La rutina no contiene una lista válida de pasos.")

    previous_positions = None

    if isinstance(pasos, list):
        for i, paso in enumerate(pasos, start=1):
            nombre = paso.get("nombre", f"Paso {i}")
            posiciones = paso.get("posiciones")
            duracion = paso.get("duracion")

            if not isinstance(posiciones, dict) or not posiciones:
                errors.append(f"{nombre}: posiciones vacío o inválido.")
                continue

            try:
                duracion = float(duracion)
                if duracion <= 0:
                    errors.append(f"{nombre}: duración debe ser positiva.")
            except Exception:
                errors.append(f"{nombre}: duración inválida.")
                duracion = 1.0

            current_positions = {}

            for k, v in posiciones.items():
                try:
                    idx = int(k)
                except Exception:
                    errors.append(f"{nombre}: índice no entero: {k}")
                    continue

                try:
                    value = float(v)
                except Exception:
                    errors.append(f"{nombre}: valor no numérico en índice {k}: {v}")
                    continue

                current_positions[idx] = value

                if valid_indices and idx not in valid_indices:
                    warnings.append(f"{nombre}: índice {idx} no aparece como motor controlado en joint_map.")

                lim = limits_by_index.get(str(idx))

                if lim:
                    lower = lim.get("lower")
                    upper = lim.get("upper")

                    if lower is not None and value < float(lower):
                        errors.append(f"{nombre}: índice {idx} por debajo del límite {lower}. Valor={value}")

                    if upper is not None and value > float(upper):
                        errors.append(f"{nombre}: índice {idx} por encima del límite {upper}. Valor={value}")

            if previous_positions is not None:
                common = set(previous_positions.keys()) & set(current_positions.keys())

                for idx in common:
                    delta = abs(current_positions[idx] - previous_positions[idx])
                    speed = delta / max(duracion, 1e-6)

                    if speed > max_rad_per_sec:
                        warnings.append(
                            f"{nombre}: cambio rápido en índice {idx}: "
                            f"{speed:.3f} rad/s > {max_rad_per_sec:.3f} rad/s"
                        )

            previous_positions = current_positions

    print("\n[VALIDACIÓN]")
    print(f"Archivo: {path}")
    print(f"Errores: {len(errors)}")
    print(f"Advertencias: {len(warnings)}")

    if warnings:
        print("\n[ADVERTENCIAS]")
        for w in warnings:
            print(f" - {w}")

    if errors:
        print("\n[ERRORES]")
        for e in errors:
            print(f" - {e}")
        print("\n[RESULTADO] NO VÁLIDO")
        return 1

    print("\n[RESULTADO] VÁLIDO")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Valida rutinas JSON de poses para G1 23 DoF.")
    parser.add_argument("pose_json", help="Ruta al archivo .json de la rutina.")
    parser.add_argument("--joint-map", default=str(DEFAULT_JOINT_MAP))
    parser.add_argument("--limits", default=str(DEFAULT_LIMITS))
    parser.add_argument("--max-rad-per-sec", type=float, default=1.5)
    args = parser.parse_args()

    exit_code = validate_pose(
        Path(args.pose_json).expanduser().resolve(),
        Path(args.joint_map).expanduser().resolve(),
        Path(args.limits).expanduser().resolve(),
        args.max_rad_per_sec
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
