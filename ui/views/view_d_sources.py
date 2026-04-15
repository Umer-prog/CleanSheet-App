from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
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


class ViewDSources(ScreenBase):
    """Dimension source management view."""

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
        title_lbl = QLabel("Dimension Tables")
        title_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 15px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel(
            "Add new dimension tables here. Existing dimension tables are locked "
            "and cannot be replaced or deleted."
        )
        meta_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: transparent; border: none;"
        )
        tb_text.addWidget(title_lbl)
        tb_text.addWidget(meta_lbl)
        tb_lay.addLayout(tb_text, 1)

        add_btn = _btn_primary("+ Add Dimension Table")
        add_btn.clicked.connect(self._on_add_dim_table)
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
        sc_title = QLabel("CURRENT DIMENSION TABLES")
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
        dims = list(self.project.get("dim_tables", []))

        count = len(dims)
        self._count_lbl.setText(str(count))
        self._count_lbl.setVisible(count > 0)

        if not dims:
            empty = QLabel("No dimension tables added yet.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #334155; font-size: 12px; background: transparent; "
                "padding: 32px; border: none;"
            )
            self._rows_layout.addWidget(empty)
            return

        for dim in dims:
            self._rows_layout.addWidget(self._make_source_row(dim))

    def _make_source_row(self, dim_name: str) -> QFrame:
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
            "QFrame { background: rgba(34,211,153,0.08); border-radius: 7px; border: none; }"
        )
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("◨")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #34d399; font-size: 14px; background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        # Name + meta
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(dim_name)
        name_lbl.setStyleSheet(
            "color: #cbd5e1; font-size: 13px; font-weight: 500; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel("Dimension table")
        meta_lbl.setStyleSheet(
            "color: #475569; font-size: 11px; background: transparent; border: none;"
        )
        info_col.addWidget(name_lbl)
        info_col.addWidget(meta_lbl)
        lay.addLayout(info_col, 1)

        # View button
        view_btn = QPushButton("View")
        view_btn.setFixedHeight(34)
        view_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 7px; "
            "color: #94a3b8; font-size: 12px; padding: 0 14px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); color: #cbd5e1; }"
        )
        view_btn.clicked.connect(lambda _=False, n=dim_name: self._on_view_table(n))
        lay.addWidget(view_btn)

        # Locked badge
        locked_lbl = QLabel("Locked")
        locked_lbl.setStyleSheet(
            "color: #475569; font-size: 11px; "
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); "
            "border-radius: 5px; padding: 2px 10px;"
        )
        lay.addWidget(locked_lbl)

        return row

    # ------------------------------------------------------------------
    # Business logic
    # ------------------------------------------------------------------

    def _on_view_table(self, dim_name: str) -> None:
        def worker():
            import pandas as pd
            path = self.project_path / "data" / "dim" / f"{dim_name}.json"
            return pd.read_json(path, orient="records")

        def on_success(df):
            from ui.popups.popup_replace import PopupDimView
            dlg = PopupDimView(self, dim_df=df, dim_table=dim_name)
            dlg.exec()

        self._run_background(
            worker,
            on_success,
            lambda exc: __import__("PySide6.QtWidgets", fromlist=["QMessageBox"])
                        .QMessageBox.critical(self, "Error", f"Could not load table:\n{exc}"),
        )

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
