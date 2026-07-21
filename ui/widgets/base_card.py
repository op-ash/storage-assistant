"""
Base Card Widget

All dashboard cards should inherit from this class.
"""

from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
)


class BaseCard(QFrame):

    def __init__(self):

        super().__init__()

        self.setObjectName("BaseCard")

        self.layout = QVBoxLayout(self)

        self.layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        self.layout.setSpacing(18)

    # ==========================================================
    # Convenience
    # ==========================================================

    def body(self):

        return self.layout