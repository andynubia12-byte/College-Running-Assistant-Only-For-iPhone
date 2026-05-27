# GeoPilot PySide6 重构计划

## 1. 动机

### 为什么放弃 WinUI 3

| 问题 | 细节 |
|------|------|
| 运行时体积 | .NET 10 self-contained 发布 ~65MB，加上 PyInstaller 后端 ~50MB，MSI 膨胀到 115MB |
| 双语言维护 | C# + Python 两套代码，类型转换、JSON 序列化、API 契约处处是坑 |
| 打包复杂度 | dotnet publish → PyInstaller → WiX MSI 三步，WiX v4/v5 兼容性差 |
| 调试困难 | C# 端的异常 Python 端看不到，Python 端的错误 C# 端只能拿到 HTTP 状态码 |
| 异步鸿沟 | C# async ↔ HTTP ↔ Python asyncio，三层异步模型互不透明 |

### 为什么选 PySide6

- Python 生态统一：GUI + 业务逻辑 + pymobiledevice3 全在一个进程
- 打包简单：PyInstaller 一步出 `.exe`，无 WiX、无 .NET SDK
- 成熟稳定：Qt 框架 30 年历史，LGPL 许可
- 体积可控：PySide6 核心 ~30MB（含 Qt 库），总体积预计 < 60MB

## 2. 架构设计

### 当前架构（要抛弃的）

```
GeoPilot.exe (C# WinUI3) ──HTTP──> pybackend.exe --serve (FastAPI)
                                       │
                                  pymobiledevice3
                                       │
                                  pybackend.exe --tunneld (admin, port 49151)
                                       │
                                  iOS Device
```

### 目标架构

```
GeoPilot.exe (PySide6 + backend)
  │
  ├── ui/          # PySide6 界面
  │   ├── main_window.py
  │   ├── pages/
  │   │   ├── home_page.py
  │   │   ├── settings_page.py
  │   │   ├── run_page.py
  │   │   └── ...
  │   └── widgets/     # 可复用组件
  │
  ├── backend/     # 现有模块（基本不动）
  │   ├── config.py
  │   ├── device.py
  │   ├── localization.py
  │   ├── modes.py
  │   └── routes.py
  │
  └── app.py       # 入口 + 生命周期管理
       │
       ├── asyncio event loop (via qasync)
       ├── DeviceLocalizer (直接调用，不走 HTTP)
       ├── TunneldManager (spawn pybackend --tunneld)
       └── pymobiledevice3
              │
         iOS Device
```

### 关键变化

| 项 | 旧（WinUI 3） | 新（PySide6） |
|----|--------------|--------------|
| 前后端通信 | HTTP 127.0.0.1:51234 | 同进程直接调用 |
| 异步模型 | C# async ↔ HTTP ↔ asyncio | `qasync` 统一 asyncio + Qt |
| 状态管理 | FastAPI `state` 全局 | `AppState` 单例 |
| 打包 | dotnet + PyInstaller + WiX | PyInstaller only |
| 体积 | 115MB MSI | 预计 50-60MB exe |

## 3. 关键技术决策

### 3.1 异步桥接：qasync

pymobiledevice3 大量使用 `async/await`（`connect_via_tunneld`、`DeviceLocalizer.set`、`gen_pace` 等）。

PySide6 的 Qt 事件循环是 C++ 层的，不兼容原生 asyncio。**qasync** 库解决这个问题：

```python
# app.py
import qasync
import asyncio
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)
loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)

# 现在可以在 PySide6 槽函数里直接 await 异步函数
async def on_connect_clicked(self):
    device = await connect_via_tunneld(udid=self.selected_udid)
    self.localizer = await DeviceLocalizer(device).__aenter__()
    self.update_status(f"已连接: {device}")

loop.run_until_complete(app.exec_())
```

**优点**：现有 `backend/` 所有 `async def` 不需要改。

### 3.2 Tunneld 管理：保持独立进程

tunneld 需要管理员权限（创建 TUN 虚拟网卡），不能合入主进程。保持 `--tunneld` 子进程模式：

