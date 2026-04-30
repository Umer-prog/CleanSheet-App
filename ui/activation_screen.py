"""
Activation screen — shown before the main window when the license is invalid.
Accepts when a valid license is successfully installed so main.py can continue.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.license_constants import LICENSE_FILE_NAME, LICENSE_SEARCH_PATHS
from core.machine_id import get_machine_id
from core.license_validator import LicenseResult, validate_license

_SUPPORT_EMAIL = "support@gd365.com"

_HEADING: dict[str, str] = {
    "NO_FILE":           "Activate CleanSheet",
    "EXPIRED":           "License Expired",
    "WRONG_MACHINE":     "License Not Valid for This Computer",
    "INVALID_SIGNATURE": "Invalid License File",
    "INVALID_FORMAT":    "Invalid License File",
}


class ActivationScreen(QDialog):
    """Frameless activation dialog. Call exec() — returns Accepted if license installed."""

    def __init__(self, result: LicenseResult) -> None:
        super().__init__(None)
        self._result = result
        self._machine_id = get_machine_id()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedSize(540, 660)
        self.setStyleSheet("QDialog { background: #0f1117; }")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_header())
        root.addWidget(self._build_body(), 1)
        root.addWidget(self._build_footer())

        # Center on screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2,
        )

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setFixedHeight(80)
        frame.setStyleSheet("QFrame { background: #13161e; border-bottom: 1px solid rgba(255,255,255,0.07); }")

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(28, 14, 28, 14)
        lay.setSpacing(2)

        reason = self._result.failure_reason or "NO_FILE"
        heading = _HEADING.get(reason, "CleanSheet Activation")

        title_lbl = QLabel(
            f"<span style='font-size:16px; font-weight:700; color:#f1f5f9;'>CleanSheet</span>"
            f"<br><span style='font-size:12px; color:#94a3b8;'>{heading}</span>"
        )
        title_lbl.setTextFormat(Qt.RichText)
        lay.addWidget(title_lbl)

        return frame

    # ------------------------------------------------------------------
    # Body — switches on failure reason
    # ------------------------------------------------------------------

    def _build_body(self) -> QWidget:
        frame = QFrame()
        frame.setStyleSheet("QFrame { background: #0f1117; }")

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(16)

        reason = self._result.failure_reason or "NO_FILE"

        if reason == "NO_FILE":
            self._build_no_file(lay)
        elif reason == "EXPIRED":
            self._build_expired(lay)
        elif reason == "WRONG_MACHINE":
            self._build_wrong_machine(lay)
        else:
            self._build_invalid(lay)

        lay.addStretch(1)
        return frame

    # ---- NO_FILE ----

    def _build_no_file(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_section_label("Your Machine ID"))
        lay.addWidget(self._machine_id_box())
        self._copy_btn = _copy_button(self._machine_id, self)
        lay.addWidget(self._copy_btn)

        lay.addWidget(_divider())

        lay.addWidget(_muted("Send your Machine ID to support@gd365.com."))
        lay.addWidget(_muted("You will receive a license file by email."))

        lay.addWidget(_divider())

        lay.addWidget(_section_label("Already have a license file?"))
        browse = _primary_button("Browse for License File")
        browse.clicked.connect(self._browse_for_license)
        lay.addWidget(browse)

        lay.addWidget(_license_hint_label())
        self._inline_error = _error_label()
        lay.addWidget(self._inline_error)

    # ---- EXPIRED ----

    def _build_expired(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_body_text(self._result.failure_message))
        lay.addWidget(_email_link(_SUPPORT_EMAIL))
        lay.addWidget(_divider())
        browse = _primary_button("Browse for New License File")
        browse.clicked.connect(self._browse_for_license)
        lay.addWidget(browse)
        lay.addWidget(_license_hint_label())
        self._inline_error = _error_label()
        lay.addWidget(self._inline_error)

    # ---- WRONG_MACHINE ----

    def _build_wrong_machine(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_body_text(self._result.failure_message))
        lay.addWidget(_divider())
        lay.addWidget(_section_label("Your Machine ID"))
        lay.addWidget(self._machine_id_box())
        self._copy_btn = _copy_button(self._machine_id, self)
        lay.addWidget(self._copy_btn)
        lay.addWidget(_email_link(_SUPPORT_EMAIL))
        lay.addWidget(_divider())
        lay.addWidget(_section_label("Already have a license for this computer?"))
        browse = _primary_button("Browse for New License File")
        browse.clicked.connect(self._browse_for_license)
        lay.addWidget(browse)
        lay.addWidget(_license_hint_label())
        self._inline_error = _error_label()
        lay.addWidget(self._inline_error)

    # ---- INVALID_SIGNATURE / INVALID_FORMAT ----

    def _build_invalid(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_body_text(self._result.failure_message))
        lay.addWidget(_email_link(_SUPPORT_EMAIL))
        lay.addWidget(_divider())
        browse = _primary_button("Browse for License File")
        browse.clicked.connect(self._browse_for_license)
        lay.addWidget(browse)
        lay.addWidget(_license_hint_label())
        self._inline_error = _error_label()
        lay.addWidget(self._inline_error)

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    def _build_footer(self) -> QWidget:
        frame = QFrame()
        frame.setFixedHeight(56)
        frame.setStyleSheet("QFrame { background: #13161e; border-top: 1px solid rgba(255,255,255,0.07); }")

        lay = QHBoxLayout(frame)
        lay.setContentsMargins(28, 0, 28, 0)

        version_lbl = QLabel("CleanSheet — Licensed software")
        version_lbl.setStyleSheet("color: #94a3b8; font-size: 11px; background: transparent;")
        lay.addWidget(version_lbl, 1)

        close_btn = QPushButton("Exit")
        close_btn.setObjectName("btn_ghost")
        close_btn.setFixedHeight(34)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)

        return frame

    # ------------------------------------------------------------------
    # Machine ID widget
    # ------------------------------------------------------------------

    def _machine_id_box(self) -> QLineEdit:
        box = QLineEdit(self._machine_id)
        box.setReadOnly(True)
        box.setAlignment(Qt.AlignCenter)
        box.setFixedHeight(42)
        box.setFont(QFont("Consolas", 14))
        box.setStyleSheet(
            "QLineEdit {"
            "  background: #13161e;"
            "  border: 1px solid rgba(59,130,246,0.3);"
            "  border-radius: 7px;"
            "  color: #93c5fd;"
            "  letter-spacing: 2px;"
            "}"
        )
        return box

    # ------------------------------------------------------------------
    # Browse and validate
    # ------------------------------------------------------------------

    def _browse_for_license(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select License File", "", "License Files (*.lic);;All Files (*)"
        )
        if not path:
            return

        src = Path(path)
        dest_dir = self._first_writable_path()
        if dest_dir is None:
            self._show_error("Could not find a writable location for the license file.")
            return

        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest_dir / LICENSE_FILE_NAME)
        except OSError as exc:
            self._show_error(f"Could not copy license file: {exc}")
            return

        new_result = validate_license()
        if new_result.valid:
            self.accept()
        else:
            self._show_error(new_result.failure_message)

    def _first_writable_path(self) -> Path | None:
        for directory in LICENSE_SEARCH_PATHS:
            p = Path(directory)
            try:
                p.mkdir(parents=True, exist_ok=True)
                test = p / ".write_test"
                test.touch()
                test.unlink()
                return p
            except OSError:
                continue
        return None

    def _show_error(self, message: str) -> None:
        if hasattr(self, "_inline_error"):
            self._inline_error.setText(message)
            self._inline_error.setVisible(True)


# ------------------------------------------------------------------
# Helper widget builders
# ------------------------------------------------------------------

def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #f1f5f9; font-size: 13px; font-weight: 600; background: transparent;")
    return lbl


def _body_text(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: #94a3b8; font-size: 13px; background: transparent;")
    return lbl


def _muted(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("color: #94a3b8; font-size: 12px; background: transparent;")
    return lbl


def _email_link(email: str) -> QLabel:
    lbl = QLabel(f"<a href='mailto:{email}' style='color:#3b82f6;'>{email}</a>")
    lbl.setTextFormat(Qt.RichText)
    lbl.setOpenExternalLinks(True)
    lbl.setStyleSheet("background: transparent;")
    return lbl


def _primary_button(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setObjectName("btn_primary")
    btn.setFixedHeight(38)
    btn.setCursor(Qt.PointingHandCursor)
    return btn


def _copy_button(value: str, parent: QDialog) -> QPushButton:
    btn = QPushButton("Copy Machine ID")
    btn.setObjectName("btn_outline")
    btn.setFixedHeight(34)
    btn.setCursor(Qt.PointingHandCursor)

    def _copy():
        QApplication.clipboard().setText(value)
        btn.setText("Copied")
        QTimer.singleShot(2000, lambda: btn.setText("Copy Machine ID"))

    btn.clicked.connect(_copy)
    return btn


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet("QFrame { background: rgba(255,255,255,0.07); border: none; }")
    return line


def _error_label() -> QLabel:
    lbl = QLabel()
    lbl.setWordWrap(True)
    lbl.setStyleSheet("color: #f87171; font-size: 12px; background: transparent;")
    lbl.setVisible(False)
    return lbl


def _license_hint_label() -> QLabel:
    """Shows expected .lic drop path(s) so support can guide users without ambiguity."""
    lines = ["Expected location:"] + [
        str(p / LICENSE_FILE_NAME) for p in LICENSE_SEARCH_PATHS
    ]
    lbl = QLabel("\n".join(lines))
    lbl.setWordWrap(True)
    lbl.setStyleSheet(
        "color: #94a3b8; font-size: 11px; font-family: Consolas; background: transparent;"
    )
    return lbl
