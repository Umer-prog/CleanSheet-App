from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme


class PopupSheetSelector(QDialog):
    """Modal popup that lets the user select sheets and set a category for each."""

    CATEGORY_VALUES = ["Select Category", "Transaction", "Dimension"]

    def __init__(self, parent, excel_path: Path, sheet_names: list[str]):
        super().__init__(parent)
        self._result: list[dict] | None = None
        self._rows: list[dict] = []
        self._excel_path = Path(excel_path)

        self.setWindowTitle("Select Sheets")
        self.setFixedSize(520, 460)
        self.setModal(True)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_body(sheet_names), 1)
        root.addWidget(self._make_footer())

    @property
    def result(self) -> list[dict] | None:  # type: ignore[override]
        return self._result

    # ------------------------------------------------------------------

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("QFrame { background-color: #3b82f6; }")
        lay = QHBoxLayout(header)
        lay.setContentsMargins(24, 0, 24, 0)

        title = QLabel("Select Sheets")
        title.setFont(theme.font(18, "bold"))
        title.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(title)

        sub = QLabel(self._excel_path.name)
        sub.setFont(theme.font(11))
        sub.setStyleSheet("color: #f1f5f9; background: transparent;")
        lay.addWidget(sub, 1)
        return header

    def _make_body(self, sheet_names: list[str]) -> QWidget:
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; }")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 12, 16, 12)
        body_lay.setSpacing(8)

        lbl = QLabel("Choose sheets and category")
        lbl.setFont(theme.font(12, "bold"))
        lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        body_lay.addWidget(lbl)

        # Scroll area for sheet rows
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        for sheet_name in sheet_names:
            self._rows.append(self._build_sheet_row(sheet_name))

        scroll.setWidget(container)
        body_lay.addWidget(scroll, 1)
        return body

    def _build_sheet_row(self, sheet_name: str) -> dict:
        row = QFrame()
        row.setStyleSheet("QFrame { background-color: #0f1117; border-radius: 8px; }")
        row_lay = QHBoxLayout(row)
        row_lay.setContentsMargins(12, 8, 12, 8)
        row_lay.setSpacing(12)

        checkbox = QCheckBox(sheet_name)
        checkbox.setFont(theme.font(12))
        checkbox.setStyleSheet("color: #f1f5f9; background: transparent;")
        row_lay.addWidget(checkbox, 1)

        combo = QComboBox()
        combo.addItems(self.CATEGORY_VALUES)
        combo.setCurrentIndex(0)
        combo.setFixedWidth(160)
        combo.setFixedHeight(32)
        combo.setVisible(False)
        row_lay.addWidget(combo)

        checkbox.stateChanged.connect(lambda state, c=combo: c.setVisible(state == Qt.CheckState.Checked.value))

        self._list_layout.addWidget(row)
        return {"sheet_name": sheet_name, "checkbox": checkbox, "combo": combo}

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
        selections = []
        for row in self._rows:
            if not row["checkbox"].isChecked():
                continue
            category = row["combo"].currentText().strip()
            if category not in ("Transaction", "Dimension"):
                self._error_lbl.setText("Please choose a category for each selected sheet.")
                return
            selections.append({"sheet_name": row["sheet_name"], "category": category})

        if not selections:
            self._error_lbl.setText("Select at least one sheet.")
            return

        self._result = selections
        QDialog.accept(self)


def select_sheets(parent, excel_path: Path, sheet_names: list[str]) -> list[dict] | None:
    """Open the sheet selector popup and return selected rows, or None if cancelled."""
    dialog = PopupSheetSelector(parent, excel_path=excel_path, sheet_names=sheet_names)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.result
    return None
