#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart-Sports-AutoLocate v2
基于 pymobiledevice3 的 iOS 虚拟定位工具，通过 tunneld + DVT 协议直连设备。
需要先以管理员身份运行: python -m pymobiledevice3 remote tunneld
"""

import argparse
import asyncio
import json
import math
import random
import sys
import time
from pathlib import Path
from threading import Thread

from pynput import keyboard

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CONFIG_FILE = Path("config.json")
ROUTES_DIR = Path("routes")

DEFAULT_CONFIG = {
    "mode": "route",
    "loop_count": 10,
    "point_interval": 0.1,
    "jitter_meters": 1.0,
    "midpoint_probability": 0,
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
            "sw": {"lat": 39.990, "lng": 116.325},
        },
    },
}

METERS_PER_DEG_LAT = 111320.0
stop_requested = False


def load_config():
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        print(f"[INFO] 已加载配置: {CONFIG_FILE}")
        return cfg
    print("[INFO] 未找到配置，创建默认配置")
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False), encoding="utf-8")
    return DEFAULT_CONFIG.copy()


async def connect_via_tunneld(udid=None, save_choice=True):
    """通过运行中的 tunneld 连接设备。udid 指定设备，否则多设备时交互选择。"""
    from pymobiledevice3.tunneld.api import get_tunneld_devices
    from pymobiledevice3.exceptions import TunneldConnectionError

    try:
        devices = await get_tunneld_devices()
    except TunneldConnectionError:
        print("[ERROR] 无法连接到 tunneld (127.0.0.1:49151)")
        print("  请先以管理员身份运行:")
        print("  python -m pymobiledevice3 remote tunneld")
        sys.exit(1)

    if not devices:
        print("[ERROR] tunneld 已运行但未发现设备")
        print("  请检查 USB 连接并确保设备已解锁")
        sys.exit(1)

    if udid:
        for d in devices:
            if d.peer_info["Properties"]["UniqueDeviceID"] == udid:
                return d
        print(f"[ERROR] 未找到设备: {udid}")
        sys.exit(1)

    # 尝试匹配上次选择的 UDID
    if len(devices) > 1 and CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            last_udid = json.load(f).get("last_udid")
        if last_udid:
            for d in devices:
                if d.peer_info["Properties"]["UniqueDeviceID"] == last_udid:
                    p = d.peer_info["Properties"]
                    print(f"[INFO] 自动连接上次设备: {p['ProductType']} ({p['OSVersion']})")
                    return d

    if len(devices) == 1:
        info = devices[0].peer_info["Properties"]
        print(f"[INFO] 唯一设备: {info['ProductType']} ({info['OSVersion']})")
        return devices[0]

    # 多设备：列出让用户选
    print(f"\n[INFO] 发现 {len(devices)} 台设备:")
    for i, d in enumerate(devices, 1):
        p = d.peer_info["Properties"]
        print(f"  [{i}] {p['ProductType']}  iOS {p['OSVersion']}  {p['UniqueDeviceID'][:16]}...")

    while True:
        try:
            choice = input("请选择设备编号: ").strip()
            d = devices[int(choice) - 1]
            new_udid = d.peer_info["Properties"]["UniqueDeviceID"]
            if save_choice and CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                cfg["last_udid"] = new_udid
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(cfg, f, indent=4, ensure_ascii=False)
            return d
        except (ValueError, IndexError):
            print(f"  请输入 1-{len(devices)}")


def select_route(route_arg=None):
    files = sorted(ROUTES_DIR.glob("*.json"))
    files = [f for f in files if f.name != "config.json"]
    if not files:
        print(f"[ERROR] {ROUTES_DIR}/ 下没有路线文件")
        sys.exit(1)

    if route_arg:
        if route_arg.isdigit():
            idx = int(route_arg) - 1
            if 0 <= idx < len(files):
                return files[idx]
        else:
            for f in files:
                if f.stem == route_arg or f.name == route_arg:
                    return f
        print(f"[ERROR] 未找到路线: {route_arg}")
        sys.exit(1)

    if len(files) == 1:
        print(f"[INFO] 自动选择唯一路线: {files[0].name}")
        return files[0]

    print("\n可用的路线:")
    for i, f in enumerate(files, 1):
        data = json.loads(f.read_text(encoding="utf-8"))
        name = data.get("route_name", f.stem)
        points = len(data.get("coordinates", []))
        print(f"  [{i}] {name} ({points} 个点)")

    while True:
        try:
            choice = int(input("\n选择路线编号: ").strip())
            return files[choice - 1]
        except (ValueError, IndexError):
            print(f"请输入 1-{len(files)}")
        except EOFError:
            print("[ERROR] 非交互模式请用 --route 指定路线")
            sys.exit(1)


def load_route(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    coords = data.get("coordinates", [])
    if not coords:
        print(f"[ERROR] 路线 {path.name} 中没有 coordinates")
        sys.exit(1)
    return data


def apply_jitter(lat, lng, jitter_meters):
    if jitter_meters <= 0:
        return lat, lng
    dlat = random.uniform(-jitter_meters, jitter_meters) / METERS_PER_DEG_LAT
    dlng = random.uniform(-jitter_meters, jitter_meters) / (METERS_PER_DEG_LAT * math.cos(math.radians(lat)))
    return lat + dlat, lng + dlng


# ==================== 随机游走 (random_walk 模式) ====================


def parse_rectangle(corners):
    """从四个角提取矩形边界。角点顺序不敏感，自动取 min/max。"""
    lats = [p["lat"] for p in corners.values()]
    lngs = [p["lng"] for p in corners.values()]
    return {"min_lat": min(lats), "max_lat": max(lats), "min_lng": min(lngs), "max_lng": max(lngs)}


def random_position_in_bounds(bounds):
    """矩形内均匀随机取点"""
    return {
        "lat": random.uniform(bounds["min_lat"], bounds["max_lat"]),
        "lng": random.uniform(bounds["min_lng"], bounds["max_lng"]),
    }


def step_position(curr, direction_deg, speed_ms, interval_s, bounds):
    """
    执行一个 tick 的移动。
    返回 (next_pos, new_direction)。
    碰到边界时镜面反射方向。
    """
    step_m = speed_ms * interval_s
    dlat_per_m = 1.0 / METERS_PER_DEG_LAT
    dlng_per_m = 1.0 / (METERS_PER_DEG_LAT * math.cos(math.radians(curr["lat"])))

    d_rad = math.radians(direction_deg)
    next_pos = {
        "lat": curr["lat"] + step_m * math.cos(d_rad) * dlat_per_m,
        "lng": curr["lng"] + step_m * math.sin(d_rad) * dlng_per_m,
    }
    new_dir = direction_deg

    # 边界反弹
    hit_lat = False
    hit_lng = False
    if next_pos["lat"] < bounds["min_lat"]:
        next_pos["lat"] = bounds["min_lat"] + (bounds["min_lat"] - next_pos["lat"])
        hit_lat = True
    elif next_pos["lat"] > bounds["max_lat"]:
        next_pos["lat"] = bounds["max_lat"] - (next_pos["lat"] - bounds["max_lat"])
        hit_lat = True

    if next_pos["lng"] < bounds["min_lng"]:
        next_pos["lng"] = bounds["min_lng"] + (bounds["min_lng"] - next_pos["lng"])
        hit_lng = True
    elif next_pos["lng"] > bounds["max_lng"]:
        next_pos["lng"] = bounds["max_lng"] - (next_pos["lng"] - bounds["max_lng"])
        hit_lng = True

    if hit_lat:
        new_dir = -new_dir
    if hit_lng:
        new_dir = 180 - new_dir

    return next_pos, new_dir % 360


async def run_random_walk(loc, config):
    global stop_requested

    rw = config["random_walk"]
    bounds = parse_rectangle(rw["corners"])
    speed_ms = rw["speed_ms"]
    dir_stddev = rw["direction_change_stddev"]
    duration = rw.get("duration_seconds", 600)
    point_interval = config.get("point_interval", 0.05)
    jitter_meters = config.get("jitter_meters", 3.0)
    midpoint_prob = config.get("midpoint_probability", 0.15)

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

        # 中点插入
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

        # 每 10 秒输出一次进度
        if tick % max(1, int(10 / point_interval)) == 0:
            elapsed = time.time() - t_start
            print(f"  [{elapsed:.0f}s] {tick} ticks  |  {total_dist:.0f}m  |  "
                  f"({pos['lat']:.8f}, {pos['lng']:.8f})")

        await asyncio.sleep(point_interval)

    elapsed = time.time() - t_start
    print(f"\n[DONE] {tick} 次定位  |  {total_dist:.0f}m  |  耗时 {elapsed:.1f}s  |  速率 {tick / elapsed:.1f} Hz")


# ==================== 配速跑道 (pace 模式) ====================


def _deg_per_m(lat):
    """每米对应的经纬度偏移量"""
    return 1.0 / METERS_PER_DEG_LAT, 1.0 / (METERS_PER_DEG_LAT * math.cos(math.radians(lat)))


def _offset(lat, lng, dlat_m, dlng_m):
    """从 (lat, lng) 偏移 (dlat_m, dlng_m) 米"""
    dlat_d, dlng_d = _deg_per_m(lat)
    return {"lat": lat + dlat_m * dlat_d, "lng": lng + dlng_m * dlng_d}


def _generate_track(bounds, R, L, track_points, vertical):
    """
    生成跑道点序列：两个半圆 + 两条直道。
    vertical=True 表示直道沿经线（上下），半圆在纬线方向。
    """
    center_lat = (bounds["min_lat"] + bounds["max_lat"]) / 2
    center_lng = (bounds["min_lng"] + bounds["max_lng"]) / 2
    dlat_d, dlng_d = _deg_per_m(center_lat)

    # 四个圆心 (上直道两端两个半圆, 下直道两端两个半圆)
    if vertical:
        half_L = L / 2
        top_center = {"lat": center_lat + half_L * dlat_d, "lng": center_lng}
        bot_center = {"lat": center_lat - half_L * dlat_d, "lng": center_lng}
    else:
        half_L = L / 2
        top_center = {"lat": center_lat, "lng": center_lng + half_L * dlng_d}
        bot_center = {"lat": center_lat, "lng": center_lng - half_L * dlng_d}

    # 跑道四段周长
    half_circle = math.pi * R
    straight = L
    total = 2 * half_circle + 2 * straight

    # 按弧长均匀分配点数
    n_circle = max(int(track_points * half_circle / total), 3)
    n_straight = max(int(track_points * straight / total), 2)
    # 补齐
    while 2 * n_circle + 2 * n_straight < track_points:
        n_circle += 1

    coords = []

    def arc_points(center, start_deg):
        for j in range(n_circle):
            a = math.radians(start_deg + 180 * j / n_circle)
            coords.append(_offset(center["lat"], center["lng"], R * math.sin(a), R * math.cos(a)))

    def straight_points(fr, to):
        for j in range(n_straight):
            frac = j / n_straight
            coords.append({"lat": fr["lat"] + (to["lat"] - fr["lat"]) * frac,
                            "lng": fr["lng"] + (to["lng"] - fr["lng"]) * frac})

    # 逆时针：下半圆(左→右) → 右直道(下→上) → 上半圆(右→左) → 左直道(上→下)

    # 下半圆: 180°(左) → 360°/0°(右)，经底部
    arc_points(bot_center, 180)

    # 右直道: 下半圆终点 → 上半圆右端
    right_bot = coords[-1]
    right_top = _offset(top_center["lat"], top_center["lng"], 0, R)
    straight_points(right_bot, right_top)

    # 上半圆: 0°(右) → 180°(左)，经顶部
    arc_points(top_center, 0)

    # 左直道: 上半圆终点 → 下半圆左端
    left_top = coords[-1]
    left_bot = _offset(bot_center["lat"], bot_center["lng"], 0, -R)
    straight_points(left_top, left_bot)

    return coords, total


async def run_pace(loc, config):
    global stop_requested

    rw = config["random_walk"]
    bounds = parse_rectangle(rw["corners"])
    pace_min_per_km = rw.get("pace_min_per_km", 5.0)
    duration = rw.get("duration_seconds", 1800)
    margin_m = rw.get("ellipse_margin_meters", 2)
    track_points = rw.get("ellipse_points", 200)
    jitter_meters = config.get("jitter_meters", 1.0)

    # 矩形尺寸
    center_lat = (bounds["min_lat"] + bounds["max_lat"]) / 2
    w_m = (bounds["max_lng"] - bounds["min_lng"]) * METERS_PER_DEG_LAT * math.cos(math.radians(center_lat))
    h_m = (bounds["max_lat"] - bounds["min_lat"]) * METERS_PER_DEG_LAT
    vertical = h_m >= w_m  # 长边=直道

    short = min(w_m, h_m) / 2 - margin_m
    long = max(w_m, h_m)

    base_R = max(short, 3)
    base_L = max(long - 2 * base_R, 5)

    def _new_track():
        scale = random.uniform(0.6, 1.0)
        R = base_R * scale
        L = max(long - 2 * R, 5)
        return _generate_track(bounds, R, L, track_points, vertical)

    coords, lap_dist = _new_track()
    speed_ms = 1000.0 / (pace_min_per_km * 60.0)

    print(f"\n{'=' * 50}")
    print(f"模式: 配速跑道 (pace)")
    print(f"配速: {pace_min_per_km:.1f} min/km ({speed_ms:.1f} m/s)")
    print(f"跑道: 直道{base_L:.0f}m 半圆R{base_R:.0f}m  |  边距{margin_m:.0f}m")
    print(f"每圈约 {lap_dist:.0f}m（随机变化）  |  总长: {duration}s ({duration / 60:.1f}min)")
    print(f"{'=' * 50}\n")

    tick = 0
    total_dist = 0.0
    t_start = time.time()
    t_end = t_start + duration
    total = len(coords)
    i = 0
    step_dist = lap_dist / total
    point_interval = lap_dist / speed_ms / total

    while time.time() < t_end:
        if stop_requested:
            break

        if i == 0 and tick > 0:
            coords, lap_dist = _new_track()
            step_dist = lap_dist / total
            point_interval = lap_dist / speed_ms / total

        pt = coords[i]
        lat, lng = apply_jitter(pt["lat"], pt["lng"], jitter_meters)
        await loc.set(lat, lng)
        tick += 1
        total_dist += step_dist
        i = (i + 1) % total

        if tick % max(1, int(1.0 / point_interval)) == 0:
            elapsed = time.time() - t_start
            cur_pace = (elapsed / 60) / (total_dist / 1000)
            print(f"  [{elapsed:.0f}s] {tick} ticks  |  {total_dist:.0f}m  |  实际配速 {cur_pace:.1f} min/km")

        await asyncio.sleep(point_interval)

    elapsed = time.time() - t_start
    final_pace = (elapsed / 60) / (total_dist / 1000) if total_dist > 0 else 0
    print(f"\n[DONE] {tick} 次  |  {total_dist:.0f}m ({total_dist / 1000:.2f}km)  |  "
          f"实际配速 {final_pace:.1f} min/km")


async def run_route(loc, route_data, config):
    global stop_requested

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

            lat, lng = apply_jitter(coordinates[i]["lat"], coordinates[i]["lng"], jitter_meters)
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
    """输入西北和东南两个对角，自动填充另外两角。"""
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
    """交互式设置，返回 (mode, route_data, overrides)"""
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
        CONFIG_FILE.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
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
        CONFIG_FILE.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
        return "random_walk", None, {}

    elif choice == "3":
        return "route", None, {}

    elif choice == "4":
        return "calibrate", None, {}

    else:
        return "developer_mode", None, {}


async def calibrate_corners(config, udid=None):
    """连接设备，逐角微调坐标。WASD 移动，手机上看位置对了按回车确认。"""
    rsd = await connect_via_tunneld(udid=udid)
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

    rw = config.get("random_walk", {})
    old = rw.get("corners")

    # 初始值：有就用，没有给北京附近
    if old:
        corners = {k: dict(v) for k, v in old.items()}
    else:
        default = {"lat": 28.735, "lng": 115.825}
        corners = {"nw": dict(default), "ne": dict(default), "se": dict(default), "sw": dict(default)}

    labels = [("nw", "西北"), ("ne", "东北"), ("se", "东南"), ("sw", "西南")]
    step_m = 20.0

    async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as loc:
        for key, label in labels:
            pos = corners[key]
            await loc.set(pos["lat"], pos["lng"])

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

                await loc.set(pos["lat"], pos["lng"])
                print(f"  ({pos['lat']:.8f}, {pos['lng']:.8f})  步长={step_m:.0f}m")

    # 自动填充四个角（基于 NW 和 SE 推算 NE、SW）
    nw = corners["nw"]
    se = corners["se"]
    corners["ne"] = {"lat": nw["lat"], "lng": se["lng"]}
    corners["sw"] = {"lat": se["lat"], "lng": nw["lng"]}

    rw["corners"] = corners
    config["random_walk"] = rw
    CONFIG_FILE.write_text(json.dumps(config, indent=4, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] 四角已保存到 {CONFIG_FILE}")
    print(f"  NW: {corners['nw']['lat']:.8f}, {corners['nw']['lng']:.8f}")
    print(f"  NE: {corners['ne']['lat']:.8f}, {corners['ne']['lng']:.8f}")
    print(f"  SE: {corners['se']['lat']:.8f}, {corners['se']['lng']:.8f}")
    print(f"  SW: {corners['sw']['lat']:.8f}, {corners['sw']['lng']:.8f}")
    rsd.close()


async def handle_developer_mode(config, udid=None):
    """检查/激活开发者模式 (iOS 16+ 虚拟定位的前置条件)"""
    rsd = await connect_via_tunneld(udid=udid)

    from pymobiledevice3.services.amfi import AmfiService
    from pymobiledevice3.exceptions import DeviceHasPasscodeSetError

    try:
        status = await rsd.get_developer_mode_status()
    except Exception as e:
        print(f"[WARN] 无法查询开发者模式状态: {e}")
        print("  设备可能不支持此操作（iOS 15 及以下无此限制）")
        rsd.close()
        return True

    if status:
        print("[OK] 开发者模式已开启，无需额外操作")
        rsd.close()
        return True

    amfi = AmfiService(rsd)
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
                await amfi.reveal_developer_mode_option_in_ui()
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
                await amfi.enable_developer_mode(enable_post_restart=True)
                print("[OK] 开发者模式已激活！")
                rsd.close()
                return True
            except DeviceHasPasscodeSetError:
                print("[ERROR] 设备设置了锁屏密码，无法自动激活开发者模式")
                print("  请先关闭锁屏密码再试，或使用选项 [1] 手动开启。")
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


async def async_main(args, preset_mode=None, preset_route_data=None):
    global stop_requested

    config = load_config()

    if args.mode:
        # 命令行模式：从 args 和 config 读取
        if args.loop:
            config["loop_count"] = args.loop
        if args.duration:
            config.setdefault("random_walk", {})["duration_seconds"] = args.duration
        if args.interval is not None:
            config["point_interval"] = args.interval
        mode = args.mode
    else:
        # 交互模式：使用菜单选择的 mode
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
            route_path = select_route(route_arg=args.route)
            route_data = load_route(route_path)
    else:
        rw = config.get("random_walk", {})
        if not rw.get("corners"):
            print("[ERROR] random_walk 模式需要在 config.json 中设置 random_walk.corners")
            print("  请使用交互模式设置矩形区域，或编辑 config.json")
            sys.exit(1)

    rsd = await connect_via_tunneld(udid=args.udid)

    # 自动检查开发者模式（仅提醒，不阻塞）
    try:
        if not await rsd.get_developer_mode_status():
            print("\n[WARN] 开发者模式未开启 — 虚拟定位可能不生效")
            print("  可用 python main.py --devmode 检查并开启")
            print()
    except Exception:
        pass  # iOS 15 及以下设备无此检查，忽略

    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation

    start_stop_listener()

    try:
        async with DvtProvider(rsd) as dvt, LocationSimulation(dvt) as loc:
            if not stop_requested:
                if mode == "route":
                    await run_route(loc, route_data, config)
                elif mode == "pace":
                    await run_pace(loc, config)
                else:
                    await run_random_walk(loc, config)
            await loc.clear()
    except KeyboardInterrupt:
        print("\n[STOP] 用户中断")
    finally:
        stop_requested = True


def main():
    parser = argparse.ArgumentParser(description="Smart-Sports-AutoLocate v2")
    parser.add_argument("--mode", "-m", choices=["route", "random_walk", "pace", "developer_mode"], help="运行模式")
    parser.add_argument("--route", "-r", help="路线名称或编号 (route 模式)")
    parser.add_argument("--loop", "-l", type=int, help="循环圈数 (route 模式)")
    parser.add_argument("--duration", "-d", type=int, help="运行时长/秒 (random_walk 模式)")
    parser.add_argument("--udid", "-u", help="目标设备 UDID")
    parser.add_argument("--interval", "-i", type=float, help="定位间隔（秒）")
    parser.add_argument("--devmode", action="store_true", help="检查/激活开发者模式")
    args = parser.parse_args()

    mode = None
    route_data = None

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
        # 命令行模式：直接跑
        try:
            asyncio.run(async_main(args, preset_mode=args.mode, preset_route_data=route_data))
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

    # 交互式菜单（循环，校准完后回菜单）
    while True:
        config = load_config()
        mode, route_data, _ = interactive_setup(config)

        if mode == "route":
            route_path = select_route()
            route_data = load_route(route_path)

        if mode == "calibrate":
            try:
                asyncio.run(async_main(args, preset_mode="calibrate"))
            except Exception as e:
                print(f"\n[ERROR] {e}")
                import traceback
                traceback.print_exc()
            continue  # 回菜单

        if mode == "developer_mode":
            try:
                asyncio.run(handle_developer_mode(load_config(), udid=args.udid))
            except Exception as e:
                print(f"\n[ERROR] {e}")
                import traceback
                traceback.print_exc()
            continue  # 回菜单

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
