"""Tests for Android 11+ Wireless Debugging pairing and mDNS discovery."""

import subprocess
from unittest.mock import MagicMock, patch

from adb_auto_player.device.adb import adb_client, adb_scanner, wireless_debugging
from adb_auto_player.device.adb.wireless_debugging import (
    MdnsService,
    is_same_device,
    pair_device,
    parse_connect_services,
)
from adb_auto_player.models.pydantic.adb_settings import (
    AdbSettings,
    WirelessDebuggingSettings,
)

_MDNS_OUTPUT = """List of discovered mdns services
adb-R58M123-AbCdEf\t_adb-tls-pairing._tcp\t192.168.1.50:41001
adb-R58M123-AbCdEf\t_adb-tls-connect._tcp\t192.168.1.50:37123
adb-XYZ-123\t_adb-tls-connect._tcp.\t192.168.1.77:40000
"""


def _completed(stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        args=[], returncode=0, stdout=stdout, stderr=stderr
    )


_PHONE = MdnsService("adb-R58M123-AbCdEf", "192.168.1.50:37123")
_OTHER_PHONE = MdnsService("adb-XYZ-123", "192.168.1.77:40000")


class TestParseConnectServices:
    def test_only_connect_services_are_returned(self):
        assert parse_connect_services(_MDNS_OUTPUT) == [_PHONE, _OTHER_PHONE]

    def test_empty_output(self):
        assert parse_connect_services("List of discovered mdns services\n") == []


class TestIsSameDevice:
    def test_address_serial(self):
        assert is_same_device("192.168.1.50:37123", _PHONE)

    def test_mdns_auto_connect_serial(self):
        assert is_same_device("adb-R58M123-AbCdEf._adb-tls-connect._tcp", _PHONE)

    def test_different_device(self):
        assert not is_same_device("127.0.0.1:5555", _PHONE)
        assert not is_same_device("adb-XYZ-123._adb-tls-connect._tcp", _PHONE)


class TestPairDevice:
    def test_success(self):
        with patch.object(
            wireless_debugging.subprocess,
            "run",
            return_value=_completed("Successfully paired to 192.168.1.50:41001"),
        ) as run:
            assert pair_device("192.168.1.50:41001", " 123456 ", "127.0.0.1", 5037)
        cmd = run.call_args.args[0]
        assert cmd[1:] == [
            "-H",
            "127.0.0.1",
            "-P",
            "5037",
            "pair",
            "192.168.1.50:41001",
            "123456",
        ]

    def test_wrong_code(self):
        with patch.object(
            wireless_debugging.subprocess,
            "run",
            return_value=_completed(
                "Failed: Wrong password or connection was dropped."
            ),
        ):
            assert not pair_device("192.168.1.50:41001", "000000", "127.0.0.1", 5037)

    def test_timeout(self):
        with patch.object(
            wireless_debugging.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="adb", timeout=15),
        ):
            assert not pair_device("192.168.1.50:41001", "123456", "127.0.0.1", 5037)


def _settings(**wireless) -> AdbSettings:
    return AdbSettings(wireless_debugging=WirelessDebuggingSettings(**wireless))


def _client() -> MagicMock:
    client = MagicMock()
    client.host = "127.0.0.1"
    client.port = 5037
    return client


