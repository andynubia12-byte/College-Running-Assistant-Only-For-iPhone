from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QDoubleSpinBox, QSpinBox, QGroupBox, QMessageBox,
)

from backend.config import load_config, save_config


class WalkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load_config()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("随机游走")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        form = QFormLayout()

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 20.0)
        self.speed_spin.setValue(3.0)
        self.speed_spin.setSuffix(" m/s")
        self.speed_spin.setDecimals(1)
        form.addRow("速度:", self.speed_spin)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(60, 36000)
        self.duration_spin.setValue(1800)
        self.duration_spin.setSuffix(" 秒")
        form.addRow("时长:", self.duration_spin)

        self.jitter_spin = QDoubleSpinBox()
        self.jitter_spin.setRange(0.0, 20.0)
        self.jitter_spin.setValue(3.0)
        self.jitter_spin.setSuffix(" 米")
        self.jitter_spin.setDecimals(1)
        form.addRow("抖动:", self.jitter_spin)

        self.dir_spin = QDoubleSpinBox()
        self.dir_spin.setRange(0.5, 45.0)
        self.dir_spin.setValue(5.0)
        self.dir_spin.setSuffix(" deg")
        self.dir_spin.setDecimals(1)
        form.addRow("方向变化:", self.dir_spin)

        layout.addLayout(form)

        ctrl = QHBoxLayout()
        self.start_btn = QPushButton("开始运行")
        self.start_btn.clicked.connect(self._on_start)
        ctrl.addWidget(self.start_btn)

        self.back_btn = QPushButton("返回")
        ctrl.addWidget(self.back_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        layout.addStretch()

    def _load_config(self):
        cfg = load_config()
        rw = cfg.get("random_walk", {})
        self.speed_spin.setValue(rw.get("speed_ms", 3.0))
        self.duration_spin.setValue(rw.get("duration_seconds", 1800))
        self.jitter_spin.setValue(cfg.get("jitter_meters", 3.0))
        self.dir_spin.setValue(rw.get("direction_change_stddev", 5.0))
        self._config = cfg

    def _on_start(self):
        rw = self._config.get("random_walk", {})
        if not rw.get("corners"):
            QMessageBox.warning(self, "缺少配置",
                "未设置矩形区域 (corners)。\n请先在 config.json 中设置或使用校准功能。")
            return

        cfg = self._config.copy()
        cfg["jitter_meters"] = self.jitter_spin.value()
        rw = cfg.setdefault("random_walk", {})
        rw["speed_ms"] = self.speed_spin.value()
        rw["duration_seconds"] = self.duration_spin.value()
        rw["direction_change_stddev"] = self.dir_spin.value()
        save_config(cfg)

        speed = self.speed_spin.value()
        run_config = {
            "mode": "walk",
            "config": cfg,
            "title": f"随机游走 — {speed:.1f} m/s ({speed * 3.6:.1f} km/h)",
            "duration": self.duration_spin.value(),
        }
        w = self.window()
        if hasattr(w, "start_run"):
            w.start_run(run_config)
