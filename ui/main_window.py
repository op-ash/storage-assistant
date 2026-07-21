"""
Main application window.

Responsibilities
----------------
- Creates the main application shell.
- Hosts sidebar.
- Hosts stacked pages.
- Hosts status bar.

No backend logic belongs here.
"""

from ui.pages.dashboard import DashboardPage

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from ui.styles.theme import *
from ui.widgets.sidebar import Sidebar


class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        self._setup_window()

        self._create_layout()

        self._create_pages()

        self._create_sidebar()

        self._create_statusbar()

        self._connect_signals()

    # ==========================================================
    # WINDOW
    # ==========================================================

    def _setup_window(self):

        self.setWindowTitle("Storage Manager")

        self.resize(1500, 900)

        self.setMinimumSize(1200, 700)

    # ==========================================================
    # ROOT LAYOUT
    # ==========================================================

    def _create_layout(self):

        self.central_widget = QWidget()

        self.setCentralWidget(self.central_widget)

        self.root_layout = QVBoxLayout()

        self.root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.root_layout.setSpacing(0)

        self.central_widget.setLayout(self.root_layout)

        self.content_layout = QHBoxLayout()

        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.content_layout.setSpacing(0)

        self.root_layout.addLayout(self.content_layout)

    # ==========================================================
    # SIDEBAR
    # ==========================================================

    def _create_sidebar(self):

        self.sidebar = Sidebar()

        self.content_layout.insertWidget(
            0,
            self.sidebar,
        )

    # ==========================================================
    # STACKED PAGES
    # ==========================================================

    def _create_pages(self):

        self.pages = QStackedWidget()

        self.pages.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        page_names = [
            DashboardPage(),
            QWidget(),
            QWidget(),
            QWidget(),
            QWidget(),
        ]

        for page in page_names:

            if isinstance(page, QWidget) and not isinstance(page, DashboardPage):
                layout = QVBoxLayout(page)

                label = QLabel("Coming Soon")

                label.setAlignment(Qt.AlignCenter)

                layout.addStretch()

                layout.addWidget(label)

                layout.addStretch()

            self.pages.addWidget(page)

        self.content_layout.addWidget(self.pages)

    # ==========================================================
    # STATUS BAR
    # ==========================================================

    def _create_statusbar(self):

        self.status = QStatusBar()

        self.status.showMessage("Ready")

        self.setStatusBar(self.status)

    # ==========================================================
    # SIGNALS
    # ==========================================================

    def _connect_signals(self):

        self.sidebar.page_changed.connect(

            self.pages.setCurrentIndex

        )