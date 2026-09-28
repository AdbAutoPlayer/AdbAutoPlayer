"""Minimal mDNS query for Wireless Debugging, independent of adb.

adb's own mDNS discovery (`adb mdns services`) can come back empty even when
the phone answers on the network, e.g. on PCs with extra virtual adapters
(VMware, VPNs). This sends the query from every local IPv4 interface and asks
for unicast replies, which is enough to find `_adb-tls-connect` services.
"""

import logging
import select
import socket
import struct
import time
from dataclasses import dataclass, field

import psutil

_MDNS_GROUP = ("224.0.0.251", 5353)
_TLS_CONNECT_SERVICE = "_adb-tls-connect._tcp.local"
_DNS_TYPE_A = 1
_DNS_TYPE_PTR = 12
_DNS_TYPE_SRV = 33
# Class IN with the "unicast response" bit set (RFC 6762 section 5.4).
_DNS_CLASS_IN_UNICAST = 0x8001
_DNS_HEADER = struct.Struct(">HHHHHH")
_RR_HEADER = struct.Struct(">HHIH")
_SRV_HEADER = struct.Struct(">HHH")
_IPV4_LENGTH = 4
_LABEL_POINTER_MASK = 0xC0
_MAX_POINTER_JUMPS = 16
_MAX_PACKET_SIZE = 9000
_SKIPPED_IP_PREFIXES = ("127.", "169.254.")


@dataclass
class _Answers:
    """Records collected from all mDNS replies."""

    # instance name -> (target host, port)
    srv: dict[str, tuple[str, int]] = field(default_factory=dict)
    # host name -> IPv4
    a: dict[str, str] = field(default_factory=dict)
    # instance name -> IP of the device that sent it
    sender: dict[str, str] = field(default_factory=dict)


def query_connect_services(timeout: float = 2.0) -> list[tuple[str, str]]:
    """Find Wireless Debugging connect services with a direct mDNS query.

    Args:
        timeout: Seconds to wait for replies.

    Returns:
        `(name, "IP:Port")` pairs, where name is the service instance name
        without the service suffix (e.g. `adb-21041FDEE002A8-hTCyhs`).
    """
    sockets = _open_sockets()
    if not sockets:
        return []
    answers = _Answers()
    try:
        query = _build_query(_TLS_CONNECT_SERVICE)
        for sock in sockets:
            try:
                sock.sendto(query, _MDNS_GROUP)
            except OSError as e:
                logging.debug(f"mDNS query send failed: {e}")
        _collect_replies(sockets, answers, timeout)
    finally:
        for sock in sockets:
            sock.close()
    return _to_services(answers)


def _open_sockets() -> list[socket.socket]:
    sockets: list[socket.socket] = []
    for addresses in psutil.net_if_addrs().values():
        for address in addresses:
            ip = address.address
            if address.family != socket.AF_INET or ip.startswith(_SKIPPED_IP_PREFIXES):
                continue
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            try:
                sock.bind((ip, 0))
                sock.setsockopt(
                    socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(ip)
                )
            except OSError as e:
                logging.debug(f"mDNS: skipping interface {ip}: {e}")
                sock.close()
                continue
            sockets.append(sock)
    return sockets


def _collect_replies(
    sockets: list[socket.socket], answers: _Answers, timeout: float
) -> None:
    deadline = time.monotonic() + timeout
    while (remaining := deadline - time.monotonic()) > 0:
        readable, _, _ = select.select(sockets, [], [], remaining)
        for sock in readable:
            try:
                data, (sender_ip, _) = sock.recvfrom(_MAX_PACKET_SIZE)
            except OSError:
                continue
            try:
                _parse_reply(data, sender_ip, answers)
            except (IndexError, struct.error, UnicodeDecodeError, ValueError) as e:
                logging.debug(f"mDNS: ignoring malformed reply from {sender_ip}: {e}")


def _build_query(service: str) -> bytes:
    header = _DNS_HEADER.pack(0, 0, 1, 0, 0, 0)
    return (
        header
        + _encode_name(service)
        + struct.pack(">HH", _DNS_TYPE_PTR, _DNS_CLASS_IN_UNICAST)
    )


def _encode_name(name: str) -> bytes:
    labels = (label.encode() for label in name.split("."))
    return b"".join(bytes([len(label)]) + label for label in labels) + b"\0"


def _read_name(data: bytes, offset: int) -> tuple[str, int]:
    """Read a (possibly compressed) DNS name.

    Returns:
        The name and the offset right after it at its original position.

    Raises:
        ValueError: On a compression pointer loop.
    """
    labels: list[str] = []
    jumps = 0
    end: int | None = None
    while True:
        length = data[offset]
        if length == 0:
            return ".".join(labels), end if end is not None else offset + 1
        if length & _LABEL_POINTER_MASK == _LABEL_POINTER_MASK:
            jumps += 1
            if jumps > _MAX_POINTER_JUMPS:
                raise ValueError("DNS name compression loop")
            if end is None:
                end = offset + 2
            offset = ((length & ~_LABEL_POINTER_MASK) << 8) | data[offset + 1]
            continue
        labels.append(data[offset + 1 : offset + 1 + length].decode())
        offset += 1 + length


def _parse_reply(data: bytes, sender_ip: str, answers: _Answers) -> None:
    _, _, questions, *record_counts = _DNS_HEADER.unpack_from(data)
    offset = _DNS_HEADER.size
    for _ in range(questions):
        _, offset = _read_name(data, offset)
        offset += 4  # QTYPE + QCLASS
    for _ in range(sum(record_counts)):
        name, offset = _read_name(data, offset)
        rtype, _, _, length = _RR_HEADER.unpack_from(data, offset)
        offset += _RR_HEADER.size
        if rtype == _DNS_TYPE_SRV and name.endswith(f".{_TLS_CONNECT_SERVICE}"):
            _, _, port = _SRV_HEADER.unpack_from(data, offset)
            target, _ = _read_name(data, offset + _SRV_HEADER.size)
            answers.srv[name] = (target, port)
            answers.sender[name] = sender_ip
        elif rtype == _DNS_TYPE_A and length == _IPV4_LENGTH:
            answers.a[name] = socket.inet_ntoa(data[offset : offset + length])
        offset += length


def _to_services(answers: _Answers) -> list[tuple[str, str]]:
    services: list[tuple[str, str]] = []
    for instance, (target, port) in answers.srv.items():
        ip = answers.a.get(target, answers.sender[instance])
        name = instance.removesuffix(f".{_TLS_CONNECT_SERVICE}")
        services.append((name, f"{ip}:{port}"))
    return services
