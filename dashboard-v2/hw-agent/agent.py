#!/usr/bin/env python3
"""
Hardware Agent V2 - Collecte avancée des stats hardware via WebSocket.

Fonctionnalités:
- CPU: usage, fréquence, cores, nom via WMI
- RAM: usage, détails
- GPU: NVIDIA via GPUtil
- Disques: noms via WMI, usage
- Réseau: vitesse up/down
- Processus: top 5 par RAM
- Système: OS, uptime
- Optionnel: LibreHardwareMonitor pour temp/power/fan

Configuration via .env:
    WS_URL=wss://api.dashboard.example.com/hardware/ws/agent
    HW_AGENT_TOKEN=your-secret-token
    LHM_URL=http://localhost:8085 (optionnel)
"""
import os
import sys
import json
import asyncio
import platform
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

os.environ['PYTHONUNBUFFERED'] = '1'

import psutil
import websockets
from dotenv import load_dotenv

load_dotenv()

# Configuration
WS_URL = os.getenv("WS_URL", "ws://localhost:8000/hardware/ws/agent")
HW_AGENT_TOKEN = os.getenv("HW_AGENT_TOKEN", "")
INTERVAL = int(os.getenv("INTERVAL", "2"))
LHM_URL = os.getenv("LHM_URL", "")  # LibreHardwareMonitor Web Server URL

# Cache pour calcul des vitesses réseau
_last_net_io = None
_last_net_time = None


def get_wmi_cpu_name() -> str:
    """Récupère le vrai nom du CPU via WMI (Windows only)."""
    try:
        import wmi
        c = wmi.WMI()
        for cpu in c.Win32_Processor():
            return cpu.Name.strip()
    except Exception:
        pass

    # Fallback: essayer via platform
    try:
        import subprocess
        result = subprocess.run(
            ['wmic', 'cpu', 'get', 'name'],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in result.stdout.split('\n') if l.strip() and l.strip() != 'Name']
        if lines:
            return lines[0]
    except Exception:
        pass

    return platform.processor() or "Unknown CPU"


