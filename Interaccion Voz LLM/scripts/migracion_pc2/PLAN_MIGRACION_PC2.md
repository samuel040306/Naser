# Plan de migración aislada al PC2 del Unitree G1

## Objetivo

Migrar el agente local de voz al PC2 sin modificar ni reemplazar las
dependencias existentes de ROS 2, Unitree SDK2, CycloneDDS, JetPack,
CUDA o Python del sistema.

## Principios de aislamiento

1. No utilizar `sudo pip`, `sudo pip3` ni instalaciones globales de Python.
2. No actualizar o reemplazar el Python del sistema.
3. No reinstalar JetPack, CUDA, cuDNN ni controladores NVIDIA.
4. No reemplazar ROS 2 Foxy ni CycloneDDS.
5. No instalar whisper.cpp en `/usr`, `/usr/local` o `/opt`.
6. No modificar el SDK de Unitree instalado globalmente.
7. No crear servicios de systemd hasta terminar las pruebas manuales.
8. No permitir más de un publicador de control sobre `rt/arm_sdk`.
9. No ejecutar poses mientras el robot camina o cambia de modo.
10. Mantener el robot detenido durante las primeras pruebas.

## Ubicaciones aisladas previstas

- Repositorio:
  dentro de la carpeta de Robotics del usuario `unitree`.

- Entorno Python:
  `Interaccion Voz LLM/.venv_pc2`

- Código externo:
  `Interaccion Voz LLM/externos/whisper.cpp`

- Compilación del PC2:
  `Interaccion Voz LLM/externos/whisper.cpp/build-pc2`

- Modelos:
  `Interaccion Voz LLM/scripts/recursos/modelos`

- Logs:
  `Interaccion Voz LLM/scripts/logs`

## Fases

1. Diagnóstico de solo lectura.
2. Revisión de compatibilidad.
3. Creación del entorno virtual aislado.
4. Compilación local de whisper.cpp contra el CUDA ya instalado.
5. Instalación de dependencias Python únicamente dentro del entorno virtual.
6. Benchmark del STT en el PC2.
7. Integración del micrófono UDP del G1.
8. Integración del altavoz.
9. Integración del router físico de poses.
10. Prueba completa con el robot detenido.

## Estrategia de reversión

Mientras se respeten estas rutas, la instalación podrá revertirse eliminando:

- `.venv_pc2`
- `externos/whisper.cpp/build-pc2`
- los modelos descargados
- los archivos temporales y logs

La reversión no deberá requerir modificar paquetes del sistema.
