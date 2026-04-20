from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import get_sheet_as_dataframe, load_excel_sheets, save_as_json
from core.dim_manager import delete_dim_table
from core.mapping_manager import get_active_dim_tables
from core.project_manager import save_project_json
from core.project_paths import active_dim_dir
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


class _OrphanDeleteConfirm:
    """Dark-themed confirmation dialog for orphaned dimension table deletion."""

    def __init__(self, parent, dim_name: str):
        self._dlg = QDialog(parent)
        self._dlg.setWindowTitle("Delete Orphaned Dimension Table")
        self._dlg.setFixedSize(500, 240)
        self._dlg.setModal(True)
        self._dlg.setStyleSheet("QDialog { background-color: #0f1117; }")
        self.confirmed = False

        outer = QVBoxLayout(self._dlg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("QFrame { background-color: #ef4444; }")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(22, 0, 22, 0)
        h_lbl = QLabel("Delete Dimension Table")
        h_lbl.setStyleSheet(
            "color: #fff; font-size: 15px; font-weight: 700; "
            "background: transparent; border: none;"
        )
        h_lay.addWidget(h_lbl)
        outer.addWidget(header)

        # Body
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; }")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(22, 18, 22, 18)
        b_lay.setSpacing(10)

        msg = QLabel(
            f"<b style='color:#f1f5f9;'>{dim_name}</b> has no active mappings "
            f"and is eligible for deletion.<br><br>"
            f"This will <b>permanently remove</b> the dimension table and all its data. "
            f"This action cannot be undone by reverting to a snapshot."
        )
        msg.setTextFormat(Qt.RichText)
        msg.setWordWrap(True)
        msg.setStyleSheet(
            "color: #94a3b8; font-size: 13px; background: transparent; border: none;"
        )
        b_lay.addWidget(msg)
        outer.addWidget(body, 1)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet("QFrame { background-color: #0f1117; }")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(22, 0, 22, 0)
        f_lay.setSpacing(8)
        f_lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(
            "QPushButton { background: transparent; "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 7px; "
            "color: #64748b; font-size: 13px; padding: 0 18px; }"
            "QPushButton:hover { border-color: rgba(255,255,255,0.22); color: #94a3b8; }"
        )
        cancel_btn.clicked.connect(self._dlg.reject)
        f_lay.addWidget(cancel_btn)

        delete_btn = QPushButton("Delete Permanently")
        delete_btn.setFixedHeight(36)
        delete_btn.setStyleSheet(
            "QPushButton { background: #ef4444; border: none; border-radius: 7px; "
            "color: #fff; font-size: 13px; font-weight: 600; padding: 0 18px; }"
            "QPushButton:hover { background: #dc2626; }"
        )
        delete_btn.clicked.connect(self._confirm)
        f_lay.addWidget(delete_btn)
        outer.addWidget(footer)

    def _confirm(self) -> None:
        self.confirmed = True
        self._dlg.accept()

    def exec(self) -> None:
        self._dlg.exec()


