from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme


class PopupAdd(QDialog):
    """Modal popup to add a new row to a dim table."""

    def __init__(
        self,
        parent,
        dim_table: str,
        dim_columns: list[str],
        mapped_column: str,
        bad_value: str,
        on_confirm,
    ):
        super().__init__(parent)
        self._dim_columns = dim_columns
        self._mapped_column = mapped_column
        self._bad_value = bad_value
        self._on_confirm = on_confirm
        self._entries: dict[str, QLineEdit] = {}

        # Height grows with number of columns, capped at 600
        height = min(600, 160 + len(dim_columns) * 74)
        self.setWindowTitle("Add To Dimension")
        self.setFixedSize(520, height)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header(dim_table))
        root.addWidget(self._make_body(), 1)
        root.addWidget(self._make_footer())

    # ------------------------------------------------------------------

    def _make_header(self, dim_table: str) -> QFrame:
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("QFrame { background-color: #3b82f6; }")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Add New Dimension Row")
        title.setFont(theme.font(18, "bold"))
        title.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(title)

        sub = QLabel(f"Table: {dim_table}")
        sub.setFont(theme.font(11))
        sub.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(sub, 1)
        return header

    def _make_body(self) -> QWidget:
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; }")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 12, 16, 12)
        body_lay.setSpacing(0)

        # Scrollable field area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        fields_lay = QVBoxLayout(container)
        fields_lay.setContentsMargins(4, 4, 4, 4)
        fields_lay.setSpacing(6)
        fields_lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        for col in self._dim_columns:
            lbl = QLabel(col)
            lbl.setFont(theme.font(12, "bold"))
            lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            fields_lay.addWidget(lbl)

            entry = QLineEdit()
            entry.setFixedHeight(38)
            entry.setPlaceholderText(f"Enter {col}")
            if col == self._mapped_column:
                entry.setText(self._bad_value)
            fields_lay.addWidget(entry)
            self._entries[col] = entry

        scroll.setWidget(container)
        body_lay.addWidget(scroll, 1)
        return body

    def _make_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(68)
        footer.setStyleSheet("QFrame { background-color: #13161e; border-top: 1px solid #0f1117; }")
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(24, 0, 24, 0)
        lay.setSpacing(8)

        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(11))
        self._error_lbl.setStyleSheet("color: #f87171; background: transparent;")
        lay.addWidget(self._error_lbl, 1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_outline")
        cancel_btn.setFixedSize(100, 38)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

        add_btn = QPushButton("Add Row")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedSize(120, 38)
        add_btn.clicked.connect(self._submit)
        lay.addWidget(add_btn)

        return footer

    def _submit(self) -> None:
        row: dict[str, str] = {}
        for col, entry in self._entries.items():
            value = entry.text().strip()
            if not value:
                self._error_lbl.setText("All fields are required.")
                return
            row[col] = value

        self._on_confirm(row)
        self.accept()
