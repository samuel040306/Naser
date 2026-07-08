#!/usr/bin/env python3
import argparse
import csv
import json
import sys
from pathlib import Path
from datetime import datetime
import xml.etree.ElementTree as ET

try:
    import mujoco
    HAVE_MUJOCO = True
except Exception:
    mujoco = None
    HAVE_MUJOCO = False


SCRIPT_DIR = Path(__file__).resolve().parent
POSES_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG_DIR = POSES_ROOT / "config"
DEFAULT_OUTPUT_DIR = POSES_ROOT / "model_outputs"


UPPER_BODY_KEYWORDS = [
    "waist", "torso", "trunk",
    "shoulder", "elbow", "wrist", "arm"
]

LEG_KEYWORDS = [
    "hip", "knee", "ankle", "foot", "leg"
]


def classify_group(name: str, body_name: str = "") -> str:
    text = f"{name} {body_name}".lower()

    if any(k in text for k in UPPER_BODY_KEYWORDS):
        return "upper_body"

    if any(k in text for k in LEG_KEYWORDS):
        return "leg"

    if "free" in text or "floating" in text or "root" in text:
        return "root"

    return "unknown"


def safe_float_list(value):
    if value is None:
        return None

    try:
        return [float(x) for x in value]
    except Exception:
        return None


def mj_name(model, obj_type, idx):
    try:
        name = mujoco.mj_id2name(model, obj_type, int(idx))
        return name if name is not None else ""
    except Exception:
        return ""


def inspect_with_mujoco(xml_path: Path):
    model = mujoco.MjModel.from_xml_path(str(xml_path))

    joint_type_names = {
        int(mujoco.mjtJoint.mjJNT_FREE): "free",
        int(mujoco.mjtJoint.mjJNT_BALL): "ball",
        int(mujoco.mjtJoint.mjJNT_SLIDE): "slide",
        int(mujoco.mjtJoint.mjJNT_HINGE): "hinge",
    }

    actuator_by_joint = {}

    for a in range(model.nu):
        trn_type = int(model.actuator_trntype[a])
        joint_id = int(model.actuator_trnid[a][0])

        if trn_type == int(mujoco.mjtTrn.mjTRN_JOINT) and joint_id >= 0:
            actuator_by_joint.setdefault(joint_id, []).append({
                "actuator_index": a,
                "actuator_name": mj_name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, a),
                "ctrl_limited": bool(model.actuator_ctrllimited[a]),
                "ctrl_range": [
                    float(model.actuator_ctrlrange[a][0]),
                    float(model.actuator_ctrlrange[a][1])
                ] if bool(model.actuator_ctrllimited[a]) else None,
            })

    joints = []

    for j in range(model.njnt):
        joint_name = mj_name(model, mujoco.mjtObj.mjOBJ_JOINT, j)
        body_id = int(model.jnt_bodyid[j])
        body_name = mj_name(model, mujoco.mjtObj.mjOBJ_BODY, body_id)
        joint_type = int(model.jnt_type[j])
        joint_type_name = joint_type_names.get(joint_type, str(joint_type))

        actuators = actuator_by_joint.get(j, [])
        primary_actuator = actuators[0] if actuators else None

        jnt_limited = bool(model.jnt_limited[j])
        jnt_range = [
            float(model.jnt_range[j][0]),
            float(model.jnt_range[j][1])
        ] if jnt_limited else None

        group = classify_group(joint_name, body_name)

        joints.append({
            "joint_index": j,
            "joint_name": joint_name,
            "joint_type": joint_type_name,
            "body_index": body_id,
            "body_name": body_name,
            "qpos_address": int(model.jnt_qposadr[j]),
            "dof_address": int(model.jnt_dofadr[j]),
            "joint_limited": jnt_limited,
            "joint_range": jnt_range,
            "actuators": actuators,
            "motor_index": primary_actuator["actuator_index"] if primary_actuator else None,
            "actuator_name": primary_actuator["actuator_name"] if primary_actuator else None,
            "ctrl_limited": primary_actuator["ctrl_limited"] if primary_actuator else None,
            "ctrl_range": primary_actuator["ctrl_range"] if primary_actuator else None,
            "group": group,
            "controlled_index": primary_actuator["actuator_index"] if primary_actuator else None
        })

    return {
        "inspection_backend": "mujoco_python",
        "xml_path": str(xml_path),
        "robot": "unitree_g1",
        "model_label": "g1_23dof",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "nq": int(model.nq),
        "nv": int(model.nv),
        "nu": int(model.nu),
        "njnt": int(model.njnt),
        "nbody": int(model.nbody),
        "joints": joints
    }


