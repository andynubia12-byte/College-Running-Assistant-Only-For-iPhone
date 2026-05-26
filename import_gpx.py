#!/usr/bin/env python3
"""
GPX 路线导入工具
将 GPX 文件转换为 Smart-Sports-AutoLocate v2 的 JSON 路线格式

用法:
    python import_gpx.py route.gpx

支持来源:
    - 高德地图 / 百度地图 导出的 GPX
    - Strava / Keep / 咕咚 等运动 App 导出的 GPX
    - 在线地图工具 (如 https://www.gpx.studio/)
"""

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROUTES_DIR = Path("routes")
NS = {"gpx": "http://www.topografix.com/GPX/1/1"}


def parse_gpx(filepath):
    """解析 GPX 文件，提取所有坐标点"""
    tree = ET.parse(filepath)
    root = tree.getroot()

    # 尝试带命名空间和不带命名空间两种方式
    points = root.findall(".//gpx:trk/gpx:trkseg/gpx:trkpt", NS)
    if not points:
        points = root.findall(".//{http://www.topografix.com/GPX/1/1}trk/{http://www.topografix.com/GPX/1/1}trkseg/{http://www.topografix.com/GPX/1/1}trkpt")

    if not points:
        # Try parsing without namespace
        points = root.findall(".//trkpt")
    if not points:
        # Try wpt (waypoints)
        points = root.findall(".//wpt")
    if not points:
        # Try rte/rtept (route points)
        points = root.findall(".//rtept")

    if not points:
        print("[ERROR] GPX 文件中未找到轨迹点")
        print("  支持的格式: <trkpt>, <wpt>, <rtept>")
        sys.exit(1)

    coords = []
    for pt in points:
        lat = float(pt.get("lat"))
        lon = float(pt.get("lon"))
        coords.append({"lat": lat, "lng": lon})

    return coords


def main():
    if len(sys.argv) < 2:
        print("用法: python import_gpx.py <gpx文件路径>")
        print("  python import_gpx.py campus.gpx")
        sys.exit(1)

    gpx_path = Path(sys.argv[1])
    if not gpx_path.exists():
        print(f"[ERROR] 文件不存在: {gpx_path}")
        sys.exit(1)

    coords = parse_gpx(gpx_path)
    print(f"[INFO] 解析到 {len(coords)} 个轨迹点")

    route_name = gpx_path.stem
    route_data = {
        "route_name": route_name,
        "source": str(gpx_path.name),
        "coordinates": coords,
    }

    ROUTES_DIR.mkdir(exist_ok=True)

    out = ROUTES_DIR / f"{route_name}.json"
    if out.exists():
        overwrite = input(f"  路线 {out.name} 已存在，覆盖？(y/n): ").strip().lower()
        if overwrite != "y":
            alt = input("  新路线名称: ").strip()
            if alt:
                out = ROUTES_DIR / f"{alt}.json"

    out.write_text(json.dumps(route_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] 已保存到 {out}")


if __name__ == "__main__":
    main()
