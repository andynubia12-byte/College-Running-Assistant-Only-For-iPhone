# GeoPilot

iOS 虚拟定位桌面工具。通过 USB 连接 iPhone/iPad，实时模拟 GPS 位置，支持多设备批量控制。

## 功能

- **多设备管理** — 同时连接多台 iOS 设备，批量勾选、统一控制
- **配速跑道** — 在矩形区域内生成椭圆跑道，按指定配速（min/km）模拟跑步
- **随机游走** — 在矩形区域内模拟随机移动，可调速度、方向和抖动
- **路线回放** — 导入 GPX/JSON 路线文件，按路径点回放，支持循环
- **矩形校准** — WASD 实时操控设备 GPS，逐角标定矩形边界，保存为场地预设
- **场地预设** — 导入/导出 JSON 配置文件，一键切换不同场地的四角坐标和参数
- **开发者模式** — 检查、显示、激活 iOS 设备的开发者模式

## 系统要求

- Windows 10/11 x64
- Python 3.11+（开发模式）
- iTunes 或 Apple Device USB 驱动（设备连接需要）
- 管理员权限（tunneld 虚拟网卡需要）

## 快速开始

-下载最新的 Release 版本，目前只有 Portable 版本
-在 Apple 官方渠道安装 iTunes 或者在 Microsoft Store 下载并安装。
-若您的 Apple 设备从未开启过开发者模式，请先进入该软件设置，下滑到底部，可以帮助您打开开发者模式。
-初次使用需要先行校准矩形，根据提示进行操作，保存 Config File。
-如果看不到您的设备，请点击 刷新设备 按钮。
-选中设备并应用。可以多设备同时模拟定位。
-一般使用跑道模式。

### 开发模式

```bash
pip install -r requirements.txt
python app.py
```

### 打包版本

直接运行 `dist/GeoPilot/GeoPilot.exe`，或使用安装包 `dist/GeoPilot_setup.exe`。

### 构建

```bash
pyinstaller geosim.spec --clean --noconfirm
```

输出在 `dist/GeoPilot/`。

## 使用流程

1. 启动 GeoPilot，点击「启动 tunneld」并在 UAC 弹窗中确认提权
2. USB 连接 iPhone/iPad，点击「刷新设备」
3. 勾选需要控制的设备，点击「连接选中」
4. 选择或校准场地配置（矩形四角）
5. 选择运行模式（配速跑 / 随机游走 / 路线回放）
6. 调整参数，点击「开始运行」

## 项目结构

```
├── app.py                  # GUI 入口（--tunneld 模式启动后台服务）
├── main.py                 # CLI 入口（遗留）
├── geosim.spec             # PyInstaller 打包配置
├── requirements.txt        # Python 依赖
├── config.json             # 默认配置文件
├── configs/                # 场地预设目录
├── routes/                 # 路线文件目录
├── backend/
│   ├── config.py           # 配置读写模块
│   ├── device.py           # iOS 设备连接
│   ├── device_models.py    # 设备型号映射表
│   ├── localization.py     # DVT LocationSimulation 服务
│   ├── modes.py            # 移动算法（跑道/随机/路线）
│   └── routes.py           # 路线文件管理
├── ui/
│   ├── main_window.py      # 主窗口 & 页面导航
│   ├── app_state.py        # 全局状态单例
│   ├── theme.py            # QSS 主题系统（亮色/暗色）
│   ├── tunneld_manager.py  # tunneld 进程管理
│   ├── pages/
│   │   ├── home_page.py    # 首页仪表盘
│   │   ├── pace_page.py    # 配速跑道
│   │   ├── walk_page.py    # 随机游走
│   │   ├── route_page.py   # 路线回放
│   │   ├── run_page.py     # 运行执行页
│   │   ├── calibrate_page.py # 矩形校准
│   │   ├── settings_page.py  # 设置 & 配置管理
│   │   └── log_page.py     # 日志查看
│   ├── controllers/
│   │   └── run_controller.py # 异步运行控制器
│   └── fonts/              # PingFang SC 字体
└── tunneld_service.py      # tunneld 后台服务入口
```

## 依赖

| 包 | 用途 |
|---|---|
| pymobiledevice3 | iOS 设备通信（tunneld、DVT、LocationSimulation） |
| PySide6 | Qt GUI 框架 |
| qasync | asyncio 与 Qt 事件循环桥接 |
| pytun-pmd3 | TUN 虚拟网卡驱动（wintun.dll） |
| uvicorn | ASGI 服务器（tunneld 内部使用） |

## 许可

内部工具，仅供开发测试使用。
