import subprocess
import os
import re
import platform
import json
from fastapi import Body
import ipaddress
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pysnmp.hlapi.v3arch import (
    get_cmd,
    SnmpEngine, 
    CommunityData, 
    UdpTransportTarget, 
    ContextData, 
    ObjectType, 
    ObjectIdentity
)
import asyncio
import socket
import threading
from datetime import datetime
import time

app = FastAPI()

trafico_cache = {}
logs_syslog = []

# Aseguramos que la carpeta static exista para evitar errores al montar
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INVENTORY_PATH = os.path.join(BASE_DIR, "inventario", "inventario.ini")

def obtener_dispositivos_inventario():
    dispositivos = []
    if os.path.exists(INVENTORY_PATH):
        with open(INVENTORY_PATH, "r") as f:
            for linea in f:
                # RegEx mejorada para evitar capturar comentarios del .ini
                match = re.match(r'^(\S+)\s+ansible_host=([\d\.]+)', linea.strip())
                if match:
                    nombre = match.group(1)
                    nombre_up = nombre.upper()
                    ip = match.group(2)
                    
                    # Lógica de detección de tipo
                    if "L3SW" in nombre_up:
                        tipo = "l3switch"
                    elif "SW" in nombre_up:
                        tipo = "switch"
                    elif "R" in nombre_up:
                        tipo = "router"
                    else:
                        tipo = "generic"
                    
                    # Ajusta esta ruta si tus fotos están en static/img/
                    imagen_url = f"/static/{tipo}.png"
                    
                    dispositivos.append({
                        "nombre": nombre,
                        "ip": ip,
                        "tipo": tipo,
                        "imagen": imagen_url,
                        "estado": "Cargado"
                    })
    return dispositivos

