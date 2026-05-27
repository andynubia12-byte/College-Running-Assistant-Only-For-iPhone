from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
)
from PySide6.QtCore import QDateTime


class LogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("运行日志")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        top.addWidget(title)
        top.addStretch()

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        top.addWidget(self.clear_btn)

        self.back_btn = QPushButton("返回")
        top.addWidget(self.back_btn)
        layout.addLayout(top)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(500)
        layout.addWidget(self.log_view)

    def append(self, text: str):
        ts = QDateTime.currentDateTime().toString("HH:mm:ss")
        self.log_view.append(f"[{ts}] {text}")

    def _on_clear(self):
        self.log_view.clear()
