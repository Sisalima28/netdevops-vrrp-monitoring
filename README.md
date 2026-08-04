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
\`\`\`bash
python main.py
\`\`\`

## Ejecución de playbooks
\`\`\`bash
ansible-playbook -i inventario/inventario.ini.example playbooks/vrrp_config.yml
\`\`\`

## Datos experimentales
La carpeta `data/` contiene los tiempos individuales de las 20 repeticiones
por método (manual/automatizado) para aprovisionamiento y monitoreo,
usados en el artículo asociado a este proyecto.
