from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
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


def _btn_primary(text: str, height: int = 34) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setStyleSheet(
        "QPushButton { background: #3b82f6; border: none; border-radius: 7px; "
        "color: white; font-size: 12px; font-weight: 500; padding: 0 16px; }"
        "QPushButton:hover { background: #2563eb; }"
        "QPushButton:pressed { background: #1d4ed8; }"
        "QPushButton:disabled { background: rgba(59,130,246,0.3); color: rgba(255,255,255,0.4); }"
    )
    return b


def _btn_ghost(text: str, height: int = 34) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setStyleSheet(
        "QPushButton { background: rgba(255,255,255,0.04); "
        "border: 1px solid rgba(255,255,255,0.09); border-radius: 7px; "
        "color: #94a3b8; font-size: 12px; padding: 0 14px; }"
        "QPushButton:hover { background: rgba(255,255,255,0.08); color: #cbd5e1; }"
    )
    return b


def _btn_danger(text: str, height: int = 34) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setStyleSheet(
        "QPushButton { background: rgba(239,68,68,0.07); "
        "border: 1px solid rgba(239,68,68,0.2); border-radius: 7px; "
        "color: #f87171; font-size: 12px; padding: 0 14px; }"
        "QPushButton:hover { background: rgba(239,68,68,0.14); }"
    )
    return b


class ViewTSources(ScreenBase):
    """Transaction source management view."""

    def __init__(self, parent, project: dict, on_project_changed, on_go_mapping_setup):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self.on_go_mapping_setup = on_go_mapping_setup

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Topbar ───────────────────────────────────────────────────────
        topbar = QFrame()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(28, 0, 28, 0)
        tb_lay.setSpacing(16)

        tb_text = QVBoxLayout()
        tb_text.setSpacing(2)
        title_lbl = QLabel("Transaction Tables")
        title_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 15px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel(
            "Upload new versions for existing tables, delete obsolete ones, "
            "or add new transaction tables."
        )
        meta_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: transparent; border: none;"
        )
        tb_text.addWidget(title_lbl)
        tb_text.addWidget(meta_lbl)
        tb_lay.addLayout(tb_text, 1)

        add_btn = _btn_primary("+ Add Transaction Table")
        add_btn.clicked.connect(self._on_add_transaction_table)
        tb_lay.addWidget(add_btn)
        outer.addWidget(topbar)

        # ── Content area ─────────────────────────────────────────────────
        content = QWidget()
        content.setStyleSheet("background: #0f1117;")
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(28, 20, 28, 20)
        c_lay.setSpacing(16)

        # Section card
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: rgba(255,255,255,5); "
            "border: 1px solid rgba(255,255,255,18); border-radius: 10px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # Card header
        sc_hdr = QFrame()
        sc_hdr.setFixedHeight(44)
        sc_hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); border-radius: 0; }"
        )
        sch_lay = QHBoxLayout(sc_hdr)
        sch_lay.setContentsMargins(18, 0, 18, 0)
        sc_title = QLabel("CURRENT TRANSACTION TABLES")
        sc_title.setStyleSheet(
            "color: #475569; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        sch_lay.addWidget(sc_title, 1)
        self._count_lbl = QLabel("")
        self._count_lbl.setFixedHeight(20)
        self._count_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: rgba(255,255,255,13); "
            "border-radius: 10px; padding: 2px 8px; border: none;"
        )
        self._count_lbl.setVisible(False)
        sch_lay.addWidget(self._count_lbl)
        card_lay.addWidget(sc_hdr)

        # Rows scroll area
        self._rows_scroll, _, self._rows_layout = make_scroll_area()
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        card_lay.addWidget(self._rows_scroll, 1)
        c_lay.addWidget(card, 1)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet("color: #f87171; font-size: 11px; background: transparent;")
        c_lay.addWidget(self._error_lbl)

        outer.addWidget(content, 1)

        self._setup_overlay("Working...")
        self._render_rows()

    # ------------------------------------------------------------------

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def _render_rows(self) -> None:
        clear_layout(self._rows_layout)
        tables = list(self.project.get("transaction_tables", []))

        count = len(tables)
        self._count_lbl.setText(str(count))
        self._count_lbl.setVisible(count > 0)

        if not tables:
            empty = QLabel("No transaction tables added yet.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #334155; font-size: 12px; background: transparent; "
                "padding: 32px; border: none;"
            )
            self._rows_layout.addWidget(empty)
            return

        for table in tables:
            self._rows_layout.addWidget(self._make_source_row(table))

    def _make_source_row(self, table_name: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); border-radius: 0; }"
        )
        lay = QHBoxLayout(row)
        lay.setContentsMargins(18, 13, 18, 13)
        lay.setSpacing(12)

        # Icon box
        icon_box = QFrame()
        icon_box.setFixedSize(32, 32)
        icon_box.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.1); border-radius: 7px; border: none; }"
        )
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("◧")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #3b82f6; font-size: 14px; background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        # Name + meta
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(table_name)
        name_lbl.setStyleSheet(
            "color: #cbd5e1; font-size: 13px; font-weight: 500; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel("Transaction table")
        meta_lbl.setStyleSheet(
            "color: #475569; font-size: 11px; background: transparent; border: none;"
        )
        info_col.addWidget(name_lbl)
        info_col.addWidget(meta_lbl)
        lay.addLayout(info_col, 1)

        # Actions
        upload_btn = _btn_ghost("Upload New Version")
        upload_btn.clicked.connect(lambda _=False, t=table_name: self._on_upload_new_version(t))
        lay.addWidget(upload_btn)

        del_btn = _btn_danger("Delete")
        del_btn.setFixedWidth(80)
        del_btn.clicked.connect(lambda _=False, t=table_name: self._on_delete_table(t))
        lay.addWidget(del_btn)

        return row

    # ------------------------------------------------------------------
    # Business logic (unchanged)
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
