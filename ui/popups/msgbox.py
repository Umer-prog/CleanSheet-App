from __future__ import annotations

import subprocess

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout,
)

from core.app_logger import get_log_file_path

# ── Colour tokens ──────────────────────────────────────────────────────────────
_BG       = "#13161e"
_SURFACE  = "#0d1117"
_BORDER   = "rgba(255,255,255,0.09)"
_DIVIDER  = "rgba(255,255,255,0.06)"
_TEXT     = "#f1f5f9"
_MUTED    = "#94a3b8"

# Semantic accent sets  (icon_hex, icon_bg, icon_border, strip_bg, strip_border,
#                        confirm_bg, confirm_border, confirm_text, confirm_hover)
_ACCENT = {
    "critical": (
        "#f87171",
        "rgba(239,68,68,0.12)", "rgba(239,68,68,0.25)",
        "rgba(239,68,68,0.06)", "rgba(239,68,68,0.15)",
        "rgba(239,68,68,0.14)", "rgba(239,68,68,0.35)",
        "#f87171", "rgba(239,68,68,0.25)",
    ),
    "warning": (
        "#fbbf24",
        "rgba(217,119,6,0.12)", "rgba(217,119,6,0.25)",
        "rgba(217,119,6,0.06)", "rgba(217,119,6,0.15)",
        "rgba(217,119,6,0.14)", "rgba(217,119,6,0.35)",
        "#fbbf24", "rgba(217,119,6,0.25)",
    ),
    "info": (
        "#60a5fa",
        "rgba(59,130,246,0.12)", "rgba(59,130,246,0.25)",
        "rgba(59,130,246,0.06)", "rgba(59,130,246,0.15)",
        "#3b82f6", "#2563eb",
        "#ffffff", "#2563eb",
    ),
}

_ICONS = {
    "critical": "✕",
    "warning":  "⚠",
    "info":     "ℹ",
    "question": "?",
}


def _btn_cancel() -> str:
    return (
        "QPushButton { background: rgba(255,255,255,0.04); "
        "border: 1px solid rgba(255,255,255,0.09); border-radius: 7px; "
        f"color: {_MUTED}; font-size: 12px; padding: 0 18px; }}"
        "QPushButton:hover { background: rgba(255,255,255,0.09); color: #f1f5f9; }"
    )


def _btn_confirm(kind: str) -> str:
    a = _ACCENT[kind]
    confirm_bg, confirm_border, confirm_text, confirm_hover = a[5], a[6], a[7], a[8]
    return (
        f"QPushButton {{ background: {confirm_bg}; border: 1px solid {confirm_border}; "
        f"border-radius: 7px; color: {confirm_text}; font-size: 12px; "
        f"font-weight: 500; padding: 0 20px; }}"
        f"QPushButton:hover {{ background: {confirm_hover}; }}"
    )


class _MsgDialog(QDialog):
    """Shared base for all custom message dialogs."""

    def __init__(
        self,
        parent,
        kind: str,          # "critical" | "warning" | "info"
        icon_char: str,
        title: str,
        text: str,
        buttons: list[tuple[str, str]],  # [(label, role), ...] role: "confirm"|"cancel"|"help"
        default_role: str = "cancel",
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(460)
        self.setStyleSheet(
            f"QDialog {{ background: {_BG}; border: 1px solid {_BORDER}; border-radius: 12px; }}"
        )
        if parent:
            self.setWindowModality(Qt.ApplicationModal)

        self._result_role: str = default_role
        accent = _ACCENT[kind]

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {_BG}; border: none; border-radius: 12px; }}"
        )
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
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
            f"QFrame {{ background: {accent[1]}; border: 1px solid {accent[2]}; "
            f"border-radius: 8px; }}"
        )
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon_char)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"color: {accent[0]}; font-size: 14px; font-weight: 700; "
            f"background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        h_lay.addWidget(icon_box)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {_TEXT}; font-size: 14px; font-weight: 600; "
            f"background: transparent; border: none;"
        )
        h_lay.addWidget(title_lbl, 1)
        c_lay.addWidget(hdr)

        # ── Body ──────────────────────────────────────────────────────────
        body = QFrame()
        body.setStyleSheet(f"QFrame {{ background: {_BG}; border: none; }}")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(20, 16, 20, 16)
        b_lay.setSpacing(10)

        strip = QFrame()
        strip.setStyleSheet(
            f"QFrame {{ background: {accent[3]}; border: 1px solid {accent[4]}; "
            f"border-radius: 8px; }}"
        )
        s_lay = QHBoxLayout(strip)
        s_lay.setContentsMargins(14, 10, 14, 10)
        s_lay.setSpacing(0)

        msg_lbl = QLabel(text)
        msg_lbl.setTextFormat(Qt.RichText)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        s_lay.addWidget(msg_lbl)
        b_lay.addWidget(strip)
        c_lay.addWidget(body, 1)

        # ── Footer ────────────────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            f"QFrame {{ background: {_SURFACE}; border: none; "
            f"border-top: 1px solid {_DIVIDER}; "
            f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }}"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(20, 0, 20, 0)
        f_lay.setSpacing(8)
        f_lay.addStretch()

        for label, role in buttons:
            btn = QPushButton(label)
            btn.setFixedHeight(34)
            btn.setCursor(Qt.PointingHandCursor)
            if role == "cancel":
                btn.setStyleSheet(_btn_cancel())
            elif role == "confirm":
                btn.setStyleSheet(_btn_confirm(kind))
            elif role == "help":
                btn.setStyleSheet(_btn_cancel())

            def _make_handler(r):
                def _handler():
                    self._result_role = r
                    if r in ("confirm", "help"):
                        self.accept()
                    else:
                        self.reject()
                return _handler

            btn.clicked.connect(_make_handler(role))
            f_lay.addWidget(btn)

        c_lay.addWidget(footer)
        root.addWidget(card)

        self.adjustSize()

        if parent:
            QTimer.singleShot(0, self._centre_on_parent)
            QTimer.singleShot(50, self.raise_)

    def _centre_on_parent(self) -> None:
        p = self.parent()
        if p is None:
            return
        pg = p.window().geometry()
        self.move(
            pg.x() + (pg.width()  - self.width())  // 2,
            pg.y() + (pg.height() - self.height()) // 2,
        )

    def result_role(self) -> str:
        return self._result_role


