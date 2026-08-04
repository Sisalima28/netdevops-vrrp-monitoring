# Topología de laboratorio (EVE-NG)

Este archivo `.unl` contiene la topología usada en las pruebas del proyecto,
exportada desde EVE-NG Community Edition.

## Requisitos para importarla
- EVE-NG Community o Professional instalado.
- Imágenes de los siguientes dispositivos (no incluidas por licencia):
  - 2x Switch multicapa (L3SW1, L3SW2) — Cisco IOS, imagen
    `i86bi_linux_l2-adventerprisek9-ms.SSA.high_iron_20190423.bin`
  - 2x Switch de capa 2 (SW1, SW2)
  - 1x Router (R1)
- 4x nodos Linux/PC ligeros para simular los hosts finales (PC0-PC3).

## Cómo importar
1. Copiar `netdevops-lab.unl` a la carpeta de labs de tu servidor EVE-NG.
2. Asegurarse de tener las imágenes correspondientes ya cargadas en EVE-NG.
3. Abrir el laboratorio desde la interfaz web de EVE-NG.