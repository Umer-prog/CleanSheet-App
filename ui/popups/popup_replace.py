from __future__ import annotations

from typing import Callable

import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QTableView, QVBoxLayout, QWidget,
)

from ui.workers import Worker


# ---------------------------------------------------------------------------
# Virtualised data model — only visible rows are rendered by Qt
# ---------------------------------------------------------------------------

class _DataFrameModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame, parent=None):
        super().__init__(parent)
        self._df = df

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._df)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self._df.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            return str(self._df.iloc[index.row(), index.column()])
        return None

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return str(self._df.columns[section]).upper()
        return None

    def update_df(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df
        self.endResetModel()


# ---------------------------------------------------------------------------
# Replace Value dialog
# ---------------------------------------------------------------------------

class PopupReplace(QDialog):
    """
    Replace Value dialog — 6D design.

    Shows the dim table as a virtualised QTableView (all rows accessible,
    only visible ones rendered). A live preview strip updates as the user
    selects a row.
    """

    def __init__(
        self,
        parent,
        bad_value: str,
        valid_values: list[str],
        on_confirm: Callable[[str], None],
        dim_df: pd.DataFrame | None = None,
        dim_table: str = "",
        dim_column: str = "",
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setFixedSize(720, 520)
        self.setStyleSheet("QDialog { background: #13161e; border-radius: 12px; }")

        self._on_confirm   = on_confirm
        self._bad_value    = bad_value
        self._valid_values = valid_values
        self._dim_df       = dim_df
        self._dim_table    = dim_table
        self._dim_column   = (
            dim_column
            or (list(dim_df.columns)[0] if dim_df is not None and not dim_df.empty else "")
        )
        self._selected_value: str | None = None
        self._selected_frame: QFrame | None = None
        self._row_frames: list[tuple[QFrame, str]] = []  # fallback list only
        self._table_view: QTableView | None = None
        self._full_df: pd.DataFrame | None = self._dim_df
        self._search_query: str = ""
        self._search_debounce: QTimer | None = None
        self._active_search_worker: Worker | None = None

        # Centre on parent
        if parent:
            pg = parent.window().geometry()
            self.move(
                pg.x() + (pg.width()  - self.width())  // 2,
                pg.y() + (pg.height() - self.height()) // 2,
            )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #13161e; "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        card_lay.addWidget(self._build_header())
        card_lay.addWidget(self._build_body(), 1)
        card_lay.addWidget(self._build_footer())

        root.addWidget(card)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def _build_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(64)
        hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(12)

        icon_box = QFrame()
        icon_box.setFixedSize(34, 34)
        icon_box.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.12); "
            "border: 1px solid rgba(59,130,246,0.25); border-radius: 8px; }"
        )
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("✎")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #60a5fa; font-size: 15px; background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        header_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:14px; font-weight:600;'>Replace Value</span>"
            f"<br>"
            f"<span style='color:#94a3b8; font-size:11px;'>Select the correct value from "
            f"<span style='color:#60a5fa; font-family:\"Courier New\";'>{self._dim_table}</span></span>"
        )
        header_lbl.setTextFormat(Qt.RichText)
        header_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(header_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(
           "QPushButton { background: rgba(255,255,255,0.06); "
            "border: 1px solid rgba(255,255,255,0.14); border-radius: 6px; "
            "color: #94a3b8; font-size: 12px; padding: 0; }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); color: #f87171; }"
        )
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return hdr

    # ------------------------------------------------------------------
    # Body
    # ------------------------------------------------------------------

    def _build_body(self) -> QWidget:
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.setSpacing(12)

        lay.addWidget(self._build_bad_value_strip())

        has_df = self._dim_df is not None and not self._dim_df.empty
        if has_df:
            lay.addWidget(self._build_dim_table(), 1)
        else:
            lay.addWidget(self._build_fallback_list(), 1)

        self._preview_strip = self._build_preview_strip()
        self._preview_strip.setVisible(False)
        lay.addWidget(self._preview_strip)

        return body

    def _build_bad_value_strip(self) -> QFrame:
        strip = QFrame()
        strip.setStyleSheet(
            "QFrame { background: rgba(239,68,68,0.06); "
            "border: 1px solid rgba(239,68,68,0.15); border-radius: 8px; }"
        )
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(14, 9, 14, 9)
        lay.setSpacing(8)

        _lbl(lay, "⚠", "color:#f87171; font-size:11px;")
        _lbl(lay, "Current bad value:", "color:#cbd5e1; font-size:11px;")
        _lbl(
            lay,
            self._bad_value or "(empty)",
            "color:#f87171; font-size:12px; font-weight:600; font-family:'Courier New';",
        )
        _lbl(lay, "→", "color:#94a3b8;")
        _lbl(lay, "replace with a valid dimension value", "color:#94a3b8; font-size:11px;")
        lay.addStretch()
        return strip

    def _build_dim_table(self) -> QFrame:
        wrap = QFrame()
        wrap.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 9px; }"
        )
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Table name / count bar ────────────────────────────────────
        tbl_hdr = QFrame()
        tbl_hdr.setFixedHeight(36)
        tbl_hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        th_lay = QHBoxLayout(tbl_hdr)
        th_lay.setContentsMargins(14, 0, 14, 0)
        th_lay.setSpacing(8)
        _lbl(th_lay, "DIMENSION TABLE",
             "color:#cbd5e1; font-size:10px; font-weight:600; letter-spacing:1px;")
        _lbl(th_lay, self._dim_table,
             "color:#60a5fa; font-size:11px; font-family:'Courier New';")
        th_lay.addStretch()
        self._row_count_lbl = _lbl(th_lay, f"{len(self._dim_df)} rows",
                                   "color:#94a3b8; font-size:11px;")
        lay.addWidget(tbl_hdr)

        # ── Search bar ────────────────────────────────────────────────
        search_frame = QFrame()
        search_frame.setFixedHeight(54)
        search_frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        sf_lay = QHBoxLayout(search_frame)
        sf_lay.setContentsMargins(12, 10, 12, 10)
        self._table_search = QLineEdit()
        self._table_search.setPlaceholderText("Search values...")
        self._table_search.setFixedHeight(30)
        self._table_search.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; "
            "color: #94a3b8; font-size: 12px; padding: 0 10px; }"
            "QLineEdit:focus { border-color: rgba(59,130,246,0.4); "
            "background: rgba(255,255,255,0.06); color: #cbd5e1; }"
            "QLineEdit::placeholder { color: rgba(148,163,184,0.55); }"
        )
        self._table_search.textChanged.connect(self._on_table_search)
        sf_lay.addWidget(self._table_search)
        lay.addWidget(search_frame)

        # Debounce timer — fires _fire_filter 300ms after the last keystroke
        self._search_debounce = QTimer(self)
        self._search_debounce.setSingleShot(True)
        self._search_debounce.setInterval(300)
        self._search_debounce.timeout.connect(self._fire_filter)

        # ── QTableView — direct model, filtered in background worker ──
        self._table_model = _DataFrameModel(self._dim_df)

        self._table_view = QTableView()
        self._table_view.setModel(self._table_model)
        self._table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table_view.verticalHeader().setVisible(False)
        self._table_view.horizontalHeader().setStretchLastSection(True)
        self._table_view.horizontalHeader().setDefaultSectionSize(140)
        self._table_view.verticalHeader().setDefaultSectionSize(36)
        self._table_view.setShowGrid(False)
        self._table_view.setStyleSheet(
            "QTableView { background: transparent; border: none; "
            "color: #94a3b8; font-size: 12px; outline: none; }"
            "QTableView::item { padding: 0 14px; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); }"
            "QTableView::item:selected { background: rgba(59,130,246,0.10); "
            "color: #93c5fd; }"
            "QHeaderView { border: none; }"
            "QHeaderView::section { background: rgba(255,255,255,0.02); "
            "color: #cbd5e1; font-size: 10px; font-weight: 600; "
            "border: none; border-bottom: 1px solid rgba(255,255,255,0.06); "
            "padding: 4px 14px; }"
            "QScrollBar:vertical { width: 6px; background: transparent; margin: 0; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12); "
            "border-radius: 3px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
            "QScrollBar:horizontal { height: 6px; background: transparent; margin: 0; }"
            "QScrollBar::handle:horizontal { background: rgba(255,255,255,0.12); "
            "border-radius: 3px; min-width: 20px; }"
            "QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }"
        )
        self._table_view.selectionModel().selectionChanged.connect(self._on_dim_selection)
        lay.addWidget(self._table_view, 1)
        return wrap

    def _on_table_search(self, text: str) -> None:
        self._search_query = text
        self._search_debounce.stop()
        self._search_debounce.start()

    def _fire_filter(self) -> None:
        query = self._search_query.strip()
        full = self._full_df
        if not query:
            self._table_model.update_df(full)
            self._row_count_lbl.setText(f"{len(full)} rows")
            return

        def _do_filter():
            masks = [
                full[col].astype(str).str.contains(query, case=False, na=False)
                for col in full.columns
            ]
            mask = masks[0]
            for m in masks[1:]:
                mask = mask | m
            return full[mask].reset_index(drop=True)

        def _on_done(filtered: pd.DataFrame) -> None:
            self._table_model.update_df(filtered)
            visible = len(filtered)
            total = len(self._full_df)
            self._row_count_lbl.setText(
                f"{visible} / {total} rows" if self._search_query.strip() else f"{total} rows"
            )

        w = Worker(_do_filter)
        w.finished.connect(_on_done)
        w.errored.connect(lambda _: None)
        w.start()
        self._active_search_worker = w

    def _on_dim_selection(self, selected, deselected) -> None:
        indexes = self._table_view.selectionModel().selectedRows()
        if not indexes:
            return
        df_row = self._table_model._df.iloc[indexes[0].row()]
        val = (str(df_row[self._dim_column])
               if self._dim_column in df_row.index else str(df_row.iloc[0]))
        self._selected_value = val
        self._preview_to.setText(val)
        self._preview_strip.setVisible(True)
        self._confirm_btn.setEnabled(True)

    def _build_fallback_list(self) -> QFrame:
        """Shown when no dim_df is available — simple list of valid_values with search."""
        wrap = QFrame()
        wrap.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 9px; }"
        )
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Search bar ────────────────────────────────────────────────
        search_frame = QFrame()
        search_frame.setFixedHeight(44)
        search_frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        sf_lay = QHBoxLayout(search_frame)
        sf_lay.setContentsMargins(12, 6, 12, 6)
        self._fallback_search = QLineEdit()
        self._fallback_search.setPlaceholderText("Search values...")
        self._fallback_search.setFixedHeight(30)
        self._fallback_search.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; "
            "color: #94a3b8; font-size: 12px; padding: 0 10px; }"
            "QLineEdit:focus { border-color: rgba(59,130,246,0.4); "
            "background: rgba(255,255,255,0.06); color: #cbd5e1; }"
            "QLineEdit::placeholder { color: rgba(148,163,184,0.55); }"
        )
        self._fallback_search.textChanged.connect(self._on_fallback_search)
        sf_lay.addWidget(self._fallback_search)
        lay.addWidget(search_frame)

        # ── Scrollable value list ─────────────────────────────────────
        self._fallback_scroll = QScrollArea()
        self._fallback_scroll.setWidgetResizable(True)
        self._fallback_scroll.setFrameStyle(QFrame.NoFrame)
        self._fallback_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._fallback_container = QWidget()
        self._fallback_container.setStyleSheet("background: transparent;")
        self._fallback_rows_lay = QVBoxLayout(self._fallback_container)
        self._fallback_rows_lay.setContentsMargins(0, 0, 0, 0)
        self._fallback_rows_lay.setSpacing(0)
        self._fallback_rows_lay.setAlignment(Qt.AlignTop)

        self._build_fallback_rows(self._valid_values)

        self._fallback_scroll.setWidget(self._fallback_container)
        lay.addWidget(self._fallback_scroll, 1)
        return wrap

    def _build_fallback_rows(self, values: list[str]) -> None:
        """Populate the fallback list with the given values (clears first)."""
        while self._fallback_rows_lay.count():
            item = self._fallback_rows_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._row_frames.clear()

        for i, val in enumerate(values):
            frame = QFrame()
            frame.setFixedHeight(36)
            frame.setCursor(Qt.PointingHandCursor)
            _set_row_style(frame, selected=False)
            fl = QHBoxLayout(frame)
            fl.setContentsMargins(14, 0, 14, 0)
            lbl = QLabel(val)
            lbl.setStyleSheet(
                "color: #94a3b8; font-size: 12px; font-family: 'Courier New'; "
                "background: transparent; border: none;"
            )
            fl.addWidget(lbl)

            def _click(event=None, _i=i, _v=val, _f=frame):
                self._select_row(_i, _v, _f)

            frame.mousePressEvent = _click
            lbl.mousePressEvent   = _click
            self._row_frames.append((frame, val))
            self._fallback_rows_lay.addWidget(frame)

    def _on_fallback_search(self, text: str) -> None:
        query = text.strip().lower()
        filtered = [v for v in self._valid_values if query in v.lower()] if query else self._valid_values
        self._build_fallback_rows(filtered)

    def _build_preview_strip(self) -> QFrame:
        strip = QFrame()
        strip.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.06); "
            "border: 1px solid rgba(59,130,246,0.15); border-radius: 8px; }"
        )
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(14, 9, 14, 9)
        lay.setSpacing(8)

        _lbl(lay, "✓", "color:#60a5fa; font-size:11px;")
        _lbl(lay, "Will replace:", "color:#cbd5e1; font-size:11px;")

        self._preview_from = QLabel(self._bad_value or "(empty)")
        self._preview_from.setStyleSheet(
            "color: #f87171; font-size: 12px; font-weight: 600; "
            "font-family: 'Courier New'; background: transparent; border: none;"
        )
        lay.addWidget(self._preview_from)

        _lbl(lay, "→", "color:#94a3b8;")

        self._preview_to = QLabel("")
        self._preview_to.setStyleSheet(
            "color: #34d399; font-size: 12px; font-weight: 600; "
            "font-family: 'Courier New'; background: transparent; border: none;"
        )
        lay.addWidget(self._preview_to)
        lay.addStretch()
        return strip

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(8)
        lay.addStretch()

        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(34)
        cancel.setStyleSheet(_ghost_btn())
        cancel.clicked.connect(self.reject)
        lay.addWidget(cancel)

        self._confirm_btn = QPushButton("Apply Replace")
        self._confirm_btn.setFixedHeight(34)
        self._confirm_btn.setEnabled(False)
        self._confirm_btn.setStyleSheet(_primary_btn())
        self._confirm_btn.clicked.connect(self._submit)
        lay.addWidget(self._confirm_btn)

        return footer

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def _select_row(self, idx: int, value: str, frame: QFrame) -> None:
        """Used by the fallback list (no dim_df) path only."""
        if self._selected_frame and self._selected_frame is not frame:
            _set_row_style(self._selected_frame, selected=False)
            for lbl in self._selected_frame.findChildren(QLabel):
                ss = lbl.styleSheet()
                lbl.setStyleSheet(
                    ss.replace("color: #93c5fd", "color: #94a3b8")
                      .replace("color: #7dd3fc", "color: #94a3b8")
                )

        self._selected_frame = frame
        self._selected_value = value
        _set_row_style(frame, selected=True)
        for lbl in frame.findChildren(QLabel):
            ss = lbl.styleSheet()
            lbl.setStyleSheet(
                ss.replace("color: #94a3b8", "color: #93c5fd")
                  .replace("color: #94a3b8", "color: #7dd3fc")
            )

        self._preview_to.setText(value)
        self._preview_strip.setVisible(True)
        self._confirm_btn.setEnabled(True)

    def _submit(self) -> None:
        if self._selected_value is None:
            return
        self._on_confirm(self._selected_value)
        self.accept()


