import math

import qasync

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QMessageBox, QGridLayout,
)
from PySide6.QtCore import Qt

from backend.config import load_config, save_config
from backend.localization import DeviceLocalizer
from ui.app_state import get_state

METERS_PER_DEG_LAT = 111320.0


class CalibratePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._localizer = None
        self._pos = {"lat": 0.0, "lng": 0.0}
        self._step_m = 20.0
        self._corner_order = [("nw", "西北"), ("ne", "东北"), ("se", "东南"), ("sw", "西南")]
        self._corner_idx = 0
        self._corners = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("校准矩形四角")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        # corner indicators
        self.corner_labels = {}
        corner_row = QHBoxLayout()
        for key, label in self._corner_order:
            lbl = QLabel(f"□ {label}")
            lbl.setStyleSheet("padding: 6px 12px; border: 1px solid gray; border-radius: 4px;")
            self.corner_labels[key] = lbl
            corner_row.addWidget(lbl)
        layout.addLayout(corner_row)

        # step size
        step_row = QHBoxLayout()
        step_row.addWidget(QLabel("步长:"))
        self.step_label = QLabel("20 m")
        self.step_label.setStyleSheet("font-weight: bold;")
        step_row.addWidget(self.step_label)
        self.step_plus_btn = QPushButton("+")
        self.step_plus_btn.clicked.connect(self._on_step_up)
        step_row.addWidget(self.step_plus_btn)
        self.step_minus_btn = QPushButton("-")
        self.step_minus_btn.clicked.connect(self._on_step_down)
        step_row.addWidget(self.step_minus_btn)
        step_row.addStretch()
        layout.addLayout(step_row)

        # position display
        self.pos_label = QLabel("位置: —")
        self.pos_label.setStyleSheet("font-size: 14px; font-family: monospace;")
        layout.addWidget(self.pos_label)

        # direction pad
        pad_group = QGroupBox("方向控制")
        pad = QGridLayout(pad_group)
        pad.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.w_btn = QPushButton("W ↑ 北")
        self.w_btn.setMinimumHeight(40)
        self.w_btn.pressed.connect(lambda: self._move("w"))
        pad.addWidget(self.w_btn, 0, 1)

        self.a_btn = QPushButton("A ← 西")
        self.a_btn.setMinimumHeight(40)
        self.a_btn.pressed.connect(lambda: self._move("a"))
        pad.addWidget(self.a_btn, 1, 0)

        self.s_btn = QPushButton("S ↓ 南")
        self.s_btn.setMinimumHeight(40)
        self.s_btn.pressed.connect(lambda: self._move("s"))
        pad.addWidget(self.s_btn, 1, 2)

        self.d_btn = QPushButton("D → 东")
        self.d_btn.setMinimumHeight(40)
        self.d_btn.pressed.connect(lambda: self._move("d"))
        pad.addWidget(self.d_btn, 2, 1)

        layout.addWidget(pad_group)

        # action buttons
        act_row = QHBoxLayout()
        self.confirm_btn = QPushButton("✓ 确认此角")
        self.confirm_btn.clicked.connect(self._on_confirm)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setStyleSheet("font-weight: bold;")
        act_row.addWidget(self.confirm_btn)

        self.start_btn = QPushButton("开始校准")
        self.start_btn.clicked.connect(self._on_start)
        act_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        act_row.addWidget(self.cancel_btn)

        self.back_btn = QPushButton("返回")
        act_row.addWidget(self.back_btn)

        act_row.addStretch()
        layout.addLayout(act_row)

        # confirmed corners display
        self.confirmed_label = QLabel("已确认: (无)")
        layout.addWidget(self.confirmed_label)

        layout.addStretch()

    # ---- public ----

    def refresh_config(self):
        self._corners = {}
        self._corner_idx = 0
        self._step_m = 20.0
        self.step_label.setText("20 m")
        self.pos_label.setText("位置: —")
        self._update_corner_styles()
        self._update_confirmed()

    # ---- private ----

    def _update_corner_styles(self):
        for key, lbl in self.corner_labels.items():
            parts = lbl.text().split()
            name = parts[-1] if parts else ""
            if key in self._corners:
                lbl.setText(f"☑ {name}")
                lbl.setStyleSheet("padding: 6px 12px; border: 1px solid green; border-radius: 4px; color: green;")
            elif self._corner_idx < len(self._corner_order) and self._corner_order[self._corner_idx][0] == key:
                lbl.setText(f"▶ {name}")
                lbl.setStyleSheet("padding: 6px 12px; border: 2px solid blue; border-radius: 4px; font-weight: bold;")
            else:
                lbl.setText(f"□ {name}")
                lbl.setStyleSheet("padding: 6px 12px; border: 1px solid gray; border-radius: 4px;")

    def _update_confirmed(self):
        parts = []
        for key, _label in self._corner_order:
            if key in self._corners:
                c = self._corners[key]
                parts.append(f"{key.upper()}: ({c['lat']:.8f}, {c['lng']:.8f})")
        self.confirmed_label.setText("已确认: " + (" | ".join(parts) if parts else "(无)"))

    def _update_pos_display(self):
        self.pos_label.setText(f"位置: ({self._pos['lat']:.8f}, {self._pos['lng']:.8f})  步长: {self._step_m:.0f}m")

    @qasync.asyncSlot()
    async def _on_start(self):
        state = get_state()
        if state.rsd is None:
            QMessageBox.warning(self, "未连接", "请先返回首页连接设备")
            return

        self.start_btn.setEnabled(False)
        try:
            self._localizer = DeviceLocalizer(state.rsd)
            await self._localizer.__aenter__()

            cfg = load_config()
            rw = cfg.get("random_walk", {})
            old = rw.get("corners")
            if old:
                self._corners = {k: dict(v) for k, v in old.items()}
            else:
                default = {"lat": 28.735, "lng": 115.825}
                self._corners = {key: dict(default) for key, _label in self._corner_order}

            self._corner_idx = 0
            await self._move_to_current_corner()
            self.confirm_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "启动失败", str(e))
            self.start_btn.setEnabled(True)

    async def _move_to_current_corner(self):
        if self._corner_idx >= len(self._corner_order):
            return
        key = self._corner_order[self._corner_idx][0]
        self._pos = dict(self._corners.get(key, {"lat": 0, "lng": 0}))
        self._update_pos_display()
        self._update_corner_styles()
        await self._send_position()

    async def _send_position(self):
        if self._localizer:
            await self._localizer.set(self._pos["lat"], self._pos["lng"])

    @qasync.asyncSlot()
    async def _move(self, direction):
        if self._localizer is None:
            return

        if direction == "w":
            self._pos["lat"] += self._step_m / METERS_PER_DEG_LAT
        elif direction == "s":
            self._pos["lat"] -= self._step_m / METERS_PER_DEG_LAT
        elif direction == "d":
            self._pos["lng"] += self._step_m / (METERS_PER_DEG_LAT * math.cos(math.radians(self._pos["lat"])))
        elif direction == "a":
            self._pos["lng"] -= self._step_m / (METERS_PER_DEG_LAT * math.cos(math.radians(self._pos["lat"])))

        self._update_pos_display()
        await self._send_position()

    def _on_step_up(self):
        self._step_m = min(self._step_m * 2, 100)
        self.step_label.setText(f"{self._step_m:.0f} m")
        self._update_pos_display()

    def _on_step_down(self):
        self._step_m = max(self._step_m / 2, 1)
        self.step_label.setText(f"{self._step_m:.0f} m")
        self._update_pos_display()

    @qasync.asyncSlot()
    async def _on_confirm(self):
        if self._corner_idx >= len(self._corner_order):
            return

        key = self._corner_order[self._corner_idx][0]
        self._corners[key] = {"lat": round(self._pos["lat"], 8), "lng": round(self._pos["lng"], 8)}
        self._update_confirmed()
        self._update_corner_styles()

        self._corner_idx += 1
        if self._corner_idx >= len(self._corner_order):
            await self._finish()
        else:
            await self._move_to_current_corner()

    async def _finish(self):
        cfg = load_config()
        rw = cfg.setdefault("random_walk", {})
        rw["corners"] = self._corners
        save_config(cfg)

        if self._localizer:
            await self._localizer.__aexit__(None, None, None)
            self._localizer = None

        self.confirm_btn.setEnabled(False)
        self.start_btn.setEnabled(True)

        parts = [f"{k.upper()}: ({v['lat']:.8f}, {v['lng']:.8f})" for k, v in self._corners.items()]
        QMessageBox.information(self, "校准完成",
            f"四角坐标已保存到 config.json:\n\n" + "\n".join(parts))

    @qasync.asyncSlot()
    async def _on_cancel(self):
        if self._localizer:
            await self._localizer.__aexit__(None, None, None)
            self._localizer = None
        self.confirm_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self._corner_idx = 0
        self._update_corner_styles()
