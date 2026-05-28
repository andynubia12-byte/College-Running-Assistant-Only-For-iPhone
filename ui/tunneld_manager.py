import os
import socket
import subprocess
import sys
from pathlib import Path


class TunneldManager:
    PORT = 49151
    POLL_INTERVAL_MS = 500
    POLL_RETRIES = 30

    @staticmethod
    def is_running() -> bool:
        try:
            s = socket.create_connection(("127.0.0.1", TunneldManager.PORT), timeout=1)
            s.close()
            return True
        except OSError:
            return False

    @staticmethod
    def launch() -> bool:
        """启动 tunneld 进程（非阻塞）。进程已在运行则返回 True。"""
        if TunneldManager.is_running():
            return True

        parent_pid = os.getpid()
        frozen = getattr(sys, 'frozen', False)

        if sys.platform == "win32":
            import ctypes

            if frozen:
                # 打包后：ShellExecute GeoPilot.exe --tunneld
                params = f"--tunneld --parent-pid {parent_pid}"
                work_dir = str(Path(sys.executable).parent)
            else:
                # 开发模式：ShellExecute python.exe tunneld_service.py
                project_root = Path(__file__).parent.parent.resolve()
                service_script = str(project_root / "tunneld_service.py")
                params = f'"{service_script}" --parent-pid {parent_pid}'
                work_dir = str(project_root)

            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, params, work_dir, 1
            )
        else:
            if frozen:
                subprocess.Popen(
                    [sys.executable, "--tunneld", "--parent-pid", str(parent_pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            else:
                project_root = Path(__file__).parent.parent.resolve()
                subprocess.Popen(
                    [sys.executable, str(project_root / "tunneld_service.py"),
                     "--parent-pid", str(parent_pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )

        return True
