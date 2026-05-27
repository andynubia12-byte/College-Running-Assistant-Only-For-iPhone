#!/usr/bin/env python3
"""定位发送模块 — 包装 DVT LocationSimulation"""

from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation


class DeviceLocalizer:
    """管理 iOS 设备的虚拟定位连接和操作"""

    def __init__(self, rsd):
        self.rsd = rsd
        self.dvt = None
        self.loc = None

    async def __aenter__(self):
        self.dvt = DvtProvider(self.rsd)
        await self.dvt.__aenter__()
        self.loc = LocationSimulation(self.dvt)
        await self.loc.__aenter__()
        return self

    async def __aexit__(self, *args):
        try:
            if self.loc:
                await self.loc.clear()
                await self.loc.__aexit__(*args)
        finally:
            if self.dvt:
                await self.dvt.__aexit__(*args)

    async def set(self, lat, lng):
        """设置设备定位到指定坐标"""
        await self.loc.set(lat, lng)

    async def clear(self):
        """清除虚拟定位，恢复真实 GPS"""
        await self.loc.clear()


async def create_localizer(rsd):
    """快捷创建 DeviceLocalizer 上下文管理器"""
    return DeviceLocalizer(rsd)
