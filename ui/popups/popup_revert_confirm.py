from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout,
)

import ui.theme as theme


class PopupRevertConfirm(QDialog):
    """Confirmation popup before reverting to a selected manifest."""

    def __init__(self, parent, manifest_id: str, on_confirm):
        super().__init__(parent)
        self._on_confirm = on_confirm

        self.setWindowTitle("Confirm Revert")
        self.setFixedSize(520, 300)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header(manifest_id))
        root.addWidget(self._make_body(manifest_id), 1)
        root.addWidget(self._make_footer())

    # ------------------------------------------------------------------

    def _make_header(self, manifest_id: str) -> QFrame:
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("QFrame { background-color: #3b82f6; }")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Revert Confirmation")
        title.setFont(theme.font(18, "bold"))
        title.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(title)

        sub = QLabel(manifest_id)
        sub.setFont(theme.font(11))
        sub.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(sub, 1)
        return header

    def _make_body(self, manifest_id: str) -> QFrame:
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; }")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 20, 24, 20)

        msg = QLabel(
            f"Revert current transaction data to '{manifest_id}'?\n\n"
            "This will restore files in data/transactions from the selected manifest.\n"
            "Newer manifests will remain in history."
        )
        msg.setFont(theme.font(13))
        msg.setStyleSheet("color: #f1f5f9; background: transparent;")
        msg.setWordWrap(True)
        lay.addWidget(msg)
        lay.addStretch(1)
        return body

    def _make_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(68)
        footer.setStyleSheet("QFrame { background-color: #13161e; border-top: 1px solid #0f1117; }")
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(8)

        lay.addStretch(1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_outline")
        cancel_btn.setFixedSize(100, 38)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

        revert_btn = QPushButton("Revert")
        revert_btn.setObjectName("btn_primary")
        revert_btn.setFixedSize(120, 38)
        revert_btn.clicked.connect(self._confirm)
        lay.addWidget(revert_btn)

        return footer

    def _confirm(self) -> None:
        self._on_confirm()
        self.accept()
