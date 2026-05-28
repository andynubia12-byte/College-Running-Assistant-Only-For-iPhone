from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)

        self.tunneld_label = QLabel("tunneld: 检测中...")
        self.tunneld_label.setStyleSheet("color: #86909C;")
        self.device_label = QLabel("设备: 未连接")

        layout.addWidget(self.tunneld_label)
        layout.addSpacing(16)
        layout.addWidget(self.device_label)
        layout.addStretch()

    def set_tunneld_status(self, running: bool):
        if running:
            self.tunneld_label.setText("tunneld  ●  运行中")
            self.tunneld_label.setStyleSheet("color: #00B42A; font-weight: 600;")
        else:
            self.tunneld_label.setText("tunneld  ○  未运行")
            self.tunneld_label.setStyleSheet("color: #E34D59; font-weight: 600;")

    def set_device_info(self, text: str):
        self.device_label.setText(f"设备: {text}")
        self.device_label.setStyleSheet("color: #1D2129; font-weight: 600;")
