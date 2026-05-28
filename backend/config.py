#!/usr/bin/env python3
"""配置管理模块"""

import json
from pathlib import Path

CONFIG_FILE = Path("config.json")

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


def load_config():
    """加载配置，不存在则创建默认配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg
    CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=4, ensure_ascii=False), encoding="utf-8")
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    """保存配置到文件"""
    CONFIG_FILE.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")


# ---- config presets (configs/ directory) ----

CONFIGS_DIR = Path("configs")


def list_config_presets():
    """列出所有 config 预设文件"""
    CONFIGS_DIR.mkdir(exist_ok=True)
    files = sorted(CONFIGS_DIR.glob("*.json"))
    return [f.stem for f in files]


def load_config_preset(name):
    """加载指定预设文件"""
    path = CONFIGS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"预设文件不存在: {name}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_config_preset(name, cfg):
    """保存到预设文件"""
    CONFIGS_DIR.mkdir(exist_ok=True)
    path = CONFIGS_DIR / f"{name}.json"
    path.write_text(json.dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")


def delete_config_preset(name):
    """删除预设文件"""
    path = CONFIGS_DIR / f"{name}.json"
    if path.exists():
        path.unlink()
