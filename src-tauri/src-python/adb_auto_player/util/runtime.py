import platform
import sys
from functools import lru_cache

import psutil


class RuntimeInfo:
    """Utility class for retrieving runtime and system information.

    Provides details about the operating system, CPU architecture, memory,
    processor, and frozen (packaged) status of the Python environment.
    Includes convenience helpers to detect OS type and CPU architecture.
    """

    @staticmethod
    @lru_cache(maxsize=1)
    def is_frozen() -> bool:
        """Whether the code is running as a frozen (compiled or as .exe) environment."""
        return hasattr(sys, "frozen") or "__compiled__" in globals()

    @staticmethod
    def platform() -> str:
        """Return the OS with full platform information.

        e.g. Windows-10-10.0.22631-SP0
        """
        return platform.platform()

    @staticmethod
    @lru_cache(maxsize=1)
    def system() -> str:
        """Return the OS name (e.g., Windows, Linux, Darwin)."""
        return platform.system()

    @staticmethod
    @lru_cache(maxsize=1)
    def machine() -> str:
        """Return the CPU architecture of the system (e.g., x86_64, arm64)."""
        return platform.machine()

    @staticmethod
    def processor() -> str:
        """Return the processor name or type as reported by the OS."""
        return platform.processor()

    @staticmethod
    def cpu_count(logical: bool = True) -> int:
        """Return the number of CPU cores.

        Args:
            logical (bool): If True, return logical cores (including hyperthreading).
                            If False, return physical cores.
        """
        return psutil.cpu_count(logical=logical)

    @staticmethod
    def memory_in_gb() -> int:
        """Return the total system memory in gigabytes (rounded to 2 decimal places)."""
        return round(psutil.virtual_memory().total / (1024**3), 2)

    @classmethod
    def is_x86(cls) -> bool:
        """Return True if the CPU architecture is x86 or AMD64."""
        arch = cls.machine().lower()
        return any(x in arch for x in ("x86", "amd64", "i386", "i686"))

    @classmethod
    def is_arm(cls) -> bool:
        """Return True if the CPU architecture is ARM (including aarch variants)."""
        arch = cls.machine().lower()
        return any(x in arch for x in ("arm", "aarch"))

    @classmethod
    def is_windows(cls) -> bool:
        """Return True if the OS is Windows."""
        return cls.system().lower() == "windows"

    @classmethod
    def is_mac(cls) -> bool:
        """Return True if the OS is macOS (Darwin)."""
        return cls.system().lower() in ("darwin", "macos")

    @classmethod
    def is_linux(cls) -> bool:
        """Return True if the OS is Linux."""
        return cls.system().lower() == "linux"