```python
# ui/tunneld_manager.py
import subprocess, sys, time
from pathlib import Path

class TunneldManager:
    PORT = 49151

    @staticmethod
    def is_running() -> bool:
        import socket
        try:
            s = socket.create_connection(("127.0.0.1", 49151), timeout=1)
            s.close()
            return True
        except Exception:
            return False

    @staticmethod
    def start():
        """以管理员权限启动 tunneld。UAC 弹窗。"""
        if TunneldManager.is_running():
            return True
        exe = sys.executable
        args = [exe, "--tunneld"]
        # ShellExecute 'runas' 触发 UAC
        subprocess.Popen(
            args,
            shell=True,  # Windows 需要 shell 来触发 runas
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        # 等待就绪
        for _ in range(30):
            time.sleep(0.5)
            if TunneldManager.is_running():
                return True
        return False
```

### 3.3 定位模拟线程模型

`DeviceLocalizer.set(lat, lng)` 是 `async`，高频率调用（每 0.05 秒一次）。在 PySide6 中放在 asyncio 事件循环里直接 await：

```python
# run_page.py
async def _run_loop(self, generator, localizer):
    async for data, meta in generator:
        if self._stop_requested:
            break
        if data is None:
            continue
        lat, lng, tick, dist, *_ = data
        await localizer.set(lat, lng)  # 直接调用，无 HTTP 开销
        self._update_ui_signal.emit(tick, dist, lat, lng)
    await localizer.clear()
```

注意：更新 UI 必须通过 Qt Signal 回到主线程。qasync 的 `asyncSlot` 可以简化这点。

### 3.4 单例状态管理

替代原来的 `AppState` + FastAPI `state`：

```python
# app_state.py
from dataclasses import dataclass, field
from typing import Optional
from backend.localization import DeviceLocalizer

@dataclass
class AppState:
    """全局应用状态，替代旧 server.py 中的 state"""
    localizer: Optional[DeviceLocalizer] = None
    rsd = None
    running: bool = False
    mode: Optional[str] = None
    tick: int = 0
    total_dist: float = 0.0
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    connected_device_info: dict = field(default_factory=dict)

# 全局单例
_state = AppState()

def get_state() -> AppState:
    return _state
```

## 4. 目录结构

```
GeoPilot/
├── main.py                 # 入口（保留 --tunneld, --serve 向前兼容）
├── app.py                  # PySide6 应用入口 + qasync 设置
├── build.bat               # PyInstaller 打包
├── geosim.spec             # PyInstaller spec
│
├── backend/                # 保持不变
│   ├── __init__.py
│   ├── config.py
│   ├── device.py
│   ├── localization.py
│   ├── modes.py
│   └── routes.py
│
├── ui/                     # 新增 PySide6 界面
│   ├── __init__.py
│   ├── app_state.py        # 全局状态
│   ├── tunneld_manager.py  # tunneld 进程管理
│   ├── main_window.py      # 主窗口
│   ├── pages/
│   │   ├── __init__.py
│   │   ├── home_page.py    # 首页 — 设备连接 + 状态
│   │   ├── pace_page.py    # 配速跑道
│   │   ├── walk_page.py    # 随机游走
│   │   ├── route_page.py   # 路线播放
│   │   ├── calibrate_page.py # 校准矩形
│   │   ├── settings_page.py  # 配置管理
│   │   └── log_page.py     # 日志查看
│   └── widgets/
│       ├── __init__.py
│       ├── status_bar.py
│       └── map_picker.py
│
├── configs/                # 不变
├── routes/                 # 不变
└── installer/              # 可废弃（PyInstaller 替代 WiX）
```

## 5. 核心页面设计

### 5.1 主窗口 (main_window.py)

```
┌─────────────────────────────────────────┐
│ GeoPilot                    [设置] [日志] │  ← 标题栏
├─────────────────────────────────────────┤
│  tunneld ●运行中   已连接: iPhone 15 Pro │  ← 状态栏
├─────────────────────────────────────────┤
│                                         │
│  [StackedWidget — 页面切换]              │
│                                         │
└─────────────────────────────────────────┘
```

用 `QStackedWidget` 管理页面切换，替代 WinUI 的 `Frame.Navigate`。

### 5.2 首页 (home_page.py)

