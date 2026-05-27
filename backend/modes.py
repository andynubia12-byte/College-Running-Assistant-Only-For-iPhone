#!/usr/bin/env python3
"""三种定位模式的轨迹生成逻辑"""

import asyncio
import math
import random
import time

METERS_PER_DEG_LAT = 111320.0


# ==================== 坐标工具函数 ====================


def apply_jitter(lat, lng, jitter_meters):
    """在坐标上施加随机抖动，模拟真实 GPS 误差"""
    if jitter_meters <= 0:
        return lat, lng
    dlat = random.uniform(-jitter_meters, jitter_meters) / METERS_PER_DEG_LAT
    dlng = random.uniform(-jitter_meters, jitter_meters) / (METERS_PER_DEG_LAT * math.cos(math.radians(lat)))
    return lat + dlat, lng + dlng


def parse_rectangle(corners):
    """从四个角提取矩形边界"""
    lats = [p["lat"] for p in corners.values()]
    lngs = [p["lng"] for p in corners.values()]
    return {"min_lat": min(lats), "max_lat": max(lats), "min_lng": min(lngs), "max_lng": max(lngs)}


# ==================== 配速跑道 (pace) ====================


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

    if vertical:
        half_L = L / 2
        top_center = {"lat": center_lat + half_L * dlat_d, "lng": center_lng}
        bot_center = {"lat": center_lat - half_L * dlat_d, "lng": center_lng}
    else:
        half_L = L / 2
        top_center = {"lat": center_lat, "lng": center_lng + half_L * dlng_d}
        bot_center = {"lat": center_lat, "lng": center_lng - half_L * dlng_d}

    half_circle = math.pi * R
    straight = L
    total = 2 * half_circle + 2 * straight

    n_circle = max(int(track_points * half_circle / total), 3)
    n_straight = max(int(track_points * straight / total), 2)
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
    arc_points(bot_center, 180)
    right_bot = coords[-1]
    right_top = _offset(top_center["lat"], top_center["lng"], 0, R)
    straight_points(right_bot, right_top)
    arc_points(top_center, 0)
    left_top = coords[-1]
    left_bot = _offset(bot_center["lat"], bot_center["lng"], 0, -R)
    straight_points(left_top, left_bot)

    return coords, total


async def gen_pace(config, stop_event):
    """
    配速跑道轨迹生成器。
    每次迭代 yield (lat, lng, step_dist, lap_dist)，供调用方发送定位。
    """
    rw = config["random_walk"]
    bounds = parse_rectangle(rw["corners"])
    pace_min_per_km = rw.get("pace_min_per_km", 5.0)
    duration = rw.get("duration_seconds", 1800)
    margin_m = rw.get("ellipse_margin_meters", 2)
    track_points = rw.get("ellipse_points", 200)
    jitter_meters = config.get("jitter_meters", 1.0)

    center_lat = (bounds["min_lat"] + bounds["max_lat"]) / 2
    w_m = (bounds["max_lng"] - bounds["min_lng"]) * METERS_PER_DEG_LAT * math.cos(math.radians(center_lat))
    h_m = (bounds["max_lat"] - bounds["min_lat"]) * METERS_PER_DEG_LAT
    vertical = h_m >= w_m
    short = min(w_m, h_m) / 2 - margin_m
    long = max(w_m, h_m)
    base_R = max(short, 3)
    base_L = max(long - 2 * base_R, 5)

    speed_ms = 1000.0 / (pace_min_per_km * 60.0)

    info = {
        "pace_min_per_km": pace_min_per_km,
        "speed_ms": speed_ms,
        "base_R": base_R,
        "base_L": base_L,
        "margin_m": margin_m,
        "duration": duration,
    }

    yield None, info  # 第一个 yield 返回元数据

    tick = 0
    total_dist = 0.0
    t_start = time.time()
    t_end = t_start + duration
    total = track_points
    i = 0

    # 生成第一圈轨迹
    scale = random.uniform(0.6, 1.0)
    R = base_R * scale
    L = max(long - 2 * R, 5)
    coords, lap_dist = _generate_track(bounds, R, L, total, vertical)
    step_dist = lap_dist / total
    point_interval = lap_dist / speed_ms / total

    while time.time() < t_end:
        if stop_event.is_set():
            break

        if i == 0 and tick > 0:
            scale = random.uniform(0.6, 1.0)
            R = base_R * scale
            L = max(long - 2 * R, 5)
            coords, lap_dist = _generate_track(bounds, R, L, total, vertical)
            step_dist = lap_dist / total
            point_interval = lap_dist / speed_ms / total

        pt = coords[i]
        lat, lng = apply_jitter(pt["lat"], pt["lng"], jitter_meters)
        tick += 1
        total_dist += step_dist
        i = (i + 1) % total

        yield (lat, lng, tick, total_dist, step_dist, point_interval), None

        await asyncio.sleep(point_interval)

    # 最终状态
    elapsed = time.time() - t_start
    yield None, {"done": True, "tick": tick, "total_dist": total_dist, "elapsed": elapsed}


