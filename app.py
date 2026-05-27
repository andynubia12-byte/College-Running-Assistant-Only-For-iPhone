#!/usr/bin/env python3
"""GeoPilot PySide6 GUI entry point."""
import sys
import os
import asyncio

# PyInstaller console=False compatibility
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

import qasync
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("GeoPilot")
    app.setOrganizationName("GeoPilot")

    async def run():
        window = MainWindow()
        window.show()

        # Wait until the app quits
        stop_event = asyncio.Event()
        app.aboutToQuit.connect(stop_event.set)
        await stop_event.wait()

    try:
        qasync.run(run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