```
┌──────────────────────────────────┐
│ 设备列表:                         │
│ ┌──────────────────────────────┐ │
│ │ iPhone 15 Pro  iOS 18.2      │ │ ← QListWidget
│ │ iPad Air      iOS 17.6       │ │
│ └──────────────────────────────┘ │
│ [刷新设备]  [连接选中设备]         │
│                                  │
│ ┌────────┐ ┌────────┐ ┌───────┐ │
│ │ 配速   │ │ 随机   │ │ 路线  │ │  ← 模式卡片
│ │ 跑道   │ │ 游走   │ │ 播放  │ │
│ └────────┘ └────────┘ └───────┘ │
│ ┌────────┐                      │
│ │ 校准   │                      │
│ │ 矩形   │                      │
│ └────────┘                      │
└──────────────────────────────────┘
```

### 5.3 运行页 (run_page.py)

三种模式共用同一个 RunPage，通过参数区分：

```
┌──────────────────────────────────┐
│ 模式: 配速跑道                    │
│ 配速: 5.0 min/km  已跑: 3.2 km   │
│ 时间: 12:30        剩余: 17:30    │
│                                  │
│ 进度: ████████░░░░ 40%           │
│                                  │
│ [开始] [暂停] [停止]              │
│                                  │
│ 日志:                             │
│ [12:00] tick=100  (28.733,115.813)│
│ ...                              │
└──────────────────────────────────┘
```

## 6. 异步难题 & 解决方案

### 6.1 问题：长时间运行的 async generator 如何不阻塞 UI

```python
# modes.py 返回 async generator
gen = gen_pace(config, stop_event)

# 在 PySide6 里遍历它
async for data, meta in gen:
    await localizer.set(lat, lng)  # 每次 0.05s
    # 需要更新 UI → 必须用 Signal
```

### 6.2 方案

```python
from PySide6.QtCore import QObject, Signal
import qasync

class RunController(QObject):
    """管理定位运行的核心控制器"""
    status_updated = Signal(dict)      # tick, dist, lat, lng
    run_finished = Signal(dict)       # done info
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self._stop_event = asyncio.Event()
        self._task = None

    def start(self, gen, localizer):
        self._stop_event.clear()
        self._task = asyncio.ensure_future(self._run(gen, localizer))

    def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()

    @qasync.asyncSlot()
    async def _run(self, gen, localizer):
        try:
            async for data, meta in gen:
                if self._stop_event.is_set():
                    break
                if data is None:
                    continue
                lat, lng, tick, dist, *_ = data
                await localizer.set(lat, lng)
                self.status_updated.emit({
                    "tick": tick, "dist": dist,
                    "lat": lat, "lng": lng,
                })
            await localizer.clear()
            self.run_finished.emit(meta or {})
        except Exception as e:
            self.error_occurred.emit(str(e))
```

**关键点**：
- `@qasync.asyncSlot()` 将 async 方法注册为 Qt slot，可以在主线程事件循环中运行
- `Signal.emit()` 是线程安全的，确保 UI 更新在主线程执行
- `asyncio.Event` 替代 threading.Event，避免阻塞事件循环

## 7. 打包方案

### 核心原则

**不用 PyInstaller `--onefile`**。`--onefile` 每次启动解压到 `%TEMP%\_MEIxxxxx\`，对用户透明但残留临时文件。

用 **`--onedir`（目录模式）**：所有依赖在 `_internal/` 目录，跟 exe 走，零解压。

### PyInstaller 构建

```bash
pyinstaller geosim.spec --clean --noconfirm
```

产物：`dist/GeoPilot/`

```
dist/GeoPilot/
  GeoPilot.exe          ← 入口（无控制台，图标嵌入）
  _internal/            ← Python + PySide6 + pymobiledevice3 + wintun.dll
  backend/              ← 后端模块（随包分发，PySide6 直接 import）
  ui/                   ← PySide6 界面模块
  configs/              ← 预置配置
  routes/               ← 预置路线
```

### 两种分发形式（基于同一份 dist/GeoPilot/）

| 形式 | 做法 | 用户操作 |
|------|------|---------|
| 便携版 `GeoPilot_v2.0_portable.zip` | 把 `dist/GeoPilot/` 压成 zip | 解压到任意目录，双击 `GeoPilot.exe` |
| 安装版 `GeoPilot_v2.0_setup.exe` | WinRAR SFX 自解压 | 一键安装，自动创建桌面快捷方式 |

### WinRAR SFX 安装包配置

WinRAR 创建自解压文件时勾选：

```
常规:
  解压路径: %LOCALAPPDATA%\GeoPilot
  解压后运行: GeoPilot.exe
  静默模式: 全部隐藏 (无界面解压)