# ==================== 随机游走 (random_walk) ====================


def random_position_in_bounds(bounds):
    """矩形内均匀随机取点"""
    return {
        "lat": random.uniform(bounds["min_lat"], bounds["max_lat"]),
        "lng": random.uniform(bounds["min_lng"], bounds["max_lng"]),
    }


def step_position(curr, direction_deg, speed_ms, interval_s, bounds):
    """
    执行一个 tick 的移动。返回 (next_pos, new_direction)。
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


async def gen_random_walk(config, stop_event):
    """
    随机游走轨迹生成器。
    每次迭代 yield (lat, lng, tick, total_dist, point_interval)，供调用方发送定位。
    """
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

    info = {
        "bounds": bounds,
        "speed_ms": speed_ms,
        "dir_stddev": dir_stddev,
        "duration": duration,
        "point_interval": point_interval,
    }
    yield None, info

    tick = 0
    total_dist = 0.0
    t_start = time.time()
    t_end = t_start + duration

    while time.time() < t_end:
        if stop_event.is_set():
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
        tick += 1

        yield (lat_j, lng_j, tick, total_dist, point_interval, None), None

        if insert_mid:
            await asyncio.sleep(point_interval * 0.5)
            mlat = (prev_pos["lat"] + pos["lat"]) / 2
            mlng = (prev_pos["lng"] + pos["lng"]) / 2
            mlat, mlng = apply_jitter(mlat, mlng, jitter_meters)
            tick += 1
            yield (mlat, mlng, tick, total_dist, point_interval, None), None

        await asyncio.sleep(point_interval)

    elapsed = time.time() - t_start
    yield None, {"done": True, "tick": tick, "total_dist": total_dist, "elapsed": elapsed}


# ==================== 路线播放 (route) ====================


async def gen_route(route_data, config, stop_event):
    """
    路线播放轨迹生成器。
    每次迭代 yield (lat, lng, tick, ...)，供调用方发送定位。
    """
    coordinates = route_data["coordinates"]
    loop_count = config.get("loop_count", 10)
    point_interval = config.get("point_interval", 0.05)
    jitter_meters = config.get("jitter_meters", 3.0)
    midpoint_prob = config.get("midpoint_probability", 0.15)

    total = len(coordinates)
    name = route_data.get("route_name", "unknown")

    info = {
        "name": name,
        "loop_count": loop_count,
        "points": total,
        "point_interval": point_interval,
    }
    yield None, info

    tick = 0
    t_start = time.time()

    for lap in range(1, loop_count + 1):
        if stop_event.is_set():
            break

        for i in range(total):
            if stop_event.is_set():
                break

            insert_mid = False
            if i < total - 1 and not (i == 0 or i == total - 2):
                if random.random() < midpoint_prob:
                    insert_mid = True

            lat, lng = apply_jitter(coordinates[i]["lat"], coordinates[i]["lng"], jitter_meters)
            tick += 1
            yield (lat, lng, tick, None, point_interval, lap), None

            if insert_mid:
                await asyncio.sleep(point_interval * 0.5)
                a, b = coordinates[i], coordinates[i + 1]
                mlat, mlng = apply_jitter((a["lat"] + b["lat"]) / 2, (a["lng"] + b["lng"]) / 2, jitter_meters)
                tick += 1
                yield (mlat, mlng, tick, None, point_interval, lap), None

            await asyncio.sleep(point_interval)

    elapsed = time.time() - t_start
    yield None, {"done": True, "tick": tick, "elapsed": elapsed}
