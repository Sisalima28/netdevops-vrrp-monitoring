# NetDevOps VRRP Monitoring

Sistema de automatización y monitoreo de redes basado en Python, Ansible y FastAPI,
desarrollado como parte de un artículo académico sobre NetDevOps.

## Estructura del repositorio
- `playbooks/` — Playbooks de Ansible para configuración de VRRP, SNMP, Syslog e interfaces.
- `inventario/` — Inventario de ejemplo de Ansible (`inventario.ini.example`).
- `static/` y `templates/` — Frontend del dashboard (FastAPI + Jinja2).
- `topology/` — Topología de laboratorio exportada de EVE-NG.
- `data/` — Datos crudos de las pruebas experimentales (tiempos de aprovisionamiento y monitoreo).
- `main.py` — Backend de la aplicación (FastAPI).

## Requisitos
- Python 3.12.3
- Ansible core 2.18.10
- EVE-NG (Community o Professional) para recrear la topología de pruebas

## Instalación
\`\`\`bash
pip install -r requirements.txt
\`\`\`

## Ejecución

1. Activa el entorno virtual:
\`\`\`bash
source venv/bin/activate
\`\`\`

2. Inicia el servidor:
\`\`\`bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
\`\`\`

3. Abre el dashboard web en el navegador:
   - Si accedes desde la misma máquina: `http://127.0.0.1:8000`
   - Si accedes desde otra máquina o la máquina anfitriona (caso de una VM): 
     `http://IP_ASIGNADA_MAQUINA_VIRTUAL:8000`

## Uso de los playbooks

Los playbooks de Ansible no se ejecutan manualmente por consola: el 
sistema los invoca automáticamente desde el backend de FastAPI cuando 
se interactúa con los botones correspondientes en el dashboard web 
(por ejemplo, "Configurar VRRP", "Configurar SNMP", "Configurar Syslog"). 
Cada acción del dashboard dispara la ejecución del playbook asociado 
sobre los dispositivos definidos en `inventario/`.

## Datos experimentales
La carpeta `data/` contiene los tiempos individuales de las 20 repeticiones
por método (manual/automatizado) para aprovisionamiento y monitoreo,
usados en el artículo asociado a este proyecto.
