from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import get_sheet_as_dataframe, load_excel_sheets, save_as_csv
from core.mapping_manager import delete_mappings_for_table, get_mappings
from core.project_manager import save_project_json
from core.snapshot_manager import create_snapshot
from ui.screen1_sources import normalize_table_name
from ui.workers import ScreenBase, clear_layout, make_scroll_area


def count_mappings_for_table(mappings: list[dict], table_name: str) -> int:
    target = table_name.strip()
    return sum(
        1 for m in mappings
        if m.get("transaction_table", "").strip() == target
        or m.get("dim_table", "").strip() == target
    )


def has_table_name_conflict(project: dict, table_name: str) -> bool:
    return (
        table_name in set(project.get("transaction_tables", []))
        or table_name in set(project.get("dim_tables", []))
    )


class ViewTSources(ScreenBase):
    """Transaction source management view."""

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
        title = QLabel("Transaction Sources")
        title.setFont(theme.font(22, "bold"))
        title.setStyleSheet("color: #f1f5f9;")
        hdr.addWidget(title, 1)

        add_btn = QPushButton("Add Transaction Table")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self._on_add_transaction_table)
        hdr.addWidget(add_btn)
        outer.addLayout(hdr)

        hint = QLabel(
            "How to use: Upload new versions for existing tables, delete obsolete ones, "
            "or add new transaction tables."
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

        card_title = QLabel("Current transaction tables")
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
        tables = list(self.project.get("transaction_tables", []))

        if not tables:
            lbl = QLabel("No transaction tables found.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self._rows_layout.addWidget(lbl)
            return

        for table in tables:
            row = QFrame()
            row.setStyleSheet("QFrame { background-color: #0f1117; border-radius: 8px; }")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 8, 6)

            name_lbl = QLabel(table)
            name_lbl.setFont(theme.font(12, "bold"))
            name_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            row_layout.addWidget(name_lbl, 1)

            upload_btn = QPushButton("Upload New Version")
            upload_btn.setObjectName("btn_outline")
            upload_btn.setFixedHeight(32)
            upload_btn.clicked.connect(lambda _=False, t=table: self._on_upload_new_version(t))
            row_layout.addWidget(upload_btn)

            del_btn = QPushButton("Delete")
            del_btn.setObjectName("btn_danger")
            del_btn.setFixedSize(90, 32)
            del_btn.clicked.connect(lambda _=False, t=table: self._on_delete_table(t))
            row_layout.addWidget(del_btn)

            self._rows_layout.addWidget(row)

    # ------------------------------------------------------------------

    def _on_upload_new_version(self, table_name: str) -> None:
        self._set_error("")
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Select Excel file for {table_name}", "",
            "Excel Files (*.xlsx *.xlsm *.xls)"
        )
        if not file_path:
            return
        excel_path = Path(file_path)

        def load_sheets_worker():
            return load_excel_sheets(excel_path)

        def on_sheets_loaded(sheets):
            from ui.popups.popup_single_sheet import select_single_sheet
            selected = select_single_sheet(self, excel_path, sheets, title="Select Sheet For Update")
            if not selected:
                return

            def update_worker():
                df = get_sheet_as_dataframe(excel_path, selected)
                create_snapshot(self.project_path, {table_name: df}, label=f"Updated {table_name}")

            def on_done(_):
                QMessageBox.information(self, "Updated", f"Table '{table_name}' updated.")
                self.on_project_changed(target_key="t_sources")

            self._run_background(update_worker, on_done,
                                 lambda exc: QMessageBox.critical(
                                     self, "Error", f"Could not update table:\n{exc}"
                                 ))

        self._run_background(load_sheets_worker, on_sheets_loaded,
                             lambda exc: QMessageBox.critical(
                                 self, "Error", f"Could not read file:\n{exc}"
                             ))

    def _on_delete_table(self, table_name: str) -> None:
        self._set_error("")

        def load_mappings_worker():
            return get_mappings(self.project_path)

        def on_mappings_loaded(mappings):
            count = count_mappings_for_table(mappings, table_name)
            reply = QMessageBox.question(
                self, "Confirm Delete",
                f"Deleting '{table_name}' will also remove {count} mapping(s). Confirm?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

            def delete_worker():
                csv_path = self.project_path / "data" / "transactions" / f"{table_name}.csv"
                if csv_path.exists():
                    csv_path.unlink()
                delete_mappings_for_table(self.project_path, table_name)
                save_project_json(self.project_path, {
                    "project_name": self.project.get("project_name", ""),
                    "created_at": self.project.get("created_at", ""),
                    "company": self.project.get("company", ""),
                    "transaction_tables": [
                        t for t in self.project.get("transaction_tables", []) if t != table_name
                    ],
                    "dim_tables": list(self.project.get("dim_tables", [])),
                })

            self._run_background(delete_worker,
                                 lambda _: self.on_project_changed(target_key="t_sources"),
                                 lambda exc: QMessageBox.critical(
                                     self, "Error", f"Could not delete table:\n{exc}"
                                 ))

        self._run_background(load_mappings_worker, on_mappings_loaded,
                             lambda exc: self._set_error(f"Could not read mappings: {exc}"))

    def _on_add_transaction_table(self) -> None:
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
            selected = select_single_sheet(self, excel_path, sheets, title="Select Transaction Sheet")
            if not selected:
                return
            table_name = normalize_table_name(selected)
            if has_table_name_conflict(self.project, table_name):
                self._set_error(f"Table name already exists: {table_name}")
                return

            def add_worker():
                df = get_sheet_as_dataframe(excel_path, selected)
                save_as_csv(df, self.project_path / "data" / "transactions" / f"{table_name}.csv")
                create_snapshot(self.project_path, {table_name: df}, label=f"Added {table_name}")
                save_project_json(self.project_path, {
                    "project_name": self.project.get("project_name", ""),
                    "created_at": self.project.get("created_at", ""),
                    "company": self.project.get("company", ""),
                    "transaction_tables": [*self.project.get("transaction_tables", []), table_name],
                    "dim_tables": list(self.project.get("dim_tables", [])),
                })

            def on_done(_):
                go_setup = QMessageBox.question(
                    self, "Mapping Setup", "Go to mapping setup for the new table now?",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
                ) == QMessageBox.Yes
                self.on_project_changed(target_key="t_sources")
                if go_setup:
                    self.on_go_mapping_setup()

            self._run_background(add_worker, on_done,
                                 lambda exc: QMessageBox.critical(
                                     self, "Error", f"Could not add table:\n{exc}"
                                 ))

        self._run_background(load_sheets_worker, on_sheets_loaded,
                             lambda exc: QMessageBox.critical(
                                 self, "Error", f"Could not read file:\n{exc}"
                             ))
