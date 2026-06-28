"""ADB device and port scanner for running emulators."""

import logging
import os
import re
import socket
from typing import TypedDict

import psutil
from adb_auto_player.device.adb.adb_client import AdbClientHelper


class _EmulatorInfo(TypedDict):
    ports: list[int]
    name: str


# Known emulators and their process names / common ports
EMULATORS: dict[str, _EmulatorInfo] = {
    "dnplayer.exe": {
        "ports": [5555, 5557, 5559, 5561, 5563],
        "name": "LDPlayer",
    },
    "ldboxheadless.exe": {
        "ports": [5555, 5557, 5559, 5561, 5563],
        "name": "LDPlayer VM",
    },
    "hd-player.exe": {
        "ports": list(range(5555, 5566)),
        "name": "BlueStacks",
    },
    "nox.exe": {
        "ports": [62001, 62025, 62026, 62027],
        "name": "NoxPlayer",
    },
    "noxvmhandle.exe": {
        "ports": [62001, 62025, 62026, 62027],
        "name": "NoxPlayer VM",
    },
    "memu.exe": {
        "ports": [21503, 21513, 21523],
        "name": "MEmu",
    },
    "memuheadless.exe": {
        "ports": [21503, 21513, 21523],
        "name": "MEmu VM",
    },
    "mumuplayer.exe": {
        "ports": [7555, 16384],
        "name": "MuMu Player",
    },
    "nemuplayer.exe": {
        "ports": [7555, 16384],
        "name": "MuMu Player Classic",
    },
    "emulator.exe": {
        "ports": [5554, 5556, 5558, 5560],
        "name": "Android Emulator",
    },
}


def is_port_open(port: int) -> bool:
    """Check if a TCP port is open on localhost."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            s.connect(("127.0.0.1", port))
            return True
    except Exception:
        return False


def _get_running_emulators_and_ports() -> tuple[list[str], set[int]]:
    """Scan running processes for emulators and extract their ports."""
    running_emulators = []
    ports = set()
    for proc in psutil.process_iter(["name"]):
        try:
            name = proc.info["name"]
            if not name:
                continue
            name_lower = name.lower()
            if name_lower in EMULATORS:
                running_emulators.append(name_lower)
                try:
                    for conn in proc.connections(kind="tcp"):
                        is_loopback = conn.laddr.ip in ("127.0.0.1", "0.0.0.0")
                        if conn.status == psutil.CONN_LISTEN or is_loopback:
                            ports.add(conn.laddr.port)
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
            pass
    return running_emulators, ports


def _get_bluestacks_ports() -> set[int]:
    """Parse BlueStacks config files to find configured ADB ports."""
    ports = set()
    program_data = os.environ.get("PROGRAMDATA", "C:\\ProgramData")
    bst_config = os.path.join(program_data, "BlueStacks_nxt", "bluestacks.conf")
    if os.path.exists(bst_config):
        try:
            with open(bst_config, errors="ignore") as f:
                for line in f:
                    if "adb_port" in line:
                        match = re.search(r'adb_port="(\d+)"', line)
                        if match:
                            ports.add(int(match.group(1)))
        except Exception as e:
            logging.debug(f"Failed to read bluestacks.conf: {e}")
    return ports


def scan_emulator_ports() -> list[str]:
    """Scan for active emulator ADB ports on loopback."""
    candidate_ports = set()

    # 1. Process scanning
    running_emulators, proc_ports = _get_running_emulators_and_ports()
    candidate_ports.update(proc_ports)

    # 2. Add common default ports for running emulators
    for name in running_emulators:
        candidate_ports.update(EMULATORS[name]["ports"])

    # 3. Add BlueStacks specific ports
    candidate_ports.update(_get_bluestacks_ports())

    # 4. Standard fallback
    candidate_ports.add(5555)

    # 5. Filter open ports
    open_ports = [port for port in sorted(candidate_ports) if is_port_open(port)]
    logging.debug(f"Discovered open loopback ports: {open_ports}")

    # 6. Test ADB connectivity
    active_devices = []
    client = AdbClientHelper.get_adb_client()

    try:
        connected = client.list()
        for d in connected:
            if d.state == "device":
                active_devices.append(d.serial)
    except Exception as e:
        logging.debug(f"Failed to list connected devices: {e}")

    for port in open_ports:
        device_id = f"127.0.0.1:{port}"
        if device_id in active_devices:
            continue

        try:
            device = AdbClientHelper.get_adb_device(device_id)
            if device is not None:
                active_devices.append(device_id)
        except Exception as e:
            logging.debug(f"Failed to connect to device {device_id}: {e}")

    # De-duplicate preserving order
    seen = set()
    result = [d for d in active_devices if not (d in seen or seen.add(d))]
    logging.info(f"Discovered active ADB devices: {result}")
    return result