def inspect_with_xml_fallback(xml_path: Path):
    tree = ET.parse(xml_path)
    root = tree.getroot()

    actuator_joint_map = {}
    actuator_index = 0

    for actuator_node in root.findall(".//actuator/*"):
        joint_name = actuator_node.attrib.get("joint")
        if not joint_name:
            continue

        ctrlrange = actuator_node.attrib.get("ctrlrange")
        ctrl_range = None

        if ctrlrange:
            try:
                parts = [float(x) for x in ctrlrange.split()]
                if len(parts) == 2:
                    ctrl_range = parts
            except Exception:
                ctrl_range = None

        actuator_joint_map.setdefault(joint_name, []).append({
            "actuator_index": actuator_index,
            "actuator_name": actuator_node.attrib.get("name", ""),
            "ctrl_limited": ctrl_range is not None,
            "ctrl_range": ctrl_range
        })
        actuator_index += 1

    joints = []
    joint_counter = 0

    def walk_body(body_node, body_name=""):
        nonlocal joint_counter

        current_body_name = body_node.attrib.get("name", body_name)

        for joint_node in body_node.findall("joint"):
            joint_name = joint_node.attrib.get("name", f"joint_{joint_counter}")
            joint_type = joint_node.attrib.get("type", "hinge")
            range_attr = joint_node.attrib.get("range")
            jnt_range = None

            if range_attr:
                try:
                    parts = [float(x) for x in range_attr.split()]
                    if len(parts) == 2:
                        jnt_range = parts
                except Exception:
                    jnt_range = None

            actuators = actuator_joint_map.get(joint_name, [])
            primary_actuator = actuators[0] if actuators else None
            group = classify_group(joint_name, current_body_name)

            joints.append({
                "joint_index": joint_counter,
                "joint_name": joint_name,
                "joint_type": joint_type,
                "body_index": None,
                "body_name": current_body_name,
                "qpos_address": None,
                "dof_address": None,
                "joint_limited": jnt_range is not None,
                "joint_range": jnt_range,
                "actuators": actuators,
                "motor_index": primary_actuator["actuator_index"] if primary_actuator else None,
                "actuator_name": primary_actuator["actuator_name"] if primary_actuator else None,
                "ctrl_limited": primary_actuator["ctrl_limited"] if primary_actuator else None,
                "ctrl_range": primary_actuator["ctrl_range"] if primary_actuator else None,
                "group": group,
                "controlled_index": primary_actuator["actuator_index"] if primary_actuator else None
            })

            joint_counter += 1

        for child_body in body_node.findall("body"):
            walk_body(child_body, current_body_name)

    for worldbody in root.findall(".//worldbody"):
        for body in worldbody.findall("body"):
            walk_body(body)

    return {
        "inspection_backend": "xml_fallback",
        "xml_path": str(xml_path),
        "robot": "unitree_g1",
        "model_label": "g1_23dof",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "nq": None,
        "nv": None,
        "nu": actuator_index,
        "njnt": len(joints),
        "nbody": None,
        "joints": joints,
        "warning": "Fallback XML usado. Para obtener qpos_address/dof_address reales instala/importa mujoco en Python."
    }


