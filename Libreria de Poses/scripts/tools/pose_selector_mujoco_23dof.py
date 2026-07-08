#!/usr/bin/env python3
import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
POSES_ROOT = SCRIPT_DIR.parent
DEFAULT_POSES_DIR = POSES_ROOT / "poses_json"
PLAY_SCRIPT = SCRIPT_DIR / "play_pose_mujoco_23dof.py"


def list_pose_files(poses_dir: Path):
    if not poses_dir.is_dir():
        return []

    return sorted(poses_dir.glob("*.json"))


def main():
    parser = argparse.ArgumentParser(description="Selector de poses G1 23 DoF para MuJoCo.")
    parser.add_argument("--poses-dir", default=str(DEFAULT_POSES_DIR))
    parser.add_argument("--interface", default="lo")
    parser.add_argument("--num-motors", type=int, default=29)
    args = parser.parse_args()

    poses_dir = Path(args.poses_dir).expanduser().resolve()

    while True:
        poses = list_pose_files(poses_dir)

        print("\n=== Librería de Poses G1 23 DoF ===")

        if not poses:
            print(f"No hay poses .json en: {poses_dir}")
            print("Primero captura una pose con capture_pose_mujoco_23dof.py")
            return

        for i, path in enumerate(poses, start=1):
            print(f"{i}. {path.name}")

        print("0. Salir")

        choice = input("\nSelecciona una pose: ").strip()

        if choice == "0":
            print("[INFO] Saliendo.")
            return

        try:
            idx = int(choice)
            if idx < 1 or idx > len(poses):
                raise ValueError
        except Exception:
            print("[WARN] Opción inválida.")
            continue

        selected = poses[idx - 1]

        cmd = [
            sys.executable,
            str(PLAY_SCRIPT),
            "--pose", str(selected),
            "--interface", args.interface,
            "--num-motors", str(args.num_motors)
        ]

        print(f"\n[INFO] Ejecutando: {selected.name}\n")
        subprocess.run(cmd)


if __name__ == "__main__":
    main()
