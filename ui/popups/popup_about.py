"""About CleanSheet dialog — version, company, and support info."""
from __future__ import annotations

from PySide6.QtCore import Qt
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

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        title_lbl = QLabel(f"<b>{APP_NAME}</b>")
        title_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 16px; background: transparent; border: none;"
        )
        ver_lbl = QLabel(f"Version {APP_VERSION}")
        ver_lbl.setStyleSheet(
            "color: #3b82f6; font-size: 12px; background: transparent; border: none;"
        )
        title_col.addWidget(title_lbl)
        title_col.addWidget(ver_lbl)
        h_lay.addLayout(title_col, 1)
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

        b_lay.addLayout(_row("Publisher", COMPANY))
        b_lay.addLayout(_row("Version", APP_VERSION))
        b_lay.addLayout(_row("Support", "support@gd365.com"))

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
