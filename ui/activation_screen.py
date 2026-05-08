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

_SUPPORT_EMAIL = "support@globaldata365.com"

_HEADING: dict[str, str] = {
    "NO_FILE":           "Activate BI CleanSheet 365",
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
        heading = _HEADING.get(reason, "BI CleanSheet 365 Activation")

        title_lbl = QLabel(
            f"<span style='font-size:16px; font-weight:700; color:#f1f5f9;'>BI CleanSheet 365</span>"
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

        lay.addWidget(_muted("Send your Machine ID to support@globaldata365.com."))
        lay.addWidget(_muted("You will receive a license file by email."))

        lay.addWidget(_divider())

        lay.addWidget(_section_label("Already have a license file?"))
        browse = _primary_button("Browse for License File")
        browse.clicked.connect(self._browse_for_license)
        lay.addWidget(browse)

        self._inline_error = _error_label()
        lay.addWidget(self._inline_error)

    # ---- EXPIRED ----

    def _build_expired(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_body_text(self._result.failure_message))
        lay.addWidget(_email_link(_SUPPORT_EMAIL))
        lay.addWidget(_divider())
        lay.addWidget(_section_label("Your Machine ID"))
        lay.addWidget(self._machine_id_box())
        self._copy_btn = _copy_button(self._machine_id, self)
        lay.addWidget(self._copy_btn)
        lay.addWidget(_divider())
        browse = _primary_button("Browse for New License File")
        browse.clicked.connect(self._browse_for_license)
        lay.addWidget(browse)
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
        self._inline_error = _error_label()
        lay.addWidget(self._inline_error)

    # ---- INVALID_SIGNATURE / INVALID_FORMAT ----

    def _build_invalid(self, lay: QVBoxLayout) -> None:
        lay.addWidget(_body_text(self._result.failure_message))
        lay.addWidget(_email_link(_SUPPORT_EMAIL))
        lay.addWidget(_divider())
        lay.addWidget(_section_label("Your Machine ID"))
        lay.addWidget(self._machine_id_box())
        self._copy_btn = _copy_button(self._machine_id, self)
        lay.addWidget(self._copy_btn)
        lay.addWidget(_divider())
        browse = _primary_button("Browse for License File")
        browse.clicked.connect(self._browse_for_license)
        lay.addWidget(browse)
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

        version_lbl = QLabel("BI CleanSheet 365 — Licensed software")
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
            self._show_activation_success(new_result)
        else:
            self._show_error(new_result.failure_message)

    def _show_activation_success(self, result) -> None:
        """Show a themed success dialog then accept the activation screen."""
        from core.license_validator import get_days_until_expiry
        days = get_days_until_expiry(result)
        expiry_str = str(result.expiry_date) if result.expiry_date else "Unknown"
        if days > 0:
            expiry_text = (
                f"Your license is active and valid for <b>{days} day{'s' if days != 1 else ''}</b>.<br>"
                f"Expiry date: {expiry_str}"
            )
        else:
            expiry_text = f"Your license has been activated. Expiry date: {expiry_str}"

        _show_themed_info(self, "License Activated", expiry_text)
        self.accept()

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



def _show_themed_info(parent, title: str, text: str) -> None:
    """Show a themed info dialog matching the msgbox style."""
    from PySide6.QtWidgets import QDialog, QHBoxLayout, QVBoxLayout

    _BG      = "#13161e"
    _SURFACE = "#0d1117"
    _BORDER  = "rgba(255,255,255,0.09)"
    _DIVIDER = "rgba(255,255,255,0.06)"
    _TEXT    = "#f1f5f9"
    _MUTED   = "#94a3b8"
    _STRIP_BG     = "rgba(59,130,246,0.06)"
    _STRIP_BORDER = "rgba(59,130,246,0.15)"
    _ICON_BG      = "rgba(59,130,246,0.12)"
    _ICON_BORDER  = "rgba(59,130,246,0.25)"
    _ICON_COLOR   = "#60a5fa"
    _BTN_BG       = "#3b82f6"
    _BTN_HOVER    = "#2563eb"

    dlg = QDialog(parent)
    dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
    dlg.setAttribute(Qt.WA_StyledBackground, True)
    dlg.setFixedWidth(460)
    dlg.setStyleSheet(
        f"QDialog {{ background: {_BG}; border: 1px solid {_BORDER}; border-radius: 12px; }}"
    )
    if parent:
        dlg.setWindowModality(Qt.ApplicationModal)

    root = QVBoxLayout(dlg)
    root.setContentsMargins(0, 0, 0, 0)
    root.setSpacing(0)

    card = QFrame()
    card.setStyleSheet(f"QFrame {{ background: {_BG}; border: none; border-radius: 12px; }}")
    c_lay = QVBoxLayout(card)
    c_lay.setContentsMargins(0, 0, 0, 0)
    c_lay.setSpacing(0)

    hdr = QFrame()
    hdr.setFixedHeight(64)
    hdr.setStyleSheet(
        f"QFrame {{ background: {_SURFACE}; border: none; "
        f"border-bottom: 1px solid {_DIVIDER}; "
        f"border-top-left-radius: 12px; border-top-right-radius: 12px; }}"
    )
    h_lay = QHBoxLayout(hdr)
    h_lay.setContentsMargins(20, 0, 20, 0)
    h_lay.setSpacing(12)

    icon_box = QFrame()
    icon_box.setFixedSize(32, 32)
    icon_box.setStyleSheet(
        f"QFrame {{ background: {_ICON_BG}; border: 1px solid {_ICON_BORDER}; border-radius: 8px; }}"
    )
    ib_lay = QHBoxLayout(icon_box)
    ib_lay.setContentsMargins(0, 0, 0, 0)
    icon_lbl = QLabel("✓")
    icon_lbl.setAlignment(Qt.AlignCenter)
    icon_lbl.setStyleSheet(
        f"color: {_ICON_COLOR}; font-size: 14px; font-weight: 700; background: transparent; border: none;"
    )
    ib_lay.addWidget(icon_lbl)
    h_lay.addWidget(icon_box)

    title_lbl = QLabel(title)
    title_lbl.setStyleSheet(
        f"color: {_TEXT}; font-size: 14px; font-weight: 600; background: transparent; border: none;"
    )
    h_lay.addWidget(title_lbl, 1)
    c_lay.addWidget(hdr)

    body = QFrame()
    body.setStyleSheet(f"QFrame {{ background: {_BG}; border: none; }}")
    b_lay = QVBoxLayout(body)
    b_lay.setContentsMargins(20, 16, 20, 16)

    strip = QFrame()
    strip.setStyleSheet(
        f"QFrame {{ background: {_STRIP_BG}; border: 1px solid {_STRIP_BORDER}; border-radius: 8px; }}"
    )
    s_lay = QHBoxLayout(strip)
    s_lay.setContentsMargins(14, 10, 14, 10)
    msg_lbl = QLabel(text)
    msg_lbl.setTextFormat(Qt.RichText)
    msg_lbl.setWordWrap(True)
    msg_lbl.setStyleSheet(f"color: {_MUTED}; font-size: 12px; background: transparent; border: none;")
    s_lay.addWidget(msg_lbl)
    b_lay.addWidget(strip)
    c_lay.addWidget(body, 1)

    footer = QFrame()
    footer.setFixedHeight(56)
    footer.setStyleSheet(
        f"QFrame {{ background: {_SURFACE}; border: none; "
        f"border-top: 1px solid {_DIVIDER}; "
        f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }}"
    )
    f_lay = QHBoxLayout(footer)
    f_lay.setContentsMargins(20, 0, 20, 0)
    f_lay.addStretch()

    ok_btn = QPushButton("Continue")
    ok_btn.setFixedHeight(34)
    ok_btn.setCursor(Qt.PointingHandCursor)
    ok_btn.setStyleSheet(
        f"QPushButton {{ background: {_BTN_BG}; border: none; border-radius: 7px; "
        f"color: #ffffff; font-size: 12px; font-weight: 500; padding: 0 20px; }}"
        f"QPushButton:hover {{ background: {_BTN_HOVER}; }}"
    )
    ok_btn.clicked.connect(dlg.accept)
    f_lay.addWidget(ok_btn)
    c_lay.addWidget(footer)
    root.addWidget(card)
    dlg.adjustSize()

    if parent:
        QTimer.singleShot(0, lambda: _centre_on_screen(dlg))

    dlg.exec()


def _centre_on_screen(dlg: QDialog) -> None:
    screen = QApplication.primaryScreen().availableGeometry()
    dlg.move(
        screen.center().x() - dlg.width() // 2,
        screen.center().y() - dlg.height() // 2,
    )
