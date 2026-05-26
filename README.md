# Smart-Sports-AutoLocate

**iOS 虚拟定位自动化工具 — 基于 pymobiledevice3 直连设备，无需越狱**

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

---

## 目录

- [原理](#原理)
- [环境要求](#环境要求)
- [安装](#安装)
- [快速开始](#快速开始)
- [运行模式](#三种运行模式)
- [配置说明](#配置说明)
- [命令行参数](#命令行参数)
- [路线准备](#路线准备)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [免责声明](#免责声明)

---

## 原理

通过 [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) 调用 Apple 官方 DVT (Developer Tools) 协议中的 `com.apple.dt.simulatelocation` 服务，直接向 iOS 设备注入模拟 GPS 坐标。Xcode、爱思助手、本工具使用同一底层协议。

```
main.py
  → pymobiledevice3
    → usbmuxd (USB 多路复用)
      → Lockdown (设备锁服务)
        → RSD / Tunnel (RemoteServiceDiscovery, iOS 17+)
          → DVT (Developer Tools)
            → LocationSimulation
              → 设备 GPS 改变
```

**iOS 17+ 变化**：Apple 将开发者服务的传输层从 Lockdown 直连改为基于 RemoteXPC 的隧道 (tunnel)。需要先启动 `tunneld` 守护进程，所有开发者命令通过隧道中继。

**开发者模式要求**：iOS 16+ 必须在设备设置中开启「开发者模式」才能使用 DVT 服务。本工具内置一键激活功能。

---

## 环境要求

### 硬件

- iPhone / iPad（不限型号，无需越狱）
- USB 数据线

### 软件

| 系统 | 要求 |
|---|---|
| Windows | Python 3.8+，[iTunes (Microsoft Store 版)](https://apps.microsoft.com/detail/9pb2mz1zmb1s) — 提供 Apple Mobile Device USB 驱动 |
| macOS | Python 3.8+，Xcode 命令行工具 |
| Linux | Python 3.8+，`usbmuxd`，`libimobiledevice` |

### iOS 版本对照

| iOS 版本 | 连接方式 | 开发者模式 |
|---|---|---|
| ≤ 15.x | 直连 Lockdown | 不需要 |
| 16.x | 直连 Lockdown（tunneld 可选） | **必须开启** |
| ≥ 17.0 | **必须** tunneld 隧道 | **必须开启** |

---

## 安装

```bash
# 1. 进入项目目录
cd Smart-Sports-AutoLocate

# 2. 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate       # Windows
source venv/bin/activate    # macOS / Linux

# 3. 安装依赖
pip install -r requirements.txt
```

---

## 快速开始

### 第 1 步：启动隧道服务（iOS 17+ 必需）

以**管理员身份**打开一个终端，运行 tunneld 守护进程：

```bash
# Windows（以管理员身份运行终端）
python -m pymobiledevice3 remote tunneld

# macOS / Linux
sudo python -m pymobiledevice3 remote tunneld
```

看到以下输出表示就绪：

```
INFO: Uvicorn running on http://127.0.0.1:49151 (Press CTRL+C to quit)
Created tunnel --rsd fd1e:9d27:6cd3::1 55682
```

**保持此终端运行**，后续所有操作在另一个终端执行。

> iOS 16 及以下用户可跳过此步（不启动 tunneld 也能直连），但建议仍然开启以便统一管理。

### 第 2 步：连接设备

1. iPhone 用 USB 数据线连接电脑
2. **解锁设备**，输入锁屏密码
3. 首次连接时在设备上点击「**信任此电脑**」

### 第 3 步：激活开发者模式（iOS 16+ 必需）

```bash
python main.py --devmode
```

选择 **[1] 显示选项**，然后在 iPhone 上：
**设置 → 隐私与安全性 → 开发者模式 → 开启**

设备会自动重启，之后开发者模式即生效。

> 也可以选择 [2] 完全激活（需要先关闭锁屏密码），工具会自动完成全流程。

### 第 4 步：运行

```bash
# 交互式菜单
python main.py

# 或直接指定模式
python main.py -m pace                 # 配速跑道
python main.py -m random_walk           # 随机游走
python main.py -m route -r sample -l 10 # 路线播放
```

---

## 三种运行模式

### 路线播放 (route)

按预设的经纬度轨迹点序列循环行走。适合绕校园、公园、操场等固定路线。

```bash
python main.py -m route -r campus -l 5
```

路线文件使用 JSON 格式存放在 `routes/` 目录下，支持 GPX 导入。

### 随机游走 (random_walk)

在矩形区域内随机移动，碰到边界镜面反射。适合模拟没有固定路线的自由活动。

```bash
python main.py -m random_walk -d 1800
```

首次使用建议通过交互菜单设置矩形区域，或用 `map_picker.html` 在地图上选取。

### 配速跑道 (pace)

在矩形区域内生成标准跑道轨迹（两个半圆 + 两条直道），按设定配速匀速绕圈。每圈轨迹随机微调，模拟真实跑步。

```bash
python main.py -m pace
```

适合需要精确控制距离和配速的场景。

### 开发者模式 (developer_mode)

检查或激活 iOS 设备的开发者模式。

```bash
python main.py --devmode
python main.py -m developer_mode
```

---

## 配置说明

编辑 `config.json`：

```json
{
    "loop_count": 10,
    "point_interval": 0.05,
    "jitter_meters": 3.0,
    "midpoint_probability": 0.15,
    "random_walk": {
        "speed_ms": 3.0,
        "direction_change_stddev": 5.0,
        "duration_seconds": 1800,
        "pace_min_per_km": 5.0,
        "ellipse_margin_meters": 2,
        "ellipse_points": 200,
        "corners": {
            "nw": {"lat": 39.995, "lng": 116.325},
            "ne": {"lat": 39.995, "lng": 116.330},
            "se": {"lat": 39.990, "lng": 116.330},
            "sw": {"lat": 39.990, "lng": 116.325}
        }
    }
}
```

### 通用参数

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `loop_count` | int | 10 | 路线模式循环圈数 |
| `point_interval` | float | 0.05 | 定位间隔（秒），0.02-0.1 推荐 |
| `jitter_meters` | float | 3.0 | 每次定位随机偏移范围（米）|
| `midpoint_probability` | float | 0.15 | 两点间插入中点的概率 (0-1) |

### random_walk 参数

| 参数 | 说明 |
|---|---|
| `speed_ms` | 移动速度 (m/s) |
| `direction_change_stddev` | 方向变化标准差（度/步）|
| `duration_seconds` | 运行时长（秒）|
| `pace_min_per_km` | 配速跑道目标配速 (min/km) |
| `ellipse_margin_meters` | 跑道与矩形边界的间距（米）|
| `ellipse_points` | 跑道采样点数 |
| `corners` | 矩形四角经纬度坐标 |

### 参数调优

| 场景 | interval | jitter | midpoint |
|---|---|---|---|
| 跑步 | 0.02 | 2.0 | 0.2 |
| 步行 | 0.1 | 1.0 | 0.1 |
| 骑车 | 0.01 | 5.0 | 0.3 |

**抖动 (Jitter)**：每次定位在目标坐标 ±N 米范围内随机偏移，模拟真实 GPS 误差，避免轨迹过于完美。

**中点插入 (Midpoint)**：按概率在相邻轨迹点之间插入中点，使稀疏路线更平滑。

---

## 命令行参数

```bash
python main.py [OPTIONS]
```

| 参数 | 简写 | 说明 |
|---|---|---|
| `--mode` | `-m` | 运行模式: `route` / `random_walk` / `pace` / `developer_mode` |
| `--route` | `-r` | 路线名称或编号 |
| `--loop` | `-l` | 循环圈数 |
| `--duration` | `-d` | 运行时长（秒） |
| `--interval` | `-i` | 定位间隔（秒） |
| `--udid` | `-u` | 指定设备 UDID |
| `--devmode` | | 检查/激活开发者模式 |

### 示例

```bash
# 交互式菜单
python main.py

# 配速跑步（默认参数）
python main.py -m pace

# 指定路线跑 10 圈
python main.py -m route -r campus -l 10

# 随机游走 30 分钟
python main.py -m random_walk -d 1800

# 快速定位间隔
python main.py -m route -r sample -l 5 -i 0.03

# 检查开发者模式
python main.py --devmode
```

### F12 紧急停止

运行时按 **F12** 可随时终止程序，自动清除虚拟定位。

---

## 路线准备

本工具使用真实经纬度坐标（非屏幕像素）。获取路线有以下方式：

### GPX 导入（推荐）

1. 使用 [gpx.studio](https://gpx.studio) 或其他地图工具在地图上绘制轨迹，导出为 GPX
2. 用导入工具转换：

```bash
python import_gpx.py your_route.gpx
# 输出: routes/your_route.json
```

### 手动创建

```json
{
    "route_name": "campus",
    "coordinates": [
        {"lat": 39.992800, "lng": 116.327200},
        {"lat": 39.993000, "lng": 116.327500}
    ]
}
```

放到 `routes/` 目录下即可。

### 运动 App 导出

Strava、Keep、咕咚等 App 支持 GPX 导出，导出后用 `import_gpx.py` 转换。

### 矩形区域选取

打开 `map_picker.html`（需替换百度地图 AK），在地图上拖拽画矩形，自动生成四角坐标。

---

## 项目结构

```
├── main.py                # 主程序
│                          #   - 交互式菜单
│                          #   - 三种运行模式
│                          #   - 开发者模式管理
│                          #   - F12 紧急停止
├── import_gpx.py          # GPX → JSON 路线转换
├── config.json            # 配置文件
├── requirements.txt       # Python 依赖
├── map_picker.html        # 百度地图矩形选取工具
└── routes/                # 路线文件目录
    └── sample.json        # 示例路线
```

### 核心依赖

| 库 | 用途 |
|---|---|
| [pymobiledevice3](https://github.com/doronz88/pymobiledevice3) | iOS 设备通信协议栈 (Lockdown/RSD/DVT) |
| [pynput](https://github.com/moses-palmer/pynput) | F12 全局热键监听 |

### 运行流程

```
启动 → 加载配置 + 路线
  → 连接 tunneld 获取设备
  → 检查开发者模式（警告）
  → 建立 DVT 连接
  → 循环:
      ├─ 取下一个坐标点
      ├─ 应用随机抖动
      ├─ (概率) 插入中点
      └─ 发送到设备
  → 退出时清除虚拟定位
```

---

## 常见问题

### 无法连接到 tunneld

确保管理员终端中的 tunneld 正在运行：

```bash
python -m pymobiledevice3 remote tunneld
```

确认端口 49151 未被占用。

### 未检测到设备 / No device found

按顺序检查：
1. USB 线是否插紧、是否为数据线（非仅充电线）
2. 设备是否已解锁（输入了锁屏密码）
3. 设备是否点击了「信任此电脑」
4. Windows 上 iTunes 是否已安装（提供 USB 驱动）

### 定位没变化

1. 打开 iPhone 自带「地图」App，看蓝色定位点是否在目标位置
2. 检查**开发者模式**是否已开启（`python main.py --devmode`）
3. 某些 App 有定位缓存，杀掉 App 重新打开
4. `point_interval` 设置太快可能导致 App 来不及更新

### 跑完路线后定位会恢复吗

会。程序退出时自动调用 `loc.clear()` 清除虚拟定位。异常退出时重启设备即可恢复，或手动执行：

```bash
pymobiledevice3 developer dvt simulate-location clear --tunnel ''
```

### 多台设备同时连接

tunneld 自动管理多设备隧道。有多个设备时程序会显示列表供选择，选定后自动记住。

### 可以用 Wi-Fi 连接吗

可以。首次配对仍需 USB，之后开启 Wi-Fi 同步：

```bash
pymobiledevice3 lockdown wifi-connections on --tunnel ''
```

### 需要越狱吗

不需要。使用的是 Apple 官方为开发者提供的调试协议（与 Xcode 相同），不涉及任何越狱操作。

---

## 已知限制

1. **iOS 17+ 必须走隧道**：需要管理员权限启动 tunneld（创建 TUN/TAP 虚拟网卡）
2. **开发者模式**：iOS 16+ 必须开启，首次需设备重启
3. **设备重启后需重新信任**：iOS 会在重启后清除信任状态
4. **经纬度精度**：协议支持 double 浮点数精度（约 1 厘米），过于完美的轨迹可能被反作弊检测

---

## 免责声明

**本项目仅供技术学习与研究使用。**

- 使用本工具产生的任何后果（包括但不限于违反校规、平台规则、被标记作弊、警告、处分等）由使用者自行承担
- 作者不对本工具的任何使用方式承担责任
- 体育锻炼关乎健康，锻炼身体是对健康最好的投资
- 请合理使用技术，遵守所在平台与机构的规定

---

<div align="center">

**如果这个项目对你有帮助，请给个 Star**

---

<small>由 Claude Code 接入 DeepSeek v4 Pro 完成</small>

</div>
