from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QBrush, QColor, QFont, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QScrollArea, QSizePolicy, QStyledItemDelegate,
    QTableView, QVBoxLayout, QWidget,
)

import ui.theme as theme
import ui.popups.msgbox as msgbox
from core.data_loader import load_csv, save_as_csv,get_sheet_as_dataframe
from core.dim_manager import append_dim_row, get_dim_columns, get_dim_dataframe
from core.error_detector import detect_errors
from core.final_export_manager import export_final_workbook
from core.project_manager import save_project_json
from core.project_paths import active_transactions_dir, internal_path
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
    csv_path = active_transactions_dir(project_path) / f"{t_table}.csv"
    df = load_csv(csv_path)
    if t_col not in df.columns:
        raise ValueError(f"Column '{t_col}' not found.")
    if row_index < 0 or row_index >= len(df):
        raise IndexError(f"Row index {row_index} out of bounds.")
    df.at[row_index, t_col] = str(new_value)
    save_as_csv(df, csv_path)


def delete_transaction_row(project_path, mapping, row_index: int) -> None:
    """Delete a single row from the transaction CSV by its 0-based index."""
    t_table = mapping["transaction_table"]
    csv_path = active_transactions_dir(project_path) / f"{t_table}.csv"
    df = load_csv(csv_path)
    if row_index < 0 or row_index >= len(df):
        raise IndexError(f"Row index {row_index} out of bounds.")
    df = df.drop(index=row_index).reset_index(drop=True)
    save_as_csv(df, csv_path)


def delete_transaction_rows_bulk(project_path, mapping, bad_value) -> int:
    """Delete all rows in the transaction CSV where the mapped column matches bad_value."""
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    csv_path = active_transactions_dir(project_path) / f"{t_table}.csv"
    df = load_csv(csv_path)
    if t_col not in df.columns:
        raise ValueError(f"Column '{t_col}' not found.")
    old_stripped = str(bad_value).strip()
    if old_stripped == "":
        mask = df[t_col].isna() | (df[t_col].astype(str).str.strip() == "")
    else:
        mask = df[t_col].astype(str).str.strip() == old_stripped
    count = int(mask.sum())
    if count:
        df = df[~mask].reset_index(drop=True)
        save_as_csv(df, csv_path)
    return count


def replace_transaction_values_bulk(project_path, mapping, old_value, new_value) -> int:
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    csv_path = active_transactions_dir(project_path) / f"{t_table}.csv"
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


_MAX_RENDERED_CARDS = 100   # error cards created on the main thread per render pass
_COL_CHAR_PX        = 7     # approximate pixel width per character
_COL_PADDING        = 14    # horizontal cell padding in pixels
_COL_MIN_W          = 60
_COL_MAX_W          = 220


def _estimate_col_widths(df: pd.DataFrame) -> list[int]:
    """Return per-column display widths estimated from the first 30 rows.

    Runs on the background thread so the main thread never calls the
    expensive Qt resizeColumnsToContents().
    """
    sample = df.head(30)
    widths: list[int] = []
    for col in df.columns:
        header_w = len(str(col)) * _COL_CHAR_PX + _COL_PADDING
        data_max = int(sample[col].astype(str).str.len().max() or 0) if len(sample) else 0
        data_w   = data_max * _COL_CHAR_PX + _COL_PADDING
        widths.append(max(_COL_MIN_W, min(max(header_w, data_w), _COL_MAX_W)))
    return widths


# ---------------------------------------------------------------------------
# Table model
# ---------------------------------------------------------------------------

