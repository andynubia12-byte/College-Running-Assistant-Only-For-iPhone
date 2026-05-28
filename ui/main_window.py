from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QStackedWidget

from ui.pages.home_page import HomePage
from ui.pages.pace_page import PacePage
from ui.pages.walk_page import WalkPage
from ui.pages.route_page import RoutePage
from ui.pages.run_page import RunPage
from ui.pages.settings_page import SettingsPage
from ui.pages.calibrate_page import CalibratePage
from ui.pages.log_page import LogPage
from ui.app_state import get_state


PAGE_HOME = 0
PAGE_PACE = 1
PAGE_WALK = 2
PAGE_ROUTE = 3
PAGE_RUN = 4
PAGE_CALIBRATE = 5
PAGE_SETTINGS = 6
PAGE_LOG = 7


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GeoPilot")
        self.resize(1000, 650)
        self.setMinimumSize(860, 540)

        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # PAGE_HOME
        self.home_page = HomePage()
        self.stack.addWidget(self.home_page)

        # PAGE_PACE
        self.pace_page = PacePage()
        self.pace_page.back_btn.clicked.connect(lambda: self.navigate(PAGE_HOME))
        self.stack.addWidget(self.pace_page)

        # PAGE_WALK
        self.walk_page = WalkPage()
        self.walk_page.back_btn.clicked.connect(lambda: self.navigate(PAGE_HOME))
        self.stack.addWidget(self.walk_page)

        # PAGE_ROUTE
        self.route_page = RoutePage()
        self.route_page.back_btn.clicked.connect(lambda: self.navigate(PAGE_HOME))
        self.stack.addWidget(self.route_page)

        # PAGE_RUN
        self.run_page = RunPage()
        self.run_page.back_requested.connect(self._on_run_back)
        self.stack.addWidget(self.run_page)

        # PAGE_CALIBRATE
        self.calibrate_page = CalibratePage()
        self.calibrate_page.back_btn.clicked.connect(lambda: self.navigate(PAGE_HOME))
        self.stack.addWidget(self.calibrate_page)

        # PAGE_SETTINGS
        self.settings_page = SettingsPage()
        self.settings_page.back_btn.clicked.connect(lambda: self.navigate(PAGE_HOME))
        self.stack.addWidget(self.settings_page)

        # PAGE_LOG
        self.log_page = LogPage()
        self.log_page.back_btn.clicked.connect(lambda: self.navigate(PAGE_HOME))
        self.stack.addWidget(self.log_page)

        # ---- wire home page ----
        self.home_page.pace_btn.clicked.connect(lambda: self.navigate(PAGE_PACE))
        self.home_page.walk_btn.clicked.connect(lambda: self.navigate(PAGE_WALK))
        self.home_page.route_btn.clicked.connect(lambda: self.navigate(PAGE_ROUTE))
        self.home_page.calibrate_btn.clicked.connect(lambda: self.navigate(PAGE_CALIBRATE))
        self.home_page.settings_btn.clicked.connect(lambda: self.navigate(PAGE_SETTINGS))
        self.home_page.log_btn.clicked.connect(lambda: self.navigate(PAGE_LOG))

        # ---- signals ----
        self.home_page.device_connected.connect(self._on_device_connected)

        # initial tunneld check
        from ui.tunneld_manager import TunneldManager
        self.home_page.update_tunneld_status(TunneldManager.is_running())

    def navigate(self, page_index: int):
        if page_index < self.stack.count():
            self.stack.setCurrentIndex(page_index)
        if page_index == PAGE_PACE:
            self.pace_page.reload_config()
        elif page_index == PAGE_WALK:
            self.walk_page.reload_config()
        elif page_index == PAGE_ROUTE:
            self.route_page.reload_config()
        elif page_index == PAGE_SETTINGS:
            self.settings_page._load()

    def start_run(self, run_config: dict):
        self.run_page.set_run_config(run_config)
        self.stack.setCurrentIndex(PAGE_RUN)

    def _on_run_back(self):
        state = get_state()
        if state.running:
            return
        self.navigate(PAGE_HOME)

    def _on_device_connected(self, _rsd):
        self.home_page._update_device_counts()
        self.home_page.update_tunneld_status(True)
