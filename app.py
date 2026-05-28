#!/usr/bin/env python3
"""GeoPilot PySide6 GUI entry point."""
import sys
import os
import asyncio
from pathlib import Path

# PyInstaller console=False compatibility
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


def _run_tunneld_service():
    """--tunneld 模式：启动 tunneld 服务而非 GUI。"""
    import argparse
    import threading

    parser = argparse.ArgumentParser()
    parser.add_argument("--tunneld", action="store_true")
    parser.add_argument("--parent-pid", type=int, default=0)
    args, _ = parser.parse_known_args()

    if args.parent_pid:
        def _watch_parent(pid):
            import time
            import ctypes as ct
            SYNCHRONIZE = 0x00100000
            while True:
                time.sleep(1)
                h = ct.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
                if h:
                    ct.windll.kernel32.CloseHandle(h)
                else:
                    os._exit(0)
        threading.Thread(target=_watch_parent, args=(args.parent_pid,), daemon=True).start()

    if sys.platform == "win32":
        import ctypes
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass
        ctypes.windll.kernel32.SetConsoleTitleW("GeoPilot Tunneld Service")

    from pymobiledevice3.tunneld.server import TunneldRunner
    TunneldRunner.create(host="127.0.0.1", port=49151)


def main():
    # --tunneld: service mode (no GUI)
    if "--tunneld" in sys.argv:
        _run_tunneld_service()
        return

    import qasync
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont, QFontDatabase

    from ui.main_window import MainWindow
    from ui.theme import STYLESHEET

    def _get_font_dir():
        if getattr(sys, 'frozen', False):
            return Path(sys._MEIPASS) / 'ui' / 'fonts'
        return Path(__file__).parent / 'ui' / 'fonts'

    def _load_fonts():
        font_dir = _get_font_dir()
        for f in sorted(font_dir.glob('*.otf')):
            QFontDatabase.addApplicationFont(str(f))

    app = QApplication(sys.argv)
    app.setApplicationName("GeoPilot")
    app.setOrganizationName("GeoPilot")
    app.setStyle("Fusion")
    _load_fonts()
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont("PingFang SC", 12))

    async def run():
        window = MainWindow()
        window.show()
        stop_event = asyncio.Event()
        app.aboutToQuit.connect(stop_event.set)
        await stop_event.wait()

    try:
        qasync.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
