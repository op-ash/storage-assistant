"""
Storage Overview Card
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QHBoxLayout,
)

from ui.widgets.base_card import BaseCard

class StorageOverviewCard(BaseCard):

    def __init__(self):

        super().__init__()

        self.setObjectName("StorageCard")

        self._build_ui()

    # ==========================================================
    # UI
    # ==========================================================

    def _build_ui(self):

        root = self.body()

        root.setContentsMargins(24, 24, 24, 24)

        root.setSpacing(18)

        # ------------------------------------------------------
        # Header
        # ------------------------------------------------------

        header = QHBoxLayout()

        title = QLabel("Storage Overview")
        title.setObjectName("CardTitle")

        self.last_scan = QLabel("Last Scan : Never")
        self.last_scan.setObjectName("CardSubtitle")

        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.last_scan)

        root.addLayout(header)

        # ------------------------------------------------------
        # Drive
        # ------------------------------------------------------

        self.drive_label = QLabel("C: Drive")
        self.drive_label.setObjectName("DriveTitle")

        root.addWidget(self.drive_label)

        # ------------------------------------------------------
        # Progress
        # ------------------------------------------------------

        self.progress = QProgressBar()

        self.progress.setRange(0, 100)

        self.progress.setValue(82)

        self.progress.setTextVisible(False)

        root.addWidget(self.progress)

        # ------------------------------------------------------
        # Storage Numbers
        # ------------------------------------------------------

        numbers = QHBoxLayout()

        self.used = QLabel("420 GB Used")

        self.free = QLabel("92 GB Free")

        self.total = QLabel("512 GB Total")

        self.used.setObjectName("StorageValue")
        self.free.setObjectName("StorageValue")
        self.total.setObjectName("StorageValue")

        numbers.addWidget(self.used)

        numbers.addStretch()

        numbers.addWidget(self.free)

        numbers.addStretch()

        numbers.addWidget(self.total)

        root.addLayout(numbers)

        # ------------------------------------------------------
        # Scan Button
        # ------------------------------------------------------

        self.scan_button = QPushButton("Scan Storage")

        self.scan_button.setObjectName("PrimaryButton")

        root.addWidget(
            self.scan_button,
            alignment=Qt.AlignRight,
        )