# ---------------------------------------------------------------------------
# Read-only dim-table viewer
# ---------------------------------------------------------------------------

class PopupDimView(PopupReplace):
    """View-only popup for a dimension table.

    Reuses PopupReplace's virtualised QTableView. All rows accessible via
    scroll. No row selection, no confirm button.
    """

    def __init__(self, parent, dim_df: pd.DataFrame, dim_table: str):
        super().__init__(
            parent,
            bad_value="",
            valid_values=[],
            on_confirm=lambda _: None,
            dim_df=dim_df,
            dim_table=dim_table,
            dim_column=str(dim_df.columns[0]) if len(dim_df.columns) else "",
        )

    # -- overrides called from PopupReplace.__init__ via dynamic dispatch --

    def _build_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setFixedHeight(64)
        hdr.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.setSpacing(12)

        icon_box = QFrame()
        icon_box.setFixedSize(34, 34)
        icon_box.setStyleSheet(
            "QFrame { background: rgba(34,211,153,0.10); "
            "border: 1px solid rgba(34,211,153,0.22); border-radius: 8px; }"
        )
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("◨")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #34d399; font-size: 15px; background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        row_count = len(self._dim_df) if self._dim_df is not None else 0
        header_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:14px; font-weight:600;'>Dimension Table</span>"
            f"<br>"
            f"<span style='color:#94a3b8; font-size:11px;'>"
            f"<span style='color:#60a5fa; font-family:\"Courier New\";'>{self._dim_table}</span>"
            f"  ·  {row_count:,} rows</span>"
        )
        header_lbl.setTextFormat(Qt.RichText)
        header_lbl.setStyleSheet("background: transparent; border: none;")
        lay.addWidget(header_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(
        "QPushButton { background: rgba(255,255,255,0.06); "
            "border: 1px solid rgba(255,255,255,0.14); border-radius: 6px; "
            "color: #94a3b8; font-size: 12px; padding: 0; }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); color: #f87171; }"
        )
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return hdr

    def _build_body(self) -> QWidget:
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        lay = QVBoxLayout(body)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.setSpacing(0)
        lay.addWidget(self._build_dim_table(), 1)
        return body

    def _build_dim_table(self) -> QFrame:
        """Parent builds the QTableView, then we disable selection."""
        wrap = super()._build_dim_table()
        self._table_view.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table_view.setFocusPolicy(Qt.NoFocus)
        try:
            self._table_view.selectionModel().selectionChanged.disconnect()
        except Exception:
            pass
        return wrap

    def _build_footer(self) -> QFrame:
        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QHBoxLayout(footer)
        lay.setContentsMargins(22, 0, 22, 0)
        lay.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(34)
        close_btn.setStyleSheet(_ghost_btn())
        close_btn.clicked.connect(self.reject)
        lay.addWidget(close_btn)
        return footer


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------

def _lbl(layout, text: str, style: str, stretch: int = 0) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"{style} background: transparent; border: none;")
    if stretch:
        layout.addWidget(lbl, stretch)
    else:
        layout.addWidget(lbl)
    return lbl


def _set_row_style(frame: QFrame, selected: bool) -> None:
    if selected:
        frame.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.10); border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); }"
        )
    else:
        frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.04); }"
        )


def _ghost_btn() -> str:
    return (
        "QPushButton { background: rgba(255,255,255,0.04); "
        "border: 1px solid rgba(255,255,255,0.09); "
        "border-radius: 7px; color: #94a3b8; font-size: 12px; padding: 0 16px; }"
        "QPushButton:hover { background: rgba(255,255,255,0.08); }"
    )


def _primary_btn() -> str:
    return (
        "QPushButton { background: #3b82f6; border: none; border-radius: 7px; "
        "color: #fff; font-size: 12px; font-weight: 500; padding: 0 18px; }"
        "QPushButton:hover:enabled { background: #2563eb; }"
        "QPushButton:disabled { background: rgba(255,255,255,0.04); "
        "color: rgba(148,163,184,0.45); border: 1px solid rgba(255,255,255,0.07); }"
    )
