#!/usr/bin/env python3
"""
Hardware Agent V2 - Collecte avancée des stats hardware via WebSocket.

Fonctionnalités:
- CPU: usage, fréquence, cores, nom via WMI, temp/power/fan via LHM WMI
- RAM: usage, détails
- GPU: NVIDIA via nvidia-smi
- Disques: noms via WMI, usage, températures via LHM WMI
- Réseau: vitesse up/down
- Processus: top 5 par RAM
- Système: OS, uptime

Configuration via .env:
    WS_URL=wss://api.dashboard.example.com/hardware/ws/agent
    HW_AGENT_TOKEN=your-secret-token
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

    # Uptime en jours/heures/minutes
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_delta = datetime.now() - boot_time
    total_seconds = int(uptime_delta.total_seconds())
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days > 0:
        uptime_str = f"{days}j {hours}h {minutes}min"
    else:
        uptime_str = f"{hours}h {minutes}min"

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
    """Collecte les stats GPU NVIDIA via nvidia-smi."""
    try:
        import subprocess
        result = subprocess.run(
            [
                'nvidia-smi',
                '--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total,fan.speed,power.draw',
                '--format=csv,noheader,nounits',
            ],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None

        line = result.stdout.strip().split('\n')[0]
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 7:
            return None

        def safe_float(val: str) -> float:
            try:
                return float(val)
            except (ValueError, TypeError):
                return 0

        return {
            "name": parts[0],
            "usage": safe_float(parts[2]),
            "temp": safe_float(parts[1]),
            "memory_used": safe_float(parts[3]),
            "memory_total": safe_float(parts[4]),
            "memory_percent": round(safe_float(parts[3]) / safe_float(parts[4]) * 100, 1) if safe_float(parts[4]) else 0,
            "fan_speed": safe_float(parts[5]),
            "power": safe_float(parts[6]),
        }
    except FileNotFoundError:
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


def get_lhm_sensors() -> Dict[str, Any]:
    """Récupère les capteurs via LibreHardwareMonitor WMI (root/LibreHardwareMonitor)."""
    result = {
        "cpu_temp": None,
        "cpu_power": None,
        "cpu_fan": None,
        "hdd_temps": {},  # identifier -> temp °C
    }

    try:
        import subprocess
        # Requête PowerShell unique pour tous les capteurs utiles
        ps_script = (
            "Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Sensor "
            "| Where-Object { $_.SensorType -in 'Temperature','Power','Fan' } "
            "| Select-Object Name, Value, SensorType, Parent, Identifier "
            "| ConvertTo-Json -Compress"
        )
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return result

        sensors = json.loads(proc.stdout)
        if isinstance(sensors, dict):
            sensors = [sensors]

        for s in sensors:
            name = s.get("Name", "")
            value = s.get("Value")
            stype = s.get("SensorType", "")
            parent = s.get("Parent", "")

            if value is None:
                continue
            # PowerShell peut retourner des float avec virgule dans le JSON
            if isinstance(value, str):
                value = float(value.replace(",", "."))

            # CPU Package Temperature
            if name == "CPU Package" and stype == "Temperature" and "/intelcpu/" in parent:
                result["cpu_temp"] = round(value, 1)

            # CPU Package Power
            elif name == "CPU Package" and stype == "Power" and "/intelcpu/" in parent:
                result["cpu_power"] = round(value, 1)

            # Fan/Pump avec RPM > 0 (prendre la pompe AIO si dispo, sinon premier fan actif)
            elif stype == "Fan" and value > 0 and "/gpu" not in parent:
                if result["cpu_fan"] is None or "Pump" in name:
                    result["cpu_fan"] = int(value)

            # HDD/NVMe temperatures
            elif stype == "Temperature" and ("/hdd/" in parent or "/nvme/" in parent):
                result["hdd_temps"][parent] = round(value, 1)

    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[LHM] Erreur: {e}")

    return result


def collect_all_stats() -> Dict[str, Any]:
    """Collecte toutes les stats hardware."""
    os_info = get_os_info()
    cpu = get_cpu_stats()
    gpu = get_gpu_stats()
    storage = get_storage_stats()

    # LHM WMI pour temp/power/fan CPU + HDD temps
    lhm = get_lhm_sensors()
    if lhm["cpu_temp"] is not None:
        cpu["temp"] = lhm["cpu_temp"]
    if lhm["cpu_power"] is not None:
        cpu["power"] = lhm["cpu_power"]
    if lhm["cpu_fan"] is not None:
        cpu["fan_speed"] = lhm["cpu_fan"]

    # Températures HDD/NVMe
    disk_temps = _get_disk_temps(lhm["hdd_temps"])

    return {
        "cpu": cpu,
        "ram": get_ram_stats(),
        "gpu": gpu,
        "storage": storage,
        "network": get_network_stats(),
        "processes": get_top_processes(5),
        "disk_temps": disk_temps,
        "os": os_info["name"],
        "uptime": os_info["uptime"],
        "hostname": os_info["hostname"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _get_disk_temps(hdd_temps: Dict[str, float]) -> List[Dict[str, Any]]:
    """Construit la liste des températures disques avec noms LHM."""
    if not hdd_temps:
        return []

    # Récupérer les noms des disques physiques LHM (cache)
    if not hasattr(_get_disk_temps, '_hw_map'):
        try:
            import subprocess
            ps = (
                "Get-CimInstance -Namespace root/LibreHardwareMonitor -ClassName Hardware "
                "| Where-Object HardwareType -in 'Storage' "
                "| Select-Object Name, Identifier "
                "| ConvertTo-Json -Compress"
            )
            proc = subprocess.run(
                ['powershell', '-NoProfile', '-Command', ps],
                capture_output=True, text=True, timeout=5,
            )
            hw_list = json.loads(proc.stdout) if proc.stdout.strip() else []
            if isinstance(hw_list, dict):
                hw_list = [hw_list]
            _get_disk_temps._hw_map = {
                h["Identifier"]: h["Name"] for h in hw_list
            }
        except Exception:
            _get_disk_temps._hw_map = {}

    result = []
    for identifier, temp in sorted(hdd_temps.items()):
        name = _get_disk_temps._hw_map.get(identifier, identifier)
        result.append({"name": name, "temp": temp})
    return result


async def run_agent():
    """Boucle principale de l'agent."""
    if not HW_AGENT_TOKEN:
        print("[ERROR] HW_AGENT_TOKEN non configure!")
        sys.exit(1)

    ws_url = f"{WS_URL}?token={HW_AGENT_TOKEN}"

    print(f"[Agent] Serveur: {WS_URL}")
    print(f"[Agent] Intervalle: {INTERVAL}s")
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
