from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QFrame, QMessageBox,
    QComboBox, QCheckBox,
)
from PySide6.QtCore import Signal, Qt, QSize, QTimer
import qasync

from pymobiledevice3.tunneld.api import get_tunneld_devices
from pymobiledevice3.exceptions import TunneldConnectionError

from backend.device import connect_via_tunneld, format_device_info
from ui.app_state import get_state


DEVICE_ITEM_HEIGHT = 52


class HomePage(QWidget):
    device_connected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices = []
        self._rsd = None
        self._device_checkboxes = []
        self._init_ui()

    # ── UI Construction ──────────────────────────────────

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # ── Header ──
        layout.addLayout(self._make_header())

        # ── Status Dashboard ──
        layout.addLayout(self._make_status_dashboard())

        # ── Device Section (EXPANDING — visual center) ──
        layout.addLayout(self._make_device_header())

        self.device_frame = QFrame()
        self.device_frame.setObjectName("deviceListCard")
        df_layout = QVBoxLayout(self.device_frame)
        df_layout.setContentsMargins(4, 4, 4, 4)
        df_layout.setSpacing(0)

        self.device_list = QListWidget()
        self.device_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.device_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.device_list.setMinimumHeight(160)
        self.device_list.setSizePolicy(
            self.device_list.sizePolicy().horizontalPolicy(),
            self.device_list.sizePolicy().verticalPolicy().Expanding,
        )
        df_layout.addWidget(self.device_list)

        layout.addWidget(self.device_frame, 1)

        # ── Venue Section (Fixed) ──
        self._add_section_title(layout, "场地配置")
        layout.addWidget(self._make_venue_row())

        # ── Mode Toolbar (Fixed, compact) ──
        self._add_section_title(layout, "运行模式")
        layout.addLayout(self._make_mode_toolbar())

        self._refresh_config_list()
        QTimer.singleShot(100, self._auto_refresh)

    # ── Header ──────────────────────────────────────────

    def _make_header(self):
        row = QHBoxLayout()
        title = QLabel("GeoPilot")
        title.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #0F172A; background: transparent;"
        )
        row.addWidget(title)
        row.addStretch()

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("ghostBtn")
        self.settings_btn.setToolTip("设置")
        row.addWidget(self.settings_btn)

        self.log_btn = QPushButton("ⓘ")
        self.log_btn.setObjectName("ghostBtn")
        self.log_btn.setToolTip("日志")
        row.addWidget(self.log_btn)

        return row

    # ── Status Dashboard ────────────────────────────────

    def _make_status_dashboard(self):
        row = QHBoxLayout()
        row.setSpacing(12)

        # Tunneld card
        self.tunneld_card = QFrame()
        self.tunneld_card.setObjectName("statusCard")
        tc = QVBoxLayout(self.tunneld_card)
        tc.setSpacing(4)
        tc.setContentsMargins(16, 14, 16, 14)

        self.tunneld_dot = QLabel("●")
        self.tunneld_dot.setObjectName("statusDot")
        self.tunneld_dot.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
        tc.addWidget(self.tunneld_dot)

        tl = QLabel("Tunneld")
        tl.setObjectName("statusText")
        tc.addWidget(tl)

        self.tunneld_value = QLabel("检测中...")
        self.tunneld_value.setObjectName("statusText")
        self.tunneld_value.setStyleSheet("font-size: 12px; color: #94A3B8;")
        tc.addWidget(self.tunneld_value)

        row.addWidget(self.tunneld_card, 1)

        # Device card — stats, not names
        self.device_card = QFrame()
        self.device_card.setObjectName("statusCard")
        dc = QVBoxLayout(self.device_card)
        dc.setSpacing(4)
        dc.setContentsMargins(16, 14, 16, 14)

        self.device_dot = QLabel("○")
        self.device_dot.setObjectName("statusDot")
        self.device_dot.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
        dc.addWidget(self.device_dot)

        self.device_title = QLabel("Devices")
        self.device_title.setObjectName("statusText")
        dc.addWidget(self.device_title)

        self.device_found = QLabel("0 Found")
        self.device_found.setObjectName("statusText")
        self.device_found.setStyleSheet("font-size: 12px; color: #94A3B8;")
        dc.addWidget(self.device_found)

        self.device_selected = QLabel("0 Selected")
        self.device_selected.setObjectName("statusText")
        self.device_selected.setStyleSheet("font-size: 12px; color: #94A3B8;")
        dc.addWidget(self.device_selected)

        row.addWidget(self.device_card, 1)

        # Venue card
        self.venue_card = QFrame()
        self.venue_card.setObjectName("statusCard")
        vc = QVBoxLayout(self.venue_card)
        vc.setSpacing(4)
        vc.setContentsMargins(16, 14, 16, 14)

        self.venue_dot = QLabel("—")
        self.venue_dot.setObjectName("statusDot")
        self.venue_dot.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
        vc.addWidget(self.venue_dot)

        vl = QLabel("Venue")
        vl.setObjectName("statusText")
        vc.addWidget(vl)

        self.venue_value = QLabel("未选择")
        self.venue_value.setObjectName("statusText")
        self.venue_value.setStyleSheet("font-size: 12px; color: #94A3B8;")
        vc.addWidget(self.venue_value)

        row.addWidget(self.venue_card, 1)

        return row

    # ── Device Section ──────────────────────────────────

    def _make_device_header(self):
        row = QHBoxLayout()
        row.setSpacing(8)

        title = QLabel("设备管理")
        title.setObjectName("sectionTitle")
        row.addWidget(title)

        self.device_count_label = QLabel("")
        self.device_count_label.setObjectName("captionLabel")
        row.addWidget(self.device_count_label)

        self.select_all_cb = QCheckBox("全选")
        self.select_all_cb.setEnabled(False)
        self.select_all_cb.toggled.connect(self._on_select_all)
        row.addWidget(self.select_all_cb)

        row.addStretch()

        self.refresh_btn = QPushButton("刷新设备")
        self.refresh_btn.clicked.connect(self._on_refresh)
        row.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("连接选中")
        self.connect_btn.setObjectName("primaryBtn")
        self.connect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self._on_connect)
        row.addWidget(self.connect_btn)

        self.start_tunneld_btn = QPushButton("启动 tunneld")
        self.start_tunneld_btn.clicked.connect(self._on_start_tunneld)
        row.addWidget(self.start_tunneld_btn)

        return row

    def _build_device_item_widget(self, info: dict):
        """Create a rich device list item widget with checkbox."""
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        row = QHBoxLayout(w)
        row.setContentsMargins(10, 6, 10, 6)
        row.setSpacing(10)

        cb = QCheckBox()
        cb.setChecked(True)
        cb.toggled.connect(self._on_device_checked)
        row.addWidget(cb)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        name = QLabel(info["model_name"])
        name.setObjectName("deviceName")
        text_col.addWidget(name)

        sub = QLabel(f"iOS {info['os_version']}  ·  {info['name']}")
        sub.setObjectName("deviceSub")
        text_col.addWidget(sub)

        row.addLayout(text_col, 1)
        return w, cb

    # ── Venue Section ───────────────────────────────────

    def _make_venue_row(self):
        card = QFrame()
        card.setObjectName("contentCard")
        card.setFixedHeight(52)
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 0, 14, 0)
        row.setSpacing(10)

        row.addWidget(QLabel("当前场地:"))

        self.config_combo = QComboBox()
        self.config_combo.setMinimumWidth(200)
        self.config_combo.currentTextChanged.connect(self._on_config_selected)
        row.addWidget(self.config_combo, 1)

        self.cfg_refresh_btn = QPushButton("刷新")
        self.cfg_refresh_btn.clicked.connect(self._refresh_config_list)
        row.addWidget(self.cfg_refresh_btn)

        return card

    # ── Mode Toolbar ────────────────────────────────────

    def _make_mode_toolbar(self):
        row = QHBoxLayout()
        row.setSpacing(10)

        self.pace_btn = QPushButton("🏃  配速跑")
        self.pace_btn.setObjectName("modeBtn")
        self.pace_btn.setEnabled(False)
        row.addWidget(self.pace_btn)

        self.walk_btn = QPushButton("🚶  随机游走")
        self.walk_btn.setObjectName("modeBtn")
        self.walk_btn.setEnabled(False)
        row.addWidget(self.walk_btn)

        self.route_btn = QPushButton("🗺  路线播放")
        self.route_btn.setObjectName("modeBtn")
        self.route_btn.setEnabled(False)
        row.addWidget(self.route_btn)

        self.calibrate_btn = QPushButton("📐  矩形校准")
        self.calibrate_btn.setObjectName("modeBtn")
        self.calibrate_btn.setEnabled(False)
        row.addWidget(self.calibrate_btn)

        return row

    # ── Helpers ─────────────────────────────────────────

    def _add_section_title(self, layout, text):
        lbl = QLabel(text)
        lbl.setObjectName("sectionTitle")
        layout.addWidget(lbl)

    # ── Public API ───────────────────────────────────────

    def set_mode_buttons_enabled(self, enabled: bool):
        for btn in [self.pace_btn, self.walk_btn, self.route_btn, self.calibrate_btn]:
            btn.setEnabled(enabled)

    def update_tunneld_status(self, running: bool):
        if running:
            self.tunneld_dot.setStyleSheet("color: #22C55E; font-size: 13px; font-weight: 600;")
            self.tunneld_value.setText("运行中")
            self.tunneld_value.setStyleSheet("font-size: 12px; color: #22C55E; font-weight: 600;")
        else:
            self.tunneld_dot.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
            self.tunneld_value.setText("未运行")
            self.tunneld_value.setStyleSheet("font-size: 12px; color: #94A3B8;")

    def _update_device_counts(self):
        """Recalculate and refresh found / selected counts on the status card."""
        found = len(self._devices)
        selected = sum(1 for _, cb in self._device_checkboxes if cb.isChecked())
        connected = len(get_state().rsd_list)

        if connected:
            self.device_dot.setStyleSheet("color: #22C55E; font-size: 13px; font-weight: 600;")
        elif found:
            self.device_dot.setStyleSheet("color: #F59E0B; font-size: 13px; font-weight: 600;")
        else:
            self.device_dot.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")

        self.device_found.setText(f"{found} Found")
        self.device_found.setStyleSheet(
            f"font-size: 12px; color: {'#0F172A' if found else '#94A3B8'};"
        )
        self.device_selected.setText(f"{selected} Selected")
        self.device_selected.setStyleSheet(
            f"font-size: 12px; color: {'#2563EB' if selected else '#94A3B8'}; font-weight: {'600' if selected else '400'};"
        )

    def _on_device_checked(self):
        self._update_device_counts()

    def update_venue_status(self, venue_name: str):
        if venue_name:
            self.venue_dot.setStyleSheet("color: #2563EB; font-size: 13px; font-weight: 600;")
            self.venue_value.setText(venue_name)
            self.venue_value.setStyleSheet("font-size: 12px; color: #2563EB; font-weight: 600;")
        else:
            self.venue_dot.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: 600;")
            self.venue_value.setText("未选择")
            self.venue_value.setStyleSheet("font-size: 12px; color: #94A3B8;")

    # ── Select All ──────────────────────────────────────

    def _on_select_all(self, checked: bool):
        for _, cb in self._device_checkboxes:
            cb.blockSignals(True)
            cb.setChecked(checked)
            cb.blockSignals(False)
        self._update_device_counts()

    # ── Config Preset ───────────────────────────────────

    def _refresh_config_list(self):
        from backend.config import list_config_presets

        self.config_combo.blockSignals(True)
        self.config_combo.clear()
        presets = list_config_presets()
        self.config_combo.addItem("config.json (默认)")
        for name in presets:
            self.config_combo.addItem(name)

        state = get_state()
        if state.active_config_preset and state.active_config_preset in presets:
            idx = presets.index(state.active_config_preset) + 1
            self.config_combo.setCurrentIndex(idx)
        else:
            self.config_combo.setCurrentIndex(0)

        current = self.config_combo.currentText()
        self.update_venue_status(
            current.replace("config.json (默认)", "默认配置") if current else ""
        )
        self.config_combo.blockSignals(False)

    def _on_config_selected(self, text):
        if text == "config.json (默认)":
            get_state().active_config_preset = None
            self.update_venue_status("默认配置")
        else:
            get_state().active_config_preset = text
            self.update_venue_status(text)

    def _auto_refresh(self):
        """启动时自动检测并尝试启动 tunneld，然后刷新设备列表。"""
        from ui.tunneld_manager import TunneldManager
        if TunneldManager.is_running():
            self._on_refresh()
            return

        self.update_tunneld_status(False)

        reply = QMessageBox.information(
            self, "启动 tunneld 服务",
            "GeoPilot 需要通过 tunneld 服务与 iOS 设备通信。\n\n"
            "该服务需要管理员权限才能运行。\n"
            "点击「确定」后系统将弹出 UAC 窗口，请点击「是」允许提权。",
            QMessageBox.Ok | QMessageBox.Cancel,
        )
        if reply != QMessageBox.Ok:
            return

        TunneldManager.launch()
        self._poll_tunneld_ready(TunneldManager.POLL_RETRIES, self._on_refresh)

    def _poll_tunneld_ready(self, retries: int, on_ready=None):
        """使用 QTimer 轮询 tunneld 是否已就绪，不阻塞 UI。"""
        from ui.tunneld_manager import TunneldManager
        if TunneldManager.is_running():
            self.update_tunneld_status(True)
            if on_ready:
                on_ready()
            return
        if retries > 0:
            QTimer.singleShot(
                TunneldManager.POLL_INTERVAL_MS,
                lambda: self._poll_tunneld_ready(retries - 1, on_ready),
            )
        else:
            self.start_tunneld_btn.setEnabled(True)
            self.start_tunneld_btn.setText("启动 tunneld")
            QMessageBox.warning(self, "启动失败",
                "tunneld 启动超时。\n请手动运行: python main.py --tunneld")

    # ── Async Slots ─────────────────────────────────────

    @qasync.asyncSlot()
    async def _on_refresh(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("刷新中...")
        try:
            devices = await get_tunneld_devices()
            self._devices = devices

            # Rebuild device list with custom item widgets
            self.device_list.clear()
            self._device_checkboxes.clear()

            for d in devices:
                info = format_device_info(d)
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, DEVICE_ITEM_HEIGHT))
                item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self.device_list.addItem(item)

                widget, cb = self._build_device_item_widget(info)
                self.device_list.setItemWidget(item, widget)
                self._device_checkboxes.append((item, cb))

            count = len(devices)
            self.device_count_label.setText(f"({count})" if count else "")
            self.select_all_cb.setEnabled(count > 0)
            if count > 0:
                self.select_all_cb.setChecked(True)
            self.connect_btn.setEnabled(count > 0)
            self._update_device_counts()
        except TunneldConnectionError:
            QMessageBox.warning(
                self, "tunneld 未运行",
                "无法连接到 tunneld (127.0.0.1:49151)\n\n"
                "请点击「启动 tunneld」按钮或手动运行:\n"
                "python main.py --tunneld"
            )
        finally:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("刷新设备")

    @qasync.asyncSlot()
    async def _on_connect(self):
        checked_indices = [
            i for i, (_, cb) in enumerate(self._device_checkboxes) if cb.isChecked()
        ]
        if not checked_indices:
            QMessageBox.information(self, "提示", "请先勾选至少一台设备")
            return

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText(f"连接中 (0/{len(checked_indices)})...")

        state = get_state()
        rsd_list = []
        infos = []
        errors = []

        for idx in checked_indices:
            if idx >= len(self._devices):
                continue
            try:
                udid = self._devices[idx].peer_info["Properties"]["UniqueDeviceID"]
                rsd = await connect_via_tunneld(udid=udid, save_choice=(idx == checked_indices[0]))
                rsd_list.append(rsd)
                infos.append(format_device_info(rsd))
                self.connect_btn.setText(f"连接中 ({len(rsd_list)}/{len(checked_indices)})...")
            except Exception as e:
                info = format_device_info(self._devices[idx])
                errors.append(f"{info['model_name']}: {e}")

        if not rsd_list:
            QMessageBox.warning(self, "连接失败", "所有设备连接失败:\n" + "\n".join(errors))
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("连接选中")
            return

        state.rsd_list = rsd_list
        state.connected_device_infos = infos

        self._update_device_counts()
        self.set_mode_buttons_enabled(True)
        self.device_connected.emit(rsd_list[0])
        self.update_tunneld_status(True)

        if errors:
            QMessageBox.warning(self, "部分失败", f"{count} 台连接成功\n" + "\n".join(errors))

        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("连接选中")

    def _on_start_tunneld(self):
        from ui.tunneld_manager import TunneldManager

        if TunneldManager.is_running():
            QMessageBox.information(self, "提示", "tunneld 已在运行中")
            return

        reply = QMessageBox.question(
            self, "启动 tunneld",
            "需要以管理员权限启动 tunneld 服务。\n"
            "系统将弹出 UAC 确认窗口，请点击「是」。\n\n"
            "继续？",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        TunneldManager.launch()
        self.start_tunneld_btn.setEnabled(False)
        self.start_tunneld_btn.setText("等待 tunneld...")
        self._poll_tunneld_ready(
            TunneldManager.POLL_RETRIES,
            on_ready=self._on_tunneld_ready,
        )

    def _on_tunneld_ready(self):
        QMessageBox.information(self, "成功", "tunneld 已启动")
        self.start_tunneld_btn.setEnabled(True)
        self.start_tunneld_btn.setText("启动 tunneld")
        self._on_refresh()
