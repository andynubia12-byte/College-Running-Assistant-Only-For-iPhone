#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GeoPilot — iOS 虚拟定位 CLI 工具
"""

import argparse
import asyncio
import math
import os
import random
import sys
import time
from pathlib import Path
from threading import Thread

# ==================== PyInstaller console=False 兼容 ====================
# PyInstaller 以 console=False 打包时 sys.stdout/stderr 为 None。
# tunneld 使用的 uvicorn 会在日志初始化时调用 sys.stdout.isatty()，
# 必须在所有 import 之前补上，否则 AttributeError 连锁导致 ValueError。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")

from pynput import keyboard

# ==================== 从 backend 模块导入 ====================

from backend.config import load_config, save_config, CONFIG_FILE
from backend.routes import list_routes, load_route, ROUTES_DIR
from backend.device import connect_via_tunneld, format_device_info, check_developer_mode, \
    reveal_developer_mode_option, enable_developer_mode
from backend.modes import gen_route, gen_random_walk, gen_pace, parse_rectangle, METERS_PER_DEG_LAT
from backend.localization import DeviceLocalizer

if sys.platform == "win32" and sys.stdout is not None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

stop_requested = False


# ==================== CLI 设备连接包装 ====================


async def cli_connect(udid=None):
    """CLI 版设备连接：处理多设备选择、打印信息、保存 UDID"""
    from backend.device import connect_via_tunneld as _raw_connect
    import json

    try:
        device = await _raw_connect(udid=udid)
    except ValueError as e:
        if "MULTIPLE_DEVICES" not in str(e):
            raise
        devices = e.args[1]
        print(f"\n发现 {len(devices)} 台设备:")
        for i, d in enumerate(devices, 1):
            p = d.peer_info["Properties"]
            print(f"  [{i}] {p['ProductType']}  iOS {p['OSVersion']}  {p.get('DeviceName', '?')}  {p['UniqueDeviceID'][:16]}...")
        while True:
            try:
                choice = int(input("请选择设备编号: ").strip())
                device = devices[choice - 1]
                break
            except (ValueError, IndexError):
                print(f"  请输入 1-{len(devices)}")
        # 保存 UDID
        new_udid = device.peer_info["Properties"]["UniqueDeviceID"]
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            cfg["last_udid"] = new_udid
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=4, ensure_ascii=False)

    info = format_device_info(device)
    print(f"[INFO] 已连接: {info['product_type']} (iOS {info['os_version']})")
    return device


# ==================== 三种运行模式（包装 generator，带 loc.set）====================


async def run_route(loc, route_data, config):
    global stop_requested
    stop_event = asyncio.Event()

    coordinates = route_data["coordinates"]
    loop_count = config.get("loop_count", 10)
    point_interval = config.get("point_interval", 0.05)
    jitter_meters = config.get("jitter_meters", 3.0)
    midpoint_prob = config.get("midpoint_probability", 0.15)

    total = len(coordinates)
    name = route_data.get("route_name", "unknown")

    print(f"\n{'=' * 50}")
    print(f"路线: {name}")
    print(f"圈数: {loop_count}  |  点数: {total}")
    print(f"间隔: {point_interval}s  |  抖动: +/-{jitter_meters}m")
    print(f"中点概率: {midpoint_prob * 100:.0f}%")
    print(f"{'=' * 50}\n")

    tick = 0
    t_start = time.time()

    gen = gen_route(route_data, config, stop_event)
    await gen.__anext__()  # 跳过 info yield

    for lap in range(1, loop_count + 1):
        if stop_requested:
            break
        print(f"[第 {lap}/{loop_count} 圈]")

        for i in range(total):
            if stop_requested:
                break

            insert_mid = False
            if i < total - 1 and not (i == 0 or i == total - 2):
                if random.random() < midpoint_prob:
                    insert_mid = True

            pt = coordinates[i]
            from backend.modes import apply_jitter
            lat, lng = apply_jitter(pt["lat"], pt["lng"], jitter_meters)
            await loc.set(lat, lng)
            tick += 1

            if insert_mid:
                await asyncio.sleep(point_interval * 0.5)
                a, b = coordinates[i], coordinates[i + 1]
                mlat, mlng = apply_jitter((a["lat"] + b["lat"]) / 2, (a["lng"] + b["lng"]) / 2, jitter_meters)
                await loc.set(mlat, mlng)
                tick += 1

            await asyncio.sleep(point_interval)

    elapsed = time.time() - t_start
    print(f"\n[DONE] {tick} 次定位  |  耗时 {elapsed:.1f}s  |  速率 {tick / elapsed:.1f} Hz")


async def run_random_walk(loc, config):
    global stop_requested
    stop_event = asyncio.Event()

    rw = config["random_walk"]
    bounds = parse_rectangle(rw["corners"])
    speed_ms = rw["speed_ms"]
    dir_stddev = rw["direction_change_stddev"]
    duration = rw.get("duration_seconds", 600)
    point_interval = config.get("point_interval", 0.05)
    jitter_meters = config.get("jitter_meters", 3.0)
    midpoint_prob = config.get("midpoint_probability", 0.15)

    from backend.modes import random_position_in_bounds, step_position, apply_jitter

    pos = random_position_in_bounds(bounds)
    direction = random.uniform(0, 360)

    print(f"\n{'=' * 50}")
    print(f"模式: 随机游走 (random_walk)")
    print(f"矩形: {bounds['min_lat']:.8f},{bounds['min_lng']:.8f} -> {bounds['max_lat']:.8f},{bounds['max_lng']:.8f}")
    print(f"速度: {speed_ms:.1f} m/s ({speed_ms * 3.6:.1f} km/h)")
    print(f"方向变化: +/-{dir_stddev:.0f}deg  |  间隔: {point_interval}s")
    print(f"抖动: +/-{jitter_meters}m  |  中点概率: {midpoint_prob * 100:.0f}%")
    print(f"持续: {duration}s ({duration / 60:.1f}min)")
    print(f"{'=' * 50}\n")

    tick = 0
    total_dist = 0.0
    t_start = time.time()
    t_end = t_start + duration

    while time.time() < t_end:
        if stop_requested:
            break

        prev_pos = dict(pos)
        pos, direction = step_position(pos, direction, speed_ms, point_interval, bounds)
        direction += random.gauss(0, dir_stddev)
        direction %= 360

        total_dist += math.hypot(
            (pos["lat"] - prev_pos["lat"]) * METERS_PER_DEG_LAT,
            (pos["lng"] - prev_pos["lng"]) * METERS_PER_DEG_LAT * math.cos(math.radians(pos["lat"])),
        )

        insert_mid = random.random() < midpoint_prob
        lat_j, lng_j = apply_jitter(pos["lat"], pos["lng"], jitter_meters)
        await loc.set(lat_j, lng_j)
        tick += 1

        if insert_mid:
            await asyncio.sleep(point_interval * 0.5)
            mlat = (prev_pos["lat"] + pos["lat"]) / 2
            mlng = (prev_pos["lng"] + pos["lng"]) / 2
            mlat, mlng = apply_jitter(mlat, mlng, jitter_meters)
            await loc.set(mlat, mlng)
            tick += 1

        if tick % max(1, int(10 / point_interval)) == 0:
            elapsed = time.time() - t_start
            print(f"  [{elapsed:.0f}s] {tick} ticks  |  {total_dist:.0f}m  |  "
                  f"({pos['lat']:.8f}, {pos['lng']:.8f})")

        await asyncio.sleep(point_interval)

    elapsed = time.time() - t_start
    print(f"\n[DONE] {tick} 次定位  |  {total_dist:.0f}m  |  耗时 {elapsed:.1f}s  |  速率 {tick / elapsed:.1f} Hz")


async def run_pace(loc, config):
    global stop_requested
    stop_event = asyncio.Event()

    gen = gen_pace(config, stop_event)

    # 读取 info yield（打印头部信息）
    async for data, meta in gen:
        if meta is not None:
            info = meta
            print(f"\n{'=' * 50}")
            print(f"模式: 配速跑道 (pace)")
            print(f"配速: {info['pace_min_per_km']:.1f} min/km ({info['speed_ms']:.1f} m/s)")
            print(f"跑道: 直道{info['base_L']:.0f}m 半圆R{info['base_R']:.0f}m  |  边距{info['margin_m']:.0f}m")
            print(f"总长: {info['duration']}s ({info['duration'] / 60:.1f}min)")
            print(f"{'=' * 50}\n")
        break

    t_start = time.time()

    async for data, meta in gen:
        if stop_requested:
            break
        if meta is not None:
            if "done" in meta:
                break
            continue
        if data is None:
            continue
        lat, lng, tick, total_dist, step_dist, point_interval = data
        await loc.set(lat, lng)
        if tick % max(1, int(1.0 / point_interval)) == 0:
            elapsed = time.time() - t_start
            cur_pace = (elapsed / 60) / (total_dist / 1000) if total_dist > 0 else 0
            print(f"  [{elapsed:.0f}s] {tick} ticks  |  {total_dist:.0f}m  |  实际配速 {cur_pace:.1f} min/km")
        await asyncio.sleep(0)

    if meta and "done" in meta:
        elapsed = meta["elapsed"]
        final_pace = (elapsed / 60) / (meta["total_dist"] / 1000) if meta["total_dist"] > 0 else 0
        print(f"\n[DONE] {meta['tick']} 次  |  {meta['total_dist']:.0f}m ({meta['total_dist'] / 1000:.2f}km)  |  "
              f"实际配速 {final_pace:.1f} min/km")


async def run_generic(gen, mode_name, config):
    """通用 runner：驱动 generator 并发送定位"""
    global stop_requested
    from backend.modes import apply_jitter

    info = None
    async for data, meta in gen:
        if stop_requested:
            break
        if meta is not None:
            if "done" in meta:
                break
            info = meta
            continue
        if data is None:
            continue

        lat, lng = data[0], data[1]
        # loc.set would be called here
        await asyncio.sleep(0)


# ==================== 交互式菜单 ====================


def _input_float(prompt, default=None):
    while True:
        raw = input(prompt).strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print("  请输入数字")


def _input_corners(last=None):
    nw = last["nw"] if last else None
    se = last["se"] if last else None

    print("  输入矩形两个对角坐标：")
    lat1 = _input_float(f"  西北角 纬度 ({nw['lat']}): " if nw else "  西北角 纬度: ", nw["lat"] if nw else None)
    lng1 = _input_float(f"  西北角 经度 ({nw['lng']}): " if nw else "  西北角 经度: ", nw["lng"] if nw else None)
    lat2 = _input_float(f"  东南角 纬度 ({se['lat']}): " if se else "  东南角 纬度: ", se["lat"] if se else None)
    lng2 = _input_float(f"  东南角 经度 ({se['lng']}): " if se else "  东南角 经度: ", se["lng"] if se else None)

    return {
        "nw": {"lat": max(lat1, lat2), "lng": min(lng1, lng2)},
        "ne": {"lat": max(lat1, lat2), "lng": max(lng1, lng2)},
        "se": {"lat": min(lat1, lat2), "lng": max(lng1, lng2)},
        "sw": {"lat": min(lat1, lat2), "lng": min(lng1, lng2)},
    }


def interactive_setup(config):
    rw = config.get("random_walk", {})

    print()
    print("=" * 50)
    print("  Smart-Sports-AutoLocate v2")
    print("=" * 50)
    print("  [1] 配速跑道 — 矩形内半圆+直道跑道，精确配速")
    print("  [2] 随机游走 — 矩形区域内随机移动")
    print("  [3] 路线播放 — 按预设路线文件移动")
    print("  [4] 校准矩形 — 连设备微调四角坐标")
    print("  [5] 开发者模式 — 检查/激活开发者模式")
    print("  [Q] 退出")
    print()

    while True:
        choice = input("请选择: ").strip().lower()
        if choice in ("q", "quit"):
            sys.exit(0)
        if choice in ("1", "2", "3", "4", "5"):
            break
        print("  请输入 1-5 或 Q")

    if choice == "1":
        print()
        print("--- 配速跑道设置 ---")
        print("（直接回车使用括号内的上次值）")
        last_corners = rw.get("corners")
        corners = _input_corners(last_corners)
        pace = _input_float(f"  配速 min/km ({rw.get('pace_min_per_km', 5.0)}): ", rw.get("pace_min_per_km", 5.0))
        duration = int(_input_float(f"  持续时长 秒 ({rw.get('duration_seconds', 1800)}): ", rw.get("duration_seconds", 1800)))
        jitter = _input_float(f"  抖动 米 ({config.get('jitter_meters', 1.0)}): ", config.get("jitter_meters", 1.0))

        config["jitter_meters"] = jitter
        config["random_walk"] = {
            "pace_min_per_km": pace,
            "duration_seconds": duration,
            "corners": corners,
            "ellipse_margin_meters": rw.get("ellipse_margin_meters", 2),
            "ellipse_points": rw.get("ellipse_points", 200),
        }
        config["mode"] = "pace"
        save_config(config)
        return "pace", None, {}

    elif choice == "2":
        print()
        print("--- 矩形游走设置 ---")
        last_corners = rw.get("corners")
        corners = _input_corners(last_corners)
        speed = _input_float(f"  移动速度 m/s ({rw.get('speed_ms', 3.0)}): ", rw.get("speed_ms", 3.0))
        duration = int(_input_float(f"  持续时长 秒 ({rw.get('duration_seconds', 1800)}): ", rw.get("duration_seconds", 1800)))

        config["random_walk"] = {"speed_ms": speed, "duration_seconds": duration, "corners": corners,
                                  "direction_change_stddev": rw.get("direction_change_stddev", 5.0)}
        config["mode"] = "random_walk"
        save_config(config)
        return "random_walk", None, {}

    elif choice == "3":
        return "route", None, {}

    elif choice == "4":
        return "calibrate", None, {}

    else:
        return "developer_mode", None, {}


def select_route(route_arg=None):
    """选择路线（交互或按参数）"""
    routes_list = list_routes()
    if not routes_list:
        print(f"[ERROR] {ROUTES_DIR}/ 下没有路线文件")
        sys.exit(1)

    if route_arg:
        if route_arg.isdigit():
            idx = int(route_arg) - 1
            if 0 <= idx < len(routes_list):
                return routes_list[idx]["filename"]
        else:
            for r in routes_list:
                if r["name"] == route_arg or r["filename"] == route_arg:
                    return r["filename"]
        print(f"[ERROR] 未找到路线: {route_arg}")
        sys.exit(1)

    if len(routes_list) == 1:
        print(f"[INFO] 自动选择唯一路线: {routes_list[0]['filename']}")
        return routes_list[0]["filename"]

    print("\n可用的路线:")
    for i, r in enumerate(routes_list, 1):
        print(f"  [{i}] {r['name']} ({r['points']} 个点)")

    while True:
        try:
            choice = int(input("\n选择路线编号: ").strip())
            return routes_list[choice - 1]["filename"]
        except (ValueError, IndexError):
            print(f"请输入 1-{len(routes_list)}")
        except EOFError:
            print("[ERROR] 非交互模式请用 --route 指定路线")
            sys.exit(1)


# ==================== 校准矩形 ====================


async def calibrate_corners(config, udid=None):
    METERS_PER_DEG_LAT = 111320.0
    rsd = await cli_connect(udid=udid)

    rw = config.get("random_walk", {})
    old = rw.get("corners")

    if old:
        corners = {k: dict(v) for k, v in old.items()}
    else:
        default = {"lat": 28.735, "lng": 115.825}
        corners = {"nw": dict(default), "ne": dict(default), "se": dict(default), "sw": dict(default)}

    labels = [("nw", "西北"), ("ne", "东北"), ("se", "东南"), ("sw", "西南")]
    step_m = 20.0

    async with DeviceLocalizer(rsd) as localizer:
        for key, label in labels:
            pos = corners[key]
            await localizer.set(pos["lat"], pos["lng"])

            print(f"\n--- 校准 {label}角 ({key}) ---")
            print(f"  步长: {step_m:.0f}m  |  W/S 南北 +/-  |  A/D 东西 +/-")
            print(f"  +/- 调步长  |  Enter 确认  |  当前位置: {pos['lat']:.8f}, {pos['lng']:.8f}")

            while True:
                cmd = input("  > ").strip().lower()

                if cmd == "":
                    corners[key] = {"lat": round(pos["lat"], 8), "lng": round(pos["lng"], 8)}
                    print(f"  已记录: {corners[key]['lat']:.8f}, {corners[key]['lng']:.8f}")
                    break

                if cmd in ("w", "s"):
                    delta = step_m / METERS_PER_DEG_LAT * (1 if cmd == "w" else -1)
                    pos["lat"] += delta
                elif cmd in ("d", "a"):
                    delta = step_m / (METERS_PER_DEG_LAT * math.cos(math.radians(pos["lat"])))
                    pos["lng"] += delta * (1 if cmd == "d" else -1)
                elif cmd == "+":
                    step_m = min(step_m * 2, 100)
                elif cmd == "-":
                    step_m = max(step_m / 2, 1)
                elif cmd == "q":
                    print("  已取消校准")
                    rsd.close()
                    return
                else:
                    print(f"  W=北 S=南 A=西 D=东  +=放大步长 -=缩小步长  Enter=确认")
                    continue

                await localizer.set(pos["lat"], pos["lng"])
                print(f"  ({pos['lat']:.8f}, {pos['lng']:.8f})  步长={step_m:.0f}m")

    nw = corners["nw"]
    se = corners["se"]
    corners["ne"] = {"lat": nw["lat"], "lng": se["lng"]}
    corners["sw"] = {"lat": se["lat"], "lng": nw["lng"]}

    rw["corners"] = corners
    config["random_walk"] = rw
    save_config(config)
    print(f"\n[OK] 四角已保存到 {CONFIG_FILE}")
    print(f"  NW: {corners['nw']['lat']:.8f}, {corners['nw']['lng']:.8f}")
    print(f"  NE: {corners['ne']['lat']:.8f}, {corners['ne']['lng']:.8f}")
    print(f"  SE: {corners['se']['lat']:.8f}, {corners['se']['lng']:.8f}")
    print(f"  SW: {corners['sw']['lat']:.8f}, {corners['sw']['lng']:.8f}")
    rsd.close()


# ==================== 开发者模式 ====================


async def handle_developer_mode(config, udid=None):
    rsd = await cli_connect(udid=udid)

    try:
        status = await check_developer_mode(rsd)
    except Exception as e:
        print(f"[WARN] 无法查询开发者模式状态: {e}")
        print("  设备可能不支持此操作（iOS 15 及以下无此限制）")
        rsd.close()
        return True

    if status:
        print("[OK] 开发者模式已开启，无需额外操作")
        rsd.close()
        return True

    dev_info = rsd.peer_info.get("Properties", {})
    print(f"\n{'=' * 50}")
    print(f"  开发者模式 — 未开启")
    print(f"  设备: {dev_info.get('ProductType', '?')}  iOS {dev_info.get('OSVersion', '?')}")
    print(f"{'=' * 50}")
    print()
    print("  iOS 16+ 需要开启开发者模式才能使用虚拟定位。")
    print()
    print("  请选择操作：")
    print("  [1] 显示选项 — 在 iPhone 设置中显示开发者模式开关")
    print("     （无需重启，推荐）")
    print("     然后手动: 设置 → 隐私与安全性 → 开发者模式 → 开启")
    print("  [2] 完全激活 — 自动开启开发者模式（设备会重启一次）")
    print("  [Q] 返回菜单")
    print()

    while True:
        choice = input("请选择: ").strip().lower()
        if choice in ("q", "quit", ""):
            print("[SKIP] 跳过开发者模式设置")
            rsd.close()
            return False
        if choice == "1":
            try:
                await reveal_developer_mode_option(rsd)
                print()
                print("[OK] 已发送「显示开发者模式选项」指令")
                print("  请前往 iPhone: 设置 → 隐私与安全性 → 开发者模式")
                print("  打开开关后设备会自动重启，之后本工具即可正常使用。")
            except Exception as e:
                print(f"[ERROR] 操作失败: {e}")
            rsd.close()
            return False
        elif choice == "2":
            print()
            print("[INFO] 正在激活开发者模式...")
            print("  设备将重启，请勿断开连接。重启后会自动确认。")
            try:
                await enable_developer_mode(rsd)
                print("[OK] 开发者模式已激活！")
                rsd.close()
                return True
            except RuntimeError as e:
                print(f"[ERROR] {e}")
            except Exception as e:
                print(f"[ERROR] 激活失败: {e}")
            rsd.close()
            return False
        print("  请输入 1, 2 或 Q")


def start_stop_listener():
    global stop_requested

    def on_press(key):
        global stop_requested
        if key == keyboard.Key.f12:
            print("\n[STOP] F12 停止")
            stop_requested = True
            return False

    keyboard.Listener(on_press=on_press).start()


# ==================== 主流程 ====================


async def async_main(args, preset_mode=None, preset_route_data=None):
    global stop_requested

    config = load_config()

    if args.mode:
        if args.loop:
            config["loop_count"] = args.loop
        if args.duration:
            config.setdefault("random_walk", {})["duration_seconds"] = args.duration
        if args.interval is not None:
            config["point_interval"] = args.interval
        mode = args.mode
    else:
        mode = preset_mode

    if mode not in ("route", "random_walk", "pace", "calibrate", "developer_mode"):
        print(f"[ERROR] 未知模式: {mode}")
        sys.exit(1)

    if mode == "calibrate":
        await calibrate_corners(config, udid=args.udid)
        return

    if mode == "developer_mode":
        await handle_developer_mode(config, udid=args.udid)
        return

    if mode == "route":
        if preset_route_data:
            route_data = preset_route_data
        else:
            filename = select_route(route_arg=args.route)
            route_data = load_route(filename)
    else:
        rw = config.get("random_walk", {})
        if not rw.get("corners"):
            print("[ERROR] random_walk 模式需要在 config.json 中设置 random_walk.corners")
            print("  请使用交互模式设置矩形区域，或编辑 config.json")
            sys.exit(1)

    rsd = await cli_connect(udid=args.udid)

    try:
        if not await check_developer_mode(rsd):
            print("\n[WARN] 开发者模式未开启 — 虚拟定位可能不生效")
            print("  可用 python main.py --devmode 检查并开启")
            print()
    except Exception:
        pass

    start_stop_listener()

    try:
        async with DeviceLocalizer(rsd) as localizer:
            if not stop_requested:
                if mode == "route":
                    await run_route(localizer, route_data, config)
                elif mode == "pace":
                    await run_pace(localizer, config)
                else:
                    await run_random_walk(localizer, config)
            await localizer.clear()
    except KeyboardInterrupt:
        print("\n[STOP] 用户中断")
    finally:
        stop_requested = True


def main():
    parser = argparse.ArgumentParser(description="GeoPilot")
    parser.add_argument("--mode", "-m", choices=["route", "random_walk", "pace", "developer_mode"], help="运行模式")
    parser.add_argument("--route", "-r", help="路线名称或编号 (route 模式)")
    parser.add_argument("--loop", "-l", type=int, help="循环圈数 (route 模式)")
    parser.add_argument("--duration", "-d", type=int, help="运行时长/秒 (random_walk 模式)")
    parser.add_argument("--udid", "-u", help="目标设备 UDID")
    parser.add_argument("--interval", "-i", type=float, help="定位间隔（秒）")
    parser.add_argument("--devmode", action="store_true", help="检查/激活开发者模式")
    parser.add_argument("--tunneld", action="store_true", help="启动 tunneld 隧道服务（需管理员权限）")
    args = parser.parse_args()

    # 启动 tunneld 守护进程（需管理员权限，创建 TUN 虚拟网卡）
    if args.tunneld:
        # 如果打包时 console=False, sys.stdout/stderr 为 None，
        # uvicorn 日志初始化会调用 isatty()，补上避免 AttributeError
        if sys.stdout is None:
            sys.stdout = open(os.devnull, 'w')
        if sys.stderr is None:
            sys.stderr = open(os.devnull, 'w')
        from pymobiledevice3.tunneld.server import TunneldRunner
        TunneldRunner.create(host="127.0.0.1", port=49151)
        return

    if args.devmode:
        try:
            asyncio.run(handle_developer_mode(load_config(), udid=args.udid))
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        print("\n程序结束")
        return

    if args.mode:
        try:
            asyncio.run(async_main(args, preset_mode=args.mode))
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n程序结束")
            try:
                input("按回车键退出...")
            except EOFError:
                pass
        return

    # 交互式菜单
    while True:
        config = load_config()
        mode, route_data, _ = interactive_setup(config)

        if mode == "route":
            filename = select_route()
            route_data = load_route(filename)

        if mode == "calibrate":
            try:
                asyncio.run(calibrate_corners(load_config(), udid=args.udid))
            except Exception as e:
                print(f"\n[ERROR] {e}")
                import traceback
                traceback.print_exc()
            continue

        if mode == "developer_mode":
            try:
                asyncio.run(handle_developer_mode(load_config(), udid=args.udid))
            except Exception as e:
                print(f"\n[ERROR] {e}")
                import traceback
                traceback.print_exc()
            continue

        try:
            asyncio.run(async_main(args, preset_mode=mode, preset_route_data=route_data))
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        break

    print("\n程序结束")
    try:
        input("按回车键退出...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
