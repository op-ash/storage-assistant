"""
Application entry point.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


# ==========================================================
# LOAD STYLESHEET
# ==========================================================

def load_stylesheet(app: QApplication):

    qss_path = (
        Path(__file__)
        .parent
        / "styles"
        / "dark.qss"
    )

    if not qss_path.exists():

        print(
            f"[WARNING] Stylesheet not found: {qss_path}"
        )

        return

    with open(
        qss_path,
        "r",
        encoding="utf-8",
    ) as file:

        app.setStyleSheet(
            file.read()
        )


# ==========================================================
# MAIN
# ==========================================================

def main():

    app = QApplication(sys.argv)

    app.setApplicationName(
        "Storage Manager"
    )

    app.setOrganizationName(
        "Storage Manager"
    )

    load_stylesheet(app)

    window = MainWindow()

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":

    main()