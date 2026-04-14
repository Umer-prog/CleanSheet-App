from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import get_sheet_as_dataframe, load_excel_sheets, save_as_csv, save_as_json
from core.project_manager import open_project, save_project_json
from ui.workers import ScreenBase, clear_layout, make_scroll_area

_SIDEBAR_W = 300


def normalize_table_name(sheet_name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", sheet_name.strip().lower()).strip("_")
    if not normalized:
        normalized = "table"
    if normalized[0].isdigit():
        normalized = f"table_{normalized}"
    return normalized


def find_duplicate_table_names(selected_rows: list[dict], existing_table_names: set[str]) -> set[str]:
    seen = set(existing_table_names)
    duplicates = set()
    for row in selected_rows:
        name = normalize_table_name(row.get("sheet_name", ""))
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return duplicates


def validate_confirm_requirements(source_rows: list[dict]) -> str | None:
    if not source_rows:
        return "Add at least one file before continuing."
    tx_count = dim_count = 0
    for source in source_rows:
        for sheet in source.get("sheets", []):
            category = str(sheet.get("category", "")).strip()
            if category == "Transaction":
                tx_count += 1
            elif category == "Dimension":
                dim_count += 1
            else:
                return "Every selected sheet must have a category."
    if tx_count == 0:
        return "At least one transaction sheet is required."
    if dim_count == 0:
        return "At least one dimension sheet is required."
    return None


class Screen1Sources(ScreenBase):
    """Stage 1 — add Excel files and categorize their sheets."""

    def __init__(self, app, project: dict, **kwargs):
        super().__init__()
        self.app = app
        self.project = project
        self.project_path = Path(project["project_path"])
        self._sources: list[dict] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(_SIDEBAR_W)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(20, 26, 20, 20)
        sb.setSpacing(10)

        t = QLabel("Data Loader")
        t.setFont(theme.font(20, "bold"))
        t.setStyleSheet("color: #f1f5f9;")
        sb.addWidget(t)

        desc = QLabel("Add Excel files and mark each selected sheet\nas Transaction or Dimension.")
        desc.setFont(theme.font(12))
        desc.setStyleSheet("color: #94a3b8;")
        sb.addWidget(desc)
        sb.addSpacing(6)

        back_btn = QPushButton("Back To Projects")
        back_btn.setObjectName("btn_ghost")
        back_btn.setFixedHeight(38)
        back_btn.clicked.connect(self._go_back)
        sb.addWidget(back_btn)
        sb.addStretch()
        root.addWidget(sidebar)

        # --- Content ---
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(22, 20, 22, 20)
        c_layout.setSpacing(8)

        # Header row
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Data Loader")
        title.setFont(theme.font(22, "bold"))
        title.setStyleSheet("color: #f1f5f9;")
        hdr.addWidget(title, 1)
        add_btn = QPushButton("Add File")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedHeight(40)
        add_btn.setFixedWidth(120)
        add_btn.clicked.connect(self._on_add_file)
        hdr.addWidget(add_btn)
        c_layout.addLayout(hdr)

        # Tip card
        tip = QFrame()
        tip.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        tip_layout = QVBoxLayout(tip)
        tip_layout.setContentsMargins(12, 8, 12, 8)
        tip_lbl = QLabel(
            "How to use: Add files, pick sheets, and assign Transaction or Dimension. "
            "Confirm when both categories are present."
        )
        tip_lbl.setFont(theme.font(11))
        tip_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        tip_lbl.setWordWrap(True)
        tip_layout.addWidget(tip_lbl)
        c_layout.addWidget(tip)

        # Scrollable list
        list_card = QFrame()
        list_card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        list_card_layout = QVBoxLayout(list_card)
        list_card_layout.setContentsMargins(0, 0, 0, 0)

        self._list_scroll, self._list_container, self._list_layout = make_scroll_area()
        self._list_layout.setContentsMargins(10, 8, 10, 8)
        self._list_layout.setSpacing(8)
        list_card_layout.addWidget(self._list_scroll)
        c_layout.addWidget(list_card, 1)

        # Footer
        footer_row = QHBoxLayout()
        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(12))
        self._error_lbl.setStyleSheet("color: #f87171;")
        footer_row.addWidget(self._error_lbl, 1)

        confirm_btn = QPushButton("Confirm & Continue")
        confirm_btn.setObjectName("btn_primary")
        confirm_btn.setFixedHeight(42)
        confirm_btn.setFixedWidth(180)
        confirm_btn.clicked.connect(self._on_confirm_continue)
        footer_row.addWidget(confirm_btn)
        c_layout.addLayout(footer_row)

        root.addWidget(content, 1)

        self._setup_overlay("Working...")
        self._render_sources()

    # ------------------------------------------------------------------

    def _go_back(self) -> None:
        from ui.screen0_launcher import Screen0Launcher
        self.app.show_screen(Screen0Launcher)

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    # ------------------------------------------------------------------
    # File / sheet operations
    # ------------------------------------------------------------------

    def _on_add_file(self) -> None:
        self._set_error("")
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file", "", "Excel Files (*.xlsx *.xlsm *.xls)"
        )
        if not file_path:
            return
        excel_path = Path(file_path)

        def worker():
            return load_excel_sheets(excel_path)

        def on_success(sheet_names):
            from ui.popups.popup_sheet_selector import select_sheets
            picked_rows = select_sheets(self, excel_path=excel_path, sheet_names=sheet_names)
            if not picked_rows:
                return
            existing = self._all_known_table_names()
            duplicates = find_duplicate_table_names(picked_rows, existing_table_names=existing)
            if duplicates:
                self._set_error(f"Duplicate table name(s): {', '.join(sorted(duplicates))}")
                return
            self._sources.append({"file_path": str(excel_path), "sheets": picked_rows})
            self._render_sources()

        def on_error(exc):
            QMessageBox.critical(self, "Error", f"Could not read Excel file:\n{exc}")

        self._run_background(worker, on_success, on_error)

    def _all_known_table_names(self) -> set[str]:
        names = set(self.project.get("transaction_tables", []))
        names.update(self.project.get("dim_tables", []))
        for source in self._sources:
            for sheet in source.get("sheets", []):
                names.add(normalize_table_name(sheet["sheet_name"]))
        return names

    def _on_remove_file(self, file_index: int) -> None:
        self._set_error("")
        if 0 <= file_index < len(self._sources):
            self._sources.pop(file_index)
            self._render_sources()

    def _on_remove_sheet(self, file_index: int, sheet_index: int) -> None:
        self._set_error("")
        if not (0 <= file_index < len(self._sources)):
            return
        sheets = self._sources[file_index]["sheets"]
        if 0 <= sheet_index < len(sheets):
            sheets.pop(sheet_index)
        if not sheets:
            self._sources.pop(file_index)
        self._render_sources()

    def _render_sources(self) -> None:
        clear_layout(self._list_layout)

        if not self._sources:
            lbl = QLabel("No files added yet. Click Add File to begin.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self._list_layout.addWidget(lbl)
            return

        for file_index, source in enumerate(self._sources):
            card = QFrame()
            card.setStyleSheet("QFrame { background-color: #0f1117; border-radius: 10px; }")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(6)

            top_row = QHBoxLayout()
            fname_lbl = QLabel(Path(source["file_path"]).name)
            fname_lbl.setFont(theme.font(13, "bold"))
            fname_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            top_row.addWidget(fname_lbl, 1)

            rm_file_btn = QPushButton("Remove File")
            rm_file_btn.setObjectName("btn_danger")
            rm_file_btn.setFixedHeight(30)
            rm_file_btn.setFixedWidth(98)
            rm_file_btn.clicked.connect(lambda _=False, i=file_index: self._on_remove_file(i))
            top_row.addWidget(rm_file_btn)
            card_layout.addLayout(top_row)

            for sheet_index, sheet in enumerate(source.get("sheets", [])):
                sheet_row = QHBoxLayout()
                table_name = normalize_table_name(sheet["sheet_name"])
                sheet_lbl = QLabel(
                    f"{sheet['sheet_name']}  →  {sheet['category']}  ({table_name})"
                )
                sheet_lbl.setFont(theme.font(12))
                sheet_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
                sheet_row.addWidget(sheet_lbl, 1)

                rm_sheet_btn = QPushButton("Remove")
                rm_sheet_btn.setObjectName("btn_outline")
                rm_sheet_btn.setFixedHeight(28)
                rm_sheet_btn.setFixedWidth(74)
                rm_sheet_btn.clicked.connect(
                    lambda _=False, fi=file_index, si=sheet_index: self._on_remove_sheet(fi, si)
                )
                sheet_row.addWidget(rm_sheet_btn)
                card_layout.addLayout(sheet_row)

            self._list_layout.addWidget(card)

    # ------------------------------------------------------------------
    # Confirm & persist
    # ------------------------------------------------------------------

    def _on_confirm_continue(self) -> None:
        error = validate_confirm_requirements(self._sources)
        if error:
            self._set_error(error)
            return
        self._set_error("")

        def worker():
            self._persist_sources()
            return open_project(self.project_path)

        def on_success(updated_state):
            self.app.set_current_project(updated_state)
            self.project = updated_state
            self._sources.clear()
            self._render_sources()
            self._set_error("")
            try:
                from ui.screen2_mappings import Screen2Mappings
                self.app.show_screen(Screen2Mappings, project=updated_state)
            except ImportError:
                QMessageBox.information(
                    self, "Screen 2", "Data sources saved. Screen 2 is not built yet."
                )

        def on_error(exc):
            QMessageBox.critical(self, "Error", f"Could not save selected sheets:\n{exc}")

        self._run_background(worker, on_success, on_error)

    def _persist_sources(self) -> None:
        project_data = {
            "project_name": self.project.get("project_name", ""),
            "created_at": self.project.get("created_at", ""),
            "company": self.project.get("company", ""),
            "transaction_tables": list(self.project.get("transaction_tables", [])),
            "dim_tables": list(self.project.get("dim_tables", [])),
        }
        tx_names = list(project_data["transaction_tables"])
        dim_names = list(project_data["dim_tables"])

        for source in self._sources:
            file_path = Path(source["file_path"])
            for sheet in source.get("sheets", []):
                table_name = normalize_table_name(sheet["sheet_name"])
                df = get_sheet_as_dataframe(file_path, sheet["sheet_name"])
                if sheet["category"] == "Transaction":
                    save_as_csv(df, self.project_path / "data" / "transactions" / f"{table_name}.csv")
                    if table_name not in tx_names:
                        tx_names.append(table_name)
                elif sheet["category"] == "Dimension":
                    save_as_json(df, self.project_path / "data" / "dim" / f"{table_name}.json")
                    if table_name not in dim_names:
                        dim_names.append(table_name)

        project_data["transaction_tables"] = tx_names
        project_data["dim_tables"] = dim_names
        save_project_json(self.project_path, project_data)
