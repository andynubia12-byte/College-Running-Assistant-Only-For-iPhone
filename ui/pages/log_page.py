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
        layout.setSpacing(14)
        layout.setContentsMargins(18, 18, 18, 18)

        top = QHBoxLayout()
        self.back_btn = QPushButton("← 返回")
        self.back_btn.setObjectName("backBtn")
        top.addWidget(self.back_btn)
        top.addStretch()

        title = QLabel("运行日志")
        title.setObjectName("pageTitle")
        top.addWidget(title)
        top.addStretch()

        self.clear_btn = QPushButton("清空")
        self.clear_btn.clicked.connect(self._on_clear)
        top.addWidget(self.clear_btn)
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
