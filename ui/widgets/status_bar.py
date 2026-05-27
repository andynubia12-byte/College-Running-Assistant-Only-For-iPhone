from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.tunneld_label = QLabel("tunneld: 检测中...")
        self.device_label = QLabel("设备: 未连接")

        layout.addWidget(self.tunneld_label)
        layout.addSpacing(16)
        layout.addWidget(self.device_label)
        layout.addStretch()

    def set_tunneld_status(self, running: bool):
        if running:
            self.tunneld_label.setText("tunneld ● 运行中")
            self.tunneld_label.setStyleSheet("color: green;")
        else:
            self.tunneld_label.setText("tunneld ○ 未运行")
            self.tunneld_label.setStyleSheet("color: red;")

    def set_device_info(self, text: str):
        self.device_label.setText(f"设备: {text}")
