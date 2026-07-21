"""
Modern application sidebar.

Responsibilities
----------------
- Displays navigation items.
- Tracks active page.
- Emits page_changed signal.

No backend logic belongs here.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ui.styles.theme import SIDEBAR_WIDTH


class Sidebar(QFrame):

    page_changed = Signal(int)

    def __init__(self):

        super().__init__()

        self.buttons = []

        self._build_ui()

    # ==========================================================
    # UI
    # ==========================================================

    def _build_ui(self):

        self.setObjectName("Sidebar")

        self.setFixedWidth(SIDEBAR_WIDTH)

        self.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Expanding,
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            20,
            24,
            20,
            24,
        )

        layout.setSpacing(12)

        # ------------------------------------------------------
        # Title
        # ------------------------------------------------------

        title = QLabel("Storage Manager")

        title.setObjectName("SidebarTitle")

        title.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)

        layout.addSpacing(24)

        # ------------------------------------------------------
        # Navigation
        # ------------------------------------------------------

        pages = [

            ("🏠", "Dashboard"),

            ("🧹", "Cleanup"),

            ("✨", "AI Insights"),

            ("⚙", "Settings"),

            ("ℹ", "About"),

        ]

        for index, (icon, text) in enumerate(pages):

            button = QPushButton(
                f"{icon}   {text}"
            )

            button.setObjectName(
                "SidebarButton"
            )

            button.setCheckable(True)

            button.setCursor(
                Qt.PointingHandCursor
            )

            button.clicked.connect(
                lambda checked=False, i=index:
                self.set_current_page(i)
            )

            layout.addWidget(button)

            self.buttons.append(button)

        layout.addStretch()

        version = QLabel("v1.0")

        version.setObjectName(
            "SidebarVersion"
        )

        version.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(version)

        self.set_current_page(0)

    # ==========================================================
    # ACTIVE PAGE
    # ==========================================================

    def set_current_page(
        self,
        index: int,
    ):

        for i, button in enumerate(self.buttons):

            button.setChecked(
                i == index
            )

        self.page_changed.emit(index)