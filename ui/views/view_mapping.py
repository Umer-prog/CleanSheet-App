from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QBrush, QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QStyledItemDelegate,
    QTableView, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import load_csv, save_as_csv,get_sheet_as_dataframe
from core.dim_manager import append_dim_row, get_dim_columns, get_dim_dataframe
from core.error_detector import detect_errors
from core.final_export_manager import export_final_workbook
from core.project_manager import save_project_json
from core.snapshot_manager import create_snapshot
from core.mapping_manager import get_mappings
from ui.workers import ScreenBase, clear_layout, make_scroll_area


# ---------------------------------------------------------------------------
# Utility helpers (kept as module-level for reuse from popup code)
# ---------------------------------------------------------------------------

def get_valid_dim_values(project_path: Path, dim_table: str, dim_column: str) -> list[str]:
    df = get_dim_dataframe(project_path, dim_table)
    return sorted({str(v).strip() for v in df[dim_column].tolist() if str(v).strip()})


def replace_transaction_value(project_path, mapping, row_index, new_value):
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    csv_path = Path(project_path) / "data" / "transactions" / f"{t_table}.csv"
    df = load_csv(csv_path)
    if t_col not in df.columns:
        raise ValueError(f"Column '{t_col}' not found.")
    if row_index < 0 or row_index >= len(df):
        raise IndexError(f"Row index {row_index} out of bounds.")
    df.at[row_index, t_col] = str(new_value)
    save_as_csv(df, csv_path)


def replace_transaction_values_bulk(project_path, mapping, old_value, new_value) -> int:
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    csv_path = Path(project_path) / "data" / "transactions" / f"{t_table}.csv"
    df = load_csv(csv_path)
    if t_col not in df.columns:
        raise ValueError(f"Column '{t_col}' not found.")
    old_stripped = str(old_value).strip()
    if old_stripped == "":
        # Empty cells in CSVs are read as NaN by pandas even with dtype=str.
        # Match both NaN and any whitespace-only strings.
        mask = df[t_col].isna() | (df[t_col].astype(str).str.strip() == "")
    else:
        mask = df[t_col].astype(str).str.strip() == old_stripped
    count = int(mask.sum())
    if count:
        df.loc[mask, t_col] = str(new_value)
        save_as_csv(df, csv_path)
    return count


# ---------------------------------------------------------------------------
# Table model
# ---------------------------------------------------------------------------

class _PandasModel(QAbstractTableModel):
    """Table model for transaction data with error-row and error-cell highlighting."""

    _ERR_BG  = QColor(239, 68, 68, 40)
    _ERR_FG  = QColor("#f87171")
    _NORM_FG = QColor("#94a3b8")
    _HDR_FG  = QColor("#475569")

    def __init__(self, df: pd.DataFrame,
                 error_rows: dict[int, str] | None = None,
                 mapped_col: str | None = None,
                 row_offset: int = 0):
        """
        df          : page slice of the transaction dataframe (already reset_index)
        error_rows  : {page-local row index: column name with the error}
        mapped_col  : the transaction column being mapped (for cell-level highlighting)
        row_offset  : global start row index so row numbers are correct across pages
        """
        super().__init__()
        self._df = df.reset_index(drop=True)
        self._error_rows = error_rows or {}
        self._mapped_col = mapped_col
        self._row_offset = row_offset
        self._cols = list(self._df.columns)

    # -- QAbstractTableModel interface --

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._df)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._cols)

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col_idx = index.row(), index.column()
        col_name = self._cols[col_idx]
        is_err_row = row in self._error_rows
        is_err_cell = is_err_row and self._error_rows.get(row) == col_name

        if role == Qt.DisplayRole:
            val = self._df.iat[row, col_idx]
            return "" if pd.isna(val) else str(val)

        if role == Qt.BackgroundRole and is_err_row:
            return QBrush(self._ERR_BG)

        if role == Qt.ForegroundRole:
            if is_err_cell:
                return QBrush(self._ERR_FG)
            return QBrush(self._NORM_FG)

        if role == Qt.FontRole:
            f = QFont("Courier New")
            f.setPixelSize(11)
            if is_err_cell:
                f.setBold(True)
            return f

        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal:
            if role == Qt.DisplayRole:
                return self._cols[section]
            if role == Qt.ForegroundRole:
                return QBrush(self._HDR_FG)
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return str(self._row_offset + section + 1)
        return None


# ---------------------------------------------------------------------------
# Row delegate — needed so model BackgroundRole survives Qt stylesheet engine
# ---------------------------------------------------------------------------