def write_outputs(data, output_dir: Path, config_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)

    joints = data["joints"]

    upper_body_motor_indices = []
    upper_body_joint_names = []

    for j in joints:
        if j.get("group") == "upper_body":
            upper_body_joint_names.append(j.get("joint_name"))
            if j.get("controlled_index") is not None:
                upper_body_motor_indices.append(int(j["controlled_index"]))

    upper_body_motor_indices = sorted(set(upper_body_motor_indices))

    data["upper_body_joint_names"] = upper_body_joint_names
    data["upper_body_motor_indices"] = upper_body_motor_indices

    joint_map_path = config_dir / "g1_23dof_joint_map.json"
    limits_path = config_dir / "g1_23dof_pose_limits.json"
    csv_path = output_dir / "g1_23dof_joint_summary.csv"
    full_json_path = output_dir / "g1_23dof_model_full_inspection.json"

    with open(joint_map_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    limits_by_index = {}

    for j in joints:
        idx = j.get("controlled_index")
        if idx is None:
            continue

        selected_range = j.get("ctrl_range") or j.get("joint_range")

        limits_by_index[str(idx)] = {
            "joint_name": j.get("joint_name"),
            "actuator_name": j.get("actuator_name"),
            "lower": selected_range[0] if selected_range else None,
            "upper": selected_range[1] if selected_range else None,
            "source": "ctrl_range" if j.get("ctrl_range") else "joint_range" if j.get("joint_range") else "none",
            "group": j.get("group")
        }

    limits_data = {
        "robot": "unitree_g1",
        "model_label": "g1_23dof",
        "generated_at": data["generated_at"],
        "limits_by_index": limits_by_index
    }

    with open(limits_path, "w", encoding="utf-8") as f:
        json.dump(limits_data, f, indent=2, ensure_ascii=False)

    with open(full_json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    fieldnames = [
        "joint_index", "joint_name", "joint_type",
        "body_name", "qpos_address", "dof_address",
        "joint_range", "motor_index", "actuator_name",
        "ctrl_range", "group", "controlled_index"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for j in joints:
            row = {k: j.get(k) for k in fieldnames}
            writer.writerow(row)

    print("\n[OK] Inspección finalizada.")
    print(f"[OK] Joint map: {joint_map_path}")
    print(f"[OK] Limits:    {limits_path}")
    print(f"[OK] CSV:       {csv_path}")
    print(f"[OK] Full JSON: {full_json_path}")

    print("\n[RESUMEN]")
    print(f"Backend: {data.get('inspection_backend')}")
    print(f"nu actuators: {data.get('nu')}")
    print(f"njnt joints:  {data.get('njnt')}")
    print(f"Upper body motor indices detectados: {upper_body_motor_indices}")

    if data.get("nu") not in (None, 23):
        print(f"\n[ADVERTENCIA] El modelo reporta nu={data.get('nu')}, no 23.")
        print("Verifica que el XML corresponda realmente al G1 23 DoF.")


def main():
    parser = argparse.ArgumentParser(
        description="Inspecciona un XML MuJoCo de Unitree G1 23 DoF y genera mapa articular."
    )
    parser.add_argument("--xml", required=True, help="Ruta al XML MuJoCo del G1 23 DoF.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--config-dir", default=str(DEFAULT_CONFIG_DIR))
    args = parser.parse_args()

    xml_path = Path(args.xml).expanduser().resolve()

    if not xml_path.is_file():
        print(f"[ERROR] No existe el XML: {xml_path}")
        sys.exit(1)

    try:
        if HAVE_MUJOCO:
            data = inspect_with_mujoco(xml_path)
        else:
            print("[WARN] No se pudo importar mujoco en Python. Usando lectura XML básica.")
            data = inspect_with_xml_fallback(xml_path)

    except Exception as e:
        print(f"[WARN] Falló inspección con MuJoCo Python: {e}")
        print("[WARN] Intentando fallback XML básico.")
        data = inspect_with_xml_fallback(xml_path)

    write_outputs(
        data,
        Path(args.output_dir).expanduser().resolve(),
        Path(args.config_dir).expanduser().resolve()
    )


if __name__ == "__main__":
    main()
