import subprocess
import time
import unittest


class TestServer(unittest.TestCase):
    def test_server_logs_startup(self):
        proc = subprocess.Popen(
            ["uv", "run", "adb-auto-player", "--server"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        logs = ""
        timeout = 10
        start_time = time.time()

        while True:
            # Stop after timeout
            if time.time() - start_time > timeout:
                proc.terminate()
                break

            line = proc.stdout.readline()
            if line:
                logs += line

                if "Application startup complete." in logs:
                    proc.terminate()
                    break
            else:
                time.sleep(0.1)

        proc.wait(timeout=10)

        assert "Application startup complete." in logs
