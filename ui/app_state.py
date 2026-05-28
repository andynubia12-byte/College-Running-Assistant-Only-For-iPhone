from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppState:
    rsd_list: list = field(default_factory=list)
    localizers: list = field(default_factory=list)
    running: bool = False
    mode: Optional[str] = None
    tick: int = 0
    total_dist: float = 0.0
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    connected_device_infos: list = field(default_factory=list)
    active_config_preset: Optional[str] = None

    @property
    def rsd(self):
        """Backward-compat: first connected device."""
        return self.rsd_list[0] if self.rsd_list else None

    @property
    def connected_device_info(self):
        """Backward-compat: first device info dict."""
        return self.connected_device_infos[0] if self.connected_device_infos else {}


_state = AppState()


def get_state() -> AppState:
    return _state
