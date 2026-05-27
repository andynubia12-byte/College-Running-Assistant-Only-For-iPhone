from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QListWidget, QLabel, QGroupBox, QMessageBox,
)
from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
import qasync

from pymobiledevice3.tunneld.api import get_tunneld_devices
from pymobiledevice3.exceptions import TunneldConnectionError

from backend.device import connect_via_tunneld, format_device_info
from ui.app_state import get_state


class HomePage(QWidget):
    device_connected = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._devices = []
        self._rsd = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        # ---- device section ----
        device_group = QGroupBox("设备连接")
        device_layout = QVBoxLayout(device_group)

        self.device_list = QListWidget()
        self.device_list.setMinimumHeight(80)
        device_layout.addWidget(self.device_list)

        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新设备")
        self.refresh_btn.clicked.connect(self._on_refresh)
        btn_row.addWidget(self.refresh_btn)

        self.connect_btn = QPushButton("连接选中设备")
        self.connect_btn.setEnabled(False)
        self.connect_btn.clicked.connect(self._on_connect)
        btn_row.addWidget(self.connect_btn)

        self.start_tunneld_btn = QPushButton("启动 tunneld")
        self.start_tunneld_btn.clicked.connect(self._on_start_tunneld)
        btn_row.addWidget(self.start_tunneld_btn)

        btn_row.addStretch()
        device_layout.addLayout(btn_row)

        self.device_info_label = QLabel("未连接设备")
        font = QFont()
        font.setBold(True)
        self.device_info_label.setFont(font)
        device_layout.addWidget(self.device_info_label)

        layout.addWidget(device_group)

        # ---- mode section ----
        mode_group = QGroupBox("运行模式（连接设备后可用）")
        mode_layout = QVBoxLayout(mode_group)

        card_row = QHBoxLayout()
        self.pace_btn = QPushButton("配速\n跑道")
        self.pace_btn.setMinimumHeight(60)
        self.pace_btn.setEnabled(False)
        card_row.addWidget(self.pace_btn)

        self.walk_btn = QPushButton("随机\n游走")
        self.walk_btn.setMinimumHeight(60)
        self.walk_btn.setEnabled(False)
        card_row.addWidget(self.walk_btn)

        self.route_btn = QPushButton("路线\n播放")
        self.route_btn.setMinimumHeight(60)
        self.route_btn.setEnabled(False)
        card_row.addWidget(self.route_btn)

        self.calibrate_btn = QPushButton("校准\n矩形")
        self.calibrate_btn.setMinimumHeight(60)
        self.calibrate_btn.setEnabled(False)
        card_row.addWidget(self.calibrate_btn)

        mode_layout.addLayout(card_row)
        layout.addWidget(mode_group)

        layout.addStretch()

    def set_mode_buttons_enabled(self, enabled: bool):
        for btn in [self.pace_btn, self.walk_btn, self.route_btn, self.calibrate_btn]:
            btn.setEnabled(enabled)

    # ---- async slots ----

    @qasync.asyncSlot()
    async def _on_refresh(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText("刷新中...")
        try:
            devices = await get_tunneld_devices()
            self._devices = devices
            self.device_list.clear()
            for d in devices:
                info = format_device_info(d)
                self.device_list.addItem(
                    f"{info['product_type']}  iOS {info['os_version']}  {info['name']}"
                )
            self.connect_btn.setEnabled(len(devices) > 0)
            if not devices:
                self.device_info_label.setText("未发现设备，请检查 USB 连接")
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
        row = self.device_list.currentRow()
        if row < 0 or row >= len(self._devices):
            QMessageBox.information(self, "提示", "请先选择一台设备")
            return

        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("连接中...")
        try:
            udid = self._devices[row].peer_info["Properties"]["UniqueDeviceID"]
            self._rsd = await connect_via_tunneld(udid=udid, save_choice=True)

            state = get_state()
            state.rsd = self._rsd
            state.connected_device_info = format_device_info(self._rsd)

            info = state.connected_device_info
            self.device_info_label.setText(
                f"已连接: {info['product_type']}  iOS {info['os_version']}  名称: {info['name']}"
            )
            self.set_mode_buttons_enabled(True)
            self.device_connected.emit(self._rsd)
        except Exception as e:
            QMessageBox.warning(self, "连接失败", str(e))
        finally:
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("连接选中设备")

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

        ok = TunneldManager.start()
        if ok:
            QMessageBox.information(self, "成功", "tunneld 已启动")
            # Schedule refresh via asyncSlot
            self._on_refresh()
        else:
            QMessageBox.warning(self, "失败", "tunneld 启动超时，请手动运行:\npython main.py --tunneld")
