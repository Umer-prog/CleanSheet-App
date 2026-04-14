from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import load_dim_json
from core.mapping_manager import add_mapping, get_mappings
from ui.workers import ScreenBase, clear_layout, make_scroll_area

_SIDEBAR_W = 260


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

    def __init__(self, app, project: dict, **kwargs):
        super().__init__()
        self.app = app
        self.project = project
        self.project_path = Path(project["project_path"])

        self._transaction_tables = list(project.get("transaction_tables", []))
        self._dim_tables = list(project.get("dim_tables", []))
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
            "QFrame { background: #3b82f6; border-radius: 9px; border: none; }"
        )
        logo_inner = QVBoxLayout(logo_box)
        logo_inner.setContentsMargins(0, 0, 0, 0)
        logo_lbl = QLabel("▦")
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet(
            "color: white; background: transparent; border: none; font-size: 14px;"
        )
        logo_inner.addWidget(logo_lbl)
        b_lay.addWidget(logo_box)

        name_col = QVBoxLayout()
        name_col.setSpacing(0)
        name_lbl = QLabel(theme.company_name())
        name_lbl.setStyleSheet(
            "color: #f1f5f9; background: transparent; border: none; "
            "font-size: 15px; font-weight: 600;"
        )
        sub_lbl = QLabel("DATA MAPPING")
        sub_lbl.setStyleSheet(
            "color: #475569; background: transparent; border: none; "
            "font-size: 10px; letter-spacing: 1px;"
        )
        name_col.addWidget(name_lbl)
        name_col.addWidget(sub_lbl)
        b_lay.addLayout(name_col, 1)
        lay.addWidget(brand)

        # "SETUP PROGRESS" label
        prog_lbl = QLabel("SETUP PROGRESS")
        prog_lbl.setStyleSheet(
            "color: #334155; background: transparent; border: none; "
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
            "color: #334155; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            "padding: 8px 18px 4px 18px;"
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
            "color: #334155; background: transparent; border: none; font-size: 10px;"
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

        # Back button
        back_wrap = QFrame()
        back_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        bw_lay = QHBoxLayout(back_wrap)
        bw_lay.setContentsMargins(12, 12, 12, 12)
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
                "color: #475569; background: transparent; border: none; font-size: 10px;"
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
                "color: #475569; background: transparent; border: none; font-size: 12px;"
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

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel("Mapper")
        title.setStyleSheet(
            "color: #f1f5f9; background: transparent; border: none; "
            "font-size: 15px; font-weight: 600;"
        )
        meta = QLabel(
            "Select one table on each side, pick columns, then confirm. "
            "Repeat until all tables are mapped."
        )
        meta.setStyleSheet(
            "color: #334155; background: transparent; border: none; font-size: 11px;"
        )
        text_col.addWidget(title)
        text_col.addWidget(meta)
        t_lay.addLayout(text_col, 1)
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

        dim_col_panel, dim_col_body = self._make_col_panel("Dimension Column")
        self._dim_column_menu = QComboBox()
        self._dim_column_menu.addItem("Select Column")
        self._dim_column_menu.setMinimumHeight(36)
        dim_col_body.addWidget(self._dim_column_menu)
        col_grid.addWidget(dim_col_panel, 1)

        # Centre: Confirm Mapping button — explicit blue styling so it always renders as a button
        confirm_wrap = QWidget()
        confirm_wrap.setStyleSheet("background: transparent;")
        cw_lay = QVBoxLayout(confirm_wrap)
        cw_lay.setContentsMargins(0, 0, 0, 34)
        cw_lay.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        confirm_mapping_btn = QPushButton("Confirm Mapping")
        confirm_mapping_btn.setFixedHeight(36)

        confirm_mapping_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; border: none; border-radius: 8px; "
            "color: #ffffff; font-size: 12px; font-weight: 500; padding: 0 16px; }"
            "QPushButton:hover { background: #2563eb; }"
            "QPushButton:pressed { background: #1d4ed8; }"
        )
        confirm_mapping_btn.clicked.connect(self._on_confirm_mapping)
        cw_lay.addWidget(confirm_mapping_btn)
        col_grid.addWidget(confirm_wrap)

        tx_col_panel, tx_col_body = self._make_col_panel("Transaction Column")
        self._tx_column_menu = QComboBox()
        self._tx_column_menu.addItem("Select Column")
        self._tx_column_menu.setMinimumHeight(36)
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
            "color: #475569; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        self._mappings_count_lbl = QLabel("0 mappings")
        self._mappings_count_lbl.setStyleSheet(
            "color: #334155; background: rgba(255,255,255,0.05); border: none; "
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
            "color: #475569; background: transparent; border: none; "
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
            "color: #475569; background: transparent; border: none; "
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
        self._footer_hint = QLabel("All tables must be mapped at least once before finishing setup")
        self._footer_hint.setStyleSheet(
            "color: #475569; background: transparent; border: none; font-size: 12px;"
        )
        f_lay.addWidget(self._footer_hint)
        f_lay.addWidget(self._error_lbl)
        f_lay.addStretch()

        finish_btn = QPushButton("Finish Setup →")
        finish_btn.setObjectName("btn_primary")
        finish_btn.setFixedHeight(34)
        finish_btn.setFixedWidth(140)
        finish_btn.clicked.connect(self._on_finish_setup)
        f_lay.addWidget(finish_btn)
        return footer

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _go_back(self) -> None:
        from ui.screen1_sources import Screen1Sources
        self.app.show_screen(Screen1Sources, project=self.project)

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)
        self._footer_hint.setVisible(not bool(msg))

    # ------------------------------------------------------------------
    # Table selection
    # ------------------------------------------------------------------

    def _refresh_tables(self) -> None:
        for table_name in self._dim_tables:
            btn = self._nav_btn(table_name, "dim")
            btn.clicked.connect(lambda _=False, t=table_name: self._select_dim_table(t))
            self._dim_btn_layout.addWidget(btn)
            self._dim_buttons[table_name] = btn

        for table_name in self._transaction_tables:
            btn = self._nav_btn(table_name, "tx")
            btn.clicked.connect(lambda _=False, t=table_name: self._select_transaction_table(t))
            self._tx_btn_layout.addWidget(btn)
            self._transaction_buttons[table_name] = btn

    @staticmethod
    def _nav_btn(label: str, kind: str = "dim") -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(36)
        if kind == "dim":
            dot_color = "#34d399"
        else:
            dot_color = "#60a5fa"
        btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 7px; "
            "color: #94a3b8; font-size: 12px; text-align: left; padding: 0 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.06); }"
        )
        btn.setCursor(Qt.PointingHandCursor)
        return btn

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
            QMessageBox.critical(self, "Error", f"Could not load dim table '{table_name}':\n{exc}")

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
            QMessageBox.critical(self, "Error", f"Could not load transaction table '{table_name}':\n{exc}")

        self._run_background(worker, on_success, on_error)

    def _load_dim_columns(self, table_name: str) -> list[str]:
        path = self.project_path / "data" / "dim" / f"{table_name}.json"
        return list(load_dim_json(path).columns)

    def _load_transaction_columns(self, table_name: str) -> list[str]:
        path = self.project_path / "data" / "transactions" / f"{table_name}.csv"
        return [str(c) for c in pd.read_csv(path, dtype=str, encoding="utf-8", nrows=0).columns]

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
        if any(mapping_key(m) == mapping_key(candidate) for m in self._pending_mappings):
            self._set_error("This mapping already exists.")
            return

        self._pending_mappings.append(candidate)
        self._set_error("")
        self._refresh_mappings()
        self._clear_current_selection()

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
        count = len(self._pending_mappings)
        self._mappings_count_lbl.setText(f"{count} mapping{'s' if count != 1 else ''}")

        if not self._pending_mappings:
            empty_wrap = QFrame()
            empty_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
            ew_lay = QVBoxLayout(empty_wrap)
            ew_lay.setContentsMargins(16, 16, 16, 16)
            lbl = QLabel("No mappings added yet.")
            lbl.setStyleSheet(
                "color: #334155; background: transparent; border: none; font-size: 12px;"
            )
            ew_lay.addWidget(lbl)
            self._mapping_list_layout.addWidget(empty_wrap)
            return

        for idx, mapping in enumerate(self._pending_mappings):
            row = QFrame()
            row.setObjectName("s2_mrow")
            is_last = idx == len(self._pending_mappings) - 1
            if is_last:
                row.setStyleSheet(
                    "QFrame#s2_mrow { background: transparent; border: none; }"
                )
            else:
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
                f"<span style='color:#475569;'> ↔ </span>"
                f"<span style='color:#60a5fa;'>{dim_t}</span>"
                f"<span style='color:#94a3b8; font-family:Courier New,monospace;'>.{dim_c}</span>"
            )
            text_lbl.setStyleSheet(
                "background: transparent; border: none; font-size: 12px; "
                "font-family: 'Courier New', monospace;"
            )
            row_layout.addWidget(text_lbl, 1)

            del_btn = QPushButton("✕")
            del_btn.setFixedSize(26, 26)
            del_btn.setStyleSheet(
                "QPushButton { background: rgba(239,68,68,0.07); "
                "border: 1px solid rgba(239,68,68,0.18); border-radius: 6px; "
                "color: #f87171; font-size: 11px; padding: 0; }"
                "QPushButton:hover { background: rgba(239,68,68,0.14); }"
            )
            del_btn.clicked.connect(lambda _=False, i=idx: self._delete_pending_mapping(i))
            row_layout.addWidget(del_btn)
            self._mapping_list_layout.addWidget(row)

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
            missing_tx, missing_dim = find_unmapped_tables(
                self._transaction_tables, self._dim_tables, combined
            )
            if missing_tx or missing_dim:
                chunks = []
                if missing_tx:
                    chunks.append(f"Unmapped transaction: {', '.join(missing_tx)}")
                if missing_dim:
                    chunks.append(f"Unmapped dimension: {', '.join(missing_dim)}")
                self._set_error(" | ".join(chunks))
                return

            def save_worker():
                existing_keys = {mapping_key(m) for m in existing_mappings}
                for m in self._pending_mappings:
                    if mapping_key(m) not in existing_keys:
                        add_mapping(self.project_path, m)
                        existing_keys.add(mapping_key(m))

            def on_save_success(_):
                self._pending_mappings.clear()
                self._refresh_mappings()
                self._set_error("")
                try:
                    from ui.screen3_main import Screen3Main
                    self.app.show_screen(Screen3Main, project=self.project)
                except ImportError:
                    QMessageBox.information(self, "Done", "Mappings saved. Screen 3 not built yet.")

            def on_save_error(exc):
                QMessageBox.critical(self, "Error", f"Could not save mappings:\n{exc}")

            self._run_background(save_worker, on_save_success, on_save_error)

        def on_existing_error(exc):
            QMessageBox.critical(self, "Error", f"Could not read existing mappings:\n{exc}")

        self._run_background(load_existing, on_existing_loaded, on_existing_error)
