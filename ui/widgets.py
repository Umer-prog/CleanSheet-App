"""Shared custom widget subclasses used across the UI layer."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox


class NoScrollComboBox(QComboBox):
    """QComboBox that ignores wheel events when not focused.

    Prevents accidental value changes when the user scrolls a page that
    contains a closed (collapsed) dropdown.
    """

    def wheelEvent(self, event) -> None:
        # Only scroll through items when the dropdown popup is actually open.
        # hasFocus() is unreliable on Windows — some platforms auto-focus on
        # hover before the wheel event fires, bypassing the guard.
        if self.view().isVisible():
            super().wheelEvent(event)
        else:
            event.ignore()