高级 → 自解压选项:
  模块 → 默认.sfx

  安装:
    解压后运行: GeoPilot.exe
    解压前运行: <空>
    解压后运行: <空>

  快捷方式:
    创建桌面快捷方式: GeoPilot.exe
    创建开始菜单快捷方式: GeoPilot\GeoPilot.exe

  文本和图标:
    从文件加载图标: GeoPilot.exe

  模式:
    解压到临时文件夹: 不勾选 ← 关键，直接解压到目标目录
```

同时往 `dist/GeoPilot/` 放一个 `uninstall.bat`：

```bat
@echo off
cd /d "%~dp0"
taskkill /f /im GeoPilot.exe 2>nul
cd ..
rmdir /s /q "%~dp0"
```

用户双击即卸载——删目录就行，不留控制面板条目反而更干净。

### 构建脚本

```bat
:: build.bat
pyinstaller geosim.spec --clean --noconfirm

:: 便携版
powershell Compress-Archive -Path dist\GeoPilot -DestinationPath dist\GeoPilot_v2.0_portable.zip -Force

:: 安装版（需要 WinRAR 安装路径）
"C:\Program Files\WinRAR\WinRAR.exe" a -sfx -iiconGeoPilot.exe -z"installer\sfx.conf" dist\GeoPilot_v2.0_setup.exe dist\GeoPilot\*
```

## 8. 迁移顺序（建议分 5 个 PR）

### PR 1：基础框架
- [ ] `app.py` 入口 + qasync 设置
- [ ] `ui/main_window.py` 主窗口框架 + `QStackedWidget`
- [ ] `ui/pages/home_page.py` 设备列表 + 连接/断开
- [ ] `ui/tunneld_manager.py` tunneld 启停
- [ ] `ui/app_state.py` 全局状态
- [ ] 验证：启动 app → 连接 iPhone → 看到设备信息

### PR 2：三种运行模式
- [ ] `ui/pages/run_page.py` 通用运行页面
- [ ] `ui/controllers/run_controller.py` 异步运行控制
- [ ] 配速跑道、随机游走、路线播放
- [ ] 验证：选择模式 → 设置参数 → 开始运行 → iPhone 定位变化 → 停止恢复

### PR 3：设置 & 配置管理
- [ ] `ui/pages/settings_page.py` 配置 CRUD
- [ ] 导入/导出 JSON 配置文件
- [ ] 开发者模式管理
- [ ] 验证：保存配置 → 导入配置 → 切换配置 → 参数生效

### PR 4：校准 & 日志
- [ ] `ui/pages/calibrate_page.py` 矩形校准
- [ ] `ui/pages/log_page.py` 日志查看
- [ ] 验证：校准四角坐标 → 日志实时刷新

### PR 5：打包 & 收尾
- [ ] PyInstaller spec
- [ ] 图标和资源文件
- [ ] build.bat（PyInstaller + zip + WinRAR SFX）
- [ ] uninstall.bat

## 9. 风险 & 缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| qasync 与 pymobiledevice3 兼容 | asyncio 事件循环冲突 | 先用 demo 验证 `qasync` + `TunneldRunner` |
| PySide6 体积超预期 | 安装包过大 | 排除不必要的 Qt 模块（QtWebEngine 等） |
| Windows 高 DPI 缩放 | UI 模糊 | Qt 原生支持 `QT_ENABLE_HIGHDPI_SCALING` |
| 线程安全问题 | 崩溃 | DeviceLocalizer 只在 asyncio 线程用，UI 更新走 Signal |
| PyInstaller 打包 pymobiledevice3 | 缺少 DLL | 保留现有 spec 的 hiddenimports 和 wintun 配置 |

## 10. 依赖清单

```
pyside6>=6.7          # Qt 绑定
qasync>=0.27          # asyncio ↔ Qt 桥接
pymobiledevice3>=4.0  # iOS 设备通信
pytun-pmd3            # TUN 虚拟网卡（tunneld 依赖）
```

移除的依赖：
```
fastapi, uvicorn      # 不再需要 HTTP 后端
pydantic              # 不再需要请求验证
pynput                # F12 热键可选保留
```

Total 新增体积：PySide6 ~30MB + qasync ~0.1MB。移除 FastAPI/uvicorn/pydantic ~20MB。
净增 ~10MB，但去掉了 .NET runtime ~65MB。**总体积减半**。