class ViewDSources(ScreenBase):
    """Dimension source management view."""

    def __init__(self, parent, project: dict, on_project_changed, on_go_mapping_setup):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self.on_go_mapping_setup = on_go_mapping_setup
        self._orphaned_dims: set[str] = set()
        self._search_text = ""

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
            "Add new dimension tables here. Orphaned tables (no active mappings) "
            "may be permanently deleted."
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

        # Search bar
        search_frame = QFrame()
        search_frame.setFixedHeight(46)
        search_frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); border-radius: 0; }"
        )
        sf_lay = QHBoxLayout(search_frame)
        sf_lay.setContentsMargins(14, 7, 14, 7)
        self._search_bar = QLineEdit()
        self._search_bar.setPlaceholderText("Search dimension tables...")
        self._search_bar.setFixedHeight(30)
        self._search_bar.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; "
            "color: #94a3b8; font-size: 12px; padding: 0 10px; }"
            "QLineEdit:focus { border-color: rgba(59,130,246,0.4); "
            "background: rgba(255,255,255,0.06); color: #cbd5e1; }"
            "QLineEdit::placeholder { color: #334155; }"
        )
        self._search_bar.textChanged.connect(self._on_search_changed)
        sf_lay.addWidget(self._search_bar)
        card_lay.addWidget(search_frame)

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
        self._load_orphan_state()

    # ------------------------------------------------------------------

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def _on_search_changed(self, text: str) -> None:
        self._search_text = text.strip().lower()
        self._render_rows()

    def _load_orphan_state(self) -> None:
        """Detect which dim tables are orphaned (no mappings), then render."""
        def worker():
            return get_active_dim_tables(self.project_path)

        def on_success(active_dims: set):
            all_dims = set(self.project.get("dim_tables", []))
            self._orphaned_dims = all_dims - active_dims
            self._render_rows()

        self._run_background(
            worker,
            on_success,
            lambda exc: (setattr(self, "_orphaned_dims", set()), self._render_rows()),
        )

    def _render_rows(self) -> None:
        clear_layout(self._rows_layout)
        all_dims = list(self.project.get("dim_tables", []))

        # Update count badge (always shows total, not filtered count)
        self._count_lbl.setText(str(len(all_dims)))
        self._count_lbl.setVisible(len(all_dims) > 0)

        # Apply search filter
        if self._search_text:
            dims = [d for d in all_dims if self._search_text in d.lower()]
        else:
            dims = all_dims

        if not dims:
            if self._search_text:
                msg = f'No tables match "{self._search_text}".'
            else:
                msg = "No dimension tables added yet."
            empty = QLabel(msg)
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(
                "color: #334155; font-size: 12px; background: transparent; "
                "padding: 32px; border: none;"
            )
            self._rows_layout.addWidget(empty)
            return

        for dim in dims:
            is_orphan = dim in self._orphaned_dims
            self._rows_layout.addWidget(self._make_source_row(dim, is_orphan))

    def _make_source_row(self, dim_name: str, is_orphan: bool) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); border-radius: 0; }"
        )
        lay = QHBoxLayout(row)
        lay.setContentsMargins(18, 13, 18, 13)
        lay.setSpacing(12)

        # Icon box — amber tint if orphaned, green if active
        icon_color = "rgba(245,158,11,0.10)" if is_orphan else "rgba(34,211,153,0.08)"
        icon_fg = "#fbbf24" if is_orphan else "#34d399"
        icon_box = QFrame()
        icon_box.setFixedSize(32, 32)
        icon_box.setStyleSheet(
            f"QFrame {{ background: {icon_color}; border-radius: 7px; border: none; }}"
        )
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("◨")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"color: {icon_fg}; font-size: 14px; background: transparent; border: none;"
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
        meta_text = "No active mappings — orphaned" if is_orphan else "Dimension table"
        meta_lbl = QLabel(meta_text)
        meta_lbl.setStyleSheet(
            f"color: {'#f59e0b' if is_orphan else '#475569'}; "
            "font-size: 11px; background: transparent; border: none;"
        )
        info_col.addWidget(name_lbl)
        info_col.addWidget(meta_lbl)
        lay.addLayout(info_col, 1)

        # View button (always present)
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

        if is_orphan:
            # Delete button — only for orphaned sources
            del_btn = QPushButton("Delete")
            del_btn.setFixedHeight(34)
            del_btn.setStyleSheet(
                "QPushButton { background: rgba(239,68,68,0.10); "
                "border: 1px solid rgba(239,68,68,0.28); border-radius: 7px; "
                "color: #f87171; font-size: 12px; padding: 0 14px; }"
                "QPushButton:hover { background: rgba(239,68,68,0.20); }"
            )
            del_btn.clicked.connect(lambda _=False, n=dim_name: self._on_delete_orphan(n))
            lay.addWidget(del_btn)
        else:
            # Locked badge — non-orphaned sources cannot be deleted
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
            path = active_dim_dir(self.project_path) / f"{dim_name}.json"
            return pd.read_json(path, orient="records")

        def on_success(df):
            from ui.popups.popup_replace import PopupDimView
            dlg = PopupDimView(self, dim_df=df, dim_table=dim_name)
            dlg.exec()

        self._run_background(
            worker,
            on_success,
            lambda exc: QMessageBox.critical(self, "Error", f"Could not load table:\n{exc}"),
        )

    def _on_delete_orphan(self, dim_name: str) -> None:
        """Show confirmation and permanently delete an orphaned dimension table."""
        dlg = _OrphanDeleteConfirm(self, dim_name)
        dlg.exec()
        if not dlg.confirmed:
            return

        def worker():
            # Delete the JSON data file
            delete_dim_table(self.project_path, dim_name)

            # Remove from project.json dim_tables and track as deleted
            import json as _json
            proj_file = self.project_path / "project.json"
            with open(proj_file, encoding="utf-8") as f:
                proj = _json.load(f)
            proj["dim_tables"] = [d for d in proj.get("dim_tables", []) if d != dim_name]
            deleted = list(proj.get("deleted_dim_tables", []))
            if dim_name not in deleted:
                deleted.append(dim_name)
            proj["deleted_dim_tables"] = deleted
            with open(proj_file, "w", encoding="utf-8") as f:
                _json.dump(proj, f, indent=2)

        def on_done(_):
            self.on_project_changed(target_key="d_sources")

        self._run_background(
            worker,
            on_done,
            lambda exc: QMessageBox.critical(
                self, "Error", f"Could not delete dimension table:\n{exc}"
            ),
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
                save_as_json(df, active_dim_dir(self.project_path) / f"{dim_name}.json")
                save_project_json(self.project_path, {
                    "project_name": self.project.get("project_name", ""),
                    "created_at": self.project.get("created_at", ""),
                    "company": self.project.get("company", ""),
                    "transaction_tables": list(self.project.get("transaction_tables", [])),
                    "dim_tables": [*self.project.get("dim_tables", []), dim_name],
                    "deleted_dim_tables": list(self.project.get("deleted_dim_tables", [])),
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
