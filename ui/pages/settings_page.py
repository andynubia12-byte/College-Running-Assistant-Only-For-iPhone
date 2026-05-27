import json

import qasync

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QDoubleSpinBox, QSpinBox, QGroupBox, QScrollArea,
    QMessageBox, QFileDialog,
)

from backend.config import load_config, save_config, CONFIG_FILE, DEFAULT_CONFIG
from backend.device import check_developer_mode, reveal_developer_mode_option, enable_developer_mode
from ui.app_state import get_state


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self._load()

    def _init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        top = QHBoxLayout()
        self.back_btn = QPushButton("← 返回")
        top.addWidget(self.back_btn)
        top.addStretch()
        outer.addLayout(top)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(12)

        # ---- general ----
        gen_group = QGroupBox("通用设置")
        gen_form = QFormLayout(gen_group)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.01, 1.0)
        self.interval_spin.setDecimals(3)
        self.interval_spin.setSuffix(" 秒")
        gen_form.addRow("定位间隔:", self.interval_spin)

        self.jitter_spin = QDoubleSpinBox()
        self.jitter_spin.setRange(0.0, 20.0)
        self.jitter_spin.setDecimals(1)
        self.jitter_spin.setSuffix(" 米")
        gen_form.addRow("抖动范围:", self.jitter_spin)

        self.midpoint_spin = QDoubleSpinBox()
        self.midpoint_spin.setRange(0.0, 1.0)
        self.midpoint_spin.setDecimals(2)
        gen_form.addRow("中点概率:", self.midpoint_spin)

        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(1, 9999)
        gen_form.addRow("默认圈数:", self.loop_spin)

        layout.addWidget(gen_group)

        # ---- random_walk ----
        rw_group = QGroupBox("随机游走 / 配速跑道")
        rw_form = QFormLayout(rw_group)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.5, 20.0)
        self.speed_spin.setDecimals(1)
        self.speed_spin.setSuffix(" m/s")
        rw_form.addRow("默认速度:", self.speed_spin)

        self.pace_spin = QDoubleSpinBox()
        self.pace_spin.setRange(2.0, 15.0)
        self.pace_spin.setDecimals(1)
        self.pace_spin.setSuffix(" min/km")
        rw_form.addRow("默认配速:", self.pace_spin)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(60, 36000)
        self.duration_spin.setSuffix(" 秒")
        rw_form.addRow("默认时长:", self.duration_spin)

        self.dir_spin = QDoubleSpinBox()
        self.dir_spin.setRange(0.5, 45.0)
        self.dir_spin.setDecimals(1)
        self.dir_spin.setSuffix(" deg")
        rw_form.addRow("方向变化:", self.dir_spin)

        self.margin_spin = QDoubleSpinBox()
        self.margin_spin.setRange(0.0, 50.0)
        self.margin_spin.setDecimals(0)
        self.margin_spin.setSuffix(" 米")
        rw_form.addRow("跑道边距:", self.margin_spin)

        self.epoints_spin = QSpinBox()
        self.epoints_spin.setRange(50, 1000)
        rw_form.addRow("跑道点数:", self.epoints_spin)

        layout.addWidget(rw_group)

        # ---- corners ----
        cr_group = QGroupBox("矩形四角")
        cr_layout = QVBoxLayout(cr_group)
        self.corners_label = QLabel("未设置")
        cr_layout.addWidget(self.corners_label)
        layout.addWidget(cr_group)

        # ---- developer mode ----
        dev_group = QGroupBox("开发者模式")
        dev_layout = QVBoxLayout(dev_group)

        self.dev_status_label = QLabel("状态: 未知")
        dev_layout.addWidget(self.dev_status_label)

        dev_btn_row = QHBoxLayout()
        self.check_dev_btn = QPushButton("检查状态")
        self.check_dev_btn.clicked.connect(self._check_dev_mode)
        dev_btn_row.addWidget(self.check_dev_btn)

        self.reveal_dev_btn = QPushButton("显示开发者选项")
        self.reveal_dev_btn.clicked.connect(self._reveal_dev_ui)
        dev_btn_row.addWidget(self.reveal_dev_btn)

        self.enable_dev_btn = QPushButton("完全激活")
        self.enable_dev_btn.clicked.connect(self._enable_dev_mode)
        dev_btn_row.addWidget(self.enable_dev_btn)

        dev_btn_row.addStretch()
        dev_layout.addLayout(dev_btn_row)
        layout.addWidget(dev_group)

        # ---- actions ----
        btn_row = QHBoxLayout()
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        export_btn = QPushButton("导出 JSON")
        export_btn.clicked.connect(self._export)
        btn_row.addWidget(export_btn)

        import_btn = QPushButton("导入 JSON")
        import_btn.clicked.connect(self._import)
        btn_row.addWidget(import_btn)

        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(reset_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        scroll.setWidget(w)

    # ---- load / save ----

    def _load(self):
        cfg = load_config()
        rw = cfg.get("random_walk", {})
        cr = rw.get("corners", {})

        self.interval_spin.setValue(cfg.get("point_interval", 0.1))
        self.jitter_spin.setValue(cfg.get("jitter_meters", 1.0))
        self.midpoint_spin.setValue(cfg.get("midpoint_probability", 0.0))
        self.loop_spin.setValue(cfg.get("loop_count", 10))

        self.speed_spin.setValue(rw.get("speed_ms", 3.0))
        self.pace_spin.setValue(rw.get("pace_min_per_km", 5.0))
        self.duration_spin.setValue(rw.get("duration_seconds", 1800))
        self.dir_spin.setValue(rw.get("direction_change_stddev", 5.0))
        self.margin_spin.setValue(rw.get("ellipse_margin_meters", 2))
        self.epoints_spin.setValue(rw.get("ellipse_points", 200))

        if cr:
            nw = cr.get("nw", {})
            se = cr.get("se", {})
            self.corners_label.setText(
                f"NW: ({nw.get('lat', '?')}, {nw.get('lng', '?')})  "
                f"SE: ({se.get('lat', '?')}, {se.get('lng', '?')})"
            )
        else:
            self.corners_label.setText("未设置")

    def _save(self):
        cfg = {
            "point_interval": self.interval_spin.value(),
            "jitter_meters": self.jitter_spin.value(),
            "midpoint_probability": self.midpoint_spin.value(),
            "loop_count": self.loop_spin.value(),
            "mode": "pace",
            "random_walk": {
                "speed_ms": self.speed_spin.value(),
                "pace_min_per_km": self.pace_spin.value(),
                "duration_seconds": self.duration_spin.value(),
                "direction_change_stddev": self.dir_spin.value(),
                "ellipse_margin_meters": self.margin_spin.value(),
                "ellipse_points": self.epoints_spin.value(),
            },
        }

        # preserve existing corners and last_udid
        old = load_config()
        rw_old = old.get("random_walk", {})
        if rw_old.get("corners"):
            cfg["random_walk"]["corners"] = rw_old["corners"]
        if old.get("last_udid"):
            cfg["last_udid"] = old["last_udid"]

        save_config(cfg)
        QMessageBox.information(self, "已保存", f"配置已保存到 {CONFIG_FILE}")

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出配置", "config_export.json", "JSON (*.json)")
        if not path:
            return
        self._save()
        import shutil
        shutil.copy(CONFIG_FILE, path)
        QMessageBox.information(self, "已导出", f"配置已导出到 {path}")

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "JSON (*.json)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                json.load(f)
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"无效的 JSON 文件: {e}")
            return
        import shutil
        shutil.copy(path, CONFIG_FILE)
        self._load()
        QMessageBox.information(self, "已导入", f"配置已从 {path} 导入")

    def _reset(self):
        reply = QMessageBox.question(self, "确认", "恢复为默认配置？当前设置将丢失。")
        if reply != QMessageBox.Yes:
            return
        save_config(DEFAULT_CONFIG.copy())
        self._load()
        QMessageBox.information(self, "已重置", "配置已恢复默认")

    # ---- developer mode ----

    @qasync.asyncSlot()
    async def _check_dev_mode(self):
        state = get_state()
        if state.rsd is None:
            QMessageBox.warning(self, "未连接", "请先连接设备")
            return
        try:
            ok = await check_developer_mode(state.rsd)
            if ok is None:
                self.dev_status_label.setText("状态: 不支持 (iOS 15-)")
            elif ok:
                self.dev_status_label.setText("状态: 已开启")
            else:
                self.dev_status_label.setText("状态: 未开启")
        except Exception as e:
            self.dev_status_label.setText(f"检查失败: {e}")

    @qasync.asyncSlot()
    async def _reveal_dev_ui(self):
        state = get_state()
        if state.rsd is None:
            QMessageBox.warning(self, "未连接", "请先连接设备")
            return
        try:
            await reveal_developer_mode_option(state.rsd)
            QMessageBox.information(self, "成功",
                "已在设备上显示开发者模式选项。\n"
                "请前往: 设置 → 隐私与安全性 → 开发者模式 → 开启")
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    @qasync.asyncSlot()
    async def _enable_dev_mode(self):
        state = get_state()
        if state.rsd is None:
            QMessageBox.warning(self, "未连接", "请先连接设备")
            return
        reply = QMessageBox.warning(self, "确认",
            "完全激活开发者模式会导致设备重启。\n"
            "请确保设备没有设置锁屏密码。\n\n继续？",
            QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        try:
            await enable_developer_mode(state.rsd)
            QMessageBox.information(self, "成功", "开发者模式已激活！设备将重启。")
        except RuntimeError as e:
            QMessageBox.warning(self, "失败", str(e))
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))
