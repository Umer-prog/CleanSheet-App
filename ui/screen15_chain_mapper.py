"""Screen 1.5 — Chain Column Mapper.

Inserted between Screen 1 (Data Loader) and Screen 2 (Mappings) whenever
the user adds a chain link to a sheet.  Shows two panels side-by-side:

  Left  — primary sheet columns (locked, read-only)
  Right — dropdowns to pick the matching secondary column, pre-filled by
           auto-match (exact case-insensitive first, then fuzzy fallback).

Cancel → returns to Screen 1 with no state change.
Confirm Chain → saves the column_mapping into the chain entry and
                returns to Screen 1 where the new pill is now visible.
"""
from __future__ import annotations

import tempfile
from difflib import SequenceMatcher
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from ui.widgets import NoScrollComboBox

import ui.theme as theme
from core.data_loader import get_sheet_as_dataframe
from ui.workers import ScreenBase, clear_layout

_ARROW_PATH = Path(tempfile.gettempdir()) / "_cs_combo_arrow_s15.svg"
_ARROW_PATH.write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6">'
    '<polyline points="1,1 5,5 9,1" fill="none" stroke="#94a3b8" '
    'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>",
    encoding="utf-8",
)
_ARROW_URL = str(_ARROW_PATH).replace("\\", "/")

_SIDEBAR_W = 300
_NOT_MAPPED = "— Not Mapped —"
_FUZZY_THRESHOLD = 0.60


# ── Auto-match helpers ────────────────────────────────────────────────────────

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def auto_match(primary_cols: list[str], secondary_cols: list[str]) -> dict[str, str]:
    """Return {primary_col: secondary_col} with no secondary col used twice.

    Pass 1: exact case-insensitive.
    Pass 2: best fuzzy score ≥ threshold for still-unmatched pairs.
    """
    result: dict[str, str] = {}
    used: set[str] = set()

    for p in primary_cols:
        for s in secondary_cols:
            if p.lower() == s.lower() and s not in used:
                result[p] = s
                used.add(s)
                break

    for p in primary_cols:
        if p in result:
            continue
        best_score, best = 0.0, None
        for s in secondary_cols:
            if s in used:
                continue
            score = _similarity(p, s)
            if score > best_score:
                best_score, best = score, s
        if best_score >= _FUZZY_THRESHOLD and best:
            result[p] = best
            used.add(best)

    return result


# ── Screen ────────────────────────────────────────────────────────────────────

