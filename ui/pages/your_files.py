"""
Your Files Page

Shows user-controlled folders like:

- Downloads
- Documents
- Desktop
- Pictures
- Videos

This page never shows system folders.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLineEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
)


class YourFilesPage(QWidget):

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

        root.setSpacing(20)

        # ------------------------------------------------------
        # Header
        # ------------------------------------------------------

        title = QLabel("Your Files")

        title.setObjectName("PageTitle")

        subtitle = QLabel(
            "Browse and manage files from your personal folders."
        )

        subtitle.setObjectName("PageSubtitle")

        root.addWidget(title)

        root.addWidget(subtitle)

        # ------------------------------------------------------
        # Toolbar
        # ------------------------------------------------------

        toolbar = QHBoxLayout()

        self.search = QLineEdit()

        self.search.setPlaceholderText(
            "Search files..."
        )

        toolbar.addWidget(
            self.search,
            stretch=1,
        )

        self.sort = QComboBox()

        self.sort.addItems([

            "Sort by Size",

            "Sort by Date",

            "Sort by File Type",

            "Sort by Last Opened",

        ])

        toolbar.addWidget(
            self.sort
        )

        root.addLayout(toolbar)

        # ------------------------------------------------------
        # Folder Buttons
        # ------------------------------------------------------

        folders = QHBoxLayout()

        self.downloads = QPushButton("Downloads")

        self.documents = QPushButton("Documents")

        self.desktop = QPushButton("Desktop")

        self.pictures = QPushButton("Pictures")

        self.videos = QPushButton("Videos")

        folders.addWidget(self.downloads)

        folders.addWidget(self.documents)

        folders.addWidget(self.desktop)

        folders.addWidget(self.pictures)

        folders.addWidget(self.videos)

        root.addLayout(folders)

        # ------------------------------------------------------
        # File List
        # ------------------------------------------------------

        self.file_list = QListWidget()

        root.addWidget(
            self.file_list,
            stretch=1,
        )

        self._load_demo_data()

    # ==========================================================
    # Demo Data
    # ==========================================================

    def _load_demo_data(self):

        demo = [

            (
                "ChromeSetup.exe",
                "2.4 GB • Installer • Last opened 3 months ago",
            ),

            (
                "Unity.zip",
                "1.8 GB • ZIP Archive • Yesterday",
            ),

            (
                "Movie.mp4",
                "4.6 GB • Video • Last opened 6 months ago",
            ),

            (
                "Old Project.blend",
                "890 MB • Blender • Last opened 1 year ago",
            ),

        ]

        for title, subtitle in demo:

            item = QListWidgetItem()

            item.setText(
                f"{title}\n{subtitle}"
            )

            self.file_list.addItem(item)