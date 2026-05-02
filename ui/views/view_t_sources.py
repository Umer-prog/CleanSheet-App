from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel,
    QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
import ui.popups.msgbox as msgbox
from core.data_loader import get_sheet_as_dataframe, load_excel_sheets, save_as_csv
from core.mapping_manager import delete_mappings_for_table, get_mappings
from core.project_manager import save_project_json
from core.project_paths import active_transactions_dir
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

    def __init__(
        self,
        parent,
        project: dict,
        on_project_changed: Callable,
        on_go_mapping_setup: Callable,
        on_go_screen1: Callable,
        on_chain_append: Callable,
    ):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self.on_go_mapping_setup = on_go_mapping_setup
        self._on_go_screen1 = on_go_screen1
        self._on_chain_append = on_chain_append

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
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
        )
        tb_text.addWidget(title_lbl)
        tb_text.addWidget(meta_lbl)
        tb_lay.addLayout(tb_text, 1)

        refresh_all_btn = _btn_ghost("↻ Refresh All")
        refresh_all_btn.clicked.connect(self._on_refresh_all)
        tb_lay.addWidget(refresh_all_btn)

        add_btn = _btn_primary("+ Add File")
        add_btn.clicked.connect(self._on_go_screen1)
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
            "color: #cbd5e1; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        sch_lay.addWidget(sc_title, 1)
        self._count_lbl = QLabel("")
        self._count_lbl.setFixedHeight(20)
        self._count_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: rgba(255,255,255,13); "
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
                "color: #94a3b8; font-size: 12px; background: transparent; "
                "padding: 32px; border: none;"
            )
            self._rows_layout.addWidget(empty)
            return

        for table in tables:
            self._rows_layout.addWidget(self._make_source_row(table))

    def _make_source_row(self, table_name: str) -> QFrame:
        sheets_meta = self.project.get("sheets_meta", {})
        table_meta = sheets_meta.get(table_name, {})
        if table_meta.get("is_chained") and table_meta.get("chain"):
            return self._make_chained_group(table_name, table_meta["chain"])
        return self._make_unchained_row(table_name)

    def _make_unchained_row(self, table_name: str) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); border-radius: 0; }"
        )
        lay = QHBoxLayout(row)
        lay.setContentsMargins(18, 13, 18, 13)
        lay.setSpacing(12)

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

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(table_name)
        name_lbl.setStyleSheet(
            "color: #cbd5e1; font-size: 13px; font-weight: 500; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel("Transaction table")
        meta_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
        )
        info_col.addWidget(name_lbl)
        info_col.addWidget(meta_lbl)
        lay.addLayout(info_col, 1)

        upload_btn = _btn_ghost("Upload New Version")
        upload_btn.clicked.connect(lambda _=False, t=table_name: self._on_upload_new_version(t))
        lay.addWidget(upload_btn)

        refresh_btn = _btn_ghost("Refresh")
        refresh_btn.setFixedWidth(84)
        refresh_btn.clicked.connect(lambda _=False, t=table_name: self._refresh_table(t))
        lay.addWidget(refresh_btn)

        del_btn = _btn_danger("Delete")
        del_btn.setFixedWidth(80)
        del_btn.clicked.connect(lambda _=False, t=table_name: self._on_delete_table(t))
        lay.addWidget(del_btn)

        return row

    def _make_chained_group(self, table_name: str, chain: list[dict]) -> QFrame:
        """Grouped display: primary row with buttons + indented read-only sub-rows."""
        group = QFrame()
        group.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.02); border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); border-radius: 0; }"
        )
        g_lay = QVBoxLayout(group)
        g_lay.setContentsMargins(0, 0, 0, 0)
        g_lay.setSpacing(0)

        # ── Primary row ──────────────────────────────────────────────
        primary_row = QFrame()
        primary_row.setStyleSheet("QFrame { background: transparent; border: none; }")
        p_lay = QHBoxLayout(primary_row)
        p_lay.setContentsMargins(18, 13, 18, 8)
        p_lay.setSpacing(12)

        icon_box = QFrame()
        icon_box.setFixedSize(32, 32)
        icon_box.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.15); border-radius: 7px; border: none; }"
        )
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("⛓")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #60a5fa; font-size: 13px; background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        p_lay.addWidget(icon_box)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        name_lbl = QLabel(table_name)
        name_lbl.setStyleSheet(
            "color: #cbd5e1; font-size: 13px; font-weight: 500; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel(f"Chained transaction · {len(chain)} source{'s' if len(chain) != 1 else ''}")
        meta_lbl.setStyleSheet(
            "color: #3b82f6; font-size: 11px; background: transparent; border: none;"
        )
        info_col.addWidget(name_lbl)
        info_col.addWidget(meta_lbl)
        p_lay.addLayout(info_col, 1)

        refresh_btn = _btn_ghost("Refresh")
        refresh_btn.setFixedWidth(78)
        refresh_btn.clicked.connect(lambda _=False, t=table_name: self._refresh_table(t))
        p_lay.addWidget(refresh_btn)

        append_btn = _btn_ghost("Append")
        append_btn.setFixedWidth(78)
        append_btn.clicked.connect(lambda _=False, t=table_name, c=chain: self._on_append_chain(t, c))
        p_lay.addWidget(append_btn)

        del_btn = _btn_danger("Delete")
        del_btn.setFixedWidth(78)
        del_btn.clicked.connect(lambda _=False, t=table_name, c=chain: self._on_delete_chained(t, c))
        p_lay.addWidget(del_btn)

        g_lay.addWidget(primary_row)

        # ── Sub-rows (read-only) ─────────────────────────────────────
        for entry in chain:
            sub = self._make_chained_sub_row(entry)
            g_lay.addWidget(sub)

        # Bottom padding
        pad = QWidget()
        pad.setFixedHeight(6)
        pad.setStyleSheet("background: transparent;")
        g_lay.addWidget(pad)

        return group

    def _make_chained_sub_row(self, entry: dict) -> QFrame:
        sub = QFrame()
        sub.setStyleSheet("QFrame { background: transparent; border: none; }")
        lay = QHBoxLayout(sub)
        lay.setContentsMargins(62, 2, 18, 2)
        lay.setSpacing(6)

        tree_lbl = QLabel("└")
        tree_lbl.setStyleSheet(
            "color: #1e3a5f; font-size: 11px; background: transparent; border: none;"
        )
        tree_lbl.setFixedWidth(14)
        lay.addWidget(tree_lbl)

        label = f"{entry.get('label', '')} · {entry.get('sheet_name', '')}"
        entry_lbl = QLabel(label)
        entry_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(entry_lbl, 1)

        return sub

    # ------------------------------------------------------------------
    # Refresh (individual and global)
    # ------------------------------------------------------------------

    def _refresh_table(self, table_name: str) -> None:
        self._set_error("")
        sheets_meta = self.project.get("sheets_meta", {})
        meta = sheets_meta.get(table_name, {})
        if not meta:
            self._set_error(
                f"No source path stored for '{table_name}'. Use 'Upload New Version' instead."
            )
            return
        if meta.get("is_chained") and meta.get("chain"):
            self._refresh_chained(table_name, meta)
        else:
            file_path = meta.get("file_path", "")
            sheet_name = meta.get("sheet_name", "")
            if not file_path or not sheet_name:
                self._set_error(
                    f"No source path stored for '{table_name}'. Use 'Upload New Version' instead."
                )
                return
            self._refresh_unchained(table_name, file_path, sheet_name)

    def _refresh_unchained(self, table_name: str, file_path: str, sheet_name: str) -> None:
        excel_path = Path(file_path)
        if not excel_path.exists():
            self._set_error(f"Source file not found: {file_path}")
            return

        def worker():
            df = get_sheet_as_dataframe(excel_path, sheet_name)
            out = active_transactions_dir(self.project_path) / f"{table_name}.csv"
            save_as_csv(df, out)

        def on_done(_):
            self._set_error("")
            self.on_project_changed(target_key="t_sources")

        self._run_background(
            worker,
            on_done,
            lambda exc: self._set_error(f"Refresh failed for '{table_name}': {exc}"),
        )

    def _refresh_chained(self, table_name: str, meta: dict) -> None:
        chain = meta.get("chain", [])
        missing = [e["file_path"] for e in chain if not Path(e["file_path"]).exists()]
        if missing:
            self._set_error(f"Source file(s) not found: {', '.join(missing)}")
            return

        def worker():
            from core.chain_writer import write_unified_csv
            write_unified_csv(self.project_path, table_name, "Transaction", meta)

        def on_done(_):
            self._set_error("")
            self.on_project_changed(target_key="t_sources")

        self._run_background(
            worker,
            on_done,
            lambda exc: self._set_error(f"Refresh failed for '{table_name}': {exc}"),
        )

    def _on_refresh_all(self) -> None:
        self._set_error("")
        tables = list(self.project.get("transaction_tables", []))
        sheets_meta = self.project.get("sheets_meta", {})
        project_path = self.project_path

        def worker():
            from core.chain_writer import write_unified_csv
            errors: list[str] = []
            for table_name in tables:
                meta = sheets_meta.get(table_name, {})
                try:
                    if meta.get("is_chained") and meta.get("chain"):
                        write_unified_csv(project_path, table_name, "Transaction", meta)
                    elif meta.get("file_path") and meta.get("sheet_name"):
                        excel_path = Path(meta["file_path"])
                        df = get_sheet_as_dataframe(excel_path, meta["sheet_name"])
                        out = active_transactions_dir(project_path) / f"{table_name}.csv"
                        save_as_csv(df, out)
                    else:
                        errors.append(f"{table_name} (no source path stored)")
                except Exception as exc:
                    errors.append(f"{table_name}: {exc}")
            return errors

        def on_done(errors: list[str]) -> None:
            if errors:
                self._set_error("Refresh issues: " + " | ".join(errors))
            self.on_project_changed(target_key="t_sources")

        self._run_background(
            worker,
            on_done,
            lambda exc: self._set_error(f"Refresh all failed: {exc}"),
        )

    # ------------------------------------------------------------------
    # Append chain (from Screen 3)
    # ------------------------------------------------------------------

    def _on_append_chain(self, table_name: str, chain: list[dict]) -> None:
        self._set_error("")
        if not msgbox.warning_question(
            self,
            "Append File to Chain",
            "Once a file is added to a chain, it cannot be removed on its own.<br><br>"
            "To remove it later you would need to delete the entire chain, which will also "
            "remove all associated mappings. Are you sure you want to continue?",
            confirm_label="Append",
        ):
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Excel file to append", "", "Excel Files (*.xlsx *.xlsm *.xls)"
        )
        if not file_path:
            return
        excel_path = Path(file_path)

        def worker():
            return load_excel_sheets(excel_path)

        def on_sheets_loaded(sheets):
            from ui.popups.popup_single_sheet import select_single_sheet
            picked = select_single_sheet(
                self, excel_path=excel_path, sheet_names=sheets,
                title="Select Sheet to Append",
            )
            if not picked:
                return

            primary_entry = chain[0]
            primary_header_row = self.project.get("sheets_meta", {}).get(
                table_name, {}
            ).get("header_row", primary_entry.get("header_row", 1))
            chain_context = {
                "return_to": "screen3",
                "table_name": table_name,
                "category": "Transaction",
                "existing_chain_length": len(chain),
                "primary_file_path": primary_entry["file_path"],
                "primary_sheet_name": primary_entry["sheet_name"],
                "primary_label": primary_entry.get("label", ""),
                "primary_header_row": primary_header_row,
                "secondary_file_path": str(excel_path),
                "secondary_sheet_name": picked["sheet_name"],
                "secondary_label": excel_path.name,
                "secondary_header_row": picked.get("header_row", 1),
            }
            self._on_chain_append(chain_context)

        self._run_background(
            worker,
            on_sheets_loaded,
            lambda exc: msgbox.critical(self, "Error", f"Could not read file:\n{exc}"),
        )

    # ------------------------------------------------------------------
    # Delete chained source
    # ------------------------------------------------------------------

    def _on_delete_chained(self, table_name: str, chain: list[dict]) -> None:
        self._set_error("")
        chain_summary = "\n".join(
            f"  • {e.get('label', '')} · {e.get('sheet_name', '')}"
            for e in chain
        )
        if not msgbox.critical_question(
            self,
            "Delete Chained Table",
            f"Deleting <b>{table_name}</b> will permanently remove the entire chain and all its linked sources:<br><br>"
            f"{chain_summary}<br><br>"
            f"All mappings referencing this table will also be deleted. This cannot be undone.",
            confirm_label="Delete",
        ):
            return

        def worker():
            import json as _json
            base = active_transactions_dir(self.project_path) / table_name
            for suffix in (".csv", ".parquet"):
                p = base.with_suffix(suffix)
                if p.exists():
                    p.unlink()
                    break
            delete_mappings_for_table(self.project_path, table_name)
            proj_file = self.project_path / "project.json"
            with open(proj_file, encoding="utf-8") as f:
                proj = _json.load(f)
            proj["transaction_tables"] = [
                t for t in proj.get("transaction_tables", []) if t != table_name
            ]
            sheets_meta = proj.get("sheets_meta", {})
            sheets_meta.pop(table_name, None)
            proj["sheets_meta"] = sheets_meta
            with open(proj_file, "w", encoding="utf-8") as f:
                _json.dump(proj, f, indent=2)

        self._run_background(
            worker,
            lambda _: self.on_project_changed(target_key="t_sources"),
            lambda exc: msgbox.critical(self, "Failed to Delete Source",
                                         f"The source could not be deleted. Check that the project folder is accessible.\n\nDetail: {exc}"),
        )

    # ------------------------------------------------------------------
    # Unchained actions (unchanged)
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
            prev_sheet = self.project.get("sheets_meta", {}).get(table_name, {}).get("sheet_name")
            selected = select_single_sheet(
                self, excel_path, sheets,
                title="Select Sheet For Update",
                default_sheet=prev_sheet,
            )
            if not selected:
                return

            def update_worker():
                df = get_sheet_as_dataframe(excel_path, selected["sheet_name"], header_row=selected.get("header_row"))
                out = active_transactions_dir(self.project_path) / f"{table_name}.csv"
                save_as_csv(df, out)
                sheets_meta = dict(self.project.get("sheets_meta", {}))
                existing = dict(sheets_meta.get(table_name, {}))
                existing["file_path"] = str(excel_path)
                existing["sheet_name"] = selected["sheet_name"]
                existing["header_row"] = selected.get("header_row", 1)
                existing["is_chained"] = False
                sheets_meta[table_name] = existing
                save_project_json(self.project_path, {
                    **self.project,
                    "sheets_meta": sheets_meta,
                })

            def on_done(_):
                msgbox.information(self, "Table Updated",
                                   f"<b>{table_name}</b> has been updated with the new data.")
                self.on_project_changed(target_key="t_sources")

            self._run_background(update_worker, on_done,
                                 lambda exc: msgbox.critical(
                                     self, "Failed to Update Table",
                                     f"<b>{table_name}</b> could not be updated. The file may be locked or corrupted.\n\nDetail: {exc}"
                                 ))

        self._run_background(load_sheets_worker, on_sheets_loaded,
                             lambda exc: msgbox.critical(
                                 self, "Failed to Read File",
                                 f"The Excel file could not be opened. Make sure it is not open in another application.\n\nDetail: {exc}"
                             ))

    def _on_delete_table(self, table_name: str) -> None:
        self._set_error("")

        def load_mappings_worker():
            return get_mappings(self.project_path)

        def on_mappings_loaded(mappings):
            count = count_mappings_for_table(mappings, table_name)
            if not msgbox.critical_question(
                self, "Delete Table",
                f"Deleting <b>{table_name}</b> will also remove {count} mapping(s) that reference it.<br><br>"
                f"This action cannot be undone.",
                confirm_label="Delete",
            ):
                return

            def delete_worker():
                base = active_transactions_dir(self.project_path) / table_name
                for suffix in (".csv", ".parquet"):
                    p = base.with_suffix(suffix)
                    if p.exists():
                        p.unlink()
                        break
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
                                 lambda exc: msgbox.critical(
                                     self, "Failed to Delete Table",
                                     f"<b>{table_name}</b> could not be deleted. Check that no files are open.\n\nDetail: {exc}"
                                 ))

        self._run_background(load_mappings_worker, on_mappings_loaded,
                             lambda exc: self._set_error(f"Could not read mappings: {exc}"))