def servidor_syslog():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", 5514))

    while True:
        data, addr = sock.recvfrom(4096)
        mensaje = data.decode(errors="ignore").strip()

        #   OJO QUE HE CAMBIADO ESTO
        #   logs_syslog.insert(0, {
        #        "ip": addr[0],     
        #        "mensaje": mensaje,
        #        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        #    })

        hostname = "DESCONOCIDO"

        match = re.search(r"\d+:\s+([A-Za-z0-9_-]+):", mensaje)

        if match:
            hostname = match.group(1)

        logs_syslog.insert(0, {
            "ip": addr[0],
            "hostname": hostname.upper(),
            "mensaje": mensaje,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        if len(logs_syslog) > 300:
            logs_syslog[:] = logs_syslog[:300]

def verificar_ping(ip):
    sistema = platform.system().lower()
    if sistema == "windows":
        comando = ["ping", "-n", "1", "-w", "3000", ip]
    else:
        # En Linux/macOS, -W es el timeout en segundos
        comando = ["ping", "-c", "1", "-W", "3", ip]
    
    try:
        resultado = subprocess.call(comando, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return resultado == 0
    except:
        return False

async def consulta_snmp(ip, oid):
    try:
        transport = await UdpTransportTarget.create((ip, 161), timeout=1, retries=0)
        
        errorIndication, errorStatus, errorIndex, varBinds = await get_cmd(
            SnmpEngine(),
            CommunityData('Utmach', mpModel=0),
            transport, 
            ContextData(),
            ObjectType(ObjectIdentity(oid))
        )
        
        if errorIndication or errorStatus:
            return None
            
        for varBind in varBinds:
            return str(varBind[1])
            
    except Exception as e:
        print(f"Error SNMP en {ip}: {e}")
        return None

@app.get("/api/syslog")
async def api_syslog(hostname: str = None, limit: int = 50):

    if hostname:

        logs_filtrados = [
            log for log in logs_syslog
            if log.get("hostname", "").upper() == hostname.upper()
        ]

        return logs_filtrados[:limit]

    return logs_syslog[:limit]

@app.get("/api/snmp/{ip}")
async def api_snmp(ip: str):

    dispositivo = {
        "hostname_real": ip,
        "uptime_raw": "Sin respuesta",
        "cpu": 0,
        "online": False
    }

    tareas = [
        consulta_snmp(ip, ".1.3.6.1.2.1.1.5.0"),
        consulta_snmp(ip, ".1.3.6.1.2.1.1.3.0"),
        consulta_snmp(ip, ".1.3.6.1.4.1.9.2.1.57.0")
    ]

    res = await asyncio.gather(*tareas)

    if any(res):

        hostname = res[0] or ip

        hostname = hostname.split(".")[0]

        dispositivo["hostname_real"] = hostname
        
        dispositivo["uptime_raw"] = res[1] or "N/A"

        try:
            dispositivo["cpu"] = int(res[2])
        except:
            dispositivo["cpu"] = 0

        dispositivo["online"] = True

    return dispositivo

@app.get("/monitoreo", response_class=HTMLResponse)
async def vista_monitoreo(request: Request):

    dispositivos = obtener_dispositivos_inventario()

    return templates.TemplateResponse(
        request=request,
        name="monitoreo.html",
        context={
            "request": request,
            "dispositivos": dispositivos,
            "seccion": "monitoreo"
        }
    )

@app.get("/", response_class=HTMLResponse)
async def principal(request: Request):

    dispositivos = obtener_dispositivos_inventario()

    return templates.TemplateResponse(
        request=request,
        name="principal.html",
        context={
            "request": request,
            "dispositivos": dispositivos,
            "seccion": "principal"
        }
    )
    
@app.get("/api/ping/{ip}")
async def api_ping(ip: str):

    online = verificar_ping(ip)

    return {
        "online": online,
        "estado": "Encendido" if online else "Apagado",
        "color": "green" if online else "red"
    }

@app.get("/automatizacion", response_class=HTMLResponse)
async def vista_automatizacion(request: Request):

    dispositivos = obtener_dispositivos_inventario()

    l3switches = [
        d for d in dispositivos
        if d["tipo"] == "l3switch"
    ]

    return templates.TemplateResponse(
        request=request,
        name="automatizacion.html",
        context={
            "request": request,
            "dispositivos": dispositivos,
            "l3switches": l3switches,
            "seccion": "automatizacion"
        }
    )
    
@app.get("/api/trafico/{ip}/{ifindex}")
async def api_trafico(ip: str, ifindex: int):

    oid_rx = f"1.3.6.1.2.1.2.2.1.10.{ifindex}"

    oid_tx = f"1.3.6.1.2.1.2.2.1.16.{ifindex}"

    rx_actual = await consulta_snmp(ip, oid_rx)

    tx_actual = await consulta_snmp(ip, oid_tx)

    if not rx_actual or not tx_actual:

        return {
            "rx": "0 bps",
            "tx": "0 bps"
        }

    rx_actual = int(rx_actual)

    tx_actual = int(tx_actual)

    clave = f"{ip}-{ifindex}"

    ahora = asyncio.get_event_loop().time()

    if clave not in trafico_cache:

        trafico_cache[clave] = {

            "rx": rx_actual,
            "tx": tx_actual,
            "time": ahora

        }

        return {
            "rx": "Calculando...",
            "tx": "Calculando..."
        }

    anterior = trafico_cache[clave]

    delta_tiempo = ahora - anterior["time"]

    if delta_tiempo <= 0:

        delta_tiempo = 1

    rx_bps = ((rx_actual - anterior["rx"]) * 8) / delta_tiempo

    tx_bps = ((tx_actual - anterior["tx"]) * 8) / delta_tiempo

    trafico_cache[clave] = {

        "rx": rx_actual,
        "tx": tx_actual,
        "time": ahora

    }

    def formatear(valor):

        if valor >= 1000000:
            return f"{valor / 1000000:.2f} Mbps"

        if valor >= 1000:
            return f"{valor / 1000:.2f} Kbps"

        return f"{valor:.0f} bps"

    return {

        "rx": formatear(rx_bps),
        "tx": formatear(tx_bps)

    }
    
# Uso de playbooks
def obtener_interfaces_ansible(host):

    try:

        playbook_path = os.path.join(
            BASE_DIR,
            "playbooks",
            "interfaces.yml"
        )

        inventory_path = os.path.join(
            BASE_DIR,
            "inventario",
            "inventario.ini"
        )

        comando = [

            "ansible-playbook",

            "-i",
            inventory_path,

            playbook_path,

            "-l",
            host

        ]

        resultado = subprocess.run(

            comando,
            capture_output=True,
            text=True

        )

        salida = resultado.stdout

        interfaces = []

        # Buscar contenido del msg
        match = re.search(r'"msg":\s*"(.+)"', salida, re.DOTALL)

        if not match:
            return []

        contenido = match.group(1)

        # Convertir \n en saltos reales
        contenido = contenido.replace("\\n", "\n")

        lineas = contenido.splitlines()

        for linea in lineas:

            linea = linea.strip()

            if (
                linea.startswith("Interface")
                or linea == ""
            ):
                continue

            match = re.match(

                r"(\S+)\s+"          # Interface
                r"(\S+)\s+"          # IP
                r"\S+\s+"            # OK?
                r"\S+\s+"            # Method
                r"(.+?)\s+"          # Status
                r"(\S+)$",           # Protocol

                linea
            )

            if not match:
                continue

            nombre = match.group(1)

            ip = match.group(2)

            status = match.group(3).strip()

            protocol = match.group(4).strip()

            interfaces.append({

                "ifindex": len(interfaces) + 1,

                "nombre": nombre,
                "ip": ip,
                "status": status,
                "protocol": protocol

            })

        return interfaces

    except Exception as e:

        print(f"ERROR ANSIBLE {host}: {e}")

        return []


@app.get("/api/interfaces/{nombre}")
async def api_interfaces(nombre: str):

    interfaces = await asyncio.to_thread(
        obtener_interfaces_ansible,
        nombre
    )

    return interfaces

# =========================
# VRRP
# =========================

def obtener_estado_vrrp():

    try:

        playbook_path = os.path.join(
            BASE_DIR,
            "playbooks",
            "verificar_vrrp.yml"
        )

        inventory_path = os.path.join(
            BASE_DIR,
            "inventario",
            "inventario.ini"
        )

        comando = [

            "ansible-playbook",
            "-i",
            inventory_path,
            playbook_path

        ]

        resultado = subprocess.run(
            comando,
            capture_output=True,
            text=True
        )

        salida = resultado.stdout

        dispositivos = {}

        host_actual = None

        for linea in salida.splitlines():

            # Detectar host
            match_host = re.search(
                r"ok: \[(.+?)\]",
                linea
            )

            if match_host:

                host_actual = match_host.group(1)

                dispositivos[host_actual] = []

                continue

            # Parse VRRP
            match_vrrp = re.search(

                r"Vl(\d+)\s+"          # VLAN
                r"(\d+)\s+"            # Grupo
                r"(\d+)\s+"            # Prioridad
                r"(\d+)\s+"            # Tiempo
                r"(Y|N)\s+"            # Preempt
                r"(Master|Backup)\s+"  # Estado
                r"([\d\.]+)\s+"        # Master addr
                r"([\d\.]+)",          # VIP

                linea

            )

            if match_vrrp and host_actual:

                dispositivos[host_actual].append({

                    "vlan": match_vrrp.group(1),

                    "grupo": match_vrrp.group(2),

                    "prioridad": match_vrrp.group(3),

                    "tiempo": match_vrrp.group(4),

                    "preempt": match_vrrp.group(5),

                    "estado": match_vrrp.group(6).upper(),

                    "master_addr": match_vrrp.group(7),

                    "vip": match_vrrp.group(8)

                })

        return dispositivos

    except Exception as e:

        print(f"ERROR VRRP: {e}")

        return {}


@app.get("/api/vrrp")
async def api_vrrp():

    data = await asyncio.to_thread(
        obtener_estado_vrrp
    )

    return data

# GENERAR SCRIPT PARA ANSIBLE (VRRP)
@app.post("/api/generar-vrrp")
async def generar_vrrp(data: dict = Body(...)):

    vlan_id = data.get("vlan_id")
    vlan_name = data.get("vlan_name", "")
    red = data.get("red")
    switches = data.get("switches", [])
    master = data.get("master")
    preempt = data.get("preempt", True)
    modo_ip = data.get("modo_ip", "automatico")
    ips_manuales = data.get("ips_manuales", {})

    try:

        network = ipaddress.ip_network(red, strict=False)

        hosts = list(network.hosts())

        vip = str(hosts[0])

        configuraciones = {}

        contador = 1

        for sw in switches:

            if modo_ip == "manual":

                ip_local = ips_manuales.get(sw)

            else:

                ip_local = str(hosts[contador])

                contador += 1

            prioridad = 120 if sw == master else 100

            config = []

            config.append(f"vlan {vlan_id}")

            if vlan_name:
                config.append(f" name {vlan_name}")

            config.extend([
                f"interface Vlan{vlan_id}",
                " no shutdown",
                f" ip address {ip_local} {network.netmask}",
                f" vrrp {vlan_id} ip {vip}",
                f" vrrp {vlan_id} priority {prioridad}"
            ])

            if preempt:
                config.append(
                    f" vrrp {vlan_id} preempt"
                )

            configuraciones[sw] = "\n".join(config)

        return {
            "success": True,
            "vip": vip,
            "configs": configuraciones
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
        
        
# APLICAR VRRP
@app.post("/api/aplicar-vrrp")
async def aplicar_vrrp(data: dict = Body(...)):

    try:

        configs = data.get("configs", {})

        resultados = {}
        
        inicio = time.perf_counter()

        for sw, config in configs.items():

            archivo_tmp = os.path.join(
                BASE_DIR,
                f"{sw}_tmp.cfg"
            )

            with open(archivo_tmp, "w") as f:
                f.write(config)

            comando = [

                "ansible",

                sw,

                "-i",
                INVENTORY_PATH,

                "-m",
                "cisco.ios.ios_config",

                "-a",
                f"src={archivo_tmp}"

            ]

            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True
            )

            resultados[sw] = {

                "ok": resultado.returncode == 0,

                "stdout": resultado.stdout,

                "stderr": resultado.stderr

            }

            # borrar archivo temporal
            os.remove(archivo_tmp)

        fin = time.perf_counter()

        tiempo_total = round(fin - inicio, 3)

        print("\n" + "="*60)
        print(f"TIEMPO TOTAL AUTOMATIZACIÓN: {tiempo_total} segundos")
        print("="*60 + "\n")

        return {

            "success": True,

            "resultados": resultados

        }

    except Exception as e:

        return {

            "success": False,

            "error": str(e)

        }

@app.get("/api/consulta-completa/{nombre}")
async def consulta_completa(nombre: str):

    dispositivos = obtener_dispositivos_inventario()
    dispositivo = next((d for d in dispositivos if d["nombre"] == nombre), None)

    if not dispositivo:
        return {"success": False, "error": "Dispositivo no encontrado"}

    ip = dispositivo["ip"]

    inicio = time.perf_counter()

    # SNMP: hostname, uptime, cpu (concurrente)
    snmp_data = await api_snmp(ip)

    # Interfaces vía Ansible (bloqueante, en hilo)
    interfaces = await asyncio.to_thread(obtener_interfaces_ansible, nombre)

    # Syslog filtrado (ya en memoria, instantáneo)
    logs = [
        log for log in logs_syslog
        if log.get("hostname", "").upper() == nombre.upper()
    ][:50]

    fin = time.perf_counter()
    tiempo_total = round(fin - inicio, 3)

    print("\n" + "="*60)
    print(f"TIEMPO TOTAL CONSULTA MONITOREO ({nombre}): {tiempo_total} segundos")
    print("="*60 + "\n")

    # Tráfico se consulta DESPUÉS de cerrar el cronómetro,
    # ya que requiere una lectura previa en cache para calcular bps real
    trafico = {}
    for iface in interfaces:
        trafico[iface["nombre"]] = await api_trafico(ip, iface["ifindex"])

    return {
        "success": True,
        "tiempo_total": tiempo_total,
        "snmp": snmp_data,
        "interfaces": interfaces,
        "trafico": trafico,
        "syslog": logs
    }

syslog_thread = threading.Thread(target=servidor_syslog, daemon=True)
syslog_thread.start()