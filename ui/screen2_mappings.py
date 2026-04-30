from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
import ui.popups.msgbox as msgbox
from core.data_loader import load_csv, read_table
from core.mapping_manager import add_mapping, delete_mappings_for_table, get_mappings
from core.project_manager import save_project_json
from core.project_paths import active_dim_dir, active_transactions_dir
from ui.widgets import NoScrollComboBox
from ui.workers import ScreenBase, clear_layout, make_scroll_area

_SIDEBAR_W = 300

# Tiny SVG chevron written once to a temp file; referenced as a QComboBox down-arrow image.
_ARROW_PATH = Path(tempfile.gettempdir()) / "_cs_combo_arrow.svg"
_ARROW_PATH.write_text(
    '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6">'
    '<polyline points="1,1 5,5 9,1" fill="none" stroke="#94a3b8" '
    'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
    "</svg>",
    encoding="utf-8",
)
_ARROW_URL = str(_ARROW_PATH).replace("\\", "/")


def mapping_key(mapping: dict) -> tuple:
    return (
        mapping.get("transaction_table", "").strip(),
        mapping.get("transaction_column", "").strip(),
        mapping.get("dim_table", "").strip(),
        mapping.get("dim_column", "").strip(),
    )


def validate_mapping_selection(
    transaction_table, dim_table, transaction_column, dim_column
) -> str | None:
    if not dim_table:
        return "Select a dimension table."
    if not transaction_table:
        return "Select a transaction table."
    if not dim_column or dim_column == "Select Column":
        return "Select a dimension column."
    if not transaction_column or transaction_column == "Select Column":
        return "Select a transaction column."
    return None


def find_unmapped_tables(
    transaction_tables: list[str], dim_tables: list[str], mappings: list[dict]
) -> tuple[list[str], list[str]]:
    mapped_tx = {m.get("transaction_table", "").strip() for m in mappings}
    mapped_dim = {m.get("dim_table", "").strip() for m in mappings}
    return (
        [t for t in transaction_tables if t not in mapped_tx],
        [t for t in dim_tables if t not in mapped_dim],
    )


