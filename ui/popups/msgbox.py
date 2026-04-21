from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox


def _apply(box: QMessageBox) -> QMessageBox:
    box.setWindowFlags(box.windowFlags() | Qt.FramelessWindowHint)
    return box


def question(parent, title: str, text: str, buttons, default=None) -> int:
    box = _apply(QMessageBox(parent))
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default is not None:
        box.setDefaultButton(default)
    return box.exec()


def critical(parent, title: str, text: str) -> int:
    box = _apply(QMessageBox(parent))
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    return box.exec()


def information(parent, title: str, text: str,
                buttons=QMessageBox.StandardButton.Ok, default=None) -> int:
    box = _apply(QMessageBox(parent))
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(buttons)
    if default is not None:
        box.setDefaultButton(default)
    return box.exec()
