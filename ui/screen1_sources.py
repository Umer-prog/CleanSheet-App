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

_SIDEBAR_W = 260


# ── Helper functions (logic unchanged) ────────────────────────────────────────

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


def validate_confirm_requirements(
    source_rows: list[dict],
    existing_tx: list | None = None,
    existing_dim: list | None = None,
) -> str | None:
    existing_tx = existing_tx or []
    existing_dim = existing_dim or []

    if not source_rows and not existing_tx and not existing_dim:
        return "Add at least one file before continuing."

    tx_count = len(existing_tx)
    dim_count = len(existing_dim)

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


# ── Screen ─────────────────────────────────────────────────────────────────────

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

        # ── Sidebar ──────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(_SIDEBAR_W)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(0, 0, 0, 0)
        sb.setSpacing(0)

        # Brand block
        brand = QFrame()
        brand.setFixedHeight(64)
        brand.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        bl = QHBoxLayout(brand)
        bl.setContentsMargins(18, 0, 18, 0)
        bl.setSpacing(11)

        logo_box = QFrame()
        logo_box.setFixedSize(34, 34)
        logo_box.setStyleSheet(
            "QFrame { background: #3b82f6; border-radius: 9px; border: none; }"
        )
        logo_inner = QVBoxLayout(logo_box)
        logo_inner.setContentsMargins(0, 0, 0, 0)
        logo_icon = QLabel("▦")
        logo_icon.setAlignment(Qt.AlignCenter)
        logo_icon.setContentsMargins(0, 0, 0, 3)
        logo_icon.setStyleSheet(
            "color: white; background: transparent; border: none; "
            "font-size: 30px; font-weight: 200;"
        )
        logo_inner.addWidget(logo_icon)
        bl.addWidget(logo_box)

        brand_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>{theme.company_name()}</span>"
            "<br>"
            "<span style='color:#475569; font-size:10px; letter-spacing:1px;'>DATA MAPPING</span>"
        )
        brand_lbl.setTextFormat(Qt.RichText)
        brand_lbl.setStyleSheet("background: transparent; border: none;")
        bl.addWidget(brand_lbl)
        sb.addWidget(brand)

        # Progress steps section label
        steps_label = QLabel("SETUP PROGRESS")
        steps_label.setStyleSheet(
            "color: #334155; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "padding: 14px 18px 6px 18px;"
        )
        sb.addWidget(steps_label)

        # Steps
        steps_frame = QFrame()
        steps_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        sf_lay = QVBoxLayout(steps_frame)
        sf_lay.setContentsMargins(12, 8, 12, 8)
        sf_lay.setSpacing(4)

        for num, label, state in [
            ("1", "Load Files", "active"),
            ("2", "Select Sheets", "inactive"),
            ("3", "Map Columns", "inactive"),
        ]:
            sf_lay.addWidget(self._make_step(num, label, state))
        sb.addWidget(steps_frame)

        # Project info section label
        proj_section = QLabel("PROJECT")
        proj_section.setStyleSheet(
            "color: #334155; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "padding: 8px 18px 4px 18px; margin-top: 4px;"
        )
        sb.addWidget(proj_section)

        # Project info card
        proj_card = QFrame()
        proj_card.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.06); "
            "border: 1px solid rgba(59,130,246,0.12); border-radius: 8px; }"
        )
        pc_lay = QVBoxLayout(proj_card)
        pc_lay.setContentsMargins(12, 10, 12, 10)
        pc_lay.setSpacing(2)

        proj_name_lbl = QLabel(project.get("project_name", ""))
        proj_name_lbl.setStyleSheet(
            "color: #93c5fd; background: transparent; border: none; "
            "font-size: 11px; font-weight: 600;"
        )
        proj_company_lbl = QLabel(project.get("company", ""))
        proj_company_lbl.setStyleSheet(
            "color: #334155; background: transparent; border: none; font-size: 10px;"
        )
        pc_lay.addWidget(proj_name_lbl)
        pc_lay.addWidget(proj_company_lbl)

        proj_card_wrap = QWidget()
        proj_card_wrap.setStyleSheet("background: transparent;")
        pcw_lay = QVBoxLayout(proj_card_wrap)
        pcw_lay.setContentsMargins(12, 0, 12, 0)
        pcw_lay.addWidget(proj_card)
        sb.addWidget(proj_card_wrap)

        sb.addStretch()

        # Back button
        back_footer = QFrame()
        back_footer.setFixedHeight(56)
        back_footer.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        bf_lay = QHBoxLayout(back_footer)
        bf_lay.setContentsMargins(12, 10, 12, 10)
        back_btn = QPushButton("← Back to Projects")
        back_btn.setObjectName("btn_ghost")
        back_btn.setFixedHeight(34)
        back_btn.clicked.connect(self._go_back)
        bf_lay.addWidget(back_btn)
        sb.addWidget(back_footer)

        root.addWidget(sidebar)

        # ── Main area ────────────────────────────────────────────────
        main = QFrame()
        main_lay = QVBoxLayout(main)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # Topbar
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(64)
        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(28, 0, 28, 0)

        tb_lbl = QLabel(
            "<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>Data Loader</span>"
            "<br>"
            "<span style='color:#334155; font-size:11px;'>Add Excel files and assign each sheet as Transaction or Dimension</span>"
        )
        tb_lbl.setTextFormat(Qt.RichText)
        tb_lbl.setStyleSheet("background: transparent; border: none;")
        tb_lay.addWidget(tb_lbl, 1)

        add_btn = QPushButton("+ Add File")
        add_btn.setObjectName("btn_primary")
        add_btn.setFixedHeight(34)
        add_btn.clicked.connect(self._on_add_file)
        tb_lay.addWidget(add_btn)
        main_lay.addWidget(topbar)

        # Content area
        content = QFrame()
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(28, 20, 28, 20)
        c_lay.setSpacing(16)

        # Info banner
        banner = QFrame()
        banner.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.06); "
            "border: 1px solid rgba(59,130,246,0.12); border-radius: 8px; }"
        )
        ban_lay = QHBoxLayout(banner)
        ban_lay.setContentsMargins(14, 10, 14, 10)
        ban_lay.setSpacing(8)
        ban_icon = QLabel("ℹ")
        ban_icon.setStyleSheet(
            "color: #60a5fa; background: transparent; border: none; font-size: 14px;"
        )
        ban_icon.setFixedWidth(16)
        ban_text = QLabel(
            "Add at least one Transaction and one Dimension file, then assign sheets before confirming."
        )
        ban_text.setStyleSheet(
            "color: #60a5fa; background: transparent; border: none; font-size: 12px;"
        )
        ban_lay.addWidget(ban_icon)
        ban_lay.addWidget(ban_text, 1)
        c_lay.addWidget(banner)

        # Files area card
        files_card = QFrame()
        files_card.setObjectName("files_area")
        files_card.setStyleSheet(
            "QFrame#files_area { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; }"
        )
        files_lay = QVBoxLayout(files_card)
        files_lay.setContentsMargins(0, 0, 0, 0)
        files_lay.setSpacing(0)

        # Files card header
        files_hdr = QFrame()
        files_hdr.setFixedHeight(44)
        files_hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        fh_lay = QHBoxLayout(files_hdr)
        fh_lay.setContentsMargins(20, 0, 20, 0)
        fh_title = QLabel("LOADED FILES")
        fh_title.setStyleSheet(
            "color: #475569; background: transparent; border: none; "
            "font-size: 11px; font-weight: 600; letter-spacing: 1px;"
        )
        fh_lay.addWidget(fh_title)
        fh_lay.addStretch()
        self._files_count_lbl = QLabel("0 files")
        self._files_count_lbl.setStyleSheet(
            "color: #334155; background: transparent; border: none; font-size: 11px;"
        )
        fh_lay.addWidget(self._files_count_lbl)
        files_lay.addWidget(files_hdr)

        # Switchable body: empty state or populated scroll area
        self._files_body = QFrame()
        self._files_body.setStyleSheet("QFrame { background: transparent; border: none; }")
        self._files_body_lay = QVBoxLayout(self._files_body)
        self._files_body_lay.setContentsMargins(0, 0, 0, 0)
        self._files_body_lay.setSpacing(0)
        files_lay.addWidget(self._files_body, 1)

        c_lay.addWidget(files_card, 1)
        main_lay.addWidget(content, 1)

        # Footer bar
        footer_bar = QFrame()
        footer_bar.setFixedHeight(56)
        footer_bar.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        fb_lay = QHBoxLayout(footer_bar)
        fb_lay.setContentsMargins(28, 0, 28, 0)
        fb_lay.setSpacing(12)

        self._footer_hint = QLabel(
            "Both Transaction and Dimension sheets must be present to continue"
        )
        self._footer_hint.setStyleSheet(
            "color: #475569; background: transparent; border: none; font-size: 12px;"
        )
        fb_lay.addWidget(self._footer_hint, 1)

        self._confirm_btn = QPushButton("Confirm →")
        self._confirm_btn.setObjectName("btn_ghost")
        self._confirm_btn.setFixedHeight(36)
        self._confirm_btn.clicked.connect(self._on_confirm_continue)
        fb_lay.addWidget(self._confirm_btn)
        main_lay.addWidget(footer_bar)

        root.addWidget(main, 1)

        self._setup_overlay("Working...")
        self._render_sources()

    # ── Sidebar helpers ───────────────────────────────────────────────

    def _make_step(self, num: str, label: str, state: str) -> QFrame:
        step = QFrame()
        if state == "active":
            step.setStyleSheet(
                "QFrame { background: rgba(59,130,246,0.1); border-radius: 7px; border: none; }"
            )
        elif state == "done":
            step.setStyleSheet(
                "QFrame { background: rgba(34,211,153,0.06); border-radius: 7px; border: none; }"
            )
        else:
            step.setStyleSheet("QFrame { background: transparent; border-radius: 7px; border: none; }")

        sl = QHBoxLayout(step)
        sl.setContentsMargins(10, 8, 10, 8)
        sl.setSpacing(10)

        circle = QLabel(num)
        circle.setFixedSize(22, 22)
        circle.setAlignment(Qt.AlignCenter)
        if state == "active":
            circle.setStyleSheet(
                "QLabel { background: #3b82f6; border-radius: 11px; border: none; "
                "color: white; font-size: 10px; font-weight: 600; }"
            )
        elif state == "done":
            circle.setText("✓")
            circle.setStyleSheet(
                "QLabel { background: rgba(34,211,153,0.15); border-radius: 11px; "
                "border: 1px solid rgba(34,211,153,0.3); "
                "color: #34d399; font-size: 10px; }"
            )
        else:
            circle.setStyleSheet(
                "QLabel { background: rgba(255,255,255,0.05); border-radius: 11px; "
                "border: 1px solid rgba(255,255,255,0.1); "
                "color: #475569; font-size: 10px; }"
            )
        sl.addWidget(circle)

        lbl = QLabel(label)
        if state == "active":
            lbl.setStyleSheet(
                "color: #93c5fd; background: transparent; border: none; "
                "font-size: 12px; font-weight: 500;"
            )
        elif state == "done":
            lbl.setStyleSheet(
                "color: #34d399; background: transparent; border: none; font-size: 12px;"
            )
        else:
            lbl.setStyleSheet(
                "color: #475569; background: transparent; border: none; font-size: 12px;"
            )
        sl.addWidget(lbl, 1)
        return step

    # ── Rendering ─────────────────────────────────────────────────────

    def _render_sources(self) -> None:
        clear_layout(self._files_body_lay)

        tx_tables = self.project.get("transaction_tables", [])
        dim_tables = self.project.get("dim_tables", [])
        existing_count = len(tx_tables) + len(dim_tables)
        new_count = len(self._sources)

        self._files_count_lbl.setText(
            f"{existing_count + new_count} file{'s' if (existing_count + new_count) != 1 else ''}"
        )

        # Enable confirm if combined existing + new sources satisfy requirements
        can_confirm = validate_confirm_requirements(
            self._sources,
            existing_tx=tx_tables,
            existing_dim=dim_tables,
        ) is None
        self._confirm_btn.setObjectName("btn_primary" if can_confirm else "btn_ghost")
        self._confirm_btn.style().unpolish(self._confirm_btn)
        self._confirm_btn.style().polish(self._confirm_btn)

        has_any = existing_count > 0 or new_count > 0

        if not has_any:
            self._files_body_lay.addWidget(self._make_empty_state())
            return

        scroll, _, layout = make_scroll_area()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)

        # Show already-saved tables first (read-only rows)
        if tx_tables or dim_tables:
            layout.addWidget(self._make_saved_tables_row(tx_tables, dim_tables))

        # Show newly added files (removable)
        for file_index, source in enumerate(self._sources):
            layout.addWidget(self._make_file_row(file_index, source))

        self._files_body_lay.addWidget(scroll)

    def _make_empty_state(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(10)

        icon_box = QFrame()
        icon_box.setFixedSize(52, 52)
        icon_box.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.07); "
            "border: 1px dashed rgba(59,130,246,0.25); border-radius: 12px; }"
        )
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("↑")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #3b82f6; background: transparent; border: none; font-size: 20px;"
        )
        ib_lay.addWidget(icon_lbl)

        title = QLabel("No files added yet")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(
            "color: #64748b; background: transparent; border: none; "
            "font-size: 14px; font-weight: 500;"
        )
        sub = QLabel("Click Add File or drag & drop an Excel file here")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet(
            "color: #334155; background: transparent; border: none; font-size: 12px;"
        )

        lay.addWidget(icon_box, 0, Qt.AlignHCenter)
        lay.addWidget(title)
        lay.addWidget(sub)
        return w

    def _make_saved_tables_row(self, tx_tables: list[str], dim_tables: list[str]) -> QFrame:
        """Read-only row showing tables already persisted from a previous session."""
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: rgba(34,211,153,0.03); border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); }"
        )
        rl = QHBoxLayout(row)
        rl.setContentsMargins(18, 13, 18, 13)
        rl.setSpacing(12)

        # Saved icon
        file_icon = QFrame()
        file_icon.setFixedSize(32, 32)
        file_icon.setStyleSheet(
            "QFrame { background: rgba(34,211,153,0.1); border-radius: 7px; border: none; }"
        )
        fi_lay = QVBoxLayout(file_icon)
        fi_lay.setContentsMargins(0, 0, 0, 0)
        fi_lbl = QLabel("✓")
        fi_lbl.setAlignment(Qt.AlignCenter)
        fi_lbl.setStyleSheet("color: #34d399; background: transparent; border: none; font-size: 14px;")
        fi_lay.addWidget(fi_lbl)
        rl.addWidget(file_icon)

        # Label + badges
        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        fname = QLabel("Previously loaded tables")
        fname.setStyleSheet(
            "color: #64748b; background: transparent; border: none; "
            "font-size: 13px; font-weight: 500;"
        )
        info_col.addWidget(fname)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)
        badges_row.setAlignment(Qt.AlignLeft)
        for t in tx_tables:
            badge = QLabel(f"{t} · T")
            badge.setStyleSheet(
                "color: #60a5fa; background: rgba(59,130,246,0.1); "
                "border: 1px solid rgba(59,130,246,0.2); border-radius: 4px; "
                "font-size: 10px; font-weight: 500; padding: 1px 6px;"
            )
            badges_row.addWidget(badge)
        for t in dim_tables:
            badge = QLabel(f"{t} · D")
            badge.setStyleSheet(
                "color: #34d399; background: rgba(34,211,153,0.08); "
                "border: 1px solid rgba(34,211,153,0.2); border-radius: 4px; "
                "font-size: 10px; font-weight: 500; padding: 1px 6px;"
            )
            badges_row.addWidget(badge)
        badges_row.addStretch()
        info_col.addLayout(badges_row)
        rl.addLayout(info_col, 1)

        saved_lbl = QLabel("Saved")
        saved_lbl.setStyleSheet(
            "color: #34d399; background: rgba(34,211,153,0.08); "
            "border: 1px solid rgba(34,211,153,0.2); border-radius: 4px; "
            "font-size: 10px; font-weight: 500; padding: 2px 8px;"
        )
        rl.addWidget(saved_lbl)

        return row

    def _make_file_row(self, file_index: int, source: dict) -> QFrame:
        row = QFrame()
        row.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); }"
        )
        rl = QHBoxLayout(row)
        rl.setContentsMargins(18, 13, 18, 13)
        rl.setSpacing(12)

        # File icon
        file_icon = QFrame()
        file_icon.setFixedSize(32, 32)
        file_icon.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.1); border-radius: 7px; border: none; }"
        )
        fi_lay = QVBoxLayout(file_icon)
        fi_lay.setContentsMargins(0, 0, 0, 0)
        fi_lbl = QLabel("📄")
        fi_lbl.setAlignment(Qt.AlignCenter)
        fi_lbl.setStyleSheet("background: transparent; border: none; font-size: 14px;")
        fi_lay.addWidget(fi_lbl)
        rl.addWidget(file_icon)

        # Filename + sheet badges
        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        fname = QLabel(Path(source["file_path"]).name)
        fname.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 13px; font-weight: 500;"
        )
        info_col.addWidget(fname)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(6)
        badges_row.setAlignment(Qt.AlignLeft)
        for sheet in source.get("sheets", []):
            cat = sheet.get("category", "")
            badge = QLabel(f"{sheet['sheet_name']} · {'T' if cat == 'Transaction' else 'D'}")
            if cat == "Transaction":
                badge.setStyleSheet(
                    "color: #60a5fa; background: rgba(59,130,246,0.1); "
                    "border: 1px solid rgba(59,130,246,0.2); border-radius: 4px; "
                    "font-size: 10px; font-weight: 500; padding: 1px 6px;"
                )
            else:
                badge.setStyleSheet(
                    "color: #34d399; background: rgba(34,211,153,0.08); "
                    "border: 1px solid rgba(34,211,153,0.2); border-radius: 4px; "
                    "font-size: 10px; font-weight: 500; padding: 1px 6px;"
                )
            badges_row.addWidget(badge)
        badges_row.addStretch()
        info_col.addLayout(badges_row)
        rl.addLayout(info_col, 1)

        # Remove button
        rm_btn = QPushButton("Remove")
        rm_btn.setObjectName("btn_danger")
        rm_btn.setFixedHeight(30)
        rm_btn.setFixedWidth(74)
        rm_btn.clicked.connect(lambda _=False, i=file_index: self._on_remove_file(i))
        rl.addWidget(rm_btn)

        return row

    # ── Actions (logic unchanged) ──────────────────────────────────────

    def _go_back(self) -> None:
        from ui.screen0_launcher import Screen0Launcher
        self.app.show_screen(Screen0Launcher)

    def _set_error(self, msg: str) -> None:
        self._footer_hint.setText(
            msg if msg else "Both Transaction and Dimension sheets must be present to continue"
        )
        self._footer_hint.setStyleSheet(
            f"color: {'#f87171' if msg else '#475569'}; "
            "background: transparent; border: none; font-size: 12px;"
        )

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
            # Filter out sheets already saved in the project or added this session
            already_loaded = self._all_known_table_names()
            available = [s for s in sheet_names
                         if normalize_table_name(s) not in already_loaded]

            if not available:
                self._set_error(
                    f"{excel_path.name} — all sheets from this file are already loaded."
                )
                return

            from ui.popups.popup_sheet_selector import select_sheets
            picked_rows = select_sheets(self, excel_path=excel_path, sheet_names=available)
            if not picked_rows:
                return
            # Belt-and-suspenders duplicate check after selection
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

    def _on_confirm_continue(self) -> None:
        error = validate_confirm_requirements(
            self._sources,
            existing_tx=self.project.get("transaction_tables", []),
            existing_dim=self.project.get("dim_tables", []),
        )
        if error:
            self._set_error(error)
            return
        self._set_error("")

        reply = QMessageBox.question(
            self,
            "Continue to Mapper?",
            "Are you sure you want to proceed?\n\n"
            "You can still come back and add more sheets later.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

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