class Screen2Mappings(ScreenBase):
    """Stage 2 — define dimension/transaction column mappings."""

    def __init__(self, app, project: dict, from_screen3: bool = False, **kwargs):
        super().__init__()
        self.app = app
        self.project = project
        self.project_path = Path(project["project_path"])
        self._from_screen3 = from_screen3

        self._transaction_tables = list(project.get("transaction_tables", []))
        self._dim_tables = list(project.get("dim_tables", []))
        self._locked_mappings: list[dict] = self._load_existing_mappings()
        self._pending_mappings: list[dict] = []

        self._selected_dim_table: str | None = None
        self._selected_transaction_table: str | None = None
        self._dim_buttons: dict[str, QPushButton] = {}
        self._transaction_buttons: dict[str, QPushButton] = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_sidebar())
        root.addWidget(self._make_main(), 1)

        self._setup_overlay("Loading...")
        self._refresh_tables()
        self._refresh_mappings()
        self._update_finish_btn()

    def _load_existing_mappings(self) -> list[dict]:
        try:
            return get_mappings(self.project_path)
        except Exception:
            return []

    # ── Sidebar ───────────────────────────────────────────────────────

    def _make_sidebar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("s2_sidebar")
        sidebar.setFixedWidth(_SIDEBAR_W)
        sidebar.setStyleSheet(
            "QFrame#s2_sidebar { background: #13161e; border: none; "
            "border-right: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Brand block
        brand = QFrame()
        brand.setFixedHeight(64)
        brand.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        b_lay = QHBoxLayout(brand)
        b_lay.setContentsMargins(18, 0, 18, 0)
        b_lay.setSpacing(11)

        logo_box = QFrame()
        logo_box.setFixedSize(34, 34)
        logo_box.setStyleSheet(
            "QFrame { background: #2161AC; border-radius: 9px; border: none; }"
        )
        logo_inner = QVBoxLayout(logo_box)
        logo_inner.setContentsMargins(0, 0, 0, 0)
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        _logo_px = theme.logo_pixmap(24)
        if _logo_px:
            logo_lbl.setPixmap(_logo_px)
        else:
            logo_lbl.setText("▦")
            logo_lbl.setContentsMargins(0, 0, 0, 3)
            logo_lbl.setStyleSheet(
                "color: white; background: transparent; border: none; font-size: 30px;"
            )
        logo_inner.addWidget(logo_lbl)
        b_lay.addWidget(logo_box)

        brand_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>{theme.company_name()}</span>"
            "<br>"
            "<span style='color:#94a3b8; font-size:10px; letter-spacing:1px;'>GLOBAL DATA 365</span>"
        )
        brand_lbl.setTextFormat(Qt.RichText)
        brand_lbl.setStyleSheet("background: transparent; border: none;")
        b_lay.addWidget(brand_lbl, 1)
        lay.addWidget(brand)

        # "SETUP PROGRESS" label
        prog_lbl = QLabel("SETUP PROGRESS")
        prog_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "padding: 14px 18px 6px 18px;"
        )
        lay.addWidget(prog_lbl)

        # Steps
        steps_frame = QFrame()
        steps_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        sf_lay = QVBoxLayout(steps_frame)
        sf_lay.setContentsMargins(12, 8, 12, 8)
        sf_lay.setSpacing(4)
        sf_lay.addWidget(self._make_step("✓", "Load Files", "done"))
        sf_lay.addWidget(self._make_step("✓", "Select Sheets", "done"))
        sf_lay.addWidget(self._make_step("3", "Map Columns", "active"))
        lay.addWidget(steps_frame)

        # "PROJECT" label
        proj_lbl = QLabel("PROJECT")
        proj_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "padding: 8px 18px 12px 18px; margin-top: 4px;"
        )
        lay.addWidget(proj_lbl)

        # Project info card
        info_card = QFrame()
        info_card.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.06); "
            "border: 1px solid rgba(59,130,246,0.12); border-radius: 8px; }"
        )
        ic_lay = QVBoxLayout(info_card)
        ic_lay.setContentsMargins(12, 10, 12, 10)
        ic_lay.setSpacing(2)
        proj_name = self.project.get("project_name", "—")
        proj_client = self.project.get("company_name", "")
        pn_lbl = QLabel(proj_name)
        pn_lbl.setStyleSheet(
            "color: #93c5fd; background: transparent; border: none; "
            "font-size: 11px; font-weight: 600;"
        )
        pc_lbl = QLabel(proj_client)
        pc_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; font-size: 10px;"
        )
        ic_lay.addWidget(pn_lbl)
        ic_lay.addWidget(pc_lbl)

        info_wrap = QFrame()
        info_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        iw_lay = QHBoxLayout(info_wrap)
        iw_lay.setContentsMargins(12, 0, 12, 0)
        iw_lay.addWidget(info_card)
        lay.addWidget(info_wrap)

        lay.addStretch(1)

        # Back / Cancel button
        back_wrap = QFrame()
        back_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        bw_lay = QHBoxLayout(back_wrap)
        bw_lay.setContentsMargins(12, 12, 12, 12)
        if self._from_screen3:
            back_btn = QPushButton("✕  Cancel")
            back_btn.setObjectName("btn_ghost")
            back_btn.setFixedHeight(32)
            back_btn.setStyleSheet(
                "QPushButton { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.2); "
                "border-radius: 7px; color: #f87171; font-size: 12px; padding: 0 12px; }"
                "QPushButton:hover { background: rgba(239,68,68,0.18); color: #fca5a5; }"
            )
            back_btn.clicked.connect(self._cancel_to_screen3)
        else:
            back_btn = QPushButton("← Back to Data Loader")
            back_btn.setObjectName("btn_ghost")
            back_btn.setFixedHeight(32)
            back_btn.clicked.connect(self._go_back)
        bw_lay.addWidget(back_btn)
        lay.addWidget(back_wrap)

        return sidebar

    @staticmethod
    def _make_step(num: str, label: str, state: str) -> QFrame:
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

        circle = QFrame()
        circle.setFixedSize(22, 22)
        if state == "active":
            circle.setStyleSheet(
                "QFrame { background: #3b82f6; border: 1px solid #3b82f6; "
                "border-radius: 11px; }"
            )
        elif state == "done":
            circle.setStyleSheet(
                "QFrame { background: rgba(34,211,153,0.15); "
                "border: 1px solid rgba(34,211,153,0.3); border-radius: 11px; }"
            )
        else:
            circle.setStyleSheet(
                "QFrame { background: rgba(255,255,255,0.05); "
                "border: 1px solid rgba(255,255,255,0.1); border-radius: 11px; }"
            )
        c_inner = QVBoxLayout(circle)
        c_inner.setContentsMargins(0, 0, 0, 0)
        num_lbl = QLabel(num)
        num_lbl.setAlignment(Qt.AlignCenter)
        if state == "active":
            num_lbl.setStyleSheet(
                "color: #fff; background: transparent; border: none; font-size: 10px;"
            )
        elif state == "done":
            num_lbl.setStyleSheet(
                "color: #34d399; background: transparent; border: none; font-size: 10px;"
            )
        else:
            num_lbl.setStyleSheet(
                "color: #94a3b8; background: transparent; border: none; font-size: 10px;"
            )
        c_inner.addWidget(num_lbl)
        sl.addWidget(circle)

        step_lbl = QLabel(label)
        if state == "active":
            step_lbl.setStyleSheet(
                "color: #93c5fd; background: transparent; border: none; "
                "font-size: 12px; font-weight: 500;"
            )
        elif state == "done":
            step_lbl.setStyleSheet(
                "color: #34d399; background: transparent; border: none; font-size: 12px;"
            )
        else:
            step_lbl.setStyleSheet(
                "color: #94a3b8; background: transparent; border: none; font-size: 12px;"
            )
        sl.addWidget(step_lbl, 1)
        return step

    # ── Main area ─────────────────────────────────────────────────────

    def _make_main(self) -> QWidget:
        main = QWidget()
        main.setStyleSheet("background: #0f1117;")
        m_lay = QVBoxLayout(main)
        m_lay.setContentsMargins(0, 0, 0, 0)
        m_lay.setSpacing(0)

        m_lay.addWidget(self._make_topbar())
        m_lay.addWidget(self._make_content(), 1)
        m_lay.addWidget(self._make_footer())

        return main

    def _make_topbar(self) -> QFrame:
        topbar = QFrame()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        t_lay = QHBoxLayout(topbar)
        t_lay.setContentsMargins(28, 0, 28, 0)

        topbar_lbl = QLabel(
            "<span style='color:#f1f5f9; font-size:20px; font-weight:600;'>Table Mapping</span>"
            # "<br>"
            # "<span style='color:#334155; font-size:11px;'>Select one table on each side, pick columns, then confirm. "
            # "Repeat until all tables are mapped.</span>"
        )
        topbar_lbl.setTextFormat(Qt.RichText)
        topbar_lbl.setStyleSheet("background: transparent; border: none;")
        t_lay.addWidget(topbar_lbl, 1)
        return topbar

    def _make_content(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(container)
        c_lay.setContentsMargins(20, 20, 20, 20)
        c_lay.setSpacing(16)

        # ── mapper-grid: Dimension | Transaction ──────────────────────
        mapper_grid = QHBoxLayout()
        mapper_grid.setSpacing(16)

        # Dimension Tables panel
        dim_panel = self._make_panel("Dimension Tables", "dim")
        self._dim_scroll, _, self._dim_btn_layout = make_scroll_area()
        self._dim_btn_layout.setContentsMargins(10, 10, 10, 10)
        self._dim_btn_layout.setSpacing(6)
        self._dim_btn_layout.setAlignment(Qt.AlignTop)
        dim_panel.layout().addWidget(self._dim_scroll, 1)
        mapper_grid.addWidget(dim_panel, 1)

        # Transaction Tables panel
        tx_panel = self._make_panel("Transaction Tables", "tx")
        self._tx_scroll, _, self._tx_btn_layout = make_scroll_area()
        self._tx_btn_layout.setContentsMargins(10, 10, 10, 10)
        self._tx_btn_layout.setSpacing(6)
        self._tx_btn_layout.setAlignment(Qt.AlignTop)
        tx_panel.layout().addWidget(self._tx_scroll, 1)
        mapper_grid.addWidget(tx_panel, 1)

        c_lay.addLayout(mapper_grid)

        # ── col-grid: Dim Column | Confirm Btn | Tx Column ────────────
        col_grid = QHBoxLayout()
        col_grid.setSpacing(12)

        _combo_style = (
            "QComboBox { background: rgba(255,255,255,0.05); "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; "
            "color: #cbd5e1; font-size: 12px; padding: 0 12px; min-height: 36px; }"
            "QComboBox:hover { border-color: rgba(255,255,255,0.22); }"
            "QComboBox:on { border-color: #3b82f6; }"
            "QComboBox::drop-down { border: none; width: 28px; "
            "subcontrol-origin: padding; subcontrol-position: right center; }"
            f"QComboBox::down-arrow {{ image: url({_ARROW_URL}); width: 10px; height: 6px; }}"
            "QComboBox QAbstractItemView { background: #1e2330; "
            "border: 1px solid rgba(255,255,255,0.1); color: #cbd5e1; "
            "selection-background-color: rgba(59,130,246,0.3); outline: none; }"
        )

        dim_col_panel, dim_col_body = self._make_col_panel("Dimension Column")
        self._dim_column_menu = NoScrollComboBox()
        self._dim_column_menu.addItem("Select Column")
        self._dim_column_menu.setMinimumHeight(36)
        self._dim_column_menu.setStyleSheet(_combo_style)
        dim_col_body.addWidget(self._dim_column_menu)
        col_grid.addWidget(dim_col_panel, 1)

        # Centre: arrow indicator + Confirm button pushed toward bottom
        confirm_wrap = QWidget()
        confirm_wrap.setFixedWidth(130)
        confirm_wrap.setStyleSheet("background: transparent;")
        cw_lay = QVBoxLayout(confirm_wrap)
        cw_lay.setContentsMargins(0, 0, 0, 0)
        cw_lay.setSpacing(0)
        cw_lay.setAlignment(Qt.AlignHCenter)

        cw_lay.addStretch(2)

        arrow_lbl = QLabel("\u2190\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2192")
        arrow_lbl.setAlignment(Qt.AlignCenter)
        arrow_lbl.setFixedWidth(110)
        arrow_lbl.setStyleSheet(
            "color: #6b7280; background: transparent; "
            "border: none; "
            "font-size: 14px; padding: 6px 0; letter-spacing: 1px;"
        )
        cw_lay.addWidget(arrow_lbl, 0, Qt.AlignHCenter)

        cw_lay.addStretch(1)

        confirm_mapping_btn = QPushButton("Confirm Mapping")
        confirm_mapping_btn.setFixedSize(120, 50)
        confirm_mapping_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; border: none; border-radius: 8px; "
            "color: #ffffff; font-size: 12px; font-weight: 500; padding: 0 12px; }"
            "QPushButton:hover { background: #2563eb; }"
            "QPushButton:pressed { background: #1d4ed8; }"
        )
        confirm_mapping_btn.clicked.connect(self._on_confirm_mapping)
        cw_lay.addWidget(confirm_mapping_btn, 0, Qt.AlignHCenter)

        cw_lay.addSpacing(20)
        col_grid.addWidget(confirm_wrap)

        tx_col_panel, tx_col_body = self._make_col_panel("Transaction Column")
        self._tx_column_menu = NoScrollComboBox()
        self._tx_column_menu.addItem("Select Column")
        self._tx_column_menu.setMinimumHeight(36)
        self._tx_column_menu.setStyleSheet(_combo_style)
        tx_col_body.addWidget(self._tx_column_menu)
        col_grid.addWidget(tx_col_panel, 1)

        c_lay.addLayout(col_grid)

        # ── Mappings panel ────────────────────────────────────────────
        mappings_panel = QFrame()
        mappings_panel.setObjectName("s2_mp")
        mappings_panel.setStyleSheet(
            "QFrame#s2_mp { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; }"
        )
        mp_lay = QVBoxLayout(mappings_panel)
        mp_lay.setContentsMargins(0, 0, 0, 0)
        mp_lay.setSpacing(0)

        mp_header = QFrame()
        mp_header.setFixedHeight(40)
        mp_header.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        mph_lay = QHBoxLayout(mp_header)
        mph_lay.setContentsMargins(16, 0, 16, 0)
        mp_title_lbl = QLabel("CONFIRMED MAPPINGS")
        mp_title_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        self._mappings_count_lbl = QLabel("0 mappings")
        self._mappings_count_lbl.setFixedHeight(30)
        self._mappings_count_lbl.setStyleSheet(
            "color: #94a3b8; background: rgba(255,255,255,0.05); border: none; "
            "font-size: 11px; padding: 2px 8px; border-radius: 10px;"
        )
        mph_lay.addWidget(mp_title_lbl)
        mph_lay.addStretch()
        mph_lay.addWidget(self._mappings_count_lbl)
        mp_lay.addWidget(mp_header)

        self._mapping_scroll, _, self._mapping_list_layout = make_scroll_area()
        self._mapping_list_layout.setContentsMargins(0, 0, 0, 0)
        self._mapping_list_layout.setSpacing(0)
        self._mapping_list_layout.setAlignment(Qt.AlignTop)
        mp_lay.addWidget(self._mapping_scroll, 1)

        c_lay.addWidget(mappings_panel)

        scroll.setWidget(container)
        return scroll

    def _make_panel(self, label: str, kind: str) -> QFrame:
        """Returns a panel QFrame with a header row already added; caller adds body."""
        panel = QFrame()
        panel.setObjectName(f"s2_panel_{kind}")
        panel.setStyleSheet(
            f"QFrame#s2_panel_{kind} {{ background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; }"
        )
        p_lay = QVBoxLayout(panel)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(40)
        header.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(16, 0, 16, 0)

        title_lbl = QLabel(label.upper())
        title_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()

        if kind == "dim":
            count = len(self._dim_tables)
            tag_color = "rgba(34,211,153,0.1)"
            tag_text_color = "#34d399"
        else:
            count = len(self._transaction_tables)
            tag_color = "rgba(59,130,246,0.1)"
            tag_text_color = "#60a5fa"

        tag = QLabel(f"{count} table{'s' if count != 1 else ''}")
        tag.setFixedHeight(25)
        tag.setStyleSheet(
            f"color: {tag_text_color}; background: {tag_color}; border: none; "
            "font-size: 10px; padding: 2px 7px; border-radius: 4px;"
        )
        h_lay.addWidget(tag)
        p_lay.addWidget(header)
        return panel

    def _make_col_panel(self, label: str) -> tuple[QFrame, QVBoxLayout]:
        """Returns (panel_frame, body_layout) — caller adds its widget to body_layout."""
        panel = QFrame()
        panel.setObjectName("s2_col_panel")
        panel.setStyleSheet(
            "QFrame#s2_col_panel { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 10px; }"
        )
        p_lay = QVBoxLayout(panel)
        p_lay.setContentsMargins(0, 0, 0, 0)
        p_lay.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(38)
        header.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(14, 0, 14, 0)
        lbl = QLabel(label.upper())
        lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        h_lay.addWidget(lbl)
        p_lay.addWidget(header)

        body = QFrame()
        body.setStyleSheet("QFrame { background: transparent; border: none; }")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(10, 10, 10, 10)
        p_lay.addWidget(body)

        return panel, b_lay

    def _make_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(28, 0, 28, 0)
        f_lay.setSpacing(8)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            "color: #f87171; background: transparent; border: none; font-size: 12px;"
        )
        self._footer_hint = QLabel("")
        self._footer_hint.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; font-size: 12px;"
        )
        f_lay.addWidget(self._footer_hint)
        f_lay.addWidget(self._error_lbl)
        f_lay.addStretch()

        self._finish_btn = QPushButton("Finish Setup →")
        self._finish_btn.setFixedHeight(36)
        self._finish_btn.setFixedWidth(140)
        self._finish_btn.clicked.connect(self._on_finish_setup)
        f_lay.addWidget(self._finish_btn, 0, Qt.AlignVCenter)
        return footer

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _go_back(self) -> None:
        from ui.screen1_sources import Screen1Sources
        self.app.show_screen(Screen1Sources, project=self.project)

    def _cancel_to_screen3(self) -> None:
        from ui.screen3_main import Screen3Main
        self.app.show_screen(Screen3Main, project=self.project)

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)
        self._footer_hint.setVisible(not bool(msg))

    def _update_finish_btn(self) -> None:
        has_mapping = bool(self._locked_mappings or self._pending_mappings)
        self._finish_btn.setEnabled(has_mapping)
        if has_mapping:
            self._finish_btn.setStyleSheet(
                "QPushButton { background: #3b82f6; border: none; border-radius: 8px; "
                "color: #ffffff; font-size: 12px; font-weight: 500; padding: 0 16px; }"
                "QPushButton:hover { background: #2563eb; }"
                "QPushButton:pressed { background: #1d4ed8; }"
            )
            self._footer_hint.setText(
                "Add new mappings above, then click Finish to save and continue."
                if self._locked_mappings
                else "At least 1 mapping confirmed. Click Finish when ready."
            )
        else:
            self._finish_btn.setStyleSheet(
                "QPushButton { background: #1a2235; border: 1px solid rgba(255,255,255,0.08); "
                "border-radius: 8px; color: #94a3b8; font-size: 12px; "
                "font-weight: 500; padding: 0 16px; }"
            )
            self._footer_hint.setText("Add at least 1 mapping before finishing setup.")

    # ------------------------------------------------------------------
    # Table selection
    # ------------------------------------------------------------------

    def _refresh_tables(self) -> None:
        clear_layout(self._dim_btn_layout)
        clear_layout(self._tx_btn_layout)
        self._dim_buttons.clear()
        self._transaction_buttons.clear()

        for table_name in self._dim_tables:
            row, btn = self._make_table_row(table_name, "dim")
            btn.clicked.connect(lambda _=False, t=table_name: self._select_dim_table(t))
            self._dim_btn_layout.addWidget(row)
            self._dim_buttons[table_name] = btn

        for table_name in self._transaction_tables:
            row, btn = self._make_table_row(table_name, "tx")
            btn.clicked.connect(lambda _=False, t=table_name: self._select_transaction_table(t))
            self._tx_btn_layout.addWidget(row)
            self._transaction_buttons[table_name] = btn

    def _make_table_row(self, table_name: str, kind: str) -> tuple[QFrame, QPushButton]:
        """Return a (row_frame, select_button) pair — the row also contains an X remove button."""
        row = QFrame()
        row.setStyleSheet("QFrame { background: transparent; border: none; }")
        r_lay = QHBoxLayout(row)
        r_lay.setContentsMargins(0, 0, 0, 0)
        r_lay.setSpacing(4)

        btn = QPushButton(table_name)
        btn.setFixedHeight(36)
        btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 7px; "
            "color: #94a3b8; font-size: 12px; text-align: left; padding: 0 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.06); }"
        )
        btn.setCursor(Qt.PointingHandCursor)
        r_lay.addWidget(btn, 1)

        x_btn = QPushButton("✕")
        x_btn.setFixedSize(28, 36)
        x_btn.setToolTip(f"Remove '{table_name}' from this project")
        x_btn.setStyleSheet(
            "QPushButton { background: rgba(239,68,68,0.07); "
            "border: 1px solid rgba(239,68,68,0.18); border-radius: 7px; "
            "color: #f87171; font-size: 11px; padding: 0; }"
            "QPushButton:hover { background: rgba(239,68,68,0.20); }"
        )
        x_btn.setCursor(Qt.PointingHandCursor)
        x_btn.clicked.connect(lambda _=False, t=table_name, k=kind: self._confirm_remove_table(t, k))
        if self._locked_mappings:
            x_btn.setVisible(False)
        r_lay.addWidget(x_btn)

        return row, btn

    def _set_button_selection(self, button_map: dict, selected_name: str, kind: str) -> None:
        for name, btn in button_map.items():
            if name == selected_name:
                if kind == "dim":
                    btn.setStyleSheet(
                        "QPushButton { background: rgba(34,211,153,0.08); "
                        "border: 1px solid rgba(34,211,153,0.2); border-radius: 7px; "
                        "color: #34d399; font-size: 12px; text-align: left; padding: 0 12px; }"
                    )
                else:
                    btn.setStyleSheet(
                        "QPushButton { background: rgba(59,130,246,0.1); "
                        "border: 1px solid rgba(59,130,246,0.25); border-radius: 7px; "
                        "color: #60a5fa; font-size: 12px; text-align: left; padding: 0 12px; }"
                    )
            else:
                btn.setStyleSheet(
                    "QPushButton { background: rgba(255,255,255,0.03); "
                    "border: 1px solid rgba(255,255,255,0.07); border-radius: 7px; "
                    "color: #94a3b8; font-size: 12px; text-align: left; padding: 0 12px; }"
                    "QPushButton:hover { background: rgba(255,255,255,0.06); }"
                )

    def _confirm_remove_table(self, table_name: str, kind: str) -> None:
        """Ask for confirmation then remove the table from disk, project.json, and mappings."""
        kind_label = "dimension" if kind == "dim" else "transaction"
        reply = msgbox.question(
            self,
            "Remove Table",
            f"Remove <b>{table_name}</b> from this project?<br><br>"
            f"The {kind_label} data file will be deleted from disk and any mappings "
            f"that reference it will also be removed.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        def worker():
            self._do_remove_table(table_name, kind)

        def on_success(_):
            if kind == "dim":
                self._dim_tables = [t for t in self._dim_tables if t != table_name]
                if self._selected_dim_table == table_name:
                    self._selected_dim_table = None
                self._pending_mappings = [
                    m for m in self._pending_mappings if m.get("dim_table") != table_name
                ]
            else:
                self._transaction_tables = [t for t in self._transaction_tables if t != table_name]
                if self._selected_transaction_table == table_name:
                    self._selected_transaction_table = None
                self._pending_mappings = [
                    m for m in self._pending_mappings if m.get("transaction_table") != table_name
                ]
            # Keep project dict in sync — Screen 1 reads this when navigating back
            self.project["transaction_tables"] = list(self._transaction_tables)
            self.project["dim_tables"] = list(self._dim_tables)
            self._refresh_tables()
            self._refresh_mappings()
            self._clear_current_selection()

        def on_error(exc):
            msgbox.critical(self, "Failed to Remove Table",
                            f"<b>{table_name}</b> could not be removed. The file may be locked.\n\nDetail: {exc}")

        self._run_background(worker, on_success, on_error)

    def _do_remove_table(self, table_name: str, kind: str) -> None:
        """Disk-side removal: delete data file, update project.json, purge saved mappings."""
        directory = active_dim_dir(self.project_path) if kind == "dim" else active_transactions_dir(self.project_path)
        base = directory / table_name
        try:
            for suffix in (".csv", ".parquet"):
                p = base.with_suffix(suffix)
                if p.exists():
                    p.unlink()
                    break
        except OSError as e:
            raise OSError(f"Could not delete '{table_name}': {e}") from e

        # Build updated project.json contents
        project_data = {
            "project_name": self.project.get("project_name", ""),
            "created_at": self.project.get("created_at", ""),
            "company": self.project.get("company", ""),
            "transaction_tables": [
                t for t in self.project.get("transaction_tables", []) if t != table_name
            ] if kind == "tx" else list(self.project.get("transaction_tables", [])),
            "dim_tables": [
                t for t in self.project.get("dim_tables", []) if t != table_name
            ] if kind == "dim" else list(self.project.get("dim_tables", [])),
        }
        save_project_json(self.project_path, project_data)

        # Remove all saved mappings that reference this table
        delete_mappings_for_table(self.project_path, table_name)

    def _select_dim_table(self, table_name: str) -> None:
        self._set_error("")
        self._selected_dim_table = table_name
        self._set_button_selection(self._dim_buttons, table_name, "dim")
        self._dim_column_menu.clear()
        self._dim_column_menu.addItem("Loading...")

        def worker():
            return self._load_dim_columns(table_name)

        def on_success(columns):
            if self._selected_dim_table != table_name:
                return
            self._dim_column_menu.clear()
            self._dim_column_menu.addItems(columns or ["Select Column"])

        def on_error(exc):
            if self._selected_dim_table != table_name:
                return
            self._dim_column_menu.clear()
            self._dim_column_menu.addItem("Select Column")
            msgbox.critical(self, "Failed to Load Table",
                            f"The columns for <b>{table_name}</b> could not be read. The file may be missing or corrupted.\n\nDetail: {exc}")

        self._run_background(worker, on_success, on_error)

    def _select_transaction_table(self, table_name: str) -> None:
        self._set_error("")
        self._selected_transaction_table = table_name
        self._set_button_selection(self._transaction_buttons, table_name, "tx")
        self._tx_column_menu.clear()
        self._tx_column_menu.addItem("Loading...")

        def worker():
            return self._load_transaction_columns(table_name)

        def on_success(columns):
            if self._selected_transaction_table != table_name:
                return
            self._tx_column_menu.clear()
            self._tx_column_menu.addItems(columns or ["Select Column"])

        def on_error(exc):
            if self._selected_transaction_table != table_name:
                return
            self._tx_column_menu.clear()
            self._tx_column_menu.addItem("Select Column")
            msgbox.critical(self, "Failed to Load Table",
                            f"The columns for <b>{table_name}</b> could not be read. The file may be missing or corrupted.\n\nDetail: {exc}")

        self._run_background(worker, on_success, on_error)

    def _load_dim_columns(self, table_name: str) -> list[str]:
        path = active_dim_dir(self.project_path) / f"{table_name}.csv"
        return list(load_csv(path).columns)

    def _load_transaction_columns(self, table_name: str) -> list[str]:
        path = active_transactions_dir(self.project_path) / f"{table_name}.csv"
        return list(read_table(path).columns)

    def _compare_column_compatibility(
        self, dim_table: str, dim_col: str, tx_table: str, tx_col: str
    ) -> tuple[str, str] | None:
        """Returns ("error"|"warning", message) or None if compatible.

        Three-tier value-match logic:
          0 unique matches   → "error"   (hard block — wrong column)
          1 unique match     → "error"   (hard block — not enough signal)
          2+ matches, < 60%  → "warning" (soft ask — proceed or change?)
          ≥ 60% match rate   → None      (auto-proceed, no popup)
        """
        dim_path = active_dim_dir(self.project_path) / f"{dim_table}.csv"
        dim_df = load_csv(dim_path)
        if dim_col not in dim_df.columns:
            return None
        dim_vals = [str(v).strip() for v in dim_df[dim_col].dropna() if str(v).strip()]

        tx_path = active_transactions_dir(self.project_path) / f"{tx_table}.csv"
        tx_df = read_table(tx_path)
        if tx_col not in tx_df.columns:
            return None
        tx_vals = [str(v).strip() for v in tx_df[tx_col].dropna() if str(v).strip()]

        if not tx_vals:
            return ("error", f"'{tx_col}' is empty — choose a column that contains data.")
        if not dim_vals:
            return ("error", f"Dimension column '{dim_col}' is empty — cannot use an empty reference column.")

        # ── Type mismatch check: numeric tx column vs text dim column ─────────
        def _numeric_ratio(vals: list[str]) -> float:
            if not vals:
                return 0.0
            sample = vals[:200]
            count = 0
            for v in sample:
                try:
                    float(v.replace(",", "").replace(" ", ""))
                    count += 1
                except ValueError:
                    pass
            return count / len(sample)

        tx_numeric_ratio  = _numeric_ratio(tx_vals)
        dim_numeric_ratio = _numeric_ratio(dim_vals)

        if tx_numeric_ratio >= 0.9 and dim_numeric_ratio < 0.1:
            return (
                "warning",
                f"'{tx_col}' appears to contain numeric values "
                f"({int(tx_numeric_ratio * 100)}% of sampled rows) "
                f"but '{dim_col}' is a text column.\n\n"
                "Mapping a numeric column to a text reference is unlikely to find "
                "any matches. You can proceed anyway or choose a different column.",
            )

        if dim_numeric_ratio >= 0.9 and tx_numeric_ratio < 0.1:
            return (
                "warning",
                f"'{dim_col}' is a numeric dimension column "
                f"but '{tx_col}' contains text values.\n\n"
                "Mapping a text column to a numeric reference is unlikely to find "
                "any matches. You can proceed anyway or choose a different column.",
            )

        dim_lower = {v.lower() for v in dim_vals}
        tx_sample  = tx_vals[:100]

        matching_rows    = [v for v in tx_sample if v.lower() in dim_lower]
        unique_matches   = len({v.lower() for v in matching_rows})
        overlap_pct      = len(matching_rows) / len(tx_sample)

        # ── Tier 1: no signal at all → soft override ask ──────────────
        if unique_matches == 0:
            return (
                "warning",
                f"No matching values found between '{tx_col}' and '{dim_col}'.\n\n"
                f"These columns may not correspond to the same data. "
                f"You can map anyway or choose a different column.",
            )

        # ── Tier 2: only 1 unique match → soft override ask ───────────
        if unique_matches == 1:
            return (
                "warning",
                f"Only 1 unique value in '{tx_col}' matched '{dim_col}'.\n\n"
                f"This may mean the transaction data only contains a single "
                f"category so far, or the columns may not correspond. "
                f"You can map anyway or choose a different column.",
            )

        # ── Tier 3: some matches but low coverage → soft ask ──────────
        if overlap_pct < 0.60:
            return (
                "warning",
                f"Only {int(overlap_pct * 100)}% of sampled rows in '{tx_col}' "
                f"({unique_matches} unique value{'s' if unique_matches != 1 else ''} matched) "
                f"align with '{dim_col}'.\n\n"
                f"These columns may not correspond to the same data. "
                f"You can proceed anyway or choose a different column.",
            )

        # ── Tier 4: ≥ 60% match → auto-proceed, no popup ──────────────
        return None

    # ------------------------------------------------------------------
    # Mapping list
    # ------------------------------------------------------------------

    def _on_confirm_mapping(self) -> None:
        dim_column = self._dim_column_menu.currentText().strip()
        tx_column = self._tx_column_menu.currentText().strip()
        error = validate_mapping_selection(
            transaction_table=self._selected_transaction_table,
            dim_table=self._selected_dim_table,
            transaction_column=tx_column,
            dim_column=dim_column,
        )
        if error:
            self._set_error(error)
            return

        candidate = {
            "transaction_table": self._selected_transaction_table,
            "transaction_column": tx_column,
            "dim_table": self._selected_dim_table,
            "dim_column": dim_column,
        }
        all_current = [*self._locked_mappings, *self._pending_mappings]
        if any(mapping_key(m) == mapping_key(candidate) for m in all_current):
            self._set_error("This mapping already exists.")
            return

        def do_compare():
            return self._compare_column_compatibility(
                candidate["dim_table"], candidate["dim_column"],
                candidate["transaction_table"], candidate["transaction_column"],
            )

        def _add_mapping():
            self._pending_mappings.append(candidate)
            self._set_error("")
            self._refresh_mappings()
            self._clear_current_selection()

        def on_compared(result: tuple[str, str] | None) -> None:
            if result is None:
                _add_mapping()
                return
            level, message = result
            if level == "error":
                self._set_error(message)
                return
            # soft warning — user may override
            if msgbox.warning_question(
                self, "Low Column Match", message,
                confirm_label="Map Anyway", cancel_label="Change Column",
            ):
                _add_mapping()

        self._run_background(do_compare, on_compared, lambda *_: _add_mapping())

    def _clear_current_selection(self) -> None:
        self._selected_dim_table = None
        self._selected_transaction_table = None
        self._set_button_selection(self._dim_buttons, "__none__", "dim")
        self._set_button_selection(self._transaction_buttons, "__none__", "tx")
        self._dim_column_menu.clear()
        self._dim_column_menu.addItem("Select Column")
        self._tx_column_menu.clear()
        self._tx_column_menu.addItem("Select Column")

    def _refresh_mappings(self) -> None:
        clear_layout(self._mapping_list_layout)
        total = len(self._locked_mappings) + len(self._pending_mappings)
        self._mappings_count_lbl.setText(f"{total} mapping{'s' if total != 1 else ''}")
        self._update_finish_btn()

        if not self._locked_mappings and not self._pending_mappings:
            empty_wrap = QFrame()
            empty_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
            ew_lay = QVBoxLayout(empty_wrap)
            ew_lay.setContentsMargins(16, 16, 16, 16)
            lbl = QLabel("No mappings added yet.")
            lbl.setStyleSheet(
                "color: #94a3b8; background: transparent; border: none; font-size: 12px;"
            )
            ew_lay.addWidget(lbl)
            self._mapping_list_layout.addWidget(empty_wrap)
            return

        if self._locked_mappings:
            self._mapping_list_layout.addWidget(self._make_mappings_subheader("EXISTING"))
            for mapping in self._locked_mappings:
                self._mapping_list_layout.addWidget(self._make_mapping_row(mapping, locked=True))

        if self._pending_mappings:
            if self._locked_mappings:
                self._mapping_list_layout.addWidget(self._make_mappings_subheader("NEW"))
            for idx, mapping in enumerate(self._pending_mappings):
                self._mapping_list_layout.addWidget(
                    self._make_mapping_row(mapping, locked=False, pending_idx=idx)
                )

    def _make_mappings_subheader(self, text: str) -> QFrame:
        subhdr = QFrame()
        subhdr.setFixedHeight(26)
        subhdr.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.02); border: none; "
            "border-top: 1px solid rgba(255,255,255,0.04); "
            "border-bottom: 1px solid rgba(255,255,255,0.04); }"
        )
        sh_lay = QHBoxLayout(subhdr)
        sh_lay.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; "
            "font-size: 9px; font-weight: 600; letter-spacing: 1px;"
        )
        sh_lay.addWidget(lbl)
        return subhdr

    def _make_mapping_row(self, mapping: dict, locked: bool, pending_idx: int = 0) -> QFrame:
        row = QFrame()
        row.setObjectName("s2_mrow")
        row.setStyleSheet(
            "QFrame#s2_mrow { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); }"
        )
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(16, 11, 16, 11)
        row_layout.setSpacing(10)

        tx_t = mapping["transaction_table"]
        tx_c = mapping["transaction_column"]
        dim_t = mapping["dim_table"]
        dim_c = mapping["dim_column"]

        text_lbl = QLabel(
            f"<span style='color:#60a5fa;'>{tx_t}</span>"
            f"<span style='color:#94a3b8; font-family:Courier New,monospace;'>.{tx_c}</span>"
            f"<span style='color:#94a3b8;'> ↔ </span>"
            f"<span style='color:#60a5fa;'>{dim_t}</span>"
            f"<span style='color:#94a3b8; font-family:Courier New,monospace;'>.{dim_c}</span>"
        )
        text_lbl.setStyleSheet(
            "background: transparent; border: none; font-size: 12px; "
            "font-family: 'Courier New', monospace;"
        )
        row_layout.addWidget(text_lbl, 1)

        if locked:
            lock_lbl = QLabel("existing")
            lock_lbl.setFixedHeight(20)
            lock_lbl.setAlignment(Qt.AlignCenter)
            lock_lbl.setStyleSheet(
                "color: #94a3b8; background: rgba(255,255,255,0.04); "
                "border: 1px solid rgba(255,255,255,0.07); border-radius: 4px; "
                "font-size: 9px; padding: 0 6px;"
            )
            lock_lbl.setToolTip("Existing mapping — manage from the main workspace")
            row_layout.addWidget(lock_lbl)
        else:
            del_btn = QPushButton("✕")
            del_btn.setFixedSize(26, 26)
            del_btn.setStyleSheet(
                "QPushButton { background: rgba(239,68,68,0.07); "
                "border: 1px solid rgba(239,68,68,0.18); border-radius: 6px; "
                "color: #f87171; font-size: 11px; padding: 0; }"
                "QPushButton:hover { background: rgba(239,68,68,0.14); }"
            )
            del_btn.clicked.connect(lambda _=False, i=pending_idx: self._delete_pending_mapping(i))
            row_layout.addWidget(del_btn)

        return row

    def _delete_pending_mapping(self, index: int) -> None:
        if 0 <= index < len(self._pending_mappings):
            self._pending_mappings.pop(index)
            self._refresh_mappings()

    # ------------------------------------------------------------------
    # Finish setup
    # ------------------------------------------------------------------

    def _on_finish_setup(self) -> None:
        def load_existing():
            return get_mappings(self.project_path)

        def on_existing_loaded(existing_mappings):
            combined = [*existing_mappings, *self._pending_mappings]

            def do_save():
                def save_worker():
                    existing_keys = {mapping_key(m) for m in existing_mappings}
                    for m in self._pending_mappings:
                        if mapping_key(m) not in existing_keys:
                            add_mapping(self.project_path, m)
                            existing_keys.add(mapping_key(m))
                    from core.snapshot_manager import create_initial_commit
                    create_initial_commit(self.project_path)

                def on_save_success(_):
                    self._pending_mappings.clear()
                    self._refresh_mappings()
                    self._set_error("")
                    try:
                        from ui.screen3_main import Screen3Main
                        self.app.show_screen(Screen3Main, project=self.project)
                    except ImportError:
                        msgbox.information(self, "Done", "Mappings saved. Screen 3 not built yet.")

                def on_save_error(exc):
                    msgbox.critical(self, "Failed to Save Mappings",
                                    f"Your mappings could not be saved. Check that the project folder is accessible.\n\nDetail: {exc}")

                self._run_background(save_worker, on_save_success, on_save_error)

            missing_tx, missing_dim = find_unmapped_tables(
                self._transaction_tables, self._dim_tables, combined
            )

            if not missing_tx and not missing_dim:
                reply = msgbox.question(
                    self,
                    "Finish Setup",
                    "All tables are mapped and ready to go.<br><br>"
                    "Continue to the main workspace?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.Yes:
                    do_save()
                return

            # Build warning listing the unmapped tables
            parts = []
            if missing_tx:
                parts.append(f"Transaction tables: {', '.join(missing_tx)}")
            if missing_dim:
                parts.append(f"Dimension tables: {', '.join(missing_dim)}")
            unmapped_str = "<br>".join(parts)

            reply = msgbox.question(
                self,
                "Some Tables Are Not Mapped",
                f"The following tables have no mappings and will pass through without any column matching:<br><br>"
                f"{unmapped_str}<br><br>"
                f"Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.Yes:
                do_save()

        def on_existing_error(exc):
            msgbox.critical(self, "Failed to Load Mappings",
                            f"Existing mappings could not be read. The mappings file may be corrupted.\n\nDetail: {exc}")

        self._run_background(load_existing, on_existing_loaded, on_existing_error)
