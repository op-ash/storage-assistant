"""
Cleanup Category Card

Reusable for:

- Safe to Clean
- Review Before Cleaning
- AI Suggestions
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
)

from ui.widgets.cleanup_item import CleanupItem

from ui.widgets.base_card import BaseCard

class CleanupCategoryCard(BaseCard):

    def __init__(
        self,
        title: str,
        accent: str,
        action_text: str,
    ):

        super().__init__()

        self.setObjectName("CleanupCategoryCard")

        self.title_text = title
        self.accent = accent
        self.action_text = action_text

        self.items = []

        self.selected_items = 0

        self._build_ui()

    # ==========================================================
    # UI
    # ==========================================================

    def _build_ui(self):

        root = self.body()

        root.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        root.setSpacing(18)

        # ------------------------------------------------------
        # Header
        # ------------------------------------------------------

        header = QHBoxLayout()

        self.title = QLabel(self.title_text)

        self.title.setObjectName("CardTitle")

        header.addWidget(self.title)

        header.addStretch()

        self.total_size = QLabel("0 MB")

        self.total_size.setObjectName("CleanupSize")

        header.addWidget(self.total_size)

        root.addLayout(header)

        # ------------------------------------------------------
        # Items
        # ------------------------------------------------------

        self.items_layout = QVBoxLayout()

        self.items_layout.setSpacing(12)

        root.addLayout(self.items_layout)

        # ------------------------------------------------------
        # Bottom Summary
        # ------------------------------------------------------

        bottom = QHBoxLayout()

        self.summary = QLabel(
            "Selected : 0 MB"
        )

        self.summary.setObjectName(
            "CleanupSummary"
        )

        self.action_button = QPushButton(
            self.action_text
        )

        self.action_button.setObjectName(
            "PrimaryButton"
        )

        self.action_button.setEnabled(False)

        bottom.addWidget(
            self.summary
        )

        bottom.addStretch()

        bottom.addWidget(
            self.action_button
        )

        root.addLayout(bottom)

    # ==========================================================
    # PUBLIC
    # ==========================================================

    def set_items(
        self,
        items: list,
    ):

        while self.items_layout.count():

            child = self.items_layout.takeAt(0)

            if child.widget():

                child.widget().deleteLater()

        self.items.clear()

        for item in items:

            widget = CleanupItem(

                title=item["title"],

                subtitle=item["subtitle"],

                size=item["size"],

            )

            widget.selection_changed.connect(
                self._selection_changed
            )

            self.items_layout.addWidget(
                widget
            )

            self.items.append(widget)

        self.total_size.setText(

            self._calculate_total_size()

        )

    # ==========================================================
    # Selection
    # ==========================================================

    def _selection_changed(self):

        total = 0.0

        for item in self.items:

            if item.is_selected():

                total += self._size_to_gb(

                    item.size_text

                )

        if total == 0:

            self.summary.setText(
                "Selected : 0 MB"
            )

            self.action_button.setEnabled(
                False
            )

            return

        self.summary.setText(

            f"Selected : {total:.2f} GB"

        )

        self.action_button.setEnabled(
            True
        )

    # ==========================================================
    # Helpers
    # ==========================================================

    def _calculate_total_size(self):

        total = 0.0

        for item in self.items:

            total += self._size_to_gb(
                item.size_text
            )

        return f"{total:.2f} GB"

    def _size_to_gb(
        self,
        value: str,
    ):

        value = value.strip().upper()

        if "GB" in value:

            return float(
                value.replace(
                    "GB",
                    ""
                )
            )

        if "MB" in value:

            return float(
                value.replace(
                    "MB",
                    ""
                )
            ) / 1024

        if "KB" in value:

            return float(
                value.replace(
                    "KB",
                    ""
                )
            ) / (1024 * 1024)

        return 0