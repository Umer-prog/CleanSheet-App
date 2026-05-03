from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import (
    QDialog, QFrame, QGraphicsOpacityEffect, QHBoxLayout,
    QLabel, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import _find_header_row


class PopupSheetSelector(QDialog):
    """Modal dialog — select sheets and assign Transaction / Dimension category."""

    def __init__(self, parent, excel_path: Path, sheet_names: list[str]):
        super().__init__(parent)
        self._result: list[dict] | None = None
        self._rows: list[dict] = []
        self._excel_path = Path(excel_path)

        # Pre-detect header rows for all sheets (fast — scans max 20 rows each)
        self._detected_header_rows: dict[str, int] = {}
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(excel_path), data_only=True, read_only=True)
            for name in sheet_names:
                if name in wb.sheetnames:
                    self._detected_header_rows[name] = _find_header_row(wb[name])
            wb.close()
        except Exception:
            pass

        self.setWindowTitle("Select Sheets")
        self.setFixedWidth(720)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        # Height is auto — capped via max-height logic below

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_header())
        root.addWidget(self._make_body(sheet_names), 1)
        root.addWidget(self._make_footer())

    # ── Header ────────────────────────────────────────────────────────

    def _make_header(self) -> QFrame:
        header = QFrame()
        header.setFixedHeight(70)
        header.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(header)
        lay.setContentsMargins(22, 0, 18, 0)
        lay.setSpacing(12)

        # Icon box
        icon_box = QFrame()
        icon_box.setFixedSize(34, 34)
        icon_box.setStyleSheet(
            "QFrame { background: #3b82f6; border-radius: 8px; border: none; }"
        )
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("▦")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: white; background: transparent; border: none; font-size: 14px;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        # Title + filename
        title_lbl = QLabel(
            "<span style='color:#f1f5f9; font-size:14px; font-weight:600;'>Select Sheets</span>"
            "<br>"
            f"<span style='color:#3b82f6; font-size:11px; font-family:Courier New,monospace;'>"
            f"{self._excel_path.name}</span>"
        )
        title_lbl.setTextFormat(Qt.RichText)
        title_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(title_lbl, 1)

        # Close button
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
        return header

    # ── Body ──────────────────────────────────────────────────────────

    def _make_body(self, sheet_names: list[str]) -> QWidget:
        body = QFrame()
        body.setStyleSheet("QFrame { background: #0f1117; border: none; }")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(22, 18, 22, 8)
        body_lay.setSpacing(12)

        section_lbl = QLabel("CHOOSE SHEETS AND ASSIGN CATEGORY")
        section_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        body_lay.addWidget(section_lbl)

        # Scroll area for sheet rows (max visible height ~360px)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setMaximumHeight(360)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.setAlignment(Qt.AlignTop)

        for sheet_name in sheet_names:
            row_data = self._build_sheet_row(sheet_name)
            self._rows.append(row_data)

        scroll.setWidget(container)
        body_lay.addWidget(scroll)
        return body

    def _build_sheet_row(self, sheet_name: str) -> dict:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; }"
        )
        rl = QHBoxLayout(row)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.setSpacing(12)

        # Custom checkbox frame
        chk_frame = QFrame()
        chk_frame.setFixedSize(18, 18)
        chk_frame.setCursor(Qt.PointingHandCursor)
        chk_frame.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.04); "
            "border: 1.5px solid rgba(255,255,255,0.15); border-radius: 5px; }"
        )
        rl.addWidget(chk_frame)

        # Sheet name — clipped to avoid horizontal scroll
        _MAX_NAME_PX = 260
        name_lbl = QLabel(sheet_name)
        name_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 13px; font-weight: 500; font-family: 'Courier New', monospace;"
        )
        name_lbl.setMaximumWidth(_MAX_NAME_PX)
        fm = QFontMetrics(name_lbl.font())
        name_lbl.setText(fm.elidedText(sheet_name, Qt.ElideRight, _MAX_NAME_PX))
        name_lbl.setToolTip(sheet_name)
        rl.addWidget(name_lbl, 1)

        # Transaction / Dimension toggle buttons
        cat_row = QHBoxLayout()
        cat_row.setSpacing(6)

        tx_btn = QPushButton("Transaction")
        tx_btn.setFixedHeight(28)
        tx_btn.setStyleSheet(self._cat_btn_style(False, "transaction"))
        tx_btn.setCursor(Qt.PointingHandCursor)

        dim_btn = QPushButton("Dimension")
        dim_btn.setFixedHeight(28)
        dim_btn.setStyleSheet(self._cat_btn_style(False, "dimension"))
        dim_btn.setCursor(Qt.PointingHandCursor)

        cat_row.addWidget(tx_btn)
        cat_row.addWidget(dim_btn)
        rl.addLayout(cat_row)

        # Header row selector
        hdr_lbl = QLabel("Row")
        hdr_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 10px; background: transparent; border: none;"
        )
        rl.addWidget(hdr_lbl)

        spinbox = QSpinBox()
        spinbox.setRange(1, 100)
        spinbox.setValue(self._detected_header_rows.get(sheet_name, 1))
        spinbox.setFixedSize(52, 26)
        spinbox.setEnabled(False)
        spinbox.setStyleSheet(
            "QSpinBox { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 5px; "
            "color: #94a3b8; font-size: 11px; padding: 0 2px; }"
            "QSpinBox:enabled { color: #f1f5f9; border-color: rgba(59,130,246,0.4); "
            "background: rgba(59,130,246,0.07); }"
            "QSpinBox::up-button, QSpinBox::down-button { width: 14px; border: none; "
            "background: transparent; }"
        )
        rl.addWidget(spinbox)

        # Opacity effect for dimming unchecked rows
        opacity = QGraphicsOpacityEffect()
        opacity.setOpacity(0.4)
        row.setGraphicsEffect(opacity)

        row_data = {
            "sheet_name": sheet_name,
            "checked": False,
            "category": None,
            "row_widget": row,
            "chk_frame": chk_frame,
            "tx_btn": tx_btn,
            "dim_btn": dim_btn,
            "spinbox": spinbox,
            "opacity": opacity,
        }

        # Wire up interactions
        def _toggle_check(event=None, d=row_data):
            self._set_checked(d, not d["checked"])

        chk_frame.mousePressEvent = _toggle_check
        name_lbl.mousePressEvent = _toggle_check

        def _pick_tx(event=None, d=row_data):
            if d["checked"]:
                self._set_category(d, "Transaction")

        def _pick_dim(event=None, d=row_data):
            if d["checked"]:
                self._set_category(d, "Dimension")

        tx_btn.clicked.connect(lambda _=False, d=row_data: self._set_category(d, "Transaction"))
        dim_btn.clicked.connect(lambda _=False, d=row_data: self._set_category(d, "Dimension"))

        self._list_layout.addWidget(row)
        return row_data

    def _set_checked(self, row_data: dict, checked: bool) -> None:
        row_data["checked"] = checked
        chk = row_data["chk_frame"]
        if checked:
            chk.setStyleSheet(
                "QFrame { background: #3b82f6; border: 1.5px solid #3b82f6; border-radius: 5px; }"
            )
            row_data["opacity"].setOpacity(1.0)
            row_data["spinbox"].setEnabled(True)
        else:
            chk.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.04); "
                "border: 1.5px solid rgba(255,255,255,0.15); border-radius: 5px; }"
            )
            row_data["opacity"].setOpacity(0.4)
            row_data["spinbox"].setEnabled(False)
            # Clear category when unchecked
            if row_data["category"]:
                row_data["category"] = None
                row_data["tx_btn"].setStyleSheet(self._cat_btn_style(False, "transaction"))
                row_data["dim_btn"].setStyleSheet(self._cat_btn_style(False, "dimension"))
        self._update_confirm_btn()

    def _set_category(self, row_data: dict, category: str) -> None:
        row_data["category"] = category
        row_data["tx_btn"].setStyleSheet(
            self._cat_btn_style(category == "Transaction", "transaction")
        )
        row_data["dim_btn"].setStyleSheet(
            self._cat_btn_style(category == "Dimension", "dimension")
        )
        self._update_confirm_btn()

    @staticmethod
    def _cat_btn_style(active: bool, kind: str) -> str:
        if active and kind == "transaction":
            return (
                "QPushButton { background: rgba(59,130,246,0.15); "
                "border: 1px solid rgba(59,130,246,0.35); border-radius: 6px; "
                "color: #60a5fa; font-size: 11px; font-weight: 500; padding: 0 12px; }"
            )
        if active and kind == "dimension":
            return (
                "QPushButton { background: rgba(34,211,153,0.12); "
                "border: 1px solid rgba(34,211,153,0.3); border-radius: 6px; "
                "color: #34d399; font-size: 11px; font-weight: 500; padding: 0 12px; }"
            )
        return (
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 6px; "
            "color: #cbd5e1; font-size: 11px; padding: 0 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.07); }"
        )

    # ── Footer ────────────────────────────────────────────────────────

    def _make_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(8)
        lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self.reject)
        lay.addWidget(cancel_btn)

        self._confirm_btn = QPushButton("Confirm Selection")
        self._confirm_btn.setObjectName("btn_primary")
        self._confirm_btn.setFixedHeight(34)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._on_confirm)
        lay.addWidget(self._confirm_btn)
        return footer

    def _update_confirm_btn(self) -> None:
        """Enable confirm only when every checked row has a category assigned."""
        checked = [r for r in self._rows if r["checked"]]
        can_confirm = bool(checked) and all(r["category"] for r in checked)
        self._confirm_btn.setEnabled(can_confirm)

    # ── Accept ────────────────────────────────────────────────────────

    def _on_confirm(self) -> None:
        selections = [
            {
                "sheet_name": r["sheet_name"],
                "category": r["category"],
                "header_row": r["spinbox"].value(),
            }
            for r in self._rows
            if r["checked"] and r["category"]
        ]
        if not selections:
            return
        self._result = selections
        QDialog.accept(self)

    @property
    def result(self) -> list[dict] | None:  # type: ignore[override]
        return self._result


def select_sheets(parent, excel_path: Path, sheet_names: list[str]) -> list[dict] | None:
    """Open the sheet selector dialog and return selected rows, or None if cancelled."""
    dialog = PopupSheetSelector(parent, excel_path=excel_path, sheet_names=sheet_names)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.result
    return None
