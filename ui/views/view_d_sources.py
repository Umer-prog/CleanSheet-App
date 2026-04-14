from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import get_sheet_as_dataframe, load_excel_sheets, save_as_json
from core.project_manager import save_project_json
from ui.screen1_sources import normalize_table_name
from ui.workers import ScreenBase, clear_layout, make_scroll_area


def has_dim_name_conflict(project: dict, dim_name: str) -> bool:
    return (
        dim_name in set(project.get("dim_tables", []))
        or dim_name in set(project.get("transaction_tables", []))
    )


class ViewDSources(ScreenBase):
    """Dimension source management view."""

    def __init__(self, parent, project: dict, on_project_changed, on_go_mapping_setup):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self.on_go_mapping_setup = on_go_mapping_setup

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 18)
        outer.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Dimension Sources")
        title.setFont(theme.font(22, "bold"))
        title.setStyleSheet("color: #f1f5f9;")
        hdr.addWidget(title, 1)

        add_btn = QPushButton("Add Dimension Table")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._on_add_dim_table)
        hdr.addWidget(add_btn)
        outer.addLayout(hdr)

        hint = QLabel(
            "How to use: Add new dimension tables here. Existing dimension tables "
            "are locked and cannot be replaced or deleted."
        )
        hint.setFont(theme.font(11))
        hint.setStyleSheet("color: #475569;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # List card
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        card_title = QLabel("Current dimension tables")
        card_title.setFont(theme.font(13, "bold"))
        card_title.setStyleSheet("color: #f1f5f9; background: transparent;")
        card_layout.addWidget(card_title)

        self._rows_scroll, _, self._rows_layout = make_scroll_area()
        self._rows_layout.setContentsMargins(6, 4, 6, 4)
        self._rows_layout.setSpacing(4)
        card_layout.addWidget(self._rows_scroll, 1)

        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(11))
        self._error_lbl.setStyleSheet("color: #f87171; background: transparent;")
        card_layout.addWidget(self._error_lbl)
        outer.addWidget(card, 1)

        self._setup_overlay("Working...")
        self._render_rows()

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def _render_rows(self) -> None:
        clear_layout(self._rows_layout)
        dims = list(self.project.get("dim_tables", []))

        if not dims:
            lbl = QLabel("No dimension tables found.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self._rows_layout.addWidget(lbl)
            return

        for dim in dims:
            row = QFrame()
            row.setStyleSheet("QFrame { background-color: #0f1117; border-radius: 8px; }")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 8, 6)

            name_lbl = QLabel(dim)
            name_lbl.setFont(theme.font(12, "bold"))
            name_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            row_layout.addWidget(name_lbl, 1)

            locked_btn = QPushButton("Locked")
            locked_btn.setObjectName("btn_outline")
            locked_btn.setFixedSize(90, 32)
            locked_btn.setEnabled(False)
            row_layout.addWidget(locked_btn)

            note = QLabel("Cannot delete or replace")
            note.setFont(theme.font(11))
            note.setStyleSheet("color: #475569; background: transparent;")
            row_layout.addWidget(note)

            self._rows_layout.addWidget(row)

    # ------------------------------------------------------------------

    def _on_add_dim_table(self) -> None:
        self._set_error("")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file", "", "Excel Files (*.xlsx *.xlsm *.xls)"
        )
        if not file_path:
            return
        excel_path = Path(file_path)

        def load_sheets_worker():
            return load_excel_sheets(excel_path)

        def on_sheets_loaded(sheets):
            from ui.popups.popup_single_sheet import select_single_sheet
            selected = select_single_sheet(self, excel_path, sheets, title="Select Dimension Sheet")
            if not selected:
                return
            dim_name = normalize_table_name(selected)
            if has_dim_name_conflict(self.project, dim_name):
                self._set_error(f"Dimension table already exists: {dim_name}")
                return

            def add_worker():
                df = get_sheet_as_dataframe(excel_path, selected)
                save_as_json(df, self.project_path / "data" / "dim" / f"{dim_name}.json")
                save_project_json(self.project_path, {
                    "project_name": self.project.get("project_name", ""),
                    "created_at": self.project.get("created_at", ""),
                    "company": self.project.get("company", ""),
                    "transaction_tables": list(self.project.get("transaction_tables", [])),
                    "dim_tables": [*self.project.get("dim_tables", []), dim_name],
                })

            def on_done(_):
                go_setup = QMessageBox.question(
                    self, "Mapping Setup", "Go to mapping setup for the new table now?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                ) == QMessageBox.Yes
                self.on_project_changed(target_key="d_sources")
                if go_setup:
                    self.on_go_mapping_setup()

            self._run_background(add_worker, on_done,
                                 lambda exc: QMessageBox.critical(
                                     self, "Error", f"Could not add dimension table:\n{exc}"
                                 ))

        self._run_background(load_sheets_worker, on_sheets_loaded,
                             lambda exc: QMessageBox.critical(
                                 self, "Error", f"Could not read file:\n{exc}"
                             ))
