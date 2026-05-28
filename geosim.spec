# -*- coding: utf-8 -*-
# PyInstaller spec for GeoPilot (onedir mode)
# Usage: pyinstaller geosim.spec --clean --noconfirm

import sys
from pathlib import Path

_base = Path(SPECPATH)

a = Analysis(
    ['app.py'],
    pathex=[str(_base)],
    binaries=[
        (r'C:\Users\Andy\AppData\Local\Programs\Python\Python311\Lib\site-packages\pytun_pmd3\wintun\bin\amd64\wintun.dll', 'pytun_pmd3\\wintun\\bin\\amd64'),
    ],
    datas=[
        ('backend', 'backend'),
        ('ui', 'ui'),
        ('routes', 'routes'),
        ('configs', 'configs'),
        ('config.json', '.'),
        ('tunneld_service.py', '.'),
    ],
    hiddenimports=[
        'pymobiledevice3',
        'pymobiledevice3.tunneld',
        'pymobiledevice3.tunneld.api',
        'pymobiledevice3.tunneld.server',
        'pymobiledevice3.remote',
        'pymobiledevice3.remote.remote_service_discovery',
        'pymobiledevice3.services',
        'pymobiledevice3.services.dvt',
        'pymobiledevice3.services.dvt.instruments',
        'pymobiledevice3.services.dvt.instruments.dvt_provider',
        'pymobiledevice3.services.dvt.instruments.location_simulation',
        'pymobiledevice3.services.amfi',
        'pymobiledevice3.lockdown',
        'pymobiledevice3.exceptions',
        'pymobiledevice3.usbmux',
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'zeroconf',
        'zeroconf._core',
        'zeroconf._services',
        'qasync',
        # pymobiledevice3 deps not auto-detected
        'pygments',
        'pygments.formatters',
        'pygments.lexers',
        'pygments.styles',
        # PySide6
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
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtPrintSupport',
        'PyQt5.sip',
        'sip',
        'kivy',
        'kivymd',
        'ipykernel',
        'PIL',
        'lxml',
        'rich',
        'jupyter_client',
        'jupyter_core',
        'nbformat',
        'tornado',
        'zmq',
        'sqlalchemy',
        'scipy',
        # Unused PySide6 modules
        'PySide6.QtQml',
        'PySide6.QtQuick',
        'PySide6.QtQuickWidgets',
        'PySide6.QtNetwork',
        'PySide6.QtSvg',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtOpenGL',
        'PySide6.QtOpenGLWidgets',
        'PySide6.QtPrintSupport',
        'PySide6.QtDesigner',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets',
        'PySide6.QtXml',
        'PySide6.QtSensors',
        'PySide6.QtSerialPort',
        'PySide6.QtPositioning',
        'PySide6.QtCharts',
        'PySide6.QtPdf',
        'PySide6.QtPdfWidgets',
    ],
    noarchive=False,
)

# ── Strip unused Qt DLLs to reduce package size ────────────
_QT_DLL_EXCLUDE = [
    'opengl32sw', 'Qt6Quick', 'Qt6Qml', 'Qt6Pdf', 'Qt6OpenGL',
    'Qt6Svg', 'Qt6Sql', 'Qt6Test', 'Qt6Designer',
    'Qt6Multimedia', 'Qt6Xml', 'Qt6SerialPort',
    'Qt6PrintSupport', 'Qt6Sensors', 'Qt6Positioning',
    'Qt6Charts', 'Qt6VirtualKeyboard', 'Qt6QuickWidgets',
    'Qt6Quick3D', 'Qt6SpatialAudio', 'Qt6WebEngine',
    'Qt6WebEngineCore', 'Qt6WebEngineWidgets',
    'Qt6WebChannel', 'Qt6WebSockets',
]
a.binaries = [
    (name, path, typ) for name, path, typ in a.binaries
    if not any(ex in name for ex in _QT_DLL_EXCLUDE)
]

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
