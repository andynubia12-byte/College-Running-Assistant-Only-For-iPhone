#!/usr/bin/env python3
"""设备连接和管理模块"""

import json
import sys

from .config import CONFIG_FILE
from .device_models import DEVICE_MODELS


async def connect_via_tunneld(udid=None, save_choice=True):
    """通过运行中的 tunneld 连接设备。udid 指定设备，否则多设备时交互选择。"""
    from pymobiledevice3.tunneld.api import get_tunneld_devices
    from pymobiledevice3.exceptions import TunneldConnectionError

    try:
        devices = await get_tunneld_devices()
    except TunneldConnectionError:
        raise ConnectionError(
            "无法连接到 tunneld (127.0.0.1:49151)\n"
            "请先以管理员身份运行:\n"
            "  python -m pymobiledevice3 remote tunneld"
        )

    if not devices:
        raise ConnectionError(
            "tunneld 已运行但未发现设备\n"
            "请检查 USB 连接并确保设备已解锁"
        )

    if udid:
        for d in devices:
            if d.peer_info["Properties"]["UniqueDeviceID"] == udid:
                return d
        raise ValueError(f"未找到设备: {udid}")

    # 尝试匹配上次选择的 UDID
    if len(devices) > 1 and CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            last_udid = json.load(f).get("last_udid")
        if last_udid:
            for d in devices:
                if d.peer_info["Properties"]["UniqueDeviceID"] == last_udid:
                    p = d.peer_info["Properties"]
                    return d  # caller can read name from peer_info

    if len(devices) == 1:
        return devices[0]

    # 多设备：由调用方处理选择
    raise ValueError("MULTIPLE_DEVICES", devices)


def format_device_info(d):
    """提取设备可读信息"""
    p = d.peer_info["Properties"]
    pt = p["ProductType"]
    # device name: peer_info doesn't have it, try all_values (RSD lockdown cache)
    name = p.get("DeviceName")
    if not name:
        try:
            all_vals = d.all_values
            if isinstance(all_vals, dict):
                name = all_vals.get("DeviceName")
        except Exception:
            pass
    if not name:
        name = p.get("DeviceClass") or pt
    return {
        "udid": p["UniqueDeviceID"],
        "product_type": pt,
        "model_name": DEVICE_MODELS.get(pt, pt),
        "os_version": p["OSVersion"],
        "name": name,
    }


async def check_developer_mode(rsd):
    """检查开发者模式状态，返回 True=已开启 / False=未开启 / None=不支持"""
    try:
        return await rsd.get_developer_mode_status()
    except Exception:
        return None  # iOS 15- 设备不支持此检查


async def reveal_developer_mode_option(rsd):
    """在设备上显示开发者模式选项"""
    from pymobiledevice3.services.amfi import AmfiService

    amfi = AmfiService(rsd)
    await amfi.reveal_developer_mode_option_in_ui()


async def enable_developer_mode(rsd):
    """完全激活开发者模式（设备会重启）"""
    from pymobiledevice3.services.amfi import AmfiService
    from pymobiledevice3.exceptions import DeviceHasPasscodeSetError

    amfi = AmfiService(rsd)
    try:
        await amfi.enable_developer_mode(enable_post_restart=True)
        return True
    except DeviceHasPasscodeSetError:
        raise RuntimeError("设备设置了锁屏密码，无法自动激活开发者模式。请先关闭锁屏密码再试。")
