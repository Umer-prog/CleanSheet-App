"""About CleanSheet dialog — version, company, and support info."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from core.constants import APP_NAME, APP_VERSION, COMPANY
from core.app_logger import get_log_file_path


class PopupAbout(QDialog):
    """Modal About dialog showing version and support information."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setFixedSize(420, 300)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("QDialog { background: #13161e; border-radius: 12px; }")

        if parent:
            self.setWindowModality(Qt.ApplicationModal)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────
        header = QWidget()
        header.setFixedHeight(72)
        header.setAttribute(Qt.WA_StyledBackground, True)
        header.setStyleSheet(
            "QWidget { background: #0d1117; border-bottom: 1px solid rgba(255,255,255,0.06); "
            "border-top-left-radius: 12px; border-top-right-radius: 12px; }"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(24, 0, 24, 0)

        title_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:16px; font-weight:600;'>{APP_NAME}</span>"
            f"<br><span style='color:#3b82f6; font-size:12px;'>Version {APP_VERSION}</span>"
        )
        title_lbl.setTextFormat(Qt.RichText)
        title_lbl.setStyleSheet("background: transparent; border: none;")
        h_lay.addWidget(title_lbl, 1)
        outer.addWidget(header)

        # ── Body ──────────────────────────────────────────────────────────
        body = QWidget()
        body.setAttribute(Qt.WA_StyledBackground, True)
        body.setStyleSheet("QWidget { background: #13161e; }")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(24, 20, 24, 20)
        b_lay.setSpacing(8)

        def _row(label: str, value: str) -> QHBoxLayout:
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setFixedWidth(80)
            lbl.setStyleSheet(
                "color: #cbd5e1; font-size: 11px; font-weight: 600; "
                "background: transparent; border: none;"
            )
            val = QLabel(value)
            val.setWordWrap(True)
            val.setStyleSheet(
                "color: #94a3b8; font-size: 12px; background: transparent; border: none;"
            )
            row.addWidget(lbl)
            row.addWidget(val, 1)
            return row

        _SUPPORT_EMAIL = "support@globaldata365.com"

        b_lay.addLayout(_row("Publisher", COMPANY))
        b_lay.addLayout(_row("Version", APP_VERSION))

        support_row = QHBoxLayout()
        support_key = QLabel("Support")
        support_key.setFixedWidth(80)
        support_key.setStyleSheet(
            "color: #cbd5e1; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        support_val = QLabel(_SUPPORT_EMAIL)
        support_val.setStyleSheet(
            "color: #94a3b8; font-size: 12px; background: transparent; border: none;"
        )
        copy_btn = QPushButton("Copy")
        copy_btn.setFixedSize(48, 22)
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setStyleSheet(
            "QPushButton { background: rgba(59,130,246,0.12); border: 1px solid rgba(59,130,246,0.25); "
            "border-radius: 5px; color: #60a5fa; font-size: 10px; font-weight: 600; padding: 0; }"
            "QPushButton:hover { background: rgba(59,130,246,0.22); color: #93c5fd; }"
            "QPushButton:pressed { background: rgba(59,130,246,0.32); }"
        )

        def _copy_email(_checked=False, btn=copy_btn, email=_SUPPORT_EMAIL):
            QGuiApplication.clipboard().setText(email)
            btn.setText("Copied!")
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1500, lambda: btn.setText("Copy"))

        copy_btn.clicked.connect(_copy_email)
        support_row.addWidget(support_key)
        support_row.addWidget(support_val, 1)
        support_row.addWidget(copy_btn)
        b_lay.addLayout(support_row)

        log_path = get_log_file_path()
        log_str = str(log_path) if log_path else "Not available"
        b_lay.addLayout(_row("Log file", log_str))

        b_lay.addStretch(1)
        outer.addWidget(body, 1)

        # ── Footer ────────────────────────────────────────────────────────
        footer = QWidget()
        footer.setFixedHeight(56)
        footer.setAttribute(Qt.WA_StyledBackground, True)
        footer.setStyleSheet(
            "QWidget { background: #0d1117; border-top: 1px solid rgba(255,255,255,0.06); "
            "border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(24, 0, 24, 0)

        copy_lbl = QLabel(f"© 2025 {COMPANY}")
        copy_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
        )
        f_lay.addWidget(copy_lbl, 1)

        close_btn = QPushButton("Close")
        close_btn.setFixedSize(80, 32)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; border: none; border-radius: 7px; "
            "color: white; font-size: 12px; font-weight: 500; }"
            "QPushButton:hover { background: #2563eb; }"
        )
        close_btn.clicked.connect(self.accept)
        f_lay.addWidget(close_btn)
        outer.addWidget(footer)

        if parent:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(50, self.raise_)
