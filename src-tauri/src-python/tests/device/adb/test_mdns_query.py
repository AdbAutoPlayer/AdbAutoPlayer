"""Tests for the direct mDNS query used when `adb mdns services` finds nothing.

Regression test for: on a PC with extra virtual adapters (VMware VMnet1/VMnet8)
`adb mdns services` stayed empty although the phone answered mDNS queries on
the LAN, so Wireless Debugging never found the phone's current connect port.
"""

import socket
import struct
from unittest.mock import patch

import pytest
from adb_auto_player.device.adb import mdns_query, wireless_debugging
from adb_auto_player.device.adb.mdns_query import (
    _Answers,
    _encode_name,
    _parse_reply,
    _read_name,
    _to_services,
)
from adb_auto_player.device.adb.wireless_debugging import (
    MdnsService,
    discover_connect_services,
)

_INSTANCE = "adb-21041FDEE002A8-hTCyhs._adb-tls-connect._tcp.local"
_HOST = "Android_2P0QLV7D.local"
_PHONE_IP = "192.168.178.23"


def _record(name: bytes, rtype: int, rdata: bytes) -> bytes:
    return name + struct.pack(">HHIH", rtype, 0x8001, 120, len(rdata)) + rdata


def _reply(*, with_a_record: bool = True) -> bytes:
    """Build a reply shaped like the Pixel's, using name compression."""
    header = struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 2 if with_a_record else 1)
    ptr_name = _encode_name("_adb-tls-connect._tcp.local")
    # The PTR owner name starts right after the header.
    ptr_offset = len(header)
    instance_label = b"\x19adb-21041FDEE002A8-hTCyhs"
    ptr_rdata = instance_label + struct.pack(">H", 0xC000 | ptr_offset)
    ptr = _record(ptr_name, 12, ptr_rdata)

    instance_offset = len(header) + len(ptr) - len(ptr_rdata)
    instance_ptr = struct.pack(">H", 0xC000 | instance_offset)
    srv = _record(
        instance_ptr, 33, struct.pack(">HHH", 0, 0, 35243) + _encode_name(_HOST)
    )
    records = header + ptr + srv
    if with_a_record:
        records += _record(_encode_name(_HOST), 1, socket.inet_aton(_PHONE_IP))
    return records


class TestParseReply:
    def test_resolves_address_from_srv_and_a_records(self):
        answers = _Answers()
        _parse_reply(_reply(), "10.0.0.99", answers)
        assert _to_services(answers) == [
            ("adb-21041FDEE002A8-hTCyhs", f"{_PHONE_IP}:35243")
        ]
        assert answers.srv[_INSTANCE] == (_HOST, 35243)

    def test_falls_back_to_sender_ip_without_a_record(self):
        answers = _Answers()
        _parse_reply(_reply(with_a_record=False), _PHONE_IP, answers)
        assert _to_services(answers) == [
            ("adb-21041FDEE002A8-hTCyhs", f"{_PHONE_IP}:35243")
        ]

    def test_ignores_other_services(self):
        header = struct.pack(">HHHHHH", 0, 0x8400, 0, 1, 0, 0)
        srv = _record(
            _encode_name("printer._ipp._tcp.local"),
            33,
            struct.pack(">HHH", 0, 0, 631) + _encode_name("printer.local"),
        )
        answers = _Answers()
        _parse_reply(header + srv, "192.168.178.30", answers)
        assert _to_services(answers) == []


class TestReadName:
    def test_compression_loop_raises(self):
        # A pointer that points at itself.
        with pytest.raises(ValueError, match="loop"):
            _read_name(b"\xc0\x00", 0)

    def test_plain_name(self):
        assert _read_name(_encode_name("a.bc.local"), 0) == ("a.bc.local", 12)


class TestDiscoverFallback:
    def test_uses_direct_query_when_adb_finds_nothing(self):
        with (
            patch.object(
                wireless_debugging,
                "_run_adb",
                return_value="List of discovered mdns services",
            ),
            patch.object(
                wireless_debugging,
                "query_connect_services",
                return_value=[("adb-X", f"{_PHONE_IP}:35243")],
            ) as direct,
        ):
            assert discover_connect_services("127.0.0.1", 5037) == [
                MdnsService("adb-X", f"{_PHONE_IP}:35243")
            ]
        direct.assert_called_once()

    def test_skips_direct_query_when_adb_finds_devices(self):
        adb_output = f"adb-X\t_adb-tls-connect._tcp\t{_PHONE_IP}:35243"
        with (
            patch.object(wireless_debugging, "_run_adb", return_value=adb_output),
            patch.object(wireless_debugging, "query_connect_services") as direct,
        ):
            assert discover_connect_services("127.0.0.1", 5037) == [
                MdnsService("adb-X", f"{_PHONE_IP}:35243")
            ]
        direct.assert_not_called()

    def test_direct_query_error_returns_empty(self):
        with (
            patch.object(wireless_debugging, "_run_adb", return_value=""),
            patch.object(
                wireless_debugging,
                "query_connect_services",
                side_effect=OSError("no network"),
            ),
        ):
            assert discover_connect_services("127.0.0.1", 5037) == []


class TestQueryConnectServices:
    def test_no_usable_interfaces(self):
        with patch.object(mdns_query, "_open_sockets", return_value=[]):
            assert mdns_query.query_connect_services() == []
