import socket
import subprocess
import sys
import time
from pathlib import Path


class TunneldManager:
    PORT = 49151

    @staticmethod
    def is_running() -> bool:
        try:
            s = socket.create_connection(("127.0.0.1", TunneldManager.PORT), timeout=1)
            s.close()
            return True
        except OSError:
            return False

    @staticmethod
    def start() -> bool:
        if TunneldManager.is_running():
            return True

        script_dir = str(Path(__file__).parent.parent.resolve())
        main_py = str(Path(script_dir) / "main.py")

        if sys.platform == "win32":
            import ctypes

            params = f'"{main_py}" --tunneld'
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, script_dir, 1)
        else:
            subprocess.Popen(
                [sys.executable, main_py, "--tunneld"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        for _ in range(30):
            time.sleep(0.5)
            if TunneldManager.is_running():
                return True
        return False
