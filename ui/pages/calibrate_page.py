import math

import qasync

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGroupBox, QMessageBox, QGridLayout,
)
from PySide6.QtCore import Qt

from backend.config import (
    load_config, save_config,
    load_config_preset, save_config_preset,
)
from backend.localization import DeviceLocalizer
from ui.app_state import get_state

METERS_PER_DEG_LAT = 111320.0


class CalibratePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._localizer = None
        self._active = False
        self._pos = {"lat": 0.0, "lng": 0.0}
        self._step_m = 20.0
        self._corner_order = [("nw", "西北"), ("ne", "东北"), ("se", "东南"), ("sw", "西南")]
        self._corner_idx = 0
        self._corners = {}
        self._init_ui()

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

        title = QLabel("矩形校准")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        # corner indicators — 2×2 grid matching spatial layout
        corner_grid = QGridLayout()
        corner_grid.setSpacing(10)
        corner_grid.setAlignment(Qt.AlignmentFlag.AlignCenter)

        placements = {"nw": (0, 0), "ne": (0, 1), "sw": (1, 0), "se": (1, 1)}
        self.corner_labels = {}
        for key, label_text in self._corner_order:
            lbl = QLabel(f"□ {label_text}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setMinimumWidth(72)
            lbl.setStyleSheet(
                "padding: 8px 14px; border: 2px solid #E2E8F0; border-radius: 8px; color: #94A3B8; font-size: 12px; font-weight: 500;"
            )
            self.corner_labels[key] = lbl
            r, c = placements[key]
            corner_grid.addWidget(lbl, r, c)
        layout.addLayout(corner_grid)

        # step size
        step_row = QHBoxLayout()
        step_row.addWidget(QLabel("步长:"))
        self.step_label = QLabel("20 m")
        self.step_label.setStyleSheet("font-weight: 600; color: #0F172A;")
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
        self.pos_label.setStyleSheet(
            "font-size: 13px; font-family: 'Cascadia Code', 'Consolas', monospace; color: #0F172A;"
        )
        layout.addWidget(self.pos_label)

        # direction pad
        pad_group = QGroupBox("方向控制")
        pad = QGridLayout(pad_group)
        pad.setAlignment(Qt.AlignmentFlag.AlignCenter)

        pad_btn_style = "min-height: 42px; max-height: 42px;"

        self.w_btn = QPushButton("W ↑ 北")
        self.w_btn.setStyleSheet(pad_btn_style)
        self.w_btn.pressed.connect(lambda: self._move("w"))
        pad.addWidget(self.w_btn, 0, 1)

        self.a_btn = QPushButton("A ← 西")
        self.a_btn.setStyleSheet(pad_btn_style)
        self.a_btn.pressed.connect(lambda: self._move("a"))
        pad.addWidget(self.a_btn, 1, 0)

        self.d_btn = QPushButton("D → 东")
        self.d_btn.setStyleSheet(pad_btn_style)
        self.d_btn.pressed.connect(lambda: self._move("d"))
        pad.addWidget(self.d_btn, 1, 2)

        self.s_btn = QPushButton("S ↓ 南")
        self.s_btn.setStyleSheet(pad_btn_style)
        self.s_btn.pressed.connect(lambda: self._move("s"))
        pad.addWidget(self.s_btn, 2, 1)

        layout.addWidget(pad_group)

        # action buttons
        act_row = QHBoxLayout()
        act_row.setSpacing(8)
        self.confirm_btn = QPushButton("✓ 确认此角")
        self.confirm_btn.setObjectName("primaryBtn")
        self.confirm_btn.clicked.connect(self._on_confirm)
        self.confirm_btn.setEnabled(False)
        act_row.addWidget(self.confirm_btn)

        self.start_btn = QPushButton("开始校准")
        self.start_btn.clicked.connect(self._on_start)
        act_row.addWidget(self.start_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._on_cancel)
        act_row.addWidget(self.cancel_btn)

        act_row.addStretch()
        layout.addLayout(act_row)

        # confirmed corners display
        self.confirmed_label = QLabel("已确认: (无)")
        self.confirmed_label.setObjectName("bodyLabel")
        layout.addWidget(self.confirmed_label)

        # help text
        help_text = (
            "操作说明：\n"
            "1. 点击「开始校准」，设备定位将跳转到第一个角（西北角）\n"
            "2. 用 WASD 方向键将设备走到正确的西北角位置，点击「确认此角」\n"
            "3. 系统自动将下一个角的起点设为上一个角的确认位置，无需重新走\n"
            "4. 依次确认东北、东南、西南三个角\n"
            "5. 全部确认后选择保存方式\n"
            "提示：可用 +/- 调整步长；已确认的角标记为绿色 ☑。"
        )
        help_label = QLabel(help_text)
        help_label.setObjectName("captionLabel")
        help_label.setWordWrap(True)
        help_label.setStyleSheet(
            "padding: 10px 12px; border: 1px solid #E2E8F0; border-radius: 8px;"
            "color: #94A3B8; font-size: 11px; line-height: 1.5;"
        )
        layout.addWidget(help_label)

        layout.addStretch()

    # ---- public ----

    def refresh_config(self):
        self._corners = {}
        self._active = False
        self._corner_idx = 0
        self._step_m = 20.0
        self.step_label.setText("20 m")
        self.pos_label.setText("位置: —")
        self._update_corner_styles()
        self._update_confirmed()

    # ---- private ----

    def _update_corner_styles(self):
        base = "padding: 8px 14px; border-radius: 8px; font-size: 12px;"
        for key, lbl in self.corner_labels.items():
            parts = lbl.text().split()
            name_text = parts[-1] if parts else ""
            if key in self._corners:
                lbl.setText(f"☑ {name_text}")
                lbl.setStyleSheet(
                    base + "border: 2px solid #22C55E; color: #22C55E; font-weight: 600;"
                )
            elif self._active and self._corner_idx < len(self._corner_order) and self._corner_order[self._corner_idx][0] == key:
                lbl.setText(f"▶ {name_text}")
                lbl.setStyleSheet(
                    base + "border: 2px solid #22C55E; color: #22C55E; font-weight: 600;"
                )
            else:
                lbl.setText(f"□ {name_text}")
                lbl.setStyleSheet(
                    base + "border: 2px solid #E2E8F0; color: #94A3B8; font-weight: 500;"
                )

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

            if state.active_config_preset:
                cfg = load_config_preset(state.active_config_preset)
            else:
                cfg = load_config()
            rw = cfg.get("random_walk", {})
            old = rw.get("corners")
            if old:
                first_pos = dict(old.get("nw", {"lat": 28.735, "lng": 115.825}))
            else:
                first_pos = {"lat": 28.735, "lng": 115.825}

            self._corners = {}
            self._active = True
            self._corner_idx = 0
            self._pos = first_pos
            await self._move_to_current_corner()
            self.confirm_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.warning(self, "启动失败", str(e))
            self.start_btn.setEnabled(True)

    async def _move_to_current_corner(self):
        if self._corner_idx >= len(self._corner_order):
            return
        key = self._corner_order[self._corner_idx][0]
        if key in self._corners:
            self._pos = dict(self._corners[key])
        # 如果不在 _corners 里（新校准或上一个角确认后链接过来的），
        # 保持 self._pos 不变——它就是上一个角确认的位置。
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
            await self._show_save_dialog()
        else:
            # self._pos 保持在刚确认的位置，下一个角自然从这里开始
            await self._move_to_current_corner()

    async def _show_save_dialog(self):
        """校准完成后的保存对话框：保存到当前配置 / 另存为新预设 / 放弃"""
        parts = [f"{k.upper()}: ({v['lat']:.8f}, {v['lng']:.8f})" for k, v in self._corners.items()]
        detail = "\n".join(parts)

        box = QMessageBox(self)
        box.setWindowTitle("校准完成")
        box.setText("四角坐标已确认，如何保存？")
        box.setInformativeText(detail)
        box.setIcon(QMessageBox.Icon.Question)

        save_current_btn = box.addButton("保存到当前配置", QMessageBox.ButtonRole.AcceptRole)
        save_as_btn = box.addButton("另存为新预设", QMessageBox.ButtonRole.ActionRole)
        discard_btn = box.addButton("放弃", QMessageBox.ButtonRole.RejectRole)
        box.setDefaultButton(save_current_btn)

        box.exec()
        clicked = box.clickedButton()

        if clicked == save_current_btn:
            state = get_state()
            if state.active_config_preset:
                cfg = load_config_preset(state.active_config_preset)
            else:
                cfg = load_config()
            cfg.setdefault("random_walk", {})["corners"] = self._corners
            if state.active_config_preset:
                save_config_preset(state.active_config_preset, cfg)
            else:
                save_config(cfg)
        elif clicked == save_as_btn:
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "另存为预设", "输入预设名称:")
            if ok and name.strip():
                name = name.strip()
                state = get_state()
                if state.active_config_preset:
                    base = load_config_preset(state.active_config_preset)
                else:
                    base = load_config()
                base.setdefault("random_walk", {})["corners"] = self._corners
                try:
                    save_config_preset(name, base)
                    state.active_config_preset = name
                    QMessageBox.information(self, "已保存",
                        f"新预设已保存到 configs/{name}.json\n已自动切换为当前预设。")
                except Exception as e:
                    QMessageBox.warning(self, "保存失败", str(e))
            else:
                # 取消命名 → 回退到保存到当前配置
                state = get_state()
                if state.active_config_preset:
                    cfg = load_config_preset(state.active_config_preset)
                else:
                    cfg = load_config()
                cfg.setdefault("random_walk", {})["corners"] = self._corners
                if state.active_config_preset:
                    save_config_preset(state.active_config_preset, cfg)
                else:
                    save_config(cfg)

        if self._localizer:
            await self._localizer.__aexit__(None, None, None)
            self._localizer = None

        self._active = False
        self.confirm_btn.setEnabled(False)
        self.start_btn.setEnabled(True)

    @qasync.asyncSlot()
    async def _on_cancel(self):
        if self._localizer:
            await self._localizer.__aexit__(None, None, None)
            self._localizer = None
        self.confirm_btn.setEnabled(False)
        self.start_btn.setEnabled(True)
        self._active = False
        self._corner_idx = 0
        self._update_corner_styles()
