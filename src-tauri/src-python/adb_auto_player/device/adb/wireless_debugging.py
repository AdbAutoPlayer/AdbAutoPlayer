"""Android 11+ Wireless Debugging helpers: pairing and mDNS discovery.

adbutils does not expose `adb pair` or `adb mdns`, so these call the adb
executable directly, talking to the same adb server as the AdbClient.
"""

import logging
import re
import subprocess
from typing import NamedTuple

from adbutils import _utils

from .mdns_query import query_connect_services

_PAIR_TIMEOUT_SECONDS = 15
_MDNS_TIMEOUT_SECONDS = 5
_TLS_CONNECT_SERVICE = "_adb-tls-connect._tcp"
_ADDRESS_PATTERN = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}:\d{1,5})\s*$")


def _run_adb(args: list[str], host: str, port: int, timeout: float) -> str:
    """Run an adb command against the given adb server.

    Args:
        args: adb arguments, e.g. `["mdns", "services"]`.
        host: adb server host.
        port: adb server port.
        timeout: Seconds before the command is aborted.

    Returns:
        Combined stdout and stderr.
    """
    result = subprocess.run(
        [_utils.adb_path(), "-H", host, "-P", str(port), *args],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
        # Prevent a console window flashing in the frozen Windows build.
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return f"{result.stdout}\n{result.stderr}".strip()


def pair_device(address: str, code: str, host: str, port: int) -> bool:
    """Pair with a device using Wireless Debugging's pairing code.

    Args:
        address: Pairing `IP:Port` shown on the phone.
        code: Pairing code shown on the phone.
        host: adb server host.
        port: adb server port.

    Returns:
        True if pairing succeeded.
    """
    try:
        output = _run_adb(
            ["pair", address.strip(), code.strip()],
            host,
            port,
            _PAIR_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as e:
        logging.warning(f"Wireless Debugging: pairing with {address} failed: {e}")
        return False

    if "Successfully paired" in output:
        logging.info(f"Wireless Debugging: paired with {address}")
        return True

    logging.warning(
        f"Wireless Debugging: pairing with {address} failed: {output}. "
        "The pairing code and port change every time the pairing dialog is opened."
    )
    return False


class MdnsService(NamedTuple):
    """A paired device announcing Wireless Debugging via mDNS."""

    name: str
    address: str


def discover_connect_addresses(host: str, port: int) -> list[str]:
    """List `IP:Port` addresses of paired devices announced via mDNS.

    Args:
        host: adb server host.
        port: adb server port.

    Returns:
        Connect addresses, in the order adb reports them.
    """
    return [service.address for service in discover_connect_services(host, port)]


def discover_connect_services(host: str, port: int) -> list[MdnsService]:
    """List paired devices announced via mDNS.

    Args:
        host: adb server host.
        port: adb server port.

    Returns:
        Services, in the order adb reports them.
    """
    services: list[MdnsService] = []
    try:
        output = _run_adb(["mdns", "services"], host, port, _MDNS_TIMEOUT_SECONDS)
        services = parse_connect_services(output)
    except (OSError, subprocess.SubprocessError) as e:
        logging.debug(f"Wireless Debugging: adb mDNS discovery failed: {e}")
    if services:
        return services

    # adb's discovery can miss phones that do answer, e.g. with virtual adapters.
    logging.debug("Wireless Debugging: adb found nothing, querying mDNS directly")
    try:
        return [MdnsService(n, a) for n, a in query_connect_services()]
    except OSError as e:
        logging.debug(f"Wireless Debugging: direct mDNS query failed: {e}")
        return []


def parse_connect_services(mdns_output: str) -> list[MdnsService]:
    """Extract connect services from `adb mdns services` output.

    Args:
        mdns_output: Output of `adb mdns services`.

    Returns:
        Every `_adb-tls-connect` service, without duplicate addresses.
    """
    services: list[MdnsService] = []
    for line in mdns_output.splitlines():
        if _TLS_CONNECT_SERVICE not in line:
            continue
        match = _ADDRESS_PATTERN.search(line)
        if not match or any(s.address == match.group(1) for s in services):
            continue
        services.append(MdnsService(name=line.split()[0], address=match.group(1)))
    return services


def is_same_device(serial: str, service: MdnsService) -> bool:
    """Check whether an adb serial refers to the device behind a mDNS service.

    adb auto-connects paired devices under a serial like
    `adb-<id>._adb-tls-connect._tcp` instead of `IP:Port`.

    Args:
        serial: Serial reported by `adb devices`.
        service: Discovered mDNS service.

    Returns:
        True if both refer to the same device.
    """
    return serial == service.address or serial.startswith(f"{service.name}.")
