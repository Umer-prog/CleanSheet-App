from __future__ import annotations

import subprocess

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QPushButton

from core.app_logger import get_log_file_path


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


def critical_with_log(parent, title: str, text: str) -> int:
    """Critical error dialog that includes an 'Open Log Folder' button.

    Use this for errors the user cannot recover from themselves, so they can
    easily locate the log file to send to support.
    """
    box = _apply(QMessageBox(parent))
    box.setIcon(QMessageBox.Icon.Critical)
    box.setWindowTitle(title)
    box.setText(text)
    ok_btn = box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
    log_path = get_log_file_path()
    if log_path and log_path.exists():
        log_btn = box.addButton("Open Log Folder", QMessageBox.ButtonRole.HelpRole)

        def _open_log():
            subprocess.Popen(["explorer", "/select,", str(log_path)])

        log_btn.clicked.connect(_open_log)
    box.setDefaultButton(ok_btn)
    return box.exec()


def warning(parent, title: str, text: str) -> int:
    box = _apply(QMessageBox(parent))
    box.setIcon(QMessageBox.Icon.Warning)
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
