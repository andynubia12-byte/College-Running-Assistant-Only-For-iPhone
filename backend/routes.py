#!/usr/bin/env python3
"""路线文件管理模块"""

import json
import sys
from pathlib import Path

ROUTES_DIR = Path("routes")


def list_routes():
    """列出 routes/ 下所有 JSON 路线文件"""
    ROUTES_DIR.mkdir(exist_ok=True)
    files = sorted(ROUTES_DIR.glob("*.json"))
    result = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            coords = data.get("coordinates", [])
            result.append({
                "filename": f.name,
                "name": data.get("route_name", f.stem),
                "points": len(coords),
            })
        except (json.JSONDecodeError, KeyError):
            result.append({"filename": f.name, "name": f.stem, "points": 0, "error": True})
    return result


def load_route(filename):
    """加载指定路线文件"""
    path = ROUTES_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"路线文件不存在: {filename}")
    data = json.loads(path.read_text(encoding="utf-8"))
    coords = data.get("coordinates", [])
    if not coords:
        raise ValueError(f"路线 {filename} 中没有 coordinates")
    return data


def load_route_by_name(name_or_index):
    """按名称或编号加载路线"""
    files = sorted(ROUTES_DIR.glob("*.json"))

    # 按编号
    if isinstance(name_or_index, int) or (isinstance(name_or_index, str) and name_or_index.isdigit()):
        idx = int(name_or_index) - 1
        if 0 <= idx < len(files):
            return load_route(files[idx].name)

    # 按名称或文件名
    target = str(name_or_index)
    for f in files:
        if f.stem == target or f.name == target:
            return load_route(f.name)

    raise FileNotFoundError(f"未找到路线: {name_or_index}")


def import_gpx(gpx_path):
    """导入 GPX 文件并保存为 JSON 路线。返回保存后的文件信息。"""
    import xml.etree.ElementTree as ET

    path = Path(gpx_path)
    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {gpx_path}")

    NS = {"gpx": "http://www.topografix.com/GPX/1/1"}
    tree = ET.parse(path)
    root = tree.getroot()

    # 尝试多种 GPX 格式
    points = root.findall(".//gpx:trk/gpx:trkseg/gpx:trkpt", NS)
    if not points:
        ns = "http://www.topografix.com/GPX/1/1"
        points = root.findall(f".//{{{ns}}}trk/{{{ns}}}trkseg/{{{ns}}}trkpt")
    if not points:
        points = root.findall(".//trkpt")
    if not points:
        points = root.findall(".//wpt")
    if not points:
        points = root.findall(".//rtept")

    if not points:
        raise ValueError("GPX 文件中未找到轨迹点（支持 trkpt / wpt / rtept）")

    coords = [{"lat": float(pt.get("lat")), "lng": float(pt.get("lon"))} for pt in points]

    route_name = path.stem
    route_data = {
        "route_name": route_name,
        "source": path.name,
        "coordinates": coords,
    }

    ROUTES_DIR.mkdir(exist_ok=True)
    out_path = ROUTES_DIR / f"{route_name}.json"
    out_path.write_text(json.dumps(route_data, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "filename": out_path.name,
        "name": route_name,
        "points": len(coords),
    }