class TestTryWirelessDebugging:
    def test_disabled_does_nothing(self):
        with (
            patch.object(
                adb_client.SettingsLoader, "adb_settings", return_value=_settings()
            ),
            patch.object(adb_client, "discover_connect_addresses") as discover,
            patch.object(adb_client, "pair_device") as pair,
        ):
            assert adb_client._try_wireless_debugging(_client(), "x:1") is None
        discover.assert_not_called()
        pair.assert_not_called()

    def test_discovers_paired_device_preferring_same_host(self):
        device = MagicMock()
        connected: list[str] = []

        def connect(_client, address):
            connected.append(address)
            return device

        with (
            patch.object(
                adb_client.SettingsLoader,
                "adb_settings",
                return_value=_settings(enabled=True),
            ),
            patch.object(
                adb_client,
                "discover_connect_addresses",
                return_value=["192.168.1.77:40000", "192.168.1.50:37123"],
            ),
            patch.object(adb_client, "_connect_to_device", side_effect=connect),
            patch.object(adb_client, "pair_device") as pair,
        ):
            result = adb_client._try_wireless_debugging(_client(), "192.168.1.50:35555")
        assert result is device
        assert connected == ["192.168.1.50:37123"]
        pair.assert_not_called()

    def test_no_pairing_code_skips_pairing(self):
        with (
            patch.object(
                adb_client.SettingsLoader,
                "adb_settings",
                return_value=_settings(enabled=True),
            ),
            patch.object(adb_client, "discover_connect_addresses", return_value=[]),
            patch.object(adb_client, "pair_device") as pair,
        ):
            assert adb_client._try_wireless_debugging(_client(), "x:1") is None
        pair.assert_not_called()

    def test_pairs_then_connects_to_discovered_device(self):
        device = MagicMock()
        discovered = iter([[], [], ["192.168.1.50:37123"]])

        def connect(_client, address):
            return device if address == "192.168.1.50:37123" else None

        with (
            patch.object(
                adb_client.SettingsLoader,
                "adb_settings",
                return_value=_settings(
                    enabled=True,
                    pairing_address="192.168.1.50:41001",
                    pairing_code="123456",
                ),
            ),
            patch.object(
                adb_client,
                "discover_connect_addresses",
                side_effect=lambda *_: next(discovered),
            ),
            patch.object(adb_client, "_connect_to_device", side_effect=connect),
            patch.object(adb_client, "pair_device", return_value=True) as pair,
            patch.object(adb_client.time, "sleep"),
        ):
            result = adb_client._try_wireless_debugging(_client(), "x:1")
        assert result is device
        pair.assert_called_once_with("192.168.1.50:41001", "123456", "127.0.0.1", 5037)

    def test_failed_pairing_returns_none(self):
        with (
            patch.object(
                adb_client.SettingsLoader,
                "adb_settings",
                return_value=_settings(
                    enabled=True,
                    pairing_address="192.168.1.50:41001",
                    pairing_code="000000",
                ),
            ),
            patch.object(adb_client, "discover_connect_addresses", return_value=[]),
            patch.object(adb_client, "pair_device", return_value=False),
            patch.object(adb_client, "_connect_to_device") as connect,
        ):
            assert adb_client._try_wireless_debugging(_client(), "x:1") is None
        connect.assert_not_called()


class TestScanEmulatorPorts:
    @staticmethod
    def _scan(
        settings: AdbSettings, listed_serials: list[str], services: list[MdnsService]
    ) -> tuple[list[str], MagicMock]:
        client = _client()
        client.list.return_value = [
            MagicMock(serial=serial, state="device") for serial in listed_serials
        ]
        with (
            patch.object(
                adb_scanner,
                "_get_running_emulators_and_ports",
                return_value=([], set()),
            ),
            patch.object(adb_scanner, "_get_bluestacks_ports", return_value=set()),
            patch.object(adb_scanner, "is_port_open", return_value=False),
            patch.object(
                adb_scanner.AdbClientHelper, "get_adb_client", return_value=client
            ),
            patch.object(
                adb_scanner.AdbClientHelper,
                "get_adb_device",
                return_value=MagicMock(),
            ) as get_device,
            patch.object(
                adb_scanner.SettingsLoader, "adb_settings", return_value=settings
            ),
            patch.object(
                adb_scanner, "discover_connect_services", return_value=services
            ),
        ):
            return adb_scanner.scan_emulator_ports(), get_device

    def test_disabled_does_not_list_wireless_devices(self):
        result, get_device = self._scan(_settings(), [], [_PHONE])
        assert result == []
        get_device.assert_not_called()

    def test_enabled_lists_discovered_devices(self):
        result, _ = self._scan(
            _settings(enabled=True), ["127.0.0.1:5555"], [_PHONE, _OTHER_PHONE]
        )
        assert result == [
            "127.0.0.1:5555",
            "192.168.1.50:37123",
            "192.168.1.77:40000",
        ]

    def test_skips_device_already_auto_connected_by_adb(self):
        auto_serial = "adb-R58M123-AbCdEf._adb-tls-connect._tcp"
        result, get_device = self._scan(
            _settings(enabled=True), [auto_serial], [_PHONE]
        )
        assert result == [auto_serial]
        get_device.assert_not_called()
