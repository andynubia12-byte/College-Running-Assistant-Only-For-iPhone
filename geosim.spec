# -*- coding: utf-8 -*-
# PyInstaller spec for GeoPilot (onedir mode)
# Usage: pyinstaller geosim.spec --clean --noconfirm

import sys
from pathlib import Path

_base = Path(SPECPATH)

a = Analysis(
    ['app.py'],
    pathex=[str(_base)],
    binaries=[],
    datas=[
        # backend modules (need at runtime for import)
        ('backend', 'backend'),
        # ui modules
        ('ui', 'ui'),
        # routes and configs data
        ('routes', 'routes'),
        ('configs', 'configs'),
        ('config.json', '.'),
    ],
    hiddenimports=[
        'pymobiledevice3',
        'pymobiledevice3.tunneld',
        'pymobiledevice3.tunneld.api',
        'pymobiledevice3.tunneld.server',
        'pymobiledevice3.services',
        'pymobiledevice3.services.dvt',
        'pymobiledevice3.services.dvt.instruments',
        'pymobiledevice3.services.dvt.instruments.dvt_provider',
        'pymobiledevice3.services.dvt.instruments.location_simulation',
        'pymobiledevice3.services.amfi',
        'pymobiledevice3.lockdown',
        'pymobiledevice3.exceptions',
        'qasync',
        'pynput',
        'pynput.keyboard',
        # PySide6 plugins
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='GeoPilot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(_base / 'app.ico') if (_base / 'app.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GeoPilot',
)
