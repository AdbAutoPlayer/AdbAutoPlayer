import re
import unittest

from adb_auto_player.commands.debug import _log_debug


class TestDebugCommand(unittest.TestCase):
    def test_debug_command_displays_hardware_info(self):
        with self.assertLogs(level="INFO") as log:
            _log_debug()

        self.assertTrue(log.output, "No logs were captured")

        cpu_count_found = any(
            re.search(r"CPU count: \d+", message) for message in log.output
        )
        self.assertTrue(
            cpu_count_found, "Expected 'CPU count: <number>' not found in logs"
        )

        # Check if "Memory: <number> GB" appears (match a float)
        memory_found = any(
            re.search(r"Memory: \d+(\.\d+)? GB", message) for message in log.output
        )
        self.assertTrue(
            memory_found, "Expected 'Memory: <number> GB' not found in logs"
        )


if __name__ == "__main__":
    unittest.main()
