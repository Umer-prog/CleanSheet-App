from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout,
)


class PopupRevertConfirm(QDialog):
    """Confirmation popup before reverting to a selected manifest."""

    def __init__(self, parent, manifest_id: str, on_confirm):
        super().__init__(parent)
        self._on_confirm = on_confirm

        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setFixedSize(480, 260)
        self.setStyleSheet("QDialog { background: #13161e; border-radius: 12px; }")

        # Centre on parent
        if parent:
            pg = parent.window().geometry()
            self.move(
                pg.x() + (pg.width()  - self.width())  // 2,
                pg.y() + (pg.height() - self.height()) // 2,
            )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #13161e; "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        card_lay.addWidget(self._build_header(manifest_id))
        card_lay.addWidget(self._build_body(manifest_id), 1)
        card_lay.addWidget(self._build_footer())

        root.addWidget(card)

    # ------------------------------------------------------------------

    def _build_header(self, manifest_id: str) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(64)
        hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(12)

        icon_box = QFrame()
        icon_box.setFixedSize(34, 34)
        icon_box.setStyleSheet(
            "QFrame { background: rgba(239,68,68,0.10); "
            "border: 1px solid rgba(239,68,68,0.22); border-radius: 8px; }"
        )
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("↩")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #f87171; font-size: 16px; background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel("Confirm Revert")
        title.setStyleSheet(
            "color: #f1f5f9; font-size: 14px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        text_col.addWidget(title)
        sub = QLabel(
            f"Snapshot: <span style='color:#60a5fa; font-family:\"Courier New\";'>"
            f"{manifest_id}</span>"
        )
        sub.setTextFormat(Qt.RichText)
        sub.setStyleSheet(
            "color: #475569; font-size: 11px; background: transparent; border: none;"
        )
        text_col.addWidget(sub)
        lay.addLayout(text_col, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); "
            "border-radius: 6px; color: #64748b; font-size: 11px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); color: #94a3b8; }"
        )
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return hdr

    def _build_body(self, manifest_id: str) -> QFrame:
        body = QFrame()
        body.setStyleSheet("QFrame { background: transparent; border: none; }")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(22, 20, 22, 20)
        lay.setSpacing(12)

        # Warning strip
        strip = QFrame()
        strip.setStyleSheet(
            "QFrame { background: rgba(239,68,68,0.06); "
            "border: 1px solid rgba(239,68,68,0.15); border-radius: 8px; }"
        )
        sl = QHBoxLayout(strip)
        sl.setContentsMargins(14, 10, 14, 10)
        sl.setSpacing(10)
        warn_icon = QLabel("⚠")
        warn_icon.setStyleSheet(
            "color: #f87171; font-size: 13px; background: transparent; border: none;"
        )
        sl.addWidget(warn_icon)
        warn_text = QLabel(
            "This will restore transaction data to the selected snapshot.\n"
            "Newer snapshots will remain in history but data will be rolled back."
        )
        warn_text.setWordWrap(True)
        warn_text.setStyleSheet(
            "color: #94a3b8; font-size: 12px; background: transparent; border: none;"
        )
        sl.addWidget(warn_text, 1)
        lay.addWidget(strip)
        lay.addStretch()
        return body

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(8)
        lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); "
            "border-radius: 7px; color: #94a3b8; font-size: 12px; padding: 0 16px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); }"
        )
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

        revert_btn = QPushButton("Revert")
        revert_btn.setFixedHeight(34)
        revert_btn.setStyleSheet(
            "QPushButton { background: rgba(239,68,68,0.12); "
            "border: 1px solid rgba(239,68,68,0.3); "
            "border-radius: 7px; color: #f87171; font-size: 12px; "
            "font-weight: 500; padding: 0 20px; }"
            "QPushButton:hover { background: rgba(239,68,68,0.2); }"
        )
        revert_btn.clicked.connect(self._confirm)
        lay.addWidget(revert_btn)

        return footer

    def _confirm(self) -> None:
        self._on_confirm()
        self.accept()