class Screen15ChainMapper(ScreenBase):
    """Screen 1.5 — map secondary sheet columns onto the primary sheet."""

    def __init__(
        self,
        app,
        project: dict,
        chain_context: dict,
        sources: list,
        **kwargs,
    ):
        """
        chain_context keys:
            fi, si                          — indices into sources
            primary_file_path               — absolute path of primary xlsx
            primary_sheet_name              — sheet name in primary file
            primary_label                   — display label (filename)
            secondary_file_path             — absolute path of secondary xlsx
            secondary_sheet_name            — sheet name in secondary file
            secondary_label                 — display label (filename)
        sources:
            copy of Screen 1's _sources list, passed back on exit
        """
        super().__init__()
        self.app = app
        self.project = project
        self._ctx = chain_context
        self._sources = sources

        self._primary_cols: list[str] = []
        self._secondary_cols: list[str] = []
        self._mapping_combos: list[tuple[str, NoScrollComboBox]] = []
        self._extra_section: QFrame | None = None
        self._rows_layout: QVBoxLayout | None = None
        self._confirm_btn: QPushButton | None = None
        self._error_label: QLabel | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_sidebar())

        main = QFrame()
        main_lay = QVBoxLayout(main)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)
        main_lay.addWidget(self._build_topbar())
        main_lay.addWidget(self._build_content(), 1)
        main_lay.addWidget(self._build_footer())
        root.addWidget(main, 1)

        self._loading_started = False
        self._setup_overlay("Loading columns…")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # Trigger loading here, not in __init__, so the widget has real geometry
        # when show_on() sizes the overlay — matching how Screen 1 works.
        if not self._loading_started:
            self._loading_started = True
            self._start_loading()

    # ── Sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> QFrame:
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
        logo_box.setStyleSheet("QFrame { background: #2161AC; border-radius: 9px; border: none; }")
        logo_inner = QVBoxLayout(logo_box)
        logo_inner.setContentsMargins(0, 0, 0, 0)
        logo_icon = QLabel()
        logo_icon.setAlignment(Qt.AlignCenter)
        _logo_px = theme.logo_pixmap(24)
        if _logo_px:
            logo_icon.setPixmap(_logo_px)
        else:
            logo_icon.setText("▦")
            logo_icon.setContentsMargins(0, 0, 0, 3)
            logo_icon.setStyleSheet(
                "color: white; background: transparent; border: none; "
                "font-size: 30px; font-weight: 200;"
            )
        logo_inner.addWidget(logo_icon)
        bl.addWidget(logo_box)

        brand_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>"
            f"{theme.company_name()}</span>"
            "<br>"
            "<span style='color:#94a3b8; font-size:10px; letter-spacing:1px;'>GLOBAL DATA 365</span>"
        )
        brand_lbl.setTextFormat(Qt.RichText)
        brand_lbl.setStyleSheet("background: transparent; border: none;")
        bl.addWidget(brand_lbl)
        sb.addWidget(brand)

        steps_label = QLabel("SETUP PROGRESS")
        steps_label.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "padding: 14px 18px 6px 18px;"
        )
        sb.addWidget(steps_label)

        steps_frame = QFrame()
        steps_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        sf_lay = QVBoxLayout(steps_frame)
        sf_lay.setContentsMargins(12, 8, 12, 8)
        sf_lay.setSpacing(4)

        for num, label, state in [
            ("1", "Load Files", "done"),
            ("1.5", "Chain Columns", "active"),
            ("2", "Select Sheets", "inactive"),
            ("3", "Map Columns", "inactive"),
        ]:
            sf_lay.addWidget(self._make_step(num, label, state))
        sb.addWidget(steps_frame)

        proj_section = QLabel("PROJECT")
        proj_section.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "padding: 8px 18px 12px 18px; margin-top: 4px;"
        )
        sb.addWidget(proj_section)

        proj_card = QFrame()
        proj_card.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.06); "
            "border: 1px solid rgba(59,130,246,0.12); border-radius: 8px; }"
        )
        pc_lay = QVBoxLayout(proj_card)
        pc_lay.setContentsMargins(12, 10, 12, 10)
        pc_lay.setSpacing(2)

        proj_name_lbl = QLabel(self.project.get("project_name", ""))
        proj_name_lbl.setStyleSheet(
            "color: #93c5fd; background: transparent; border: none; "
            "font-size: 11px; font-weight: 600;"
        )
        proj_company_lbl = QLabel(self.project.get("company", ""))
        proj_company_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; font-size: 10px;"
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
        return sidebar

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
                "border: 1px solid rgba(34,211,153,0.3); color: #34d399; font-size: 10px; }"
            )
        else:
            circle.setStyleSheet(
                "QLabel { background: rgba(255,255,255,0.05); border-radius: 11px; "
                "border: 1px solid rgba(255,255,255,0.1); color: #94a3b8; font-size: 10px; }"
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
                "color: #94a3b8; background: transparent; border: none; font-size: 12px;"
            )
        sl.addWidget(lbl, 1)
        return step

    # ── Topbar ────────────────────────────────────────────────────────────────

    def _build_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(64)
        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(28, 0, 28, 0)

        tb_lbl = QLabel(
            "<span style='color:#f1f5f9; font-size:20px; font-weight:600;'>Map Columns</span>"
            # "<br>"
            # "<span style='color:#334155; font-size:11px;'>"
            # "Map secondary sheet columns onto the primary sheet's columns</span>"
        )
        tb_lbl.setTextFormat(Qt.RichText)
        tb_lbl.setStyleSheet("background: transparent; border: none;")
        tb_lay.addWidget(tb_lbl, 1)
        return topbar

    # ── Content ───────────────────────────────────────────────────────────────

    def _build_content(self) -> QFrame:
        content = QFrame()
        c_lay = QVBoxLayout(content)
        c_lay.setContentsMargins(28, 20, 28, 12)
        c_lay.setSpacing(14)

        # Mapper card (takes up most vertical space)
        self._mapper_card = QFrame()
        self._mapper_card.setObjectName("chainMapperPanel")
        self._mapper_card.setStyleSheet(
            "QFrame#chainMapperPanel { background: #13161e; border-radius: 8px; "
            "border: 1px solid rgba(255,255,255,0.06); }"
        )
        self._mapper_card_lay = QVBoxLayout(self._mapper_card)
        self._mapper_card_lay.setContentsMargins(0, 0, 0, 0)
        self._mapper_card_lay.setSpacing(0)

        # Loading placeholder — replaced once columns arrive
        self._placeholder = QLabel("Loading columns…")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; font-size: 13px;"
        )
        self._mapper_card_lay.addWidget(self._placeholder)
        # Hidden until data loads to prevent a floating styled box artefact
        self._mapper_card.setVisible(False)
        c_lay.addWidget(self._mapper_card, 1)

        # Rules reminder
        rules = QFrame()
        rules.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.04); "
            "border: 1px solid rgba(59,130,246,0.10); border-radius: 8px; }"
        )
        rf_lay = QVBoxLayout(rules)
        rf_lay.setContentsMargins(14, 10, 14, 10)
        rf_lay.setSpacing(4)
        rules_title = QLabel("RULES")
        rules_title.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        rf_lay.addWidget(rules_title)
        for rule in [
            "Primary file columns are locked",
            "Map secondary file columns according to primary file",
            "Auto-matched by name similarity on load",
        ]:
            r_lbl = QLabel(f"• {rule}")
            r_lbl.setStyleSheet(
                "color: #94a3b8; background: transparent; border: none; font-size: 11px;"
            )
            rf_lay.addWidget(r_lbl)
        c_lay.addWidget(rules)
        return content

    # ── Footer ────────────────────────────────────────────────────────────────

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        fb_lay = QHBoxLayout(footer)
        fb_lay.setContentsMargins(28, 0, 28, 0)
        fb_lay.setSpacing(12)

        self._error_label = QLabel("")
        self._error_label.setStyleSheet(
            "color: #f87171; background: transparent; border: none; font-size: 12px;"
        )
        fb_lay.addWidget(self._error_label, 1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self._on_cancel)
        fb_lay.addWidget(cancel_btn)

        self._confirm_btn = QPushButton("Confirm Chain →")
        self._confirm_btn.setObjectName("btn_primary")
        self._confirm_btn.setFixedHeight(36)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.clicked.connect(self._on_confirm)
        fb_lay.addWidget(self._confirm_btn)
        return footer

    # ── Column loading ────────────────────────────────────────────────────────

    def _start_loading(self) -> None:
        def worker():
            p_df = get_sheet_as_dataframe(
                Path(self._ctx["primary_file_path"]),
                self._ctx["primary_sheet_name"],
                header_row=self._ctx.get("primary_header_row"),
            )
            s_df = get_sheet_as_dataframe(
                Path(self._ctx["secondary_file_path"]),
                self._ctx["secondary_sheet_name"],
                header_row=self._ctx.get("secondary_header_row"),
            )
            return p_df.columns.tolist(), s_df.columns.tolist()

        def on_success(result):
            self._primary_cols, self._secondary_cols = result
            if not self._primary_cols:
                self._placeholder.setText(
                    "Primary sheet has no columns — cannot chain."
                )
                return
            self._build_mapper_rows()

        def on_error(exc):
            self._placeholder.setText(f"Error loading columns: {exc}")

        self._run_background(worker, on_success, on_error)

    # ── Build mapper rows ─────────────────────────────────────────────────────

    def _build_mapper_rows(self) -> None:
        self._mapper_card.setVisible(True)
        clear_layout(self._mapper_card_lay)
        self._mapping_combos.clear()

        # ── Panel header ──────────────────────────────────────────────
        hdr = QFrame()
        hdr.setFixedHeight(44)
        hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        hl = QHBoxLayout(hdr)
        hl.setContentsMargins(20, 0, 20, 0)
        hl.setSpacing(0)

        p_label = self._ctx.get("primary_label", "Primary")
        s_label = self._ctx.get("secondary_label", "Secondary")

        primary_hdr = QLabel(
            f"<span style='color:#f1f5f9; font-size:12px; font-weight:600;'>{p_label}</span>"
            f"&nbsp;&nbsp;<span style='color:#3b82f6; font-size:10px;'>Primary</span>"
        )
        primary_hdr.setTextFormat(Qt.RichText)
        primary_hdr.setStyleSheet("background: transparent; border: none;")
        hl.addWidget(primary_hdr, 1)

        # Spacer matching the arrow column width in the data rows
        arrow_spacer = QWidget()
        arrow_spacer.setFixedWidth(120)  # arrow(100) + spacing(10*2)
        arrow_spacer.setStyleSheet("background: transparent;")
        hl.addWidget(arrow_spacer)

        secondary_hdr = QLabel(
            f"<span style='color:#f1f5f9; font-size:12px; font-weight:600;'>{s_label}</span>"
        )
        secondary_hdr.setTextFormat(Qt.RichText)
        secondary_hdr.setStyleSheet("background: transparent; border: none;")
        hl.addWidget(secondary_hdr, 1)

        self._mapper_card_lay.addWidget(hdr)

        # ── Scrollable mapping rows ───────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        self._rows_layout = QVBoxLayout(container)
        self._rows_layout.setContentsMargins(0, 0, 0, 0)
        self._rows_layout.setSpacing(0)
        self._rows_layout.setAlignment(Qt.AlignTop)

        matches = auto_match(self._primary_cols, self._secondary_cols)
        dropdown_items = [_NOT_MAPPED] + self._secondary_cols

        for primary_col in self._primary_cols:
            row = QFrame()
            row.setFixedHeight(48)
            row.setStyleSheet(
                "QFrame { background: transparent; border: none; "
                "border-bottom: 1px solid rgba(255,255,255,0.03); }"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(20, 0, 20, 0)
            rl.setSpacing(10)

            # Left: primary column name (no lock icon — columns are visually dimmed)
            left = QLabel(primary_col)
            left.setObjectName("primaryColLocked")
            left.setStyleSheet(
                "color: #94a3b8; background: transparent; border: none; "
                "font-size: 12px; font-family: 'Courier New', monospace;"
            )
            rl.addWidget(left, 1)

            # Centre: long horizontal mapping arrow
            arrow = QLabel("─────────→")
            arrow.setFixedWidth(100)
            arrow.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
            arrow.setStyleSheet(
                "color: #94a3b8; background: transparent; border: none; "
                "font-size: 13px; letter-spacing: 1px;"
            )
            rl.addWidget(arrow)

            # Right: secondary column dropdown
            combo = NoScrollComboBox()
            combo.setFixedHeight(32)
            combo.addItems(dropdown_items)
            combo.setStyleSheet(self._combo_style(duplicate=False))

            matched = matches.get(primary_col)
            if matched:
                combo.setCurrentText(matched)
            else:
                combo.setCurrentIndex(0)

            combo.currentIndexChanged.connect(self._on_combo_changed)
            self._mapping_combos.append((primary_col, combo))
            rl.addWidget(combo, 1)

            self._rows_layout.addWidget(row)

        # Extra secondary columns placeholder (rebuilt on each combo change)
        self._extra_section = QFrame()
        self._extra_section.setStyleSheet(
            "QFrame { background: transparent; border: none; }"
        )
        self._extra_section_lay = QVBoxLayout(self._extra_section)
        self._extra_section_lay.setContentsMargins(0, 0, 0, 0)
        self._extra_section_lay.setSpacing(0)
        self._rows_layout.addWidget(self._extra_section)

        self._rows_layout.addStretch()
        scroll.setWidget(container)
        self._mapper_card_lay.addWidget(scroll, 1)

        # Trigger initial validation + extra-row build
        self._on_combo_changed()

    # ── Combo validation ──────────────────────────────────────────────────────

    @staticmethod
    def _combo_style(duplicate: bool = False) -> str:
        border = "1px solid #ef4444" if duplicate else "1px solid rgba(255,255,255,0.09)"
        return (
            f"QComboBox {{ background: rgba(255,255,255,0.04); border: {border}; "
            "border-radius: 6px; color: #f1f5f9; font-size: 12px; "
            "font-family: 'Courier New', monospace; padding: 0 10px 0 10px; }"
            "QComboBox::drop-down { border: none; width: 28px; "
            "subcontrol-origin: padding; subcontrol-position: right center; }"
            f"QComboBox::down-arrow {{ image: url({_ARROW_URL}); width: 10px; height: 6px; }}"
            "QComboBox QAbstractItemView { background: #13161e; color: #f1f5f9; "
            "border: 1px solid rgba(255,255,255,0.09); "
            "selection-background-color: rgba(59,130,246,0.18); outline: none; }"
        )

    def _find_duplicates(self) -> set[str]:
        seen: set[str] = set()
        dupes: set[str] = set()
        for _, combo in self._mapping_combos:
            val = combo.currentText()
            if val == _NOT_MAPPED:
                continue
            if val in seen:
                dupes.add(val)
            seen.add(val)
        return dupes

    def _on_combo_changed(self) -> None:
        dupes = self._find_duplicates()

        for _, combo in self._mapping_combos:
            val = combo.currentText()
            is_dup = val != _NOT_MAPPED and val in dupes
            combo.setStyleSheet(self._combo_style(duplicate=is_dup))

        if dupes:
            if self._error_label:
                self._error_label.setText(
                    "Duplicate mapping — each secondary column can only be used once."
                )
            if self._confirm_btn:
                self._confirm_btn.setEnabled(False)
        else:
            if self._error_label:
                self._error_label.setText("")
            if self._confirm_btn:
                self._confirm_btn.setEnabled(True)

        self._rebuild_extra_section()

    def _rebuild_extra_section(self) -> None:
        """Refresh the informational extra-columns section below the mapped rows."""
        if self._extra_section is None:
            return

        clear_layout(self._extra_section_lay)

        currently_mapped: set[str] = {
            combo.currentText()
            for _, combo in self._mapping_combos
            if combo.currentText() != _NOT_MAPPED
        }
        extra_cols = [s for s in self._secondary_cols if s not in currently_mapped]

        if not extra_cols:
            return

        # Section label
        sep = QFrame()
        sep.setFixedHeight(30)
        sep.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.01); border: none; "
            "border-top: 1px solid rgba(255,255,255,0.05); }"
        )
        sep_lay = QHBoxLayout(sep)
        sep_lay.setContentsMargins(20, 0, 20, 0)
        sep_lbl = QLabel("EXTRA/UNMAPPED COLUMNS — not mapped with any primary file column")
        sep_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 0.4px;"
        )
        sep_lay.addWidget(sep_lbl)
        self._extra_section_lay.addWidget(sep)

        for col in extra_cols:
            row = QFrame()
            row.setFixedHeight(34)
            row.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.01); border: none; "
                "border-bottom: 1px solid rgba(255,255,255,0.02); }"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(20, 0, 20, 0)
            rl.setSpacing(0)

            blank = QLabel("—")
            blank.setStyleSheet(
                "color: #1f2937; background: transparent; border: none; font-size: 12px;"
            )
            rl.addWidget(blank, 1)

            vline = QFrame()
            vline.setFixedWidth(1)
            vline.setStyleSheet("background: rgba(255,255,255,0.04); border: none;")
            rl.addWidget(vline)

            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            wl = QHBoxLayout(wrap)
            wl.setContentsMargins(16, 0, 0, 0)
            col_lbl = QLabel(col)
            col_lbl.setStyleSheet(
                "color: #374151; background: transparent; border: none; "
                "font-size: 12px; font-family: 'Courier New', monospace; font-style: italic;"
            )
            wl.addWidget(col_lbl)
            wl.addStretch()
            rl.addWidget(wrap, 1)

            self._extra_section_lay.addWidget(row)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _set_error(self, msg: str) -> None:
        if self._error_label:
            self._error_label.setText(msg)

    def _on_cancel(self) -> None:
        if self._ctx.get("return_to") == "screen3":
            self._return_to_screen3()
        else:
            from ui.screen1_sources import Screen1Sources
            self.app.show_screen(Screen1Sources, project=self.project, sources=self._sources)

    def _return_to_screen3(self) -> None:
        from core.project_manager import open_project
        from ui.screen3_main import Screen3Main
        try:
            updated = open_project(Path(self.project["project_path"]))
        except Exception:
            updated = self.project
        self.app.set_current_project(updated)
        nav_key = "d_sources" if self._ctx.get("category") == "Dimension" else "t_sources"
        self.app.show_screen(Screen3Main, project=updated, initial_nav_key=nav_key)

    def _on_confirm(self) -> None:
        if self._find_duplicates():
            return

        column_mapping: dict[str, str] = {
            p: combo.currentText()
            for p, combo in self._mapping_combos
            if combo.currentText() != _NOT_MAPPED
        }

        if self._ctx.get("return_to") == "screen3":
            self._confirm_screen3(column_mapping)
        else:
            self._confirm_screen1(column_mapping)

    def _confirm_screen1(self, column_mapping: dict) -> None:
        fi = self._ctx["fi"]
        si = self._ctx["si"]
        sheet = self._sources[fi]["sheets"][si]
        chain = list(sheet.get("chain", []))

        if not sheet.get("is_chained", False):
            chain = [{
                "order": 0,
                "file_path": self._ctx["primary_file_path"],
                "sheet_name": self._ctx["primary_sheet_name"],
                "label": self._ctx.get("primary_label", ""),
                "column_mapping": None,
            }]

        chain.append({
            "order": len(chain),
            "file_path": self._ctx["secondary_file_path"],
            "sheet_name": self._ctx["secondary_sheet_name"],
            "label": self._ctx["secondary_label"],
            "column_mapping": column_mapping or None,
        })

        sheet["is_chained"] = True
        sheet["chain"] = chain

        from ui.screen1_sources import Screen1Sources
        self.app.show_screen(Screen1Sources, project=self.project, sources=self._sources)

    def _confirm_screen3(self, column_mapping: dict) -> None:
        import json as _json
        table_name = self._ctx["table_name"]
        category = self._ctx["category"]
        project_path = Path(self.project["project_path"])

        new_entry = {
            "order": self._ctx["existing_chain_length"],
            "file_path": self._ctx["secondary_file_path"],
            "sheet_name": self._ctx["secondary_sheet_name"],
            "label": self._ctx["secondary_label"],
            "header_row": self._ctx.get("secondary_header_row", 1),
            "column_mapping": column_mapping or None,
        }

        if self._confirm_btn:
            self._confirm_btn.setEnabled(False)

        def worker():
            from core.project_manager import open_project
            # Screen 3 append: load existing processed chain data and merge in
            # only the new sheet — do NOT re-read previously chained source files
            # so that already-resolved errors are never re-introduced.
            from core.chain_writer import append_sheet_to_existing_chain
            proj_file = project_path / "project.json"
            with open(proj_file, encoding="utf-8") as f:
                proj = _json.load(f)
            sheets_meta = proj.get("sheets_meta", {})
            table_meta = dict(sheets_meta.get(table_name, {}))
            chain = list(table_meta.get("chain", []))
            chain.append(new_entry)
            for i, e in enumerate(chain):
                e["order"] = i
            table_meta["chain"] = chain
            table_meta["is_chained"] = True
            sheets_meta[table_name] = table_meta
            proj["sheets_meta"] = sheets_meta
            with open(proj_file, "w", encoding="utf-8") as f:
                _json.dump(proj, f, indent=2)
            append_sheet_to_existing_chain(
                project_path, table_name, category, table_meta, new_entry
            )
            return open_project(project_path)

        def on_done(updated_project):
            self.app.set_current_project(updated_project)
            from ui.screen3_main import Screen3Main
            nav_key = "d_sources" if category == "Dimension" else "t_sources"
            self.app.show_screen(Screen3Main, project=updated_project, initial_nav_key=nav_key)

        def on_error(exc):
            if self._error_label:
                self._error_label.setText(f"Save failed: {exc}")
            if self._confirm_btn:
                self._confirm_btn.setEnabled(True)

        self._run_background(worker, on_done, on_error)
