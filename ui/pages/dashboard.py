"""
Dashboard Page
"""

from PySide6.QtWidgets import (
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
)

from ui.widgets.storage_overview_card import StorageOverviewCard
from ui.widgets.cleanup_category_card import CleanupCategoryCard


class DashboardPage(QWidget):

    def __init__(self):

        super().__init__()

        self._build_ui()

    # ==========================================================
    # UI
    # ==========================================================

    def _build_ui(self):

        root = QVBoxLayout(self)

        root.setContentsMargins(
            30,
            30,
            30,
            30,
        )

        root.setSpacing(24)

        # ------------------------------------------------------
        # Title
        # ------------------------------------------------------

        title = QLabel("Dashboard")

        title.setObjectName(
            "PageTitle"
        )

        root.addWidget(title)

        # ------------------------------------------------------
        # Storage
        # ------------------------------------------------------

        self.storage = StorageOverviewCard()

        root.addWidget(
            self.storage
        )

        # ------------------------------------------------------
        # Safe Cleanup
        # ------------------------------------------------------

        self.safe = CleanupCategoryCard(

            title="🟢 Safe to Clean",

            accent="#10B981",

            action_text="Clean Selected",

        )

        self.safe.set_items([

            {
                "title": "Chrome Cache",
                "subtitle": "Browser temporary files",
                "size": "2.40 GB",
            },

            {
                "title": "Windows Temporary Files",
                "subtitle": "Windows temp folder",
                "size": "1.82 GB",
            },

            {
                "title": "NVIDIA Shader Cache",
                "subtitle": "Graphics cache",
                "size": "950 MB",
            },

        ])

        root.addWidget(
            self.safe
        )

        # ------------------------------------------------------
        # Review
        # ------------------------------------------------------

        self.review = CleanupCategoryCard(

            title="🟡 Review Before Cleaning",

            accent="#F59E0B",

            action_text="Review Selected",

        )

        self.review.set_items([

            {
                "title": "Downloads",
                "subtitle": "Old installers",
                "size": "4.20 GB",
            },

            {
                "title": "CapCut Projects",
                "subtitle": "Unused exported videos",
                "size": "2.15 GB",
            },

        ])

        root.addWidget(
            self.review
        )

        root.addStretch()