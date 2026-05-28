#!/usr/bin/env python3
"""
GeoPilot Tunneld Service
========================
iOS 设备通信服务，需要管理员权限运行。
由 GeoPilot 主程序通过 UAC 提升后自动启动。
父进程退出后本服务自动终止。
"""

import sys
import os
import threading

# PyInstaller console=False 兼容
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")


def _watch_parent(pid: int):
    """后台线程：每秒检查父进程是否存在，不存在则退出。"""
    import time
    import ctypes

    SYNCHRONIZE = 0x00100000
    while True:
        time.sleep(1)
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
        else:
            # 父进程已退出 → 终止自己
            os._exit(0)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--parent-pid", type=int, default=0)
    args = parser.parse_args()

    if args.parent_pid:
        threading.Thread(target=_watch_parent, args=(args.parent_pid,), daemon=True).start()

    # 隐藏控制台窗口
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


if __name__ == "__main__":
    main()
