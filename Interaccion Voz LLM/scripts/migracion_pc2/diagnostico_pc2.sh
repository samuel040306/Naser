#!/usr/bin/env bash

set -uo pipefail

DIRECTORIO_SCRIPT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")" \
  && pwd
)"

RAIZ_PROYECTO="$(
  cd "$DIRECTORIO_SCRIPT/../../.." \
  && pwd
)"

DIRECTORIO_LOGS="$RAIZ_PROYECTO/Interaccion Voz LLM/scripts/logs"

mkdir -p "$DIRECTORIO_LOGS"

MARCA_TIEMPO="$(date +%Y%m%d_%H%M%S)"

ARCHIVO_SALIDA="$DIRECTORIO_LOGS/diagnostico_pc2_${MARCA_TIEMPO}.txt"

seccion() {
  echo
  echo "=============================================================================="
  echo "$1"
  echo "=============================================================================="
}

ejecutar() {
  local comando="$1"

  echo
  echo "\$ $comando"

  bash -lc "$comando" || {
    local codigo=$?
    echo "[AVISO] Comando no disponible o terminó con código $codigo."
  }
}

{
  echo "DIAGNÓSTICO DE SOLO LECTURA DEL PC2"
  echo "Fecha: $(date --iso-8601=seconds)"
  echo "Usuario: $(id -un)"
  echo "Host: $(hostname)"
  echo "Proyecto: $RAIZ_PROYECTO"

  seccion "1. IDENTIDAD DEL SISTEMA"

  ejecutar "uname -a"
  ejecutar "uname -m"
  ejecutar "cat /etc/os-release"
  ejecutar "hostnamectl 2>/dev/null || true"
  ejecutar "cat /etc/nv_tegra_release 2>/dev/null || true"

  seccion "2. PROCESADOR, MEMORIA Y ALMACENAMIENTO"

  ejecutar "lscpu"
  ejecutar "free -h"
  ejecutar "df -h"
  ejecutar "nproc"

  seccion "3. PYTHON"

  ejecutar "command -v python3"
  ejecutar "python3 --version"
  ejecutar "python3 -m pip --version 2>/dev/null || true"
  ejecutar "python3 -m venv --help >/dev/null 2>&1 && echo '[OK] venv disponible' || echo '[NO] venv no disponible'"
  ejecutar "python3 -c 'import sys; print(sys.executable); print(sys.version); print(sys.path)'"

  seccion "4. PAQUETES PYTHON RELEVANTES"

  ejecutar "python3 -m pip list 2>/dev/null | grep -Ei 'unitree|cyclonedds|sounddevice|webrtc|torch|whisper|numpy|scipy|pyyaml' || true"

  seccion "5. COMPILADORES Y HERRAMIENTAS"

  ejecutar "gcc --version | head -n 1"
  ejecutar "g++ --version | head -n 1"
  ejecutar "cmake --version | head -n 1"
  ejecutar "make --version | head -n 1"
  ejecutar "git --version"
  ejecutar "curl --version | head -n 1"
  ejecutar "wget --version | head -n 1"
  ejecutar "ldconfig -p 2>/dev/null | grep -Ei 'openblas|portaudio|cuda|cudnn' | head -n 80 || true"

  seccion "6. NVIDIA, JETPACK Y CUDA"

  ejecutar "command -v nvcc || true"
  ejecutar "nvcc --version 2>/dev/null || true"
  ejecutar "nvidia-smi 2>/dev/null || true"
  ejecutar "dpkg-query -W 'nvidia-jetpack' 'nvidia-l4t-core' 'nvidia-l4t-cuda' 'cuda-toolkit-*' 2>/dev/null || true"
  ejecutar "ls -ld /usr/local/cuda* 2>/dev/null || true"

  seccion "7. ROS 2 Y CYCLONEDDS"

  ejecutar "echo \"ROS_DISTRO=\${ROS_DISTRO:-NO_DEFINIDO}\""
  ejecutar "echo \"RMW_IMPLEMENTATION=\${RMW_IMPLEMENTATION:-NO_DEFINIDO}\""
  ejecutar "command -v ros2 || true"
  ejecutar "ros2 --help >/dev/null 2>&1 && echo '[OK] ros2 ejecutable' || echo '[NO] ros2 no disponible en este entorno'"
  ejecutar "printenv | grep -E '^(ROS|RMW|CYCLONEDDS|AMENT|COLCON)' | sort || true"
  ejecutar "dpkg -l 2>/dev/null | grep -E 'ros-foxy|cyclonedds' | head -n 100 || true"
  ejecutar "find /opt -maxdepth 4 -iname '*cyclonedds*' 2>/dev/null | head -n 80 || true"

  seccion "8. UNITREE SDK Y ARCHIVOS RELACIONADOS"

  ejecutar "ls -la /opt/unitree_robotics 2>/dev/null || true"
  ejecutar "find /opt/unitree_robotics -maxdepth 4 -type d 2>/dev/null | head -n 100 || true"
  ejecutar "find \"\$HOME\" -maxdepth 4 -type d \\( -iname '*unitree*' -o -iname '*robotics*' \\) 2>/dev/null | head -n 100 || true"
  ejecutar "python3 -c 'import unitree_sdk2py; print(unitree_sdk2py.__file__)' 2>/dev/null || true"

  seccion "9. DISPOSITIVOS DE AUDIO"

  ejecutar "arecord -l 2>/dev/null || true"
  ejecutar "aplay -l 2>/dev/null || true"
  ejecutar "pactl info 2>/dev/null || true"
  ejecutar "pactl list short sources 2>/dev/null || true"
  ejecutar "pactl list short sinks 2>/dev/null || true"
  ejecutar "cat /proc/asound/cards 2>/dev/null || true"

  seccion "10. RED"

  ejecutar "ip -brief address"
  ejecutar "ip route"
  ejecutar "ss -lntup 2>/dev/null | head -n 100 || true"

  seccion "11. PROCESOS RELEVANTES"

  ejecutar "ps -eo pid,user,comm,args | grep -Ei 'unitree|ros2|cyclone|dds|whisper|python' | grep -v grep | head -n 150 || true"

  seccion "12. REPOSITORIO"

  ejecutar "git -C \"$RAIZ_PROYECTO\" rev-parse --show-toplevel"
  ejecutar "git -C \"$RAIZ_PROYECTO\" branch --show-current"
  ejecutar "git -C \"$RAIZ_PROYECTO\" log -3 --oneline"
  ejecutar "git -C \"$RAIZ_PROYECTO\" status --short"

  seccion "RESUMEN PARA COMPARTIR"

  echo "Arquitectura: $(uname -m)"
  echo "Kernel: $(uname -r)"
  echo "Ubuntu: $(
    . /etc/os-release 2>/dev/null
    echo "${PRETTY_NAME:-NO_DETECTADO}"
  )"
  echo "Python: $(python3 --version 2>&1 || true)"
  echo "ROS_DISTRO: ${ROS_DISTRO:-NO_DEFINIDO}"
  echo "RMW_IMPLEMENTATION: ${RMW_IMPLEMENTATION:-NO_DEFINIDO}"
  echo "CUDA nvcc: $(nvcc --version 2>/dev/null | tail -n 1 || echo NO_DETECTADO)"
  echo "Memoria: $(free -h | awk '/^Mem:/ {print $2}')"
  echo "Espacio raíz disponible: $(df -h / | awk 'NR==2 {print $4}')"
  echo "Unitree Python: $(
    python3 -c 'import unitree_sdk2py; print(unitree_sdk2py.__file__)' \
      2>/dev/null \
      || echo NO_DETECTADO
  )"
  echo "ros2: $(command -v ros2 2>/dev/null || echo NO_DETECTADO)"
  echo "nvcc: $(command -v nvcc 2>/dev/null || echo NO_DETECTADO)"
  echo "arecord: $(command -v arecord 2>/dev/null || echo NO_DETECTADO)"
  echo "aplay: $(command -v aplay 2>/dev/null || echo NO_DETECTADO)"

  echo
  echo "[SEGURIDAD] Este diagnóstico no instaló ni modificó paquetes."
  echo "[LOG] $ARCHIVO_SALIDA"

} 2>&1 | tee "$ARCHIVO_SALIDA"

echo
echo "Diagnóstico guardado en:"
echo "$ARCHIVO_SALIDA"
