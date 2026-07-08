#!/usr/bin/env python3
import argparse
import json
import sys
import time
from pathlib import Path

try:
    from unitree_sdk2py.core.channel import ChannelFactoryInitialize
    from unitree_sdk2py.core.channel import ChannelSubscriber
    from unitree_sdk2py.idl.unitree_hg.msg.dds_ import LowState_
except Exception as e:
    print("[ERROR] No se pudo importar unitree_sdk2py.")
    print("Verifica que estés en el entorno donde ya corrías los ejemplos de Unitree.")
    print(f"Detalle: {e}")
    sys.exit(1)


SCRIPT_DIR = Path(__file__).resolve().parent
POSES_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG = POSES_ROOT / "config" / "g1_23dof_active_upper_body_indices.json"


class LowStateReader:
    def __init__(self):
        self.low_state = None
        self.last_time = None

    def handler(self, msg: LowState_):
        self.low_state = msg
        self.last_time = time.time()


def init_channel(interface):
    if interface == "lo":
        ChannelFactoryInitialize(1, "lo")
    else:
        ChannelFactoryInitialize(0, interface)


def read_q(low_state, idx):
    try:
        return float(low_state.motor_state[idx].q)
    except Exception:
        return None


def read_dq(low_state, idx):
    try:
        return float(low_state.motor_state[idx].dq)
    except Exception:
        return None


def load_names(config_path):
    if not config_path.is_file():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("active_joints_expected", {})
    except Exception:
        return {}


def parse_indices(text, max_index):
    if not text:
        return list(range(max_index + 1))

    result = []

    for part in text.split(","):
        part = part.strip()

        if not part:
            continue

        if "-" in part:
            a, b = part.split("-", 1)
            result.extend(range(int(a), int(b) + 1))
        else:
            result.append(int(part))

    return sorted(set(result))


def wait_lowstate(reader, timeout):
    print("[INFO] Esperando rt/lowstate...")

    start = time.time()

    while reader.low_state is None:
        if time.time() - start > timeout:
            print("[ERROR] No llegó rt/lowstate.")
            print("Abre MuJoCo primero y verifica la interfaz DDS.")
            sys.exit(1)

        time.sleep(0.05)

    print("[OK] rt/lowstate recibido.")


def snapshot(low_state, indices):
    values = {}

    for idx in indices:
        q = read_q(low_state, idx)

        if q is not None:
            values[idx] = q

    return values


def print_table(low_state, baseline, indices, names, threshold, show_all):
    rows = []

    for idx in indices:
        q = read_q(low_state, idx)
        dq = read_dq(low_state, idx)

        if q is None:
            continue

        q0 = baseline.get(idx, q)
        delta = q - q0

        if show_all or abs(delta) >= threshold:
            rows.append((idx, q, dq, delta, names.get(str(idx), "")))

    if not rows:
        print("[INFO] Sin cambios por encima del umbral.")
        return

    print("\nidx | q actual   | dq        | delta     | nombre esperado")
    print("----|------------|-----------|-----------|----------------")

    for idx, q, dq, delta, name in rows:
        dq_text = f"{dq: .6f}" if dq is not None else "   N/A"
        print(f"{idx:>3} | {q:> .6f} | {dq_text:>9} | {delta:> .6f} | {name}")

    print("")


def main():
    parser = argparse.ArgumentParser(
        description="Monitorea rt/lowstate para identificar qué índices cambian al mover sliders en MuJoCo."
    )
    parser.add_argument("--interface", default="lo")
    parser.add_argument("--max-index", type=int, default=28)
    parser.add_argument("--indices", default="0-28", help="Ejemplo: 0-28 o 12,15,16,17,18,19")
    parser.add_argument("--period", type=float, default=0.5)
    parser.add_argument("--threshold", type=float, default=0.005)
    parser.add_argument("--show-all", action="store_true")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--timeout", type=float, default=8.0)
    args = parser.parse_args()

    indices = parse_indices(args.indices, args.max_index)
    names = load_names(Path(args.config).expanduser())

    print("\n[CONFIGURACIÓN]")
    print(f"Interface: {args.interface}")
    print(f"Índices monitoreados: {indices}")
    print(f"Threshold: {args.threshold}")
    print("")

    init_channel(args.interface)

    reader = LowStateReader()
    sub = ChannelSubscriber("rt/lowstate", LowState_)
    sub.Init(reader.handler, 10)

    wait_lowstate(reader, args.timeout)

    input("\nDeja el robot quieto. Presiona Enter para tomar baseline...")

    baseline = snapshot(reader.low_state, indices)

    print("\n[OK] Baseline tomada.")
    print("Ahora mueve un slider en MuJoCo. El script imprimirá los índices que cambien.")
    print("Ctrl+C para salir.\n")

    try:
        while True:
            time.sleep(args.period)
            print_table(
                reader.low_state,
                baseline,
                indices,
                names,
                args.threshold,
                args.show_all
            )

    except KeyboardInterrupt:
        print("\n[INFO] Monitor finalizado.")


if __name__ == "__main__":
    main()