# ── Public API ─────────────────────────────────────────────────────────────────

def question(parent, title: str, text: str, buttons, default=None) -> int:
    """Confirmation dialog — returns QMessageBox button value for Yes/No comparisons."""
    from PySide6.QtWidgets import QMessageBox

    dlg = _MsgDialog(
        parent, "info", _ICONS["question"], title, text,
        buttons=[("Cancel", "cancel"), ("Confirm", "confirm")],
        default_role="cancel",
    )
    dlg.exec()
    if dlg.result_role() == "confirm":
        return int(QMessageBox.Yes)
    return int(QMessageBox.No)


def critical(parent, title: str, text: str) -> int:
    dlg = _MsgDialog(
        parent, "critical", _ICONS["critical"], title, text,
        buttons=[("OK", "confirm")],
        default_role="confirm",
    )
    return dlg.exec()


def critical_with_log(parent, title: str, text: str) -> int:
    """Critical error dialog with an 'Open Log Folder' button for support."""
    log_path = get_log_file_path()
    buttons = []
    if log_path and log_path.exists():
        buttons.append(("Open Log Folder", "help"))
    buttons.append(("OK", "confirm"))

    dlg = _MsgDialog(
        parent, "critical", _ICONS["critical"], title, text,
        buttons=buttons,
        default_role="confirm",
    )
    result = dlg.exec()
    if dlg.result_role() == "help":
        subprocess.Popen(["explorer", "/select,", str(log_path)])
    return result


def warning_question(parent, title: str, text: str,
                     confirm_label: str = "Continue",
                     cancel_label: str = "Cancel") -> bool:
    """Warning dialog with two custom action buttons. Returns True if confirmed."""
    dlg = _MsgDialog(
        parent, "warning", _ICONS["warning"], title, text,
        buttons=[(cancel_label, "cancel"), (confirm_label, "confirm")],
        default_role="cancel",
    )
    dlg.exec()
    return dlg.result_role() == "confirm"


def warning(parent, title: str, text: str) -> int:
    dlg = _MsgDialog(
        parent, "warning", _ICONS["warning"], title, text,
        buttons=[("OK", "confirm")],
        default_role="confirm",
    )
    return dlg.exec()


def information(parent, title: str, text: str,
                buttons=None, default=None) -> int:
    from PySide6.QtWidgets import QMessageBox

    # Detect if caller passed Yes|No buttons (used in screen3_main orphan check)
    if buttons is not None and buttons != QMessageBox.StandardButton.Ok:
        dlg = _MsgDialog(
            parent, "info", _ICONS["info"], title, text,
            buttons=[("Later", "cancel"), ("View Now", "confirm")],
            default_role="cancel",
        )
        dlg.exec()
        if dlg.result_role() == "confirm":
            return int(QMessageBox.Yes)
        return int(QMessageBox.No)

    dlg = _MsgDialog(
        parent, "info", _ICONS["info"], title, text,
        buttons=[("OK", "confirm")],
        default_role="confirm",
    )
    return dlg.exec()
