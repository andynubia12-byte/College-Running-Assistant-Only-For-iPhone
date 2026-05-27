from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AppState:
    rsd: Optional[object] = None
    localizer: Optional[object] = None
    running: bool = False
    mode: Optional[str] = None
    tick: int = 0
    total_dist: float = 0.0
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None
    connected_device_info: dict = field(default_factory=dict)


_state = AppState()


def get_state() -> AppState:
    return _state
