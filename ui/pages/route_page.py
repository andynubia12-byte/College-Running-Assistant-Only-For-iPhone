from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QListWidget, QSpinBox, QMessageBox,
)

from backend.routes import list_routes, load_route
from backend.config import load_config, save_config


class RoutePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._routes = []
        self._init_ui()
        self._refresh_routes()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("路线播放")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)

        self.route_list = QListWidget()
        self.route_list.setMinimumHeight(100)
        layout.addWidget(self.route_list)

        btn_row = QHBoxLayout()
        self.refresh_btn = QPushButton("刷新路线")
        self.refresh_btn.clicked.connect(self._refresh_routes)
        btn_row.addWidget(self.refresh_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        form = QFormLayout()

        self.loop_spin = QSpinBox()
        self.loop_spin.setRange(1, 9999)
        self.loop_spin.setValue(10)
        form.addRow("循环圈数:", self.loop_spin)

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

    def _refresh_routes(self):
        self._routes = list_routes()
        self.route_list.clear()
        for r in self._routes:
            self.route_list.addItem(f"{r['name']} ({r['points']} 个点)")

    def _on_start(self):
        row = self.route_list.currentRow()
        if row < 0 or row >= len(self._routes):
            QMessageBox.information(self, "提示", "请先选择一条路线")
            return

        route_info = self._routes[row]
        try:
            route_data = load_route(route_info["filename"])
        except Exception as e:
            QMessageBox.warning(self, "加载失败", str(e))
            return

        cfg = load_config()
        cfg["loop_count"] = self.loop_spin.value()
        save_config(cfg)

        run_config = {
            "mode": "route",
            "config": cfg,
            "route_data": route_data,
            "title": f"路线播放 — {route_info['name']} ({route_info['points']} 点 × {self.loop_spin.value()} 圈)",
            "duration": None,
        }
        w = self.window()
        if hasattr(w, "start_run"):
            w.start_run(run_config)
