"""
Cleanup Item Widget

Reusable item card used by:

- Safe to Clean
- Review Before Cleaning
- AI Suggestions
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
)


class CleanupItem(QFrame):

    selection_changed = Signal(bool)

    def __init__(
        self,
        title: str,
        subtitle: str,
        size: str,
    ):

        super().__init__()

        self.selected = False

        self.title_text = title
        self.subtitle_text = subtitle
        self.size_text = size

        self.setObjectName("CleanupItem")

        self.setCursor(Qt.PointingHandCursor)

        self._build_ui()

    # ==========================================================
    # UI
    # ==========================================================

    def _build_ui(self):

        root = QHBoxLayout(self)

        root.setContentsMargins(
            18,
            16,
            18,
            16,
        )

        root.setSpacing(18)

        # ------------------------------------------------------
        # Left Side
        # ------------------------------------------------------

        left = QVBoxLayout()

        left.setSpacing(4)

        self.title = QLabel(self.title_text)

        self.title.setObjectName("CleanupItemTitle")

        self.subtitle = QLabel(self.subtitle_text)

        self.subtitle.setObjectName("CleanupItemSubtitle")

        left.addWidget(self.title)

        left.addWidget(self.subtitle)

        # ------------------------------------------------------
        # Right Side
        # ------------------------------------------------------

        right = QVBoxLayout()

        right.setAlignment(Qt.AlignCenter)

        self.size = QLabel(self.size_text)

        self.size.setObjectName("CleanupItemSize")

        self.state = QLabel("")

        self.state.setObjectName("CleanupItemState")

        right.addWidget(self.size)

        right.addWidget(self.state)

        root.addLayout(
            left,
            stretch=1,
        )

        root.addLayout(right)

        self._refresh()

    # ==========================================================
    # Selection
    # ==========================================================

    def mousePressEvent(
        self,
        event,
    ):

        self.selected = not self.selected

        self._refresh()

        self.selection_changed.emit(
            self.selected
        )

        super().mousePressEvent(event)

    # ==========================================================
    # Public API
    # ==========================================================

    def is_selected(self):

        return self.selected

    def set_selected(
        self,
        selected: bool,
    ):

        self.selected = selected

        self._refresh()

    # ==========================================================
    # UI Refresh
    # ==========================================================

    def _refresh(self):

        if self.selected:

            self.setProperty(
                "selected",
                True,
            )

            self.state.setText("✓ Selected")

        else:

            self.setProperty(
                "selected",
                False,
            )

            self.state.setText("")

        self.style().unpolish(self)
        self.style().polish(self)