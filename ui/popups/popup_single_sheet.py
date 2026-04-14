from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QVBoxLayout,
)

import ui.theme as theme


class PopupSingleSheet(QDialog):
    """Modal popup for selecting one sheet from an Excel file."""

    def __init__(
        self,
        parent,
        excel_path: Path,
        sheet_names: list[str],
        title: str = "Select Sheet",
    ):
        super().__init__(parent)
        self._result: str | None = None
        self._sheet_names = sheet_names

        self.setWindowTitle(title)
        self.setFixedSize(520, 280)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header(title, Path(excel_path).name))
        root.addWidget(self._make_body(), 1)
        root.addWidget(self._make_footer())

    @property
    def result(self) -> str | None:  # type: ignore[override]
        return self._result

    # ------------------------------------------------------------------

    def _make_header(self, title: str, file_name: str) -> QFrame:
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("QFrame { background-color: #3b82f6; }")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(24, 0, 24, 0)

        title_lbl = QLabel(title)
        title_lbl.setFont(theme.font(18, "bold"))
        title_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(title_lbl)

        sub = QLabel(file_name)
        sub.setFont(theme.font(11))
        sub.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(sub, 1)
        return header

    def _make_body(self) -> QFrame:
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; }")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(8)

        lbl = QLabel("Choose a sheet")
        lbl.setFont(theme.font(12, "bold"))
        lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.setFixedHeight(38)
        values = self._sheet_names if self._sheet_names else ["No sheets found"]
        self._combo.addItems(values)
        self._combo.setCurrentIndex(0)
        lay.addWidget(self._combo)

        lay.addStretch(1)
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

        ok_btn = QPushButton("OK")
        ok_btn.setObjectName("btn_primary")
        ok_btn.setFixedSize(100, 38)
        ok_btn.clicked.connect(self._on_ok)
        lay.addWidget(ok_btn)

        return footer

    def _on_ok(self) -> None:
        if not self._sheet_names:
            self._error_lbl.setText("No sheets available in this file.")
            return
        choice = self._combo.currentText().strip()
        if not choice:
            self._error_lbl.setText("Select a sheet.")
            return
        self._result = choice
        self.accept()


def select_single_sheet(
    parent,
    excel_path: Path,
    sheet_names: list[str],
    title: str = "Select Sheet",
) -> str | None:
    """Open the single sheet picker and return the selected sheet name, or None."""
    dialog = PopupSingleSheet(parent, excel_path=excel_path, sheet_names=sheet_names, title=title)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.result
    return None
