from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QVBoxLayout,
)

import ui.theme as theme

_ARROW_PATH = Path(tempfile.gettempdir()) / "_cs_combo_arrow_ss.svg"
_ARROW_PATH.write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6">'
    '<polyline points="1,1 5,5 9,1" fill="none" stroke="#64748b" '
    'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>",
    encoding="utf-8",
)
_ARROW_URL = str(_ARROW_PATH).replace("\\", "/")


class PopupSingleSheet(QDialog):
    """Modal popup for selecting one sheet from an Excel file."""

    def __init__(
        self,
        parent,
        excel_path: Path,
        sheet_names: list[str],
        title: str = "Select Sheet",
        default_sheet: str | None = None,
    ):
        super().__init__(parent)
        self._result: dict | None = None
        self._sheet_names = sheet_names
        self._excel_path = Path(excel_path)
        self._file_name = self._excel_path.name
        self._default_sheet = default_sheet

        self.setWindowTitle(title)
        self.setFixedSize(480, 330)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setStyleSheet("QDialog { background: #13161e; border-radius: 12px; }")

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

        card_lay.addWidget(self._build_header(title))
        card_lay.addWidget(self._build_body(), 1)
        card_lay.addWidget(self._build_footer())

        root.addWidget(card)

    @property
    def result(self) -> dict | None:  # type: ignore[override]
        return self._result

    # ------------------------------------------------------------------

    def _build_header(self, title: str) -> QFrame:
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
            "QFrame { background: rgba(59,130,246,0.12); "
            "border: 1px solid rgba(59,130,246,0.25); border-radius: 8px; }"
        )
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("⊞")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #60a5fa; font-size: 15px; background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        title_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:14px; font-weight:600;'>{title}</span>"
            "<br>"
            f"<span style='color:#60a5fa; font-size:11px; font-family:Courier New,monospace;'>"
            f"{self._file_name}</span>"
        )
        title_lbl.setTextFormat(Qt.RichText)
        title_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(title_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); "
            "border: 1px solid rgba(255,255,255,0.14); border-radius: 6px; "
            "color: #94a3b8; font-size: 12px; padding: 0; }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); color: #f87171; }"
        )
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return hdr

    def _build_body(self) -> QFrame:
        body = QFrame()
        body.setStyleSheet("QFrame { background: transparent; border: none; }")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(22, 18, 22, 18)
        lay.setSpacing(8)

        col_lbl = QLabel("SHEET")
        col_lbl.setStyleSheet(
            "color: #475569; font-size: 10px; font-weight: 600; "
            "letter-spacing: 0.7px; background: transparent; border: none;"
        )
        lay.addWidget(col_lbl)

        self._combo = QComboBox()
        self._combo.setFixedHeight(38)
        self._combo.setStyleSheet(
            "QComboBox { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); "
            "border-radius: 7px; color: #f1f5f9; font-size: 13px; "
            "font-family: 'Segoe UI'; padding: 0 12px; }"
            "QComboBox:focus { border-color: rgba(59,130,246,0.5); }"
            "QComboBox::drop-down { border: none; width: 28px; "
            "subcontrol-origin: padding; subcontrol-position: right center; }"
            f"QComboBox::down-arrow {{ image: url({_ARROW_URL}); width: 10px; height: 6px; }}"
            "QComboBox QAbstractItemView { background: #13161e; color: #f1f5f9; "
            "border: 1px solid rgba(255,255,255,0.09); "
            "selection-background-color: rgba(59,130,246,0.18); outline: none; }"
        )
        values = self._sheet_names if self._sheet_names else ["No sheets found"]
        self._combo.addItems(values)
        if self._default_sheet and self._default_sheet in values:
            self._combo.setCurrentIndex(values.index(self._default_sheet))
        else:
            self._combo.setCurrentIndex(0)
        lay.addWidget(self._combo)

        hdr_lbl = QLabel("HEADER ROW")
        hdr_lbl.setStyleSheet(
            "color: #475569; font-size: 10px; font-weight: 600; "
            "letter-spacing: 0.7px; background: transparent; border: none;"
        )
        lay.addWidget(hdr_lbl)

        self._spinbox = QSpinBox()
        self._spinbox.setRange(1, 100)
        self._spinbox.setFixedHeight(38)
        self._spinbox.setStyleSheet(
            "QSpinBox { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); "
            "border-radius: 7px; color: #f1f5f9; font-size: 13px; "
            "font-family: 'Segoe UI'; padding: 0 12px; }"
            "QSpinBox:focus { border-color: rgba(59,130,246,0.5); }"
            "QSpinBox::up-button, QSpinBox::down-button { width: 18px; border: none; "
            "background: transparent; }"
        )
        lay.addWidget(self._spinbox)

        # Auto-detect header row for the initially selected sheet
        self._update_header_spinbox()
        self._combo.currentIndexChanged.connect(self._update_header_spinbox)

        lay.addStretch(1)
        return body

    def _update_header_spinbox(self) -> None:
        sheet = self._combo.currentText().strip()
        if not sheet or not self._excel_path.exists():
            return
        try:
            from core.data_loader import detect_header_row
            detected = detect_header_row(self._excel_path, sheet)
            self._spinbox.setValue(detected)
        except Exception:
            self._spinbox.setValue(1)

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

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            "color: #f87171; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(self._error_lbl, 1)

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

        ok_btn = QPushButton("Select Sheet")
        ok_btn.setFixedHeight(34)
        ok_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; border: none; border-radius: 7px; "
            "color: #fff; font-size: 12px; font-weight: 500; padding: 0 18px; }"
            "QPushButton:hover { background: #2563eb; }"
        )
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
        self._result = {"sheet_name": choice, "header_row": self._spinbox.value()}
        self.accept()


def select_single_sheet(
    parent,
    excel_path: Path,
    sheet_names: list[str],
    title: str = "Select Sheet",
    default_sheet: str | None = None,
) -> dict | None:
    """Open the single sheet picker and return the selected sheet name, or None."""
    dialog = PopupSingleSheet(
        parent, excel_path=excel_path, sheet_names=sheet_names,
        title=title, default_sheet=default_sheet,
    )
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.result
    return None
