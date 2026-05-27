import asyncio
from functools import partial

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QProgressBar, QTextEdit, QGroupBox,
)
from PySide6.QtCore import Signal

from backend.modes import gen_pace, gen_random_walk, gen_route
from ui.controllers.run_controller import RunController
from ui.app_state import get_state


class RunPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._controller = RunController(self)
        self._run_config = None
        self._init_ui()

        self._controller.status_updated.connect(self._on_status)
        self._controller.run_finished.connect(self._on_finished)
        self._controller.error_occurred.connect(self._on_error)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        self.mode_label = QLabel()
        self.mode_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.mode_label)

        self.stats_label = QLabel("就绪")
        layout.addWidget(self.stats_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        ctrl = QHBoxLayout()
        self.start_btn = QPushButton("开始")
        self.start_btn.clicked.connect(self._on_start)
        ctrl.addWidget(self.start_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._on_stop)
        ctrl.addWidget(self.stop_btn)

        self.back_btn = QPushButton("返回")
        self.back_btn.clicked.connect(lambda: self.back_requested.emit())
        ctrl.addWidget(self.back_btn)
        ctrl.addStretch()
        layout.addLayout(ctrl)

        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout(log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.document().setMaximumBlockCount(300)
        log_layout.addWidget(self.log_view)
        layout.addWidget(log_group)

    # ---- public ----

    def set_run_config(self, run_config: dict):
        self._run_config = run_config
        self.mode_label.setText(run_config.get("title", "未知模式"))
        self.stats_label.setText("就绪")
        self.log_view.clear()
        self.progress_bar.setVisible(False)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    # ---- private ----

    def _create_generator(self):
        cfg = self._run_config
        mode = cfg["mode"]
        config = cfg["config"]

        if mode == "pace":
            return gen_pace(config, self._controller._stop_event)
        elif mode == "walk":
            return gen_random_walk(config, self._controller._stop_event)
        elif mode == "route":
            return gen_route(cfg["route_data"], config, self._controller._stop_event)
        else:
            raise ValueError(f"未知模式: {mode}")

    def _on_start(self):
        state = get_state()
        if state.rsd is None:
            self._append_log("[ERROR] 未连接设备")
            return

        gen = self._create_generator()
        self._controller.start(state.rsd, gen)

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.back_btn.setEnabled(False)
        self._append_log("[开始]")

        duration = self._run_config.get("duration")
        if duration:
            self.progress_bar.setMaximum(int(duration))
            self.progress_bar.setValue(0)
            self.progress_bar.setVisible(True)

    def _on_stop(self):
        self._controller.stop()
        self._append_log("[停止]")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.back_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _on_status(self, data: dict):
        lat, lng = data["lat"], data["lng"]
        tick, dist = data["tick"], data["dist"]
        elapsed = data["elapsed"]

        self.stats_label.setText(
            f"tick={tick}  |  {dist:.0f}m  |  {elapsed:.0f}s  |  ({lat:.8f}, {lng:.8f})"
        )
        if self.progress_bar.isVisible():
            self.progress_bar.setValue(int(elapsed))

        if tick % max(1, int(10 / 0.05)) == 0:
            self._append_log(f"[{elapsed:.0f}s] tick={tick}  dist={dist:.0f}m")

    def _on_finished(self, meta: dict):
        self._append_log(f"[完成] {meta.get('tick', 0)} ticks  {meta.get('total_dist', 0):.0f}m  {meta.get('elapsed', 0):.0f}s")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.back_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def _on_error(self, msg: str):
        self._append_log(f"[ERROR] {msg}")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.back_btn.setEnabled(True)

    def _append_log(self, text: str):
        self.log_view.append(text)
