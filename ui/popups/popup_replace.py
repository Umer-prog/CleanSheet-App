from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

import pandas as pd

import ui.theme as theme


def _format_dim_table(df: pd.DataFrame, max_rows: int = 200) -> str:
    """Return a pipe-separated text table for the dimension dataframe."""
    if df.empty:
        return "(No rows)"
    preview = df.head(max_rows).fillna("")
    cols = list(preview.columns)

    col_widths = {
        col: max(len(str(col)), max((len(str(v)) for v in preview[col]), default=0))
        for col in cols
    }

    def _row(values) -> str:
        return " | ".join(f"{str(v):<{col_widths[c]}}" for c, v in zip(cols, values))

    sep = "-+-".join("-" * col_widths[c] for c in cols)
    lines = [_row(cols), sep]
    for _, row_data in preview.iterrows():
        lines.append(_row([row_data[c] for c in cols]))
    return "\n".join(lines)


class PopupReplace(QDialog):
    """Modal popup for selecting a replacement value from dim values."""

    def __init__(
        self,
        parent,
        bad_value: str,
        valid_values: list[str],
        on_confirm,
        dim_df: pd.DataFrame | None = None,
        dim_table: str = "",
    ):
        super().__init__(parent)
        self._on_confirm = on_confirm
        self._valid_values = valid_values
        self._dim_df = dim_df
        self._dim_table = dim_table

        has_table = dim_df is not None and not dim_df.empty
        height = 580 if has_table else 440

        self.setWindowTitle("Replace Value")
        self.setFixedSize(580, height)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header(bad_value))
        root.addWidget(self._make_body(has_table), 1)
        root.addWidget(self._make_footer())

        self._combo: QComboBox  # set in _make_body

    # ------------------------------------------------------------------

    def _make_header(self, bad_value: str) -> QFrame:
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("QFrame { background-color: #3b82f6; }")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Replace Error Value")
        title.setFont(theme.font(18, "bold"))
        title.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(title)

        display = bad_value if bad_value else "(empty / null)"
        sub = QLabel(f"Current: {display}")
        sub.setFont(theme.font(11))
        sub.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(sub, 1)
        return header

    def _make_body(self, has_table: bool) -> QWidget:
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; }")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(20, 14, 20, 14)
        body_lay.setSpacing(8)

        if has_table:
            table_lbl = QLabel(f"Dimension Table — {self._dim_table}")
            table_lbl.setFont(theme.font(12, "bold"))
            table_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            body_lay.addWidget(table_lbl)

            table_box = QTextEdit()
            table_box.setReadOnly(True)
            mono = QFont("Courier New", 10)
            table_box.setFont(mono)
            table_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
            table_box.setStyleSheet(
                "QTextEdit { background-color: #0f1117; color: #94a3b8; border-radius: 6px; }"
            )
            table_box.setPlainText(_format_dim_table(self._dim_df))
            body_lay.addWidget(table_box, 1)

            divider = QFrame()
            divider.setFixedHeight(1)
            divider.setStyleSheet("background-color: #0f1117;")
            body_lay.addWidget(divider)

        select_lbl = QLabel("Select replacement value")
        select_lbl.setFont(theme.font(12, "bold"))
        select_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        body_lay.addWidget(select_lbl)

        self._combo = QComboBox()
        self._combo.setFixedHeight(38)
        values = self._valid_values or ["No Values Available"]
        self._combo.addItems(values)
        self._combo.setCurrentIndex(0)
        body_lay.addWidget(self._combo)

        if not has_table:
            body_lay.addStretch(1)

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

        replace_btn = QPushButton("Replace")
        replace_btn.setObjectName("btn_primary")
        replace_btn.setFixedSize(120, 38)
        replace_btn.clicked.connect(self._submit)
        lay.addWidget(replace_btn)

        return footer

    def _submit(self) -> None:
        selected = self._combo.currentText().strip()
        if not self._valid_values:
            self._error_lbl.setText("No valid values available.")
            return
        if not selected:
            self._error_lbl.setText("Select a replacement value.")
            return
        self._on_confirm(selected)
        self.accept()