class _PandasModel(QAbstractTableModel):
    """Table model for transaction data with error-row and error-cell highlighting."""

    _ERR_BG  = QColor(239, 68, 68, 40)
    _ERR_FG  = QColor("#f87171")
    _NORM_FG = QColor("#94a3b8")
    _HDR_FG  = QColor("#cbd5e1")

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
        self._visible_total: int = 0
        self._transaction_df: pd.DataFrame | None = None
        self._page_size = 500
        self._current_page = 0
        self._generate_mode = False
        self._generate_check_token = 0
        self._col_widths: list[int] = []  # cached after first resize
        self._ignored_rows: dict[str, set[int]] = {}
        self._ignored_values: dict[str, set[str]] = {}  # "table.col" -> set of row indices

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
            f"<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>"
            f"{tx_t}.{tx_c}"
            f"</span>"
            f"<span style='color:#94a3b8; font-size:15px;'>  →  </span>"
            f"<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>"
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
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
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
        refresh_btn.clicked.connect(lambda: self._reload_data(force=True))
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
            "color: #cbd5e1; font-size: 10px; font-weight: 600; "
            "letter-spacing: 1px; background: transparent; border: none;"
        )
        hdr_lay.addWidget(sec_title)
        hdr_lay.addStretch()

        self._table_hint_lbl = QLabel("Error rows highlighted  ·  Click error to select")
        self._table_hint_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
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
        self._table_view.horizontalHeader().setDefaultSectionSize(140)
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
        # Fixed height: header 44px + list padding 20px + 6 cards×48px + 5 gaps×6px = 382px
        frame = QFrame()
        frame.setFixedHeight(382)
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
            "color: #94a3b8; font-size: 12px; "
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
            "color: #94a3b8; font-size: 12px; background: transparent; border: none;"
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
            "color: rgba(148,163,184,0.45); font-size: 13px; "
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
            "QPushButton:disabled { color: rgba(148,163,184,0.45); border-color: rgba(255,255,255,0.07); "
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
            "color: rgba(148,163,184,0.45); }"
        )
        lay.addWidget(self._add_btn)

        return bar

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _reload_data(self, force: bool = False) -> None:
        self._selected_error = None
        self._selected_error_frame = None
        self._transaction_df = None
        self._errors = []
        self._current_page = 0
        self._col_widths = []
        self._ignored_rows, self._ignored_values = self._load_ignored()

        mapping_id = str(self.mapping.get("id", ""))
        cache = self.project.setdefault("_validation_cache", {})
        entry = cache.get(mapping_id) if mapping_id else None

        def on_error(exc):
            self._transaction_df = None
            self._errors = []
            self._render_errors()
            self._set_footer_hint(f"Load failed: {exc}", error=True)
            self._set_generate_mode(False)

        if not force and entry is not None and not entry.get("dirty", True):
            if entry.get("tx_df") is not None:
                # Full cache hit — render immediately, no background work needed
                self._transaction_df = entry["tx_df"]
                self._errors = entry["errors"]
                self._total_errors = entry["total_errors"]
                self._col_widths = list(entry.get("col_widths") or [])
                self._update_table_view()
                self._render_errors()
                self._refresh_generate_state()
                return

        # Full load: run detect_errors + read transaction table
        self._update_table_view()
        self._show_loading_errors()

        _ign_key = (
            f"{self.mapping['transaction_table']}.{self.mapping['transaction_column']}"
        )
        _ign_vals = frozenset(self._ignored_values.get(_ign_key, set()))

        def worker():
            csv_path = (
                active_transactions_dir(self.project_path)
                / f"{self.mapping['transaction_table']}.csv"
            )
            tx_df = load_csv(csv_path)
            errors, total_found = detect_errors(
                self.project_path, self.mapping, ignored_values=_ign_vals
            )
            col_widths = _estimate_col_widths(tx_df)
            return tx_df, errors, total_found, col_widths

        def on_success(result):
            tx_df, errors, total_found, col_widths = result
            self._transaction_df = tx_df
            self._errors = errors
            self._total_errors = total_found
            self._col_widths = col_widths
            if mapping_id:
                cache[mapping_id] = {
                    "dirty": False,
                    "errors": errors,
                    "total_errors": total_found,
                    "tx_df": tx_df,
                    "col_widths": col_widths,
                }
            self._update_table_view()
            self._render_errors()
            self._refresh_generate_state()

        self._run_background(worker, on_success, on_error)

    # ------------------------------------------------------------------
    # Table view
    # ------------------------------------------------------------------

    def _visible_errors(self) -> list[dict]:
        """Return self._errors filtered to exclude ignored rows and ignored values."""
        ignored_key = f"{self.mapping['transaction_table']}.{self.mapping['transaction_column']}"
        ignored_row_set = self._ignored_rows.get(ignored_key, set())
        ignored_val_set = self._ignored_values.get(ignored_key, set())
        return [
            e for e in self._errors
            if int(e["row_index"]) not in ignored_row_set
            and str(e.get("bad_value", "")) not in ignored_val_set
        ]

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

        # Build page-local error_rows dict (excluding ignored rows)
        error_rows: dict[int, str] = {}
        for err in self._visible_errors():
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
            "color: #94a3b8; font-size: 12px; background: transparent; border: none;"
        )
        self._err_list_layout.addWidget(lbl)
        self._no_errors_widget.setVisible(False)
        self._errors_widget.setVisible(True)
        self._errors_count_lbl.setText("…")
        self._table_hint_lbl.setVisible(False)
        self._err_count_badge.setVisible(False)

    def _render_errors(self) -> None:
        clear_layout(self._err_list_layout)

        visible_errors = self._visible_errors()
        visible_total = self._total_errors - (len(self._errors) - len(visible_errors))
        truncated = self._total_errors > len(self._errors)

        # Notify sidebar badge with visible count
        if self._on_badge_update and self._nav_key:
            self._on_badge_update(self._nav_key, max(0, visible_total))

        if not visible_errors and visible_total <= 0:
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
            self._err_count_badge.setText(f"{visible_total:,} errors")
            self._err_count_badge.setVisible(True)
            self._errors_count_lbl.setText(f"{visible_total:,} unresolved")
            self._set_generate_mode(False)

            for error in visible_errors[:_MAX_RENDERED_CARDS]:
                row_num = int(error["row_index"]) + 1
                bad_val = str(error.get("bad_value", ""))
                col_name = error.get("transaction_column", "")
                self._err_list_layout.addWidget(
                    self._make_error_card(row_num, col_name, bad_val, error)
                )

            overflow = len(visible_errors) - _MAX_RENDERED_CARDS
            if overflow > 0:
                notice = QLabel(
                    f"{overflow:,} more errors not shown — "
                    f"resolve the ones above then click ↻ Refresh."
                )
                notice.setWordWrap(True)
                notice.setStyleSheet(
                    "color: #94a3b8; font-size: 11px; background: rgba(255,255,255,0.03); "
                    "border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; "
                    "padding: 8px 12px; margin: 4px 0;"
                )
                self._err_list_layout.addWidget(notice)
            elif truncated:
                notice = QLabel(
                    f"Showing first {len(self._errors):,} of {self._total_errors:,} errors. "
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
        card.setFixedHeight(48)

        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 0, 10, 0)
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
            "color: #cbd5e1; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(col_lbl)

        dot = QLabel("·")
        dot.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
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

        # --- Ignore button ---
        ignore_btn = QPushButton("Ignore")
        ignore_btn.setFixedSize(56, 26)
        ignore_btn.setCursor(Qt.PointingHandCursor)
        ignore_btn.setStyleSheet(
            "QPushButton { "
            "background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); "
            "border-radius: 5px; "
            "color: #94a3b8; font-size: 11px; font-weight: 500; "
            "padding: 0 6px; "
            "} "
            "QPushButton:hover { background: rgba(255,255,255,0.08); color: #cbd5e1; }"
        )
        ignore_btn.clicked.connect(lambda _=None, err=error: self._on_ignore_error(err))
        lay.addWidget(ignore_btn)

        # --- Delete button ---
        delete_btn = QPushButton("Delete")
        delete_btn.setFixedSize(54, 26)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.setStyleSheet(
            "QPushButton { "
            "background: rgba(239,68,68,0.12); "
            "border: 1px solid rgba(239,68,68,0.30); "
            "border-radius: 5px; "
            "color: #f87171; font-size: 11px; font-weight: 500; "
            "padding: 0 6px; "
            "} "
            "QPushButton:hover { background: rgba(239,68,68,0.22); }"
        )
        delete_btn.clicked.connect(lambda _=None, err=error: self._on_delete_error(err))
        lay.addWidget(delete_btn)

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
                    "color: #94a3b8; font-size: 12px; "
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
        visible = self._visible_errors()
        visible_total = self._total_errors - (len(self._errors) - len(visible))
        if visible or visible_total > 0:
            self._set_generate_mode(False)
            return

        self._generate_check_token += 1
        token = self._generate_check_token

        def worker():
            import json as _json
            mappings = get_mappings(self.project_path)
            ignored_file = internal_path(self.project_path) / "metadata" / "data" / "ignored_errors.json"
            ignored_rows_map: dict[str, set[int]] = {}
            ignored_vals_map: dict[str, set[str]] = {}
            try:
                with open(ignored_file, encoding="utf-8") as fh:
                    raw = _json.load(fh)
                if "rows" in raw or "values" in raw:
                    ignored_rows_map = {k: set(v) for k, v in raw.get("rows", {}).items()}
                    ignored_vals_map = {k: set(v) for k, v in raw.get("values", {}).items()}
                else:
                    ignored_rows_map = {k: set(v) for k, v in raw.items()}
            except Exception:
                pass
            for m in mappings:
                key = f"{m.get('transaction_table', '')}.{m.get('transaction_column', '')}"
                ign_vals = frozenset(ignored_vals_map.get(key, set()))
                errors, total = detect_errors(self.project_path, m, ignored_values=ign_vals)
                if total <= 0:
                    continue
                ignored_r = ignored_rows_map.get(key, set())
                visible = [
                    e for e in errors
                    if int(e["row_index"]) not in ignored_r
                ]
                if visible:
                    return False
            return True

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
                        lambda _: self._reload_data(force=True),
                        lambda exc: msgbox.critical(
                            self, "Failed to Apply Replacement",
                            f"The value could not be replaced. Check that the project data files are accessible.\n\nDetail: {exc}"
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
                count_exact = self._total_errors <= len(self._errors)
                dlg = _BulkScopePopup(self, bad_value, same_count, row_index + 1,
                                      count_exact=count_exact)
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
                    lambda _: self._reload_data(force=True),
                    lambda exc: msgbox.critical(
                        self, "Failed to Add Row",
                        f"The new row could not be saved to the dimension table. Check that the project data files are accessible.\n\nDetail: {exc}"
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

    # ------------------------------------------------------------------
    # Ignored rows persistence
    # ------------------------------------------------------------------

    def _ignored_file(self) -> Path:
        return internal_path(self.project_path) / "metadata" / "data" / "ignored_errors.json"

    def _load_ignored(self) -> tuple[dict[str, set[int]], dict[str, set[str]]]:
        import json as _json
        path = self._ignored_file()
        if not path.exists():
            return {}, {}
        try:
            with open(path, encoding="utf-8") as f:
                raw: dict = _json.load(f)
            # New format: {"rows": {...}, "values": {...}}
            # Old format (backward compat): {"table.col": [row_indices...]}
            if "rows" in raw or "values" in raw:
                rows = {k: set(v) for k, v in raw.get("rows", {}).items()}
                values = {k: set(v) for k, v in raw.get("values", {}).items()}
            else:
                rows = {k: set(v) for k, v in raw.items()}
                values = {}
            return rows, values
        except Exception:
            return {}, {}

    def _save_ignored(self) -> None:
        import json as _json
        path = self._ignored_file()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            serialisable = {
                "rows": {k: sorted(v) for k, v in self._ignored_rows.items()},
                "values": {k: sorted(v) for k, v in self._ignored_values.items()},
            }
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(serialisable, f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Ignore / Delete error actions
    # ------------------------------------------------------------------

    def _on_ignore_error(self, error: dict) -> None:
        row_index = int(error["row_index"])
        bad_val_raw = str(error.get("bad_value", ""))
        bad_val_display = bad_val_raw or "(empty)"

        same_errors = [
            e for e in self._errors
            if str(e.get("bad_value", "")) == bad_val_raw
        ]

        if len(same_errors) > 1:
            count_exact = self._total_errors <= len(self._errors)
            dlg = _BulkScopePopup(
                self, bad_val_display, len(same_errors), row_index + 1,
                verb="Ignore", count_exact=count_exact,
            )
            dlg.exec()
            if not dlg.choice:
                return
            scope = dlg.choice
        else:
            confirmed = msgbox.warning_question(
                self,
                "Ignore This Error?",
                f"Row {row_index + 1} — value <b>{bad_val_display}</b> will be hidden "
                f"from the error list. The data in the table will not change.",
                confirm_label="Ignore",
                cancel_label="Cancel",
            )
            if not confirmed:
                return
            scope = "single"

        key = f"{self.mapping['transaction_table']}.{self.mapping['transaction_column']}"
        if scope == "all":
            # Store by value so all occurrences are hidden, even beyond the 500-error cap
            self._ignored_values.setdefault(key, set()).add(bad_val_raw)
        else:
            self._ignored_rows.setdefault(key, set()).add(row_index)
        self._save_ignored()
        self._reload_data()

    def _on_delete_error(self, error: dict) -> None:
        row_index = int(error["row_index"])
        bad_val_raw = str(error.get("bad_value", ""))
        bad_val_display = bad_val_raw or "(empty)"

        same_errors = [
            e for e in self._errors
            if str(e.get("bad_value", "")) == bad_val_raw
        ]

        if len(same_errors) > 1:
            count_exact = self._total_errors <= len(self._errors)
            dlg = _BulkScopePopup(
                self, bad_val_display, len(same_errors), row_index + 1,
                verb="Delete", count_exact=count_exact,
            )
            dlg.exec()
            if not dlg.choice:
                return
            scope = dlg.choice
        else:
            confirmed = msgbox.critical_question(
                self,
                "Delete This Row?",
                f"Row {row_index + 1} — value <b>{bad_val_display}</b> will be "
                f"<b>permanently removed</b> from the transaction table.<br><br>"
                f"This cannot be undone without reverting to a previous snapshot.",
                confirm_label="Delete",
            )
            if not confirmed:
                return
            scope = "single"

        def worker():
            if scope == "all":
                delete_transaction_rows_bulk(
                    self.project_path, self.mapping, bad_value=bad_val_raw
                )
            else:
                delete_transaction_row(self.project_path, self.mapping, row_index)

        self._run_background(
            worker,
            lambda _: self._reload_data(force=True),
            lambda exc: msgbox.critical(self, "Failed to Delete Row",
                                         f"The row could not be deleted. Check that the project data files are accessible.\n\nDetail: {exc}"),
        )

    def _on_generate_final_file(self) -> None:
        if not self._generate_mode:
            return

        self._generate_btn.setEnabled(False)

        # Capture snapshot of the current (error-free) transaction table
        table_name = self.mapping["transaction_table"]
        tx_df = self._transaction_df.copy() if self._transaction_df is not None else None

        def worker(report_progress):
            if tx_df is not None:
                create_snapshot(
                    self.project_path,
                    {table_name: tx_df},
                    label=f"Generated output — {table_name}",
                )
            return export_final_workbook(
                self.project_path,
                report_progress=report_progress,
            )

        def on_progress(done: int, total: int) -> None:
            if self._overlay:
                self._overlay.update_progress(done, total)

        def on_success(path) -> None:
            self._generate_btn.setEnabled(True)
            if msgbox.info_question(
                self,
                "Export Complete",
                f"Your output file has been created at:<br><br><code>{path}</code><br><br>"
                f"Would you like to open the output folder now?",
                confirm_label="Open Folder",
                cancel_label="Close",
            ):
                import subprocess
                folder = str(path.parent) if hasattr(path, "parent") else str(path)
                subprocess.Popen(f'explorer "{folder}"')

        def on_error(exc) -> None:
            self._generate_btn.setEnabled(True)
            msgbox.critical(self, "Export Failed",
                            f"The output file could not be generated. Check that the output folder is accessible.\n\nDetail: {exc}")

        self._run_background_with_progress(
            worker,
            on_progress=on_progress,
            on_success=on_success,
            on_error=on_error,
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
        "color: #cbd5e1; "
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
        "color: #cbd5e1; "
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
# Bulk scope popup — multiple occurrences (Delete / Ignore / Replace)
# ---------------------------------------------------------------------------

class _BulkScopePopup:
    """Ask whether to act on all matching rows or only the selected one."""

    # colour tokens per verb
    _VERB_KIND = {
        "Delete":  "critical",
        "Ignore":  "warning",
        "Replace": "info",
    }
    _ACCENT = {
        "critical": (
            "#f87171",
            "rgba(239,68,68,0.12)", "rgba(239,68,68,0.25)",
            "rgba(239,68,68,0.06)", "rgba(239,68,68,0.15)",
            "rgba(239,68,68,0.14)", "rgba(239,68,68,0.35)", "#f87171", "rgba(239,68,68,0.25)",
        ),
        "warning": (
            "#fbbf24",
            "rgba(217,119,6,0.12)", "rgba(217,119,6,0.25)",
            "rgba(217,119,6,0.06)", "rgba(217,119,6,0.15)",
            "rgba(217,119,6,0.14)", "rgba(217,119,6,0.35)", "#fbbf24", "rgba(217,119,6,0.25)",
        ),
        "info": (
            "#60a5fa",
            "rgba(59,130,246,0.12)", "rgba(59,130,246,0.25)",
            "rgba(59,130,246,0.06)", "rgba(59,130,246,0.15)",
            "#3b82f6", "#2563eb", "#ffffff", "#2563eb",
        ),
    }
    _ICONS = {"critical": "✕", "warning": "⚠", "info": "ℹ"}

    def __init__(self, parent, bad_value: str, total_count: int, selected_row: int,
                 verb: str = "Replace", count_exact: bool = True):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QDialog
        self._dlg = QDialog(parent)
        self._dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._dlg.setAttribute(Qt.WA_StyledBackground, True)
        self._dlg.setFixedWidth(480)
        self._dlg.setModal(True)
        self._dlg.setStyleSheet(
            "QDialog { background: #13161e; border: 1px solid rgba(255,255,255,0.09); "
            "border-radius: 12px; }"
        )
        self.choice: str | None = None

        kind   = self._VERB_KIND.get(verb, "info")
        accent = self._ACCENT[kind]
        icon_char = self._ICONS[kind]
        count_label = str(total_count) if count_exact else f"at least {total_count}"
        display = bad_value if bad_value else "(empty / null)"

        _BG      = "#13161e"
        _SURFACE = "#0d1117"
        _DIVIDER = "rgba(255,255,255,0.06)"
        _MUTED   = "#94a3b8"

        root = QVBoxLayout(self._dlg)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {_BG}; border: none; border-radius: 12px; }}")
        c_lay = QVBoxLayout(card)
        c_lay.setContentsMargins(0, 0, 0, 0)
        c_lay.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(64)
        hdr.setStyleSheet(
            f"QFrame {{ background: {_SURFACE}; border: none; "
            f"border-bottom: 1px solid {_DIVIDER}; "
            f"border-top-left-radius: 12px; border-top-right-radius: 12px; }}"
        )
        h_lay = QHBoxLayout(hdr)
        h_lay.setContentsMargins(20, 0, 20, 0)
        h_lay.setSpacing(12)

        icon_box = QFrame()
        icon_box.setFixedSize(32, 32)
        icon_box.setStyleSheet(
            f"QFrame {{ background: {accent[1]}; border: 1px solid {accent[2]}; "
            f"border-radius: 8px; }}"
        )
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel(icon_char)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            f"color: {accent[0]}; font-size: 14px; font-weight: 700; "
            f"background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        h_lay.addWidget(icon_box)

        title_lbl = QLabel("Multiple Occurrences Found")
        title_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 14px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        h_lay.addWidget(title_lbl, 1)
        c_lay.addWidget(hdr)

        # Body
        body = QFrame()
        body.setStyleSheet(f"QFrame {{ background: {_BG}; border: none; }}")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(20, 16, 20, 16)

        strip = QFrame()
        strip.setStyleSheet(
            f"QFrame {{ background: {accent[3]}; border: 1px solid {accent[4]}; "
            f"border-radius: 8px; }}"
        )
        s_lay = QHBoxLayout(strip)
        s_lay.setContentsMargins(14, 10, 14, 10)
        msg_lbl = QLabel(
            f'<b style="color:#f1f5f9;">{display}</b> appears on '
            f'<b style="color:#f1f5f9;">{count_label} rows</b> in this mapping.<br><br>'
            f'{verb} all matching rows, or only Row {selected_row}?'
        )
        msg_lbl.setTextFormat(Qt.RichText)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet(
            f"color: {_MUTED}; font-size: 12px; background: transparent; border: none;"
        )
        s_lay.addWidget(msg_lbl)
        b_lay.addWidget(strip)
        c_lay.addWidget(body, 1)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            f"QFrame {{ background: {_SURFACE}; border: none; "
            f"border-top: 1px solid {_DIVIDER}; "
            f"border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }}"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(20, 0, 20, 0)
        f_lay.setSpacing(8)
        f_lay.addStretch()

        _btn_cancel_ss = (
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 7px; "
            f"color: {_MUTED}; font-size: 12px; padding: 0 16px; }}"
            "QPushButton:hover { background: rgba(255,255,255,0.09); color: #f1f5f9; }"
        )
        _btn_primary_ss = (
            f"QPushButton {{ background: {accent[5]}; border: 1px solid {accent[6]}; "
            f"border-radius: 7px; color: {accent[7]}; font-size: 12px; "
            f"font-weight: 500; padding: 0 16px; }}"
            f"QPushButton:hover {{ background: {accent[8]}; }}"
        )

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(_btn_cancel_ss)
        cancel_btn.clicked.connect(self._dlg.reject)
        f_lay.addWidget(cancel_btn)

        single_btn = QPushButton(f"Just Row {selected_row}")
        single_btn.setFixedHeight(34)
        single_btn.setCursor(Qt.PointingHandCursor)
        single_btn.setStyleSheet(_btn_cancel_ss)
        single_btn.clicked.connect(lambda: self._pick("single"))
        f_lay.addWidget(single_btn)

        all_btn = QPushButton(f"{verb} All  ({count_label})")
        all_btn.setFixedHeight(34)
        all_btn.setCursor(Qt.PointingHandCursor)
        all_btn.setStyleSheet(_btn_primary_ss)
        all_btn.clicked.connect(lambda: self._pick("all"))
        f_lay.addWidget(all_btn)

        c_lay.addWidget(footer)
        root.addWidget(card)
        self._dlg.adjustSize()

        if parent:
            QTimer.singleShot(0, self._centre)
            QTimer.singleShot(50, self._dlg.raise_)

    def _centre(self) -> None:
        p = self._dlg.parent()
        if p is None:
            return
        pg = p.window().geometry()
        self._dlg.move(
            pg.x() + (pg.width()  - self._dlg.width())  // 2,
            pg.y() + (pg.height() - self._dlg.height()) // 2,
        )

    def _pick(self, choice: str) -> None:
        self.choice = choice
        self._dlg.accept()

    def exec(self) -> None:
        self._dlg.exec()