def get_disk_names() -> Dict[str, str]:
    """Récupère les noms/labels des disques via WMI."""
    disk_names = {}
    try:
        import wmi
        c = wmi.WMI()
        for disk in c.Win32_LogicalDisk():
            label = disk.VolumeName or disk.Description or "Local Disk"
            disk_names[disk.DeviceID] = label
    except Exception:
        pass

    if not disk_names:
        try:
            import subprocess
            result = subprocess.run(
                ['wmic', 'logicaldisk', 'get', 'deviceid,volumename'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n')[1:]:
                parts = line.strip().split()
                if len(parts) >= 1:
                    drive = parts[0]
                    name = ' '.join(parts[1:]) if len(parts) > 1 else "Local Disk"
                    disk_names[drive] = name or "Local Disk"
        except Exception:
            pass

    return disk_names


def get_os_info() -> Dict[str, str]:
    """Récupère les infos OS détaillées."""
    os_name = f"Windows {platform.release()}"

    try:
        import subprocess
        result = subprocess.run(
            ['wmic', 'os', 'get', 'caption'],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in result.stdout.split('\n') if l.strip() and 'Caption' not in l]
        if lines:
            os_name = lines[0]
    except Exception:
        pass

    # Uptime
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_delta = datetime.now() - boot_time
    hours, remainder = divmod(int(uptime_delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return {
        "name": os_name,
        "uptime": uptime_str,
        "hostname": platform.node(),
    }


def get_cpu_stats() -> Dict[str, Any]:
    """Collecte les stats CPU complètes."""
    # Usage global et par core
    cpu_percent = psutil.cpu_percent(interval=0.1)
    cpu_percent_per_core = psutil.cpu_percent(interval=0, percpu=True)

    cpu_freq = psutil.cpu_freq()
    cpu_count = psutil.cpu_count()
    cpu_count_physical = psutil.cpu_count(logical=False)

    # Nom propre du CPU (cache après premier appel)
    if not hasattr(get_cpu_stats, '_cpu_name'):
        get_cpu_stats._cpu_name = get_wmi_cpu_name()

    return {
        "usage": cpu_percent,
        "core_usage": cpu_percent_per_core,
        "temp": None,  # Sera rempli par LHM si disponible
        "power": None,
        "fan_speed": None,
        "frequency": cpu_freq.current if cpu_freq else None,
        "frequency_max": cpu_freq.max if cpu_freq else None,
        "cores": cpu_count,
        "physical_cores": cpu_count_physical,
        "name": get_cpu_stats._cpu_name,
    }


def get_ram_stats() -> Dict[str, Any]:
    """Collecte les stats RAM."""
    mem = psutil.virtual_memory()
    return {
        "used_percent": mem.percent,
        "used_gb": round(mem.used / (1024 ** 3), 2),
        "total_gb": round(mem.total / (1024 ** 3), 2),
        "available_gb": round(mem.available / (1024 ** 3), 2),
    }


def get_gpu_stats() -> Optional[Dict[str, Any]]:
    """Collecte les stats GPU NVIDIA."""
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()

        if not gpus:
            return None

        gpu = gpus[0]
        return {
            "name": gpu.name,  # Nom complet
            "usage": round(gpu.load * 100, 1),
            "temp": gpu.temperature,
            "memory_used": round(gpu.memoryUsed, 0),
            "memory_total": round(gpu.memoryTotal, 0),
            "memory_percent": round((gpu.memoryUsed / gpu.memoryTotal) * 100, 1) if gpu.memoryTotal else 0,
            "fan_speed": None,  # GPUtil ne fournit pas ça
            "power": None,
        }
    except ImportError:
        return None
    except Exception as e:
        print(f"[GPU] Erreur: {e}")
        return None


def get_storage_stats() -> List[Dict[str, Any]]:
    """Collecte les stats disques avec noms."""
    # Récupérer les noms des disques
    if not hasattr(get_storage_stats, '_disk_names'):
        get_storage_stats._disk_names = get_disk_names()

    disk_names = get_storage_stats._disk_names
    disks = []

    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            drive_letter = partition.device.rstrip('\\')
            disk_name = disk_names.get(drive_letter, "Local Disk")

            disks.append({
                "device": drive_letter,
                "name": disk_name,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "used_gb": round(usage.used / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            continue

    return disks


def get_network_stats() -> Dict[str, Any]:
    """Calcule les vitesses réseau."""
    global _last_net_io, _last_net_time

    current_io = psutil.net_io_counters()
    current_time = time.time()

    if _last_net_io is None:
        _last_net_io = current_io
        _last_net_time = current_time
        return {"download_speed": 0, "upload_speed": 0}

    # Calculer la vitesse en Mbps
    time_delta = current_time - _last_net_time
    if time_delta > 0:
        download_speed = ((current_io.bytes_recv - _last_net_io.bytes_recv) / time_delta) * 8 / 1_000_000
        upload_speed = ((current_io.bytes_sent - _last_net_io.bytes_sent) / time_delta) * 8 / 1_000_000
    else:
        download_speed = 0
        upload_speed = 0

    _last_net_io = current_io
    _last_net_time = current_time

    return {
        "download_speed": round(download_speed, 2),
        "upload_speed": round(upload_speed, 2),
        "bytes_recv": current_io.bytes_recv,
        "bytes_sent": current_io.bytes_sent,
    }


def get_top_processes(n: int = 5) -> List[Dict[str, Any]]:
    """Récupère les N processus utilisant le plus de RAM."""
    processes = []

    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        try:
            mem_info = proc.info['memory_info']
            if mem_info:
                processes.append({
                    "id": proc.info['pid'],
                    "name": proc.info['name'],
                    "memory_mb": round(mem_info.rss / (1024 * 1024), 1),
                })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Trier par mémoire et prendre les top N
    processes.sort(key=lambda x: x['memory_mb'], reverse=True)
    return processes[:n]


def try_get_lhm_data() -> Optional[Dict[str, Any]]:
    """Essaie de récupérer les données de LibreHardwareMonitor."""
    if not LHM_URL:
        return None

    try:
        import urllib.request
        with urllib.request.urlopen(f"{LHM_URL}/data.json", timeout=2) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


def parse_lhm_data(lhm_data: Dict) -> Dict[str, Any]:
    """Parse les données LHM pour extraire temp/power/fan."""
    result = {
        "cpu_temp": None,
        "cpu_power": None,
        "cpu_fan": None,
        "gpu_temp": None,
        "gpu_power": None,
        "gpu_fan": None,
    }

    if not lhm_data:
        return result

    def parse_value(value: str, unit: str) -> Optional[float]:
        """Parse une valeur en enlevant l'unité."""
        try:
            return float(value.replace(unit, "").replace(",", ".").strip())
        except:
            return None

    def find_values(node, path=""):
        """Parcours récursif pour trouver les valeurs."""
        if isinstance(node, dict):
            text = node.get("Text", "")
            value = node.get("Value", "")
            sensor_type = node.get("Type", "")

            # CPU Temperature - chercher "CPU Package" sous un CPU Intel/AMD
            if ("Intel Core" in path or "AMD" in path) and text == "CPU Package" and sensor_type == "Temperature":
                val = parse_value(value, "°C")
                if val is not None:
                    result["cpu_temp"] = val

            # CPU Power - chercher "CPU Package" dans Powers
            if ("Intel Core" in path or "AMD" in path) and text == "CPU Package" and sensor_type == "Power":
                val = parse_value(value, "W")
                if val is not None:
                    result["cpu_power"] = val

            # CPU Fan - chercher ventilateur/pompe avec RPM > 0
            if "Fan" in text and sensor_type == "Fan" and "NVIDIA" not in path and "GPU" not in text:
                val = parse_value(value, "RPM")
                if val is not None and val > 0:
                    if result["cpu_fan"] is None or "Pump" in text:
                        result["cpu_fan"] = int(val)

            # GPU Temperature - chercher "GPU Core" sous NVIDIA/AMD
            if ("NVIDIA" in path or "AMD Radeon" in path) and text == "GPU Core" and sensor_type == "Temperature":
                val = parse_value(value, "°C")
                if val is not None:
                    result["gpu_temp"] = val

            # GPU Fan
            if ("NVIDIA" in path or "AMD Radeon" in path) and text == "GPU" and sensor_type == "Fan":
                val = parse_value(value, "RPM")
                if val is not None:
                    result["gpu_fan"] = int(val)

            for child in node.get("Children", []):
                find_values(child, f"{path}/{text}")

    find_values(lhm_data)
    return result


def collect_all_stats() -> Dict[str, Any]:
    """Collecte toutes les stats hardware."""
    os_info = get_os_info()
    cpu = get_cpu_stats()
    gpu = get_gpu_stats()

    # Essayer LHM pour les données avancées
    lhm_data = try_get_lhm_data()
    if lhm_data:
        lhm_parsed = parse_lhm_data(lhm_data)
        if lhm_parsed["cpu_temp"]:
            cpu["temp"] = lhm_parsed["cpu_temp"]
        if lhm_parsed["cpu_power"]:
            cpu["power"] = lhm_parsed["cpu_power"]
        if lhm_parsed["cpu_fan"]:
            cpu["fan_speed"] = lhm_parsed["cpu_fan"]

    return {
        "cpu": cpu,
        "ram": get_ram_stats(),
        "gpu": gpu,
        "storage": get_storage_stats(),
        "network": get_network_stats(),
        "processes": get_top_processes(5),
        "os": os_info["name"],
        "uptime": os_info["uptime"],
        "hostname": os_info["hostname"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def run_agent():
    """Boucle principale de l'agent."""
    if not HW_AGENT_TOKEN:
        print("[ERROR] HW_AGENT_TOKEN non configure!")
        sys.exit(1)

    ws_url = f"{WS_URL}?token={HW_AGENT_TOKEN}"

    print(f"[Agent] Serveur: {WS_URL}")
    print(f"[Agent] Intervalle: {INTERVAL}s")
    if LHM_URL:
        print(f"[Agent] LibreHardwareMonitor: {LHM_URL}")
    print()

    reconnect_delay = 5

    while True:
        try:
            print(f"[Agent] Connexion...")

            async with websockets.connect(ws_url, ping_interval=30, ping_timeout=10) as ws:
                print("[Agent] Connecte!")
                reconnect_delay = 5

                while True:
                    try:
                        stats = collect_all_stats()
                        await ws.send(json.dumps(stats))

                        cpu = stats["cpu"]
                        ram = stats["ram"]
                        net = stats["network"]
                        temp_str = f"{cpu['temp']:.0f}°C" if cpu['temp'] else "N/A"

                        print(
                            f"[{datetime.now().strftime('%H:%M:%S')}] "
                            f"CPU: {cpu['usage']:.0f}% ({temp_str}) | "
                            f"RAM: {ram['used_percent']:.0f}% | "
                            f"Net: D:{net['download_speed']:.1f} U:{net['upload_speed']:.1f} Mbps"
                        )

                        await asyncio.sleep(INTERVAL)

                    except websockets.ConnectionClosed:
                        print("[Agent] Connexion fermee")
                        break

        except Exception as e:
            print(f"[Agent] Erreur: {e}, retry dans {reconnect_delay}s...")

        await asyncio.sleep(reconnect_delay)
        reconnect_delay = min(reconnect_delay * 2, 60)


def main():
    print("=" * 50)
    print("  Hardware Agent V2 - Dashboard")
    print("=" * 50)
    print()

    # Test initial
    print("[Test] Collecte des stats...")
    stats = collect_all_stats()
    print(f"  OS: {stats['os']}")
    print(f"  Uptime: {stats['uptime']}")
    print(f"  CPU: {stats['cpu']['name']}")
    print(f"  Cores: {stats['cpu']['physical_cores']} physical / {stats['cpu']['cores']} logical")
    print(f"  RAM: {stats['ram']['total_gb']} Go")
    if stats['gpu']:
        print(f"  GPU: {stats['gpu']['name']}")
    print(f"  Disques: {len(stats['storage'])}")
    for disk in stats['storage']:
        print(f"    - {disk['device']} {disk['name']} ({disk['used_gb']}/{disk['total_gb']} Go)")
    print(f"  Top Process: {stats['processes'][0]['name'] if stats['processes'] else 'N/A'}")
    print()

    try:
        asyncio.run(run_agent())
    except KeyboardInterrupt:
        print("\n[Agent] Arret")


if __name__ == "__main__":
    main()