class _RowDelegate(QStyledItemDelegate):
    """Passes the model's BackgroundRole through when a QSS stylesheet is active."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        bg = index.data(Qt.BackgroundRole)
        if bg is not None:
            option.backgroundBrush = bg if isinstance(bg, QBrush) else QBrush(bg)


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

class ViewMapping(ScreenBase):
    """
    Screen 6 — mapping workspace view.

    6A state: no errors — green checkmark panel + green Generate Output button.
    6B state: errors exist — red error cards + Replace/Add buttons.
    """

    def __init__(
        self,
        parent,
        project: dict,
        mapping: dict,
        nav_key: str = "",
        on_badge_update: Callable[[str, int], None] | None = None,
    ):
        super().__init__(parent)
        self.project = project
        self.mapping = mapping
        self.project_path = Path(project["project_path"])
        self._nav_key = nav_key
        self._on_badge_update = on_badge_update

        self._selected_error: dict | None = None
        self._selected_error_frame: QFrame | None = None
        self._errors: list[dict] = []
        self._total_errors: int = 0
        self._transaction_df: pd.DataFrame | None = None
        self._page_size = 500
        self._current_page = 0
        self._generate_mode = False
        self._generate_check_token = 0
        self._col_widths: list[int] = []  # cached after first resize

        self._build_ui()
        self._setup_overlay("Loading...")
        self._reload_data()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._build_topbar())
        outer.addWidget(self._build_content_split(), 1)
        outer.addWidget(self._build_footer())

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(64)
        bar.setStyleSheet(
            "QFrame { background-color: #13161e; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(28, 0, 28, 0)
        lay.setSpacing(12)

        tx_t = self.mapping["transaction_table"]
        tx_c = self.mapping["transaction_column"]
        dim_t = self.mapping["dim_table"]
        dim_c = self.mapping["dim_column"]

        self._topbar_title = QLabel(
            f"<span style='color:#f1f5f9; font-size:14px; font-weight:600;'>"
            f"{tx_t}.{tx_c}"
            f"</span>"
            f"<span style='color:#334155; font-size:14px;'>  →  </span>"
            f"<span style='color:#f1f5f9; font-size:14px; font-weight:600;'>"
            f"{dim_t}.{dim_c}"
            f"</span>"
        )
        self._topbar_title.setTextFormat(Qt.RichText)
        self._topbar_title.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(self._topbar_title)

        self._err_count_badge = QLabel()
        self._err_count_badge.setFixedHeight(20)
        self._err_count_badge.setStyleSheet(
            "background: rgba(239,68,68,0.12); "
            "color: #f87171; "
            "font-size: 10px; font-weight: 600; "
            "padding: 0 8px; "
            "border: 1px solid rgba(239,68,68,0.25); "
            "border-radius: 10px;"
        )
        self._err_count_badge.setVisible(False)
        lay.addWidget(self._err_count_badge)

        lay.addStretch()

        # Pager
        pager = QHBoxLayout()
        pager.setSpacing(6)

        self._tx_range_lbl = QLabel("row 0–0 of 0")
        self._tx_range_lbl.setStyleSheet(
            "color: #475569; font-size: 11px; background: transparent; border: none;"
        )
        pager.addWidget(self._tx_range_lbl)

        self._prev_btn = QPushButton("Prev")
        self._prev_btn.setFixedSize(52, 28)
        self._prev_btn.setEnabled(False)
        self._prev_btn.clicked.connect(self._go_prev_page)
        self._prev_btn.setStyleSheet(_page_btn_style())
        pager.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.setFixedSize(52, 28)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._go_next_page)
        self._next_btn.setStyleSheet(_page_btn_style())
        pager.addWidget(self._next_btn)

        lay.addLayout(pager)

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedHeight(34)
        refresh_btn.clicked.connect(self._reload_data)
        refresh_btn.setStyleSheet(
            "QPushButton { "
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); "
            "border-radius: 7px; "
            "color: #94a3b8; "
            "font-size: 12px; "
            "padding: 0 14px; "
            "} "
            "QPushButton:hover { background: rgba(255,255,255,0.08); }"
        )
        lay.addWidget(refresh_btn)

        return bar

    def _build_content_split(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: #0f1117;")
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._build_table_section(), 1)
        lay.addWidget(self._build_errors_section())

        return widget

    def _build_table_section(self) -> QFrame:
        frame = QFrame()
        frame.setStyleSheet(
            "QFrame { background: transparent; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Section header
        hdr = QFrame()
        hdr.setFixedHeight(38)
        hdr.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.01); "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(20, 0, 20, 0)

        sec_title = QLabel("TABLES")
        sec_title.setStyleSheet(
            "color: #475569; font-size: 10px; font-weight: 600; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        hdr_lay.addWidget(sec_title)
        hdr_lay.addStretch()

        self._table_hint_lbl = QLabel("Error rows highlighted  ·  Click error to select")
        self._table_hint_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: transparent; border: none;"
        )
        self._table_hint_lbl.setVisible(False)
        hdr_lay.addWidget(self._table_hint_lbl)

        lay.addWidget(hdr)

        # Table view
        self._table_view = QTableView()
        self._table_view.setStyleSheet(_table_style())
        # Set the base background via palette so model's BackgroundRole isn't
        # overridden by the QSS background-color rule that cascades to items.
        _tbl_pal = self._table_view.palette()
        _tbl_pal.setColor(QPalette.ColorRole.Base, QColor("#0f1117"))
        _tbl_pal.setColor(QPalette.ColorRole.AlternateBase, QColor("#0f1117"))
        self._table_view.setPalette(_tbl_pal)
        self._table_view.setSelectionMode(QAbstractItemView.NoSelection)
        self._table_view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table_view.setShowGrid(False)
        self._table_view.setAlternatingRowColors(False)
        self._table_view.horizontalHeader().setDefaultSectionSize(120)
        self._table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._table_view.horizontalHeader().setStretchLastSection(False)
        self._table_view.verticalHeader().setDefaultSectionSize(34)
        self._table_view.verticalHeader().setVisible(True)
        self._table_view.verticalHeader().setMinimumWidth(36)
        self._table_view.verticalHeader().setMaximumWidth(56)
        self._table_view.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._table_view.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self._table_view.setItemDelegate(_RowDelegate(self._table_view))
        lay.addWidget(self._table_view, 1)

        return frame

    def _build_errors_section(self) -> QFrame:
        # Fixed height: header 44px + list padding 20px + 5 cards×40px + 4 gaps×6px = 288px
        frame = QFrame()
        frame.setFixedHeight(288)
        frame.setStyleSheet("QFrame { background: transparent; }")
        self._errors_section_frame = frame
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # 6A — no errors state
        self._no_errors_widget = QWidget()
        self._no_errors_widget.setStyleSheet("background: transparent;")
        no_err_lay = QVBoxLayout(self._no_errors_widget)
        no_err_lay.setAlignment(Qt.AlignCenter)
        no_err_lay.setSpacing(8)

        check_box = QFrame()
        check_box.setFixedSize(40, 40)
        check_box.setStyleSheet(
            "QFrame { "
            "background: rgba(34,211,153,0.1); "
            "border: 1px solid rgba(34,211,153,0.2); "
            "border-radius: 10px; "
            "}"
        )
        check_lay = QHBoxLayout(check_box)
        check_lay.setContentsMargins(0, 0, 0, 0)
        check_icon = QLabel("✓")
        check_icon.setAlignment(Qt.AlignCenter)
        check_icon.setStyleSheet(
            "color: #34d399; font-size: 18px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        check_lay.addWidget(check_icon)

        no_err_lay.addWidget(check_box, 0, Qt.AlignCenter)

        no_err_title = QLabel("No errors found")
        no_err_title.setAlignment(Qt.AlignCenter)
        no_err_title.setStyleSheet(
            "color: #34d399; font-size: 13px; font-weight: 500; "
            "background: transparent; border: none;"
        )
        no_err_lay.addWidget(no_err_title)

        no_err_sub = QLabel("All values match the dimension table")
        no_err_sub.setAlignment(Qt.AlignCenter)
        no_err_sub.setStyleSheet(
            "color: #334155; font-size: 12px; "
            "background: transparent; border: none;"
        )
        no_err_lay.addWidget(no_err_sub)

        lay.addWidget(self._no_errors_widget, 1)

        # 6B — errors state
        self._errors_widget = QWidget()
        self._errors_widget.setStyleSheet("background: transparent;")
        self._errors_widget.setVisible(False)
        err_lay = QVBoxLayout(self._errors_widget)
        err_lay.setContentsMargins(0, 0, 0, 0)
        err_lay.setSpacing(0)

        # Errors header (44px)
        err_hdr = QFrame()
        err_hdr.setFixedHeight(44)
        err_hdr.setStyleSheet(
            "QFrame { background: transparent; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        err_hdr_lay = QHBoxLayout(err_hdr)
        err_hdr_lay.setContentsMargins(20, 0, 20, 0)

        err_hdr_title = QLabel("⚠  ERRORS")
        err_hdr_title.setStyleSheet(
            "color: #f87171; font-size: 10px; font-weight: 600; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        err_hdr_lay.addWidget(err_hdr_title)
        err_hdr_lay.addStretch()

        self._errors_count_lbl = QLabel("0 unresolved")
        self._errors_count_lbl.setFixedHeight(20)
        self._errors_count_lbl.setStyleSheet(
            "background: rgba(239,68,68,0.08); "
            "color: #f87171; font-size: 11px; "
            "padding: 0px 8px; "
            "border: 1px solid rgba(239,68,68,0.15); "
            "border-radius: 10px;"
        )
        err_hdr_lay.addWidget(self._errors_count_lbl)

        err_lay.addWidget(err_hdr)

        # Scrollable error list
        self._err_scroll, _, self._err_list_layout = make_scroll_area()
        self._err_list_layout.setContentsMargins(16, 10, 16, 10)
        self._err_list_layout.setSpacing(6)
        err_lay.addWidget(self._err_scroll, 1)

        lay.addWidget(self._errors_widget, 1)

        return frame

    def _build_footer(self) -> QFrame:
        bar = QFrame()
        bar.setFixedHeight(56)
        bar.setStyleSheet(
            "QFrame { background-color: #13161e; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(28, 0, 28, 0)
        lay.setSpacing(10)

        self._footer_hint = QLabel("Select an error below to resolve it.")
        self._footer_hint.setStyleSheet(
            "color: #475569; font-size: 12px; background: transparent; border: none;"
        )
        lay.addWidget(self._footer_hint, 1)

        # Generate button (6A)
        self._generate_btn = QPushButton("Generate Output  →")
        self._generate_btn.setFixedHeight(36)
        self._generate_btn.setVisible(False)
        self._generate_btn.clicked.connect(self._on_generate_final_file)
        self._generate_btn.setStyleSheet(
            "QPushButton { "
            "background: #059669; border: none; border-radius: 8px; "
            "color: #fff; font-size: 13px; font-weight: 500; "
            "padding: 0 20px; "
            "} "
            "QPushButton:hover { background: #047857; }"
        )
        lay.addWidget(self._generate_btn)

        # Generate disabled (6B)
        self._generate_disabled_btn = QPushButton("Generate Output")
        self._generate_disabled_btn.setFixedHeight(36)
        self._generate_disabled_btn.setEnabled(False)
        self._generate_disabled_btn.setStyleSheet(
            "QPushButton { "
            "background: rgba(255,255,255,0.03); "
            "border: 1px solid rgba(255,255,255,0.07); "
            "border-radius: 8px; "
            "color: #334155; font-size: 13px; "
            "padding: 0 20px; "
            "}"
        )
        lay.addWidget(self._generate_disabled_btn)

        # Replace (6B)
        self._replace_btn = QPushButton("Replace Value")
        self._replace_btn.setFixedHeight(36)
        self._replace_btn.setEnabled(False)
        self._replace_btn.clicked.connect(self._on_replace)
        self._replace_btn.setStyleSheet(
            "QPushButton { "
            "background: rgba(59,130,246,0.12); "
            "border: 1px solid rgba(59,130,246,0.3); "
            "border-radius: 8px; "
            "color: #60a5fa; font-size: 13px; font-weight: 500; "
            "padding: 0 20px; "
            "} "
            "QPushButton:hover:enabled { background: rgba(59,130,246,0.2); } "
            "QPushButton:disabled { color: #334155; border-color: rgba(255,255,255,0.07); "
            "background: rgba(255,255,255,0.03); }"
        )
        lay.addWidget(self._replace_btn)

        # Add to Dimension (6B)
        self._add_btn = QPushButton("Add to Dimension")
        self._add_btn.setFixedHeight(36)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)
        self._add_btn.setStyleSheet(
            "QPushButton { "
            "background: #3b82f6; border: none; border-radius: 8px; "
            "color: #fff; font-size: 13px; font-weight: 500; "
            "padding: 0 20px; "
            "} "
            "QPushButton:hover:enabled { background: #2563eb; } "
            "QPushButton:disabled { background: rgba(255,255,255,0.03); "
            "color: #334155; }"
        )
        lay.addWidget(self._add_btn)

        return bar

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _reload_data(self) -> None:
        self._selected_error = None
        self._selected_error_frame = None
        self._transaction_df = None
        self._errors = []
        self._current_page = 0
        self._col_widths = []  # force re-measure on next load
        self._update_table_view()
        self._show_loading_errors()

        def worker():
            csv_path = (
                self.project_path / "data" / "transactions"
                / f"{self.mapping['transaction_table']}.csv"
            )
            tx_df = load_csv(csv_path)
            errors, total_found = detect_errors(self.project_path, self.mapping)
            return tx_df, errors, total_found

        def on_success(result):
            tx_df, errors, total_found = result
            self._transaction_df = tx_df
            self._errors = errors
            self._total_errors = total_found
            self._update_table_view()
            self._render_errors()
            self._refresh_generate_state()

        def on_error(exc):
            self._transaction_df = None
            self._errors = []
            self._render_errors()
            self._set_footer_hint(f"Load failed: {exc}", error=True)
            self._set_generate_mode(False)

        self._run_background(worker, on_success, on_error)

    # ------------------------------------------------------------------
    # Table view
    # ------------------------------------------------------------------

    def _update_table_view(self) -> None:
        if self._transaction_df is None or self._transaction_df.empty:
            self._table_view.setModel(None)
            self._tx_range_lbl.setText("row 0–0 of 0")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            return

        total_rows = len(self._transaction_df)
        max_page = max(0, (total_rows - 1) // self._page_size)
        self._current_page = min(self._current_page, max_page)
        start = self._current_page * self._page_size
        end = min(start + self._page_size, total_rows)
        page_df = self._transaction_df.iloc[start:end].copy()

        # Build page-local error_rows dict
        error_rows: dict[int, str] = {}
        for err in self._errors:
            g_idx = int(err["row_index"])
            if start <= g_idx < end:
                error_rows[g_idx - start] = err["transaction_column"]

        model = _PandasModel(page_df, error_rows, self.mapping["transaction_column"],
                             row_offset=start)
        self._table_view.setModel(model)

        if not self._col_widths:
            # First load — measure once and cache
            self._table_view.resizeColumnsToContents()
            self._col_widths = [
                max(60, min(self._table_view.columnWidth(c), 200))
                for c in range(model.columnCount())
            ]
        # Apply cached widths on every page (instant — no cell scanning)
        for col, width in enumerate(self._col_widths):
            self._table_view.setColumnWidth(col, width)

        self._tx_range_lbl.setText(f"row {start + 1}–{end} of {total_rows}")
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page < max_page)

    def _go_prev_page(self) -> None:
        if self._transaction_df is None or self._current_page <= 0:
            return
        self._current_page -= 1
        self._update_table_view()

    def _go_next_page(self) -> None:
        if self._transaction_df is None:
            return
        total = len(self._transaction_df)
        if not total:
            return
        max_page = (total - 1) // self._page_size
        if self._current_page >= max_page:
            return
        self._current_page += 1
        self._update_table_view()

    # ------------------------------------------------------------------
    # Error list
    # ------------------------------------------------------------------

    def _show_loading_errors(self) -> None:
        clear_layout(self._err_list_layout)
        lbl = QLabel("Loading…")
        lbl.setStyleSheet(
            "color: #475569; font-size: 12px; background: transparent; border: none;"
        )
        self._err_list_layout.addWidget(lbl)
        self._no_errors_widget.setVisible(False)
        self._errors_widget.setVisible(True)
        self._errors_count_lbl.setText("…")
        self._table_hint_lbl.setVisible(False)
        self._err_count_badge.setVisible(False)

    def _render_errors(self) -> None:
        clear_layout(self._err_list_layout)
        total = self._total_errors
        truncated = total > len(self._errors)

        # Notify sidebar badge with true total
        if self._on_badge_update and self._nav_key:
            self._on_badge_update(self._nav_key, total)

        if total == 0:
            # 6A state
            self._no_errors_widget.setVisible(True)
            self._errors_widget.setVisible(False)
            self._table_hint_lbl.setVisible(False)
            self._err_count_badge.setVisible(False)
            self._set_generate_mode(True)
        else:
            # 6B state
            self._no_errors_widget.setVisible(False)
            self._errors_widget.setVisible(True)
            self._table_hint_lbl.setVisible(True)
            self._err_count_badge.setText(f"{total:,} errors")
            self._err_count_badge.setVisible(True)
            self._errors_count_lbl.setText(f"{total:,} unresolved")
            self._set_generate_mode(False)

            for error in self._errors:
                row_num = int(error["row_index"]) + 1
                bad_val = str(error.get("bad_value", ""))
                col_name = error.get("transaction_column", "")
                self._err_list_layout.addWidget(
                    self._make_error_card(row_num, col_name, bad_val, error)
                )

            if truncated:
                notice = QLabel(
                    f"Showing first {len(self._errors):,} of {total:,} errors. "
                    f"Fix these, then refresh to see more."
                )
                notice.setWordWrap(True)
                notice.setStyleSheet(
                    "color: #f59e0b; font-size: 11px; background: rgba(245,158,11,0.06); "
                    "border: 1px solid rgba(245,158,11,0.2); border-radius: 6px; "
                    "padding: 8px 12px; margin: 4px 0;"
                )
                self._err_list_layout.addWidget(notice)

    def _make_error_card(self, row_num: int, col_name: str, bad_val: str,
                          error: dict) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { "
            "background: rgba(239,68,68,0.04); "
            "border: 1px solid rgba(239,68,68,0.10); "
            "border-radius: 8px; "
            "}"
        )
        card.setCursor(Qt.PointingHandCursor)
        card.setFixedHeight(40)

        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(10)

        row_pill = QLabel(f"Row {row_num}")
        row_pill.setFixedHeight(20)
        row_pill.setStyleSheet(
            "color: #94a3b8; font-size: 10px; font-weight: 600; "
            "background: rgba(255,255,255,0.05); "
            "padding: 2px 7px; border-radius: 4px; "
            "font-family: 'Courier New'; "
            "border: none;"
        )
        lay.addWidget(row_pill)

        col_lbl = QLabel(col_name)
        col_lbl.setStyleSheet(
            "color: #64748b; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(col_lbl)

        dot = QLabel("·")
        dot.setStyleSheet("color: #334155; background: transparent; border: none;")
        lay.addWidget(dot)

        val_lbl = QLabel(bad_val if bad_val else "(empty)")
        val_lbl.setStyleSheet(
            "color: #f87171; font-size: 12px; font-weight: 600; "
            "font-family: 'Courier New'; "
            "background: transparent; border: none;"
        )
        lay.addWidget(val_lbl, 1)

        tag = QLabel("Not in dimension")
        tag.setFixedHeight(20)
        tag.setStyleSheet(
            "background: rgba(239,68,68,0.10); "
            "color: #fca5a5; font-size: 10px; "
            "padding: 2px 7px; border-radius: 4px; "
            "border: none;"
        )
        lay.addWidget(tag)

        def _click(event=None, err=error, frame=card):
            self._select_error(err, frame)

        card.mousePressEvent = _click
        for child in card.findChildren(QLabel):
            child.mousePressEvent = _click

        return card

    def _select_error(self, error: dict, frame: QFrame) -> None:
        if self._generate_mode:
            return

        # Deselect previous
        if self._selected_error_frame and self._selected_error_frame is not frame:
            self._selected_error_frame.setStyleSheet(
                "QFrame { "
                "background: rgba(239,68,68,0.04); "
                "border: 1px solid rgba(239,68,68,0.10); "
                "border-radius: 8px; "
                "}"
            )

        self._selected_error = error
        self._selected_error_frame = frame
        frame.setStyleSheet(
            "QFrame { "
            "background: rgba(239,68,68,0.12); "
            "border: 1px solid rgba(239,68,68,0.30); "
            "border-radius: 8px; "
            "}"
        )

        has_value = bool(str(error.get("bad_value", "")).strip())
        self._replace_btn.setEnabled(True)
        self._add_btn.setEnabled(has_value)

        self._set_footer_hint(
            "<span style='color:#f87171; font-weight:600;'>1 error selected</span>"
            " — choose an action to resolve it",
            rich=True,
        )

    # ------------------------------------------------------------------
    # Footer helpers
    # ------------------------------------------------------------------

    def _set_footer_hint(self, text: str, error: bool = False, rich: bool = False) -> None:
        if rich:
            self._footer_hint.setTextFormat(Qt.RichText)
            self._footer_hint.setText(text)
        else:
            self._footer_hint.setTextFormat(Qt.PlainText)
            self._footer_hint.setText(text)
            if error:
                self._footer_hint.setStyleSheet(
                    "color: #f87171; font-size: 12px; "
                    "background: transparent; border: none;"
                )
            else:
                self._footer_hint.setStyleSheet(
                    "color: #475569; font-size: 12px; "
                    "background: transparent; border: none;"
                )

    def _set_error(self, msg: str) -> None:
        self._set_footer_hint(msg, error=True)

    # ------------------------------------------------------------------
    # Generate mode
    # ------------------------------------------------------------------

    def _set_generate_mode(self, enabled: bool) -> None:
        self._generate_mode = bool(enabled)

        # 6A footer
        self._generate_btn.setVisible(enabled)

        # 6B footer
        self._generate_disabled_btn.setVisible(not enabled)
        self._replace_btn.setVisible(not enabled)
        self._add_btn.setVisible(not enabled)

        if enabled:
            self._set_footer_hint("All errors resolved — ready to generate output")
        else:
            if not self._errors:
                self._set_footer_hint("Select an error below to resolve it.")
            else:
                # 6B default (no selection yet)
                if not self._selected_error:
                    self._set_footer_hint("Select an error below to resolve it.")
                # else — kept from _select_error

    def _refresh_generate_state(self) -> None:
        if self._errors:
            self._set_generate_mode(False)
            return

        self._generate_check_token += 1
        token = self._generate_check_token

        def worker():
            mappings = get_mappings(self.project_path)
            return not any(detect_errors(self.project_path, m)[1] > 0 for m in mappings)

        def on_success(all_clear):
            if token != self._generate_check_token:
                return
            self._set_generate_mode(bool(all_clear))
            if not all_clear:
                self._set_footer_hint(
                    "No errors here — resolve remaining mappings to enable export."
                )

        self._run_background(
            worker, on_success,
            lambda exc: self._set_error(f"Could not verify: {exc}"),
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_replace(self) -> None:
        if not self._selected_error:
            self._set_error("Select an error first.")
            return

        bad_value = str(self._selected_error.get("bad_value", ""))
        row_index = int(self._selected_error["row_index"])

        def worker():
            values = get_valid_dim_values(
                self.project_path, self.mapping["dim_table"], self.mapping["dim_column"]
            )
            try:
                dim_df = get_dim_dataframe(self.project_path, self.mapping["dim_table"])
            except Exception:
                dim_df = None
            return values, dim_df

        def on_success(result):
            values, dim_df = result
            same_count = sum(
                1 for e in self._errors if str(e.get("bad_value", "")) == bad_value
            )

            def open_replace_popup(scope: str) -> None:
                from ui.popups.popup_replace import PopupReplace

                def on_confirm(new_value: str) -> None:
                    def apply_worker():
                        if scope == "all":
                            replace_transaction_values_bulk(
                                self.project_path, self.mapping,
                                old_value=bad_value, new_value=new_value,
                            )
                        else:
                            replace_transaction_value(
                                self.project_path, self.mapping,
                                row_index=row_index, new_value=new_value,
                            )

                    self._run_background(
                        apply_worker,
                        lambda _: self._reload_data(),
                        lambda exc: QMessageBox.critical(
                            self, "Error", f"Could not replace:\n{exc}"
                        ),
                    )

                dlg = PopupReplace(
                    self, bad_value=bad_value, valid_values=values,
                    on_confirm=on_confirm, dim_df=dim_df,
                    dim_table=self.mapping["dim_table"],
                    dim_column=self.mapping["dim_column"],
                )
                dlg.exec()

            if same_count > 1:
                dlg = _BulkScopePopup(self, bad_value, same_count, row_index + 1)
                dlg.exec()
                if dlg.choice:
                    open_replace_popup(dlg.choice)
            else:
                open_replace_popup("single")

        self._run_background(
            worker, on_success,
            lambda exc: self._set_error(f"Could not load dim values: {exc}"),
        )

    def _on_add(self) -> None:
        if not self._selected_error:
            self._set_error("Select an error first.")
            return

        def worker():
            cols = get_dim_columns(self.project_path, self.mapping["dim_table"])
            try:
                df = get_dim_dataframe(self.project_path, self.mapping["dim_table"])
            except Exception:
                df = None
            return cols, df

        def on_success(result):
            dim_columns, dim_df = result
            from ui.popups.popup_add import PopupAdd

            # Capture now — self._selected_error is cleared when reload starts
            original_bad = str(self._selected_error.get("bad_value", "")).strip()
            row_index    = int(self._selected_error["row_index"])
            dim_col      = self.mapping["dim_column"]

            def on_confirm(row: dict) -> None:
                def apply_worker():
                    append_dim_row(self.project_path, self.mapping["dim_table"], row)
                    # If the key column was edited, keep the transaction in sync
                    new_key = str(row.get(dim_col, "")).strip()
                    if new_key != original_bad:
                        replace_transaction_value(
                            self.project_path, self.mapping, row_index, new_key
                        )

                self._run_background(
                    apply_worker,
                    lambda _: self._reload_data(),
                    lambda exc: QMessageBox.critical(
                        self, "Error", f"Could not add row:\n{exc}"
                    ),
                )

            dlg = PopupAdd(
                self,
                dim_table=self.mapping["dim_table"],
                dim_columns=dim_columns,
                mapped_column=self.mapping["dim_column"],
                bad_value=str(self._selected_error.get("bad_value", "")),
                on_confirm=on_confirm,
                dim_df=dim_df,
            )
            dlg.exec()

        self._run_background(
            worker, on_success,
            lambda exc: self._set_error(f"Could not load dim columns: {exc}"),
        )

    def _on_generate_final_file(self) -> None:
        if not self._generate_mode:
            return

        # Capture snapshot of the current (error-free) transaction table
        table_name = self.mapping["transaction_table"]
        tx_df = self._transaction_df.copy() if self._transaction_df is not None else None

        def worker():
            if tx_df is not None:
                create_snapshot(
                    self.project_path,
                    {table_name: tx_df},
                    label=f"Generated output — {table_name}",
                )
            return export_final_workbook(self.project_path)

        self._run_background(
            worker,
            lambda path: QMessageBox.information(
                self, "Final File Generated", f"Final file created:\n{path}"
            ),
            lambda exc: QMessageBox.critical(
                self, "Error", f"Could not generate final file:\n{exc}"
            ),
        )


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def _page_btn_style() -> str:
    return (
        "QPushButton { "
        "background: rgba(255,255,255,0.04); "
        "border: 1px solid rgba(255,255,255,0.08); "
        "border-radius: 6px; "
        "color: #94a3b8; font-size: 11px; "
        "padding: 0 10px; "
        "} "
        "QPushButton:hover:enabled { "
        "background: rgba(255,255,255,0.10); "
        "border-color: rgba(255,255,255,0.18); "
        "color: #cbd5e1; "
        "} "
        "QPushButton:pressed { "
        "background: rgba(255,255,255,0.06); "
        "border-color: rgba(255,255,255,0.12); "
        "} "
        "QPushButton:disabled { "
        "color: #1e293b; "
        "border-color: rgba(255,255,255,0.04); "
        "background: rgba(255,255,255,0.02); "
        "}"
    )


def _table_style() -> str:
    return (
        "QTableView { "
        "border: none; "
        "outline: none; "
        "gridline-color: transparent; "
        "selection-background-color: transparent; "
        "} "
        "QTableView::item { "
        "padding: 0 12px; "
        "border-bottom: 1px solid rgba(255,255,255,0.04); "
        "} "
        "QHeaderView::section:horizontal { "
        "background-color: #13161e; "
        "color: #475569; "
        "font-size: 10px; "
        "font-weight: 600; "
        "font-family: 'Segoe UI'; "
        "text-transform: uppercase; "
        "letter-spacing: 1px; "
        "padding: 0 12px; "
        "border: none; "
        "border-bottom: 1px solid rgba(255,255,255,0.07); "
        "height: 34px; "
        "} "
        "QHeaderView::section:vertical { "
        "background-color: #13161e; "
        "color: #334155; "
        "font-size: 10px; "
        "font-family: 'Courier New'; "
        "padding: 0 8px; "
        "border: none; "
        "border-right: 1px solid rgba(255,255,255,0.06); "
        "border-bottom: 1px solid rgba(255,255,255,0.04); "
        "} "
        "QScrollBar:horizontal { "
        "height: 6px; background: transparent; "
        "} "
        "QScrollBar::handle:horizontal { "
        "background: rgba(255,255,255,0.1); border-radius: 3px; "
        "} "
        "QScrollBar:vertical { "
        "width: 6px; background: transparent; "
        "} "
        "QScrollBar::handle:vertical { "
        "background: rgba(255,255,255,0.1); border-radius: 3px; "
        "}"
    )


# ---------------------------------------------------------------------------
# Bulk scope popup (unchanged)
# ---------------------------------------------------------------------------

class _BulkScopePopup:
    """Ask whether to replace all matching rows or only the selected one."""

    def __init__(self, parent, bad_value: str, total_count: int, selected_row: int):
        from PySide6.QtWidgets import QDialog
        self._dlg = QDialog(parent)
        self._dlg.setWindowTitle("Multiple Occurrences Found")
        self._dlg.setFixedSize(520, 280)
        self._dlg.setModal(True)
        self.choice: str | None = None

        outer = QVBoxLayout(self._dlg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("QFrame { background-color: #3b82f6; }")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(24, 0, 24, 0)
        lbl = QLabel("Multiple Occurrences Found")
        lbl.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        h_layout.addWidget(lbl)
        outer.addWidget(header)

        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        b_layout = QVBoxLayout(body)
        b_layout.setContentsMargins(24, 20, 24, 20)
        display = bad_value if bad_value else "(empty / null)"
        msg = QLabel(
            f'The value "{display}" appears on {total_count} rows in this mapping.\n\n'
            f"Replace all {total_count} rows, or only Row {selected_row}?"
        )
        msg.setStyleSheet(
            "color: #f1f5f9; font-size: 13px; background: transparent; border: none;"
        )
        msg.setWordWrap(True)
        b_layout.addWidget(msg)
        outer.addWidget(body, 1)

        footer = QFrame()
        footer.setFixedHeight(68)
        footer.setStyleSheet("QFrame { background-color: #0f1117; }")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(24, 0, 24, 0)
        f_layout.setSpacing(8)
        f_layout.addStretch()

        single_btn = QPushButton(f"Just Row {selected_row}")
        single_btn.setObjectName("btn_outline")
        single_btn.setFixedHeight(38)
        single_btn.clicked.connect(lambda: self._pick("single"))
        f_layout.addWidget(single_btn)

        all_btn = QPushButton(f"Apply to All  ({total_count} rows)")
        all_btn.setObjectName("btn_primary")
        all_btn.setFixedHeight(38)
        all_btn.clicked.connect(lambda: self._pick("all"))
        f_layout.addWidget(all_btn)
        outer.addWidget(footer)

    def _pick(self, choice: str) -> None:
        self.choice = choice
        self._dlg.accept()

    def exec(self) -> None:
        self._dlg.exec()
