from __future__ import annotations

from typing import Callable

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)


class PopupReplace(QDialog):
    """
    Replace Value dialog — 6D design.

    Shows the dim table as a clickable list; a live preview strip updates
    as the user selects a row.  No free-text input: the user can only pick
    an existing value from the dimension table.
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
        self.setFixedSize(520, 520)
        self.setStyleSheet("QDialog { background: #13161e; border-radius: 12px; }")

        self._on_confirm     = on_confirm
        self._bad_value      = bad_value
        self._valid_values   = valid_values
        self._dim_df         = dim_df
        self._dim_table      = dim_table
        self._dim_column     = (
            dim_column
            or (list(dim_df.columns)[0] if dim_df is not None and not dim_df.empty else "")
        )
        self._selected_idx: int | None = None
        self._selected_frame: QFrame | None = None
        # list of (row_frame, replacement_value_string)
        self._row_frames: list[tuple[QFrame, str]] = []

        # Center on parent
        if parent:
            pg = parent.window().geometry()
            self.move(
                pg.x() + (pg.width()  - self.width())  // 2,
                pg.y() + (pg.height() - self.height()) // 2,
            )

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Outer card frame (gives border + radius)
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #13161e; "
            "border: 1px solid rgba(255,255,255,0.09); "
            "border-radius: 12px; }"
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

        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        title = QLabel("Replace Value")
        title.setStyleSheet(
            "color: #f1f5f9; font-size: 14px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        text_col.addWidget(title)
        sub = QLabel(
            f"Select the correct value from "
            f"<span style='color:#60a5fa; font-family:\"Courier New\";'>{self._dim_table}</span>"
        )
        sub.setTextFormat(Qt.RichText)
        sub.setStyleSheet(
            "color: #475569; font-size: 11px; background: transparent; border: none;"
        )
        text_col.addWidget(sub)
        lay.addLayout(text_col, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); "
            "border-radius: 6px; color: #64748b; font-size: 11px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); color: #94a3b8; }"
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
        _lbl(lay, "Current bad value:", "color:#64748b; font-size:11px;")
        _lbl(
            lay,
            self._bad_value or "(empty)",
            "color:#f87171; font-size:12px; font-weight:600; font-family:'Courier New';",
        )
        _lbl(lay, "→", "color:#334155;")
        _lbl(lay, "replace with a valid dimension value", "color:#334155; font-size:11px;")
        lay.addStretch()
        return strip

    def _build_dim_table(self) -> QFrame:
        COL_W = 140  # fixed px per column — enables horizontal scrolling

        wrap = QFrame()
        wrap.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 9px; }"
        )
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Table name/count bar (does NOT scroll) ────────────────────
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
             "color:#475569; font-size:10px; font-weight:600; letter-spacing:1px;")
        _lbl(th_lay, self._dim_table,
             "color:#60a5fa; font-size:11px; font-family:'Courier New';")
        th_lay.addStretch()
        _lbl(th_lay, f"{len(self._dim_df)} rows", "color:#334155; font-size:11px;")
        lay.addWidget(tbl_hdr)

        # ── Single scroll area: column headers + data rows scroll together ──
        cols = list(self._dim_df.columns)
        total_w = len(cols) * COL_W + 28  # +28 for left/right padding

        scroll = QScrollArea()
        scroll.setWidgetResizable(False)        # we set explicit size
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:horizontal { height: 6px; background: transparent; }"
            "QScrollBar::handle:horizontal { background: rgba(255,255,255,0.12); "
            "border-radius: 3px; }"
            "QScrollBar:vertical { width: 6px; background: transparent; }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,0.12); "
            "border-radius: 3px; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container.setMinimumWidth(total_w)
        rows_lay = QVBoxLayout(container)
        rows_lay.setContentsMargins(0, 0, 0, 0)
        rows_lay.setSpacing(0)
        rows_lay.setAlignment(Qt.AlignTop)

        # Column header row (inside the scroll)
        col_hdr = QFrame()
        col_hdr.setFixedHeight(28)
        col_hdr.setMinimumWidth(total_w)
        col_hdr.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.02); border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        ch_lay = QHBoxLayout(col_hdr)
        ch_lay.setContentsMargins(14, 0, 14, 0)
        ch_lay.setSpacing(0)
        for col in cols:
            lbl = QLabel(col.upper())
            lbl.setFixedWidth(COL_W)
            lbl.setStyleSheet(
                "color: #334155; font-size: 10px; font-weight: 600; "
                "letter-spacing: 0.5px; background: transparent; border: none;"
            )
            ch_lay.addWidget(lbl)
        ch_lay.addStretch()
        rows_lay.addWidget(col_hdr)

        # Data rows
        for i, (_, row) in enumerate(self._dim_df.iterrows()):
            val = str(row[self._dim_column]) if self._dim_column in row.index else str(row.iloc[0])
            frame = self._make_dim_row(i, row, cols, val, COL_W, total_w)
            self._row_frames.append((frame, val))
            rows_lay.addWidget(frame)

        scroll.setWidget(container)
        lay.addWidget(scroll, 1)
        return wrap

    def _make_dim_row(self, idx: int, row, cols: list[str], key_val: str,
                      col_w: int, min_w: int) -> QFrame:
        frame = QFrame()
        frame.setFixedHeight(36)
        frame.setMinimumWidth(min_w)
        frame.setCursor(Qt.PointingHandCursor)
        _set_row_style(frame, selected=False)

        lay = QHBoxLayout(frame)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(0)

        for col_i, col in enumerate(cols):
            val = str(row[col]) if col in row.index else ""
            is_key = col == self._dim_column or col_i == 0
            lbl = QLabel(val)
            lbl.setFixedWidth(col_w)
            lbl.setStyleSheet(
                f"color: #94a3b8; font-size: 12px; "
                f"font-family: {'\"Courier New\"' if is_key else '\"Segoe UI\"'}; "
                f"background: transparent; border: none;"
            )
            lay.addWidget(lbl)

        lay.addStretch()

        def _click(event=None, i=idx, v=key_val, f=frame):
            self._select_row(i, v, f)

        frame.mousePressEvent = _click
        for child in frame.findChildren(QLabel):
            child.mousePressEvent = _click

        return frame

    def _build_fallback_list(self) -> QFrame:
        """Shown when no dim_df is available: simple list of valid_values."""
        wrap = QFrame()
        wrap.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 9px; }"
        )
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        rows_lay = QVBoxLayout(container)
        rows_lay.setContentsMargins(0, 0, 0, 0)
        rows_lay.setSpacing(0)
        rows_lay.setAlignment(Qt.AlignTop)

        for i, val in enumerate(self._valid_values):
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
            rows_lay.addWidget(frame)

        scroll.setWidget(container)
        lay.addWidget(scroll, 1)
        return wrap

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
        _lbl(lay, "Will replace:", "color:#64748b; font-size:11px;")

        self._preview_from = QLabel(self._bad_value or "(empty)")
        self._preview_from.setStyleSheet(
            "color: #f87171; font-size: 12px; font-weight: 600; "
            "font-family: 'Courier New'; background: transparent; border: none;"
        )
        lay.addWidget(self._preview_from)

        _lbl(lay, "→", "color:#334155;")

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
        if self._selected_frame and self._selected_frame is not frame:
            _set_row_style(self._selected_frame, selected=False)
            for lbl in self._selected_frame.findChildren(QLabel):
                ss = lbl.styleSheet()
                lbl.setStyleSheet(
                    ss.replace("color: #93c5fd", "color: #94a3b8")
                      .replace("color: #7dd3fc", "color: #64748b")
                )

        self._selected_idx   = idx
        self._selected_frame = frame
        _set_row_style(frame, selected=True)
        for lbl in frame.findChildren(QLabel):
            ss = lbl.styleSheet()
            lbl.setStyleSheet(
                ss.replace("color: #94a3b8", "color: #93c5fd")
                  .replace("color: #64748b", "color: #7dd3fc")
            )

        self._preview_to.setText(value)
        self._preview_strip.setVisible(True)
        self._confirm_btn.setEnabled(True)

    def _submit(self) -> None:
        if self._selected_idx is None:
            return
        _, value = self._row_frames[self._selected_idx]
        self._on_confirm(value)
        self.accept()


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
        "color: #334155; border: 1px solid rgba(255,255,255,0.07); }"
    )
