from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QDoubleSpinBox, QSpinBox, QGroupBox,
)

from backend.config import load_config, save_config, save_config_preset, load_config_preset
from ui.app_state import get_state


class PacePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header
        top = QHBoxLayout()
        self.back_btn = QPushButton("← 返回")
        self.back_btn.setObjectName("backBtn")
        top.addWidget(self.back_btn)
        top.addStretch()
        layout.addLayout(top)

        title = QLabel("配速跑道")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # Config form
        form = QFormLayout()
        form.setSpacing(10)

        self.pace_spin = QDoubleSpinBox()
        self.pace_spin.setRange(2.0, 15.0)
        self.pace_spin.setValue(5.0)
        self.pace_spin.setSuffix(" min/km")
        self.pace_spin.setDecimals(1)
        form.addRow("配速:", self.pace_spin)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(60, 36000)
        self.duration_spin.setValue(1800)
        self.duration_spin.setSuffix(" 秒")
        form.addRow("时长:", self.duration_spin)

        self.jitter_spin = QDoubleSpinBox()
        self.jitter_spin.setRange(0.0, 20.0)
        self.jitter_spin.setValue(1.0)
        self.jitter_spin.setSuffix(" 米")
        self.jitter_spin.setDecimals(1)
        form.addRow("抖动:", self.jitter_spin)

        layout.addLayout(form)

        # Start button
        ctrl = QHBoxLayout()
        self.start_btn = QPushButton("开始运行")
        self.start_btn.setObjectName("primaryBtn")
        self.start_btn.clicked.connect(self._on_start)
        ctrl.addWidget(self.start_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        layout.addStretch()

    def _load_config(self):
        state = get_state()
        if state.active_config_preset:
            cfg = load_config_preset(state.active_config_preset)
        else:
            cfg = load_config()
        rw = cfg.get("random_walk", {})
        self.pace_spin.setValue(rw.get("pace_min_per_km", 5.0))
        self.duration_spin.setValue(rw.get("duration_seconds", 1800))
        self.jitter_spin.setValue(cfg.get("jitter_meters", 1.0))
        self._config = cfg

    def reload_config(self):
        self._load_config()

    def _on_start(self):
        rw = self._config.get("random_walk", {})
        if not rw.get("corners"):
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "缺少配置",
                "未设置矩形区域 (corners)。\n请先在 config.json 中设置或使用校准功能。")
            return

        cfg = self._config.copy()
        cfg["jitter_meters"] = self.jitter_spin.value()
        rw = cfg.setdefault("random_walk", {})
        rw["pace_min_per_km"] = self.pace_spin.value()
        rw["duration_seconds"] = self.duration_spin.value()

        state = get_state()
        if state.active_config_preset:
            save_config_preset(state.active_config_preset, cfg)
        else:
            save_config(cfg)

        run_config = {
            "mode": "pace",
            "config": cfg,
            "title": f"配速跑道 — {self.pace_spin.value():.1f} min/km",
            "duration": self.duration_spin.value(),
        }
        w = self.window()
        if hasattr(w, "start_run"):
            w.start_run(run_config)
