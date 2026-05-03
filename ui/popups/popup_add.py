from __future__ import annotations

import re
from typing import Callable

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)


# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

# Excel formula-injection chars and error strings to block
_FORMULA_STARTERS = ('=', '+', '-', '@')

_EXCEL_ERRORS: frozenset[str] = frozenset({
    "#null!", "#div/0!", "#value!", "#ref!", "#name?",
    "#num!", "#n/a", "#null", "#ref", "#value", "#name",
    "#getting_data", "#spill!", "#calc!", "#field!", "#unknown!",
})

# Compiled pattern for "looks entirely numeric" (int or float, optional sign)
_NUMERIC_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")


def _infer_col_type(df: pd.DataFrame, col: str) -> str:
    """Return 'numeric' if ≥80 % of non-empty values in *col* are numeric, else 'text'."""
    if df is None or col not in df.columns:
        return "text"
    series = df[col].dropna().astype(str).str.strip()
    series = series[series != ""]
    if len(series) < 3:
        return "text"
    numeric_count = series.apply(lambda v: bool(_NUMERIC_RE.match(v))).sum()
    return "numeric" if numeric_count / len(series) >= 0.8 else "text"


def _validate(value: str, col_type: str) -> str | None:
    """
    Validate a field value.  Returns an error message string or None if valid.
    Called for every non-key column (all are required).
    """
    stripped = value.strip()

    if not stripped:
        return "This field is required."

    lower = stripped.lower()

    # Block Excel error strings
    if lower in _EXCEL_ERRORS:
        return f"'{stripped}' is an Excel error value and cannot be stored."

    # Block formula injection
    if stripped[0] in _FORMULA_STARTERS:
        return "Value cannot start with =, +, -, or @ (prevents Excel formula injection)."

    # Type check
    if col_type == "numeric":
        if not _NUMERIC_RE.match(stripped):
            return "This column expects a numeric value (e.g. 42 or 3.14)."

    return None


# ---------------------------------------------------------------------------
# Field widget
# ---------------------------------------------------------------------------

_FIELD_NORMAL  = (
    "QLineEdit { background: rgba(255,255,255,0.04); "
    "border: 1px solid rgba(255,255,255,0.09); "
    "border-radius: 7px; color: #f1f5f9; font-size: 12px; "
    "font-family: 'Segoe UI'; padding: 0 11px; }"
    "QLineEdit:focus { border-color: rgba(59,130,246,0.5); }"
)
_FIELD_ERROR   = (
    "QLineEdit { background: rgba(239,68,68,0.05); "
    "border: 1px solid rgba(239,68,68,0.4); "
    "border-radius: 7px; color: #f1f5f9; font-size: 12px; "
    "font-family: 'Segoe UI'; padding: 0 11px; }"
)
_FIELD_PREFILL = (
    "QLineEdit { background: rgba(239,68,68,0.06); "
    "border: 1px solid rgba(239,68,68,0.2); "
    "border-radius: 7px; color: #f87171; font-size: 12px; "
    "font-family: 'Courier New'; padding: 0 11px; }"
)


class _FieldWidget(QWidget):
    """Label + input + inline error for a single dim column."""

    def __init__(self, col_name: str, col_type: str, prefill: str = "",
                 readonly: bool = False, is_key: bool = False):
        super().__init__()
        self._col_type = col_type
        self._is_key   = is_key
        self.setStyleSheet("background: transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(5)

        # Label row
        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(6)
        col_lbl = QLabel(col_name.upper())
        col_lbl.setStyleSheet(
            "color: #cbd5e1; font-size: 10px; font-weight: 600; "
            "letter-spacing: 0.7px; background: transparent; border: none;"
        )
        lbl_row.addWidget(col_lbl)

        if is_key:
            tag = _pill("Key Column",
                        "rgba(59,130,246,0.1)", "#60a5fa", "rgba(59,130,246,0.2)")
        else:
            tag = _pill("Required",
                        "rgba(239,68,68,0.08)", "#f87171", "rgba(239,68,68,0.15)")
        lbl_row.addWidget(tag)

        if col_type == "numeric" and not is_key:
            type_tag = _pill("numeric",
                             "rgba(245,158,11,0.08)", "#fbbf24", "rgba(245,158,11,0.15)")
            lbl_row.addWidget(type_tag)

        lbl_row.addStretch()
        lay.addLayout(lbl_row)

        # Input
        self.entry = QLineEdit()
        self.entry.setFixedHeight(36)
        if prefill:
            self.entry.setText(prefill)
        if readonly:
            self.entry.setReadOnly(True)
            self.entry.setStyleSheet(_FIELD_PREFILL)
        elif is_key:
            # Editable but visually distinct to show it was pre-filled
            self.entry.setStyleSheet(_FIELD_PREFILL)
            self.entry.textChanged.connect(self._on_changed)
        else:
            self.entry.setStyleSheet(_FIELD_NORMAL)
            ph = "Numeric value" if col_type == "numeric" else f"Enter {col_name}"
            self.entry.setPlaceholderText(ph)
            self.entry.textChanged.connect(self._on_changed)
        lay.addWidget(self.entry)

        # Inline error label
        self._err_lbl = QLabel("")
        self._err_lbl.setStyleSheet(
            "color: #f87171; font-size: 10px; background: transparent; border: none;"
        )
        self._err_lbl.setVisible(False)
        lay.addWidget(self._err_lbl)

    def _on_changed(self, text: str) -> None:
        err = _validate(text, self._col_type)
        if err:
            self.entry.setStyleSheet(_FIELD_ERROR)
            self._err_lbl.setText(err)
            self._err_lbl.setVisible(True)
        else:
            # Key column keeps its prefill style when valid
            self.entry.setStyleSheet(_FIELD_PREFILL if self._is_key else _FIELD_NORMAL)
            self._err_lbl.setVisible(False)

    def validate(self) -> str | None:
        """Return error message or None.  Also updates visual state."""
        err = _validate(self.entry.text(), self._col_type)
        if err:
            self.entry.setStyleSheet(_FIELD_ERROR)
            self._err_lbl.setText(err)
            self._err_lbl.setVisible(True)
        else:
            self.entry.setStyleSheet(_FIELD_PREFILL if self._is_key else _FIELD_NORMAL)
            self._err_lbl.setVisible(False)
        return err

    def value(self) -> str:
        return self.entry.text().strip()


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class PopupAdd(QDialog):
    """
    Add to Dimension dialog — 6C design.

    All non-key columns are required.  Type inference is run against the
    existing dim_df so numeric columns reject non-numeric input.
    Excel error strings and formula-injection characters are blocked.
    """

    def __init__(
        self,
        parent,
        dim_table: str,
        dim_columns: list[str],
        mapped_column: str,
        bad_value: str,
        on_confirm: Callable[[dict], None],
        dim_df: pd.DataFrame | None = None,
    ):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setFixedSize(720, 620)
        self.setStyleSheet("QDialog { background: #13161e; border-radius: 12px; }")

        self._dim_table    = dim_table
        self._dim_columns  = dim_columns
        self._mapped_col   = mapped_column
        self._bad_value    = bad_value
        self._on_confirm   = on_confirm
        self._dim_df       = dim_df
        self._fields: dict[str, _FieldWidget] = {}

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

        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: #13161e; "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        card_lay.addWidget(self._build_header())
        card_lay.addWidget(self._build_error_strip())
        card_lay.addWidget(self._build_key_warn_strip())
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
            "QFrame { background: rgba(5,150,105,0.15); "
            "border: 1px solid rgba(5,150,105,0.25); border-radius: 8px; }"
        )
        ib_lay = QHBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("+")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #34d399; font-size: 18px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        ib_lay.addWidget(icon_lbl)
        lay.addWidget(icon_box)

        header_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:14px; font-weight:600;'>Add to Dimension</span>"
            f"<br>"
            f"<span style='color:#94a3b8; font-size:11px;'>New row will be added to "
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
    # Error strip (shows the bad value that triggered this dialog)
    # ------------------------------------------------------------------

    def _build_error_strip(self) -> QFrame:
        strip = QFrame()
        strip.setStyleSheet(
            "QFrame { background: rgba(239,68,68,0.05); border: none; "
            "border-bottom: 1px solid rgba(239,68,68,0.10); }"
        )
        lay = QHBoxLayout(strip)
        lay.setContentsMargins(22, 10, 22, 10)
        lay.setSpacing(8)

        _lbl(lay, "⚠", "color:#f87171; font-size:11px;")
        _lbl(lay, "Error value:", "color:#cbd5e1; font-size:11px;")
        _lbl(
            lay,
            self._bad_value or "(empty)",
            "color:#f87171; font-size:12px; font-weight:600; font-family:'Courier New';",
        )
        _lbl(lay, "— pre-filled as the key column below",
             "color:#94a3b8; font-size:11px;")
        lay.addStretch()
        return strip

    # ------------------------------------------------------------------
    # Key-changed warning strip (hidden until key value diverges)
    # ------------------------------------------------------------------

    def _build_key_warn_strip(self) -> QFrame:
        self._key_warn_strip = QFrame()
        self._key_warn_strip.setStyleSheet(
            "QFrame { background: rgba(245,158,11,0.06); border: none; "
            "border-bottom: 1px solid rgba(245,158,11,0.12); }"
        )
        lay = QHBoxLayout(self._key_warn_strip)
        lay.setContentsMargins(22, 8, 22, 8)
        lay.setSpacing(8)

        _lbl(lay, "ⓘ", "color:#fbbf24; font-size:11px;")
        self._key_warn_lbl = QLabel("")
        self._key_warn_lbl.setTextFormat(Qt.RichText)
        self._key_warn_lbl.setWordWrap(False)
        self._key_warn_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(self._key_warn_lbl, 1)

        self._key_warn_strip.setVisible(False)
        return self._key_warn_strip

    def _on_key_changed(self, text: str) -> None:
        """Show/hide the info strip when the key column value diverges."""
        if text.strip() != (self._bad_value or "").strip():
            orig = self._bad_value or "(empty)"
            self._key_warn_lbl.setText(
                f"Key changed from <span style='color:#f87171; "
                f"font-family:\"Courier New\";'>{orig}</span> — "
                f"the transaction cell will also be updated to the new value automatically."
            )
            self._key_warn_strip.setVisible(True)
        else:
            self._key_warn_strip.setVisible(False)

    # ------------------------------------------------------------------
    # Body — scrollable 2-column grid
    # ------------------------------------------------------------------

    def _build_body(self) -> QWidget:
        wrapper = QWidget()
        wrapper.setStyleSheet("background: transparent;")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollArea > QWidget > QWidget { background: transparent; }"
        )

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        grid = QGridLayout(container)
        grid.setContentsMargins(22, 12, 22, 12)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        row_idx = 0

        # ── Key column section ────────────────────────────────────────
        grid.addWidget(_section_divider("Key Column"), row_idx, 0, 1, 2)
        row_idx += 1

        col_type = _infer_col_type(self._dim_df, self._mapped_col)
        fw = _FieldWidget(
            self._mapped_col, col_type,
            prefill=self._bad_value, is_key=True,
        )
        grid.addWidget(fw, row_idx, 0, 1, 2)
        self._fields[self._mapped_col] = fw
        # Warn when the key value diverges from the original bad_value
        fw.entry.textChanged.connect(self._on_key_changed)
        row_idx += 1

        # ── Other columns (all required) ──────────────────────────────
        other_cols = [c for c in self._dim_columns if c != self._mapped_col]

        if other_cols:
            grid.addWidget(_section_divider("Required Columns"), row_idx, 0, 1, 2)
            row_idx += 1

            col_buf: list[str] = []
            for col in other_cols:
                col_buf.append(col)
                if len(col_buf) == 2:
                    for grid_col, c in enumerate(col_buf):
                        ct = _infer_col_type(self._dim_df, c)
                        fw2 = _FieldWidget(c, ct)
                        grid.addWidget(fw2, row_idx, grid_col)
                        self._fields[c] = fw2
                    row_idx += 1
                    col_buf = []

            # leftover single column
            if col_buf:
                ct = _infer_col_type(self._dim_df, col_buf[0])
                fw2 = _FieldWidget(col_buf[0], ct)
                grid.addWidget(fw2, row_idx, 0)
                self._fields[col_buf[0]] = fw2
                row_idx += 1

        # Push all field rows to the top — absorb leftover vertical space
        grid.setRowStretch(row_idx, 1)

        scroll.setWidget(container)
        outer.addWidget(scroll, 1)
        return wrapper

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

        # Required field count hint
        req_count = sum(
            1 for c in self._dim_columns if c != self._mapped_col
        )
        self._hint_lbl = QLabel(
            f"<span style='color:#f87171;'>{req_count} required</span>"
            f" field{'s' if req_count != 1 else ''} must be filled before adding"
        )
        self._hint_lbl.setTextFormat(Qt.RichText)
        self._hint_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
        )
        lay.addWidget(self._hint_lbl, 1)

        cancel = QPushButton("Cancel")
        cancel.setFixedHeight(34)
        cancel.setStyleSheet(_ghost_btn())
        cancel.clicked.connect(self.reject)
        lay.addWidget(cancel)

        self._add_btn = QPushButton("Add Row to Dimension")
        self._add_btn.setFixedHeight(34)
        self._add_btn.setStyleSheet(_green_btn())
        self._add_btn.clicked.connect(self._submit)
        lay.addWidget(self._add_btn)

        return footer

    # ------------------------------------------------------------------
    # Submit
    # ------------------------------------------------------------------

    def _submit(self) -> None:
        errors: list[str] = []
        for col, fw in self._fields.items():
            if fw.validate() is not None:
                errors.append(col)

        if errors:
            self._hint_lbl.setText(
                f"<span style='color:#f87171;'>"
                f"{len(errors)} field{'s' if len(errors) != 1 else ''} "
                f"{'have' if len(errors) != 1 else 'has'} errors — fix before adding"
                f"</span>"
            )
            self._hint_lbl.setTextFormat(Qt.RichText)
            return

        row = {col: fw.value() for col, fw in self._fields.items()}

        # Block only exact full-row duplicates (all columns must match).
        # A shared value in one column is NOT a duplicate — only the complete
        # combination of all column values being identical constitutes a dup.
        if self._dim_df is not None and not self._dim_df.empty:
            shared_cols = [c for c in row if c in self._dim_df.columns]
            if shared_cols:
                is_dup = any(
                    all(
                        str(self._dim_df.at[idx, c]).strip() == str(row[c]).strip()
                        for c in shared_cols
                    )
                    for idx in self._dim_df.index
                )
                if is_dup:
                    self._hint_lbl.setText(
                        "<span style='color:#f87171;'>"
                        "This exact row already exists in the dimension table — "
                        "every column value matches an existing row."
                        "</span>"
                    )
                    self._hint_lbl.setTextFormat(Qt.RichText)
                    return

        self._on_confirm(row)
        self.accept()


# ---------------------------------------------------------------------------
# Small shared helpers
# ---------------------------------------------------------------------------

def _lbl(layout, text: str, style: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"{style} background: transparent; border: none;")
    layout.addWidget(lbl)
    return lbl


def _pill(text: str, bg: str, color: str, border: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"background: {bg}; color: {color}; "
        f"border: 1px solid {border}; border-radius: 4px; "
        f"font-size: 10px; font-weight: 500; padding: 1px 6px;"
    )
    return lbl


def _section_divider(title: str) -> QWidget:
    w = QWidget()
    w.setStyleSheet("background: transparent;")
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 2, 0, 2)
    lay.setSpacing(10)

    lbl = QLabel(title.upper())
    lbl.setStyleSheet(
        "color: #cbd5e1; font-size: 10px; font-weight: 600; "
        "letter-spacing: 0.8px; background: transparent; border: none;"
    )
    lay.addWidget(lbl)

    line = QFrame()
    line.setFrameShape(QFrame.HLine)
    line.setStyleSheet("background: rgba(255,255,255,0.05); border: none; max-height: 1px;")
    lay.addWidget(line, 1)
    return w


def _ghost_btn() -> str:
    return (
        "QPushButton { background: rgba(255,255,255,0.04); "
        "border: 1px solid rgba(255,255,255,0.09); "
        "border-radius: 7px; color: #94a3b8; font-size: 12px; padding: 0 16px; }"
        "QPushButton:hover { background: rgba(255,255,255,0.08); }"
    )


def _green_btn() -> str:
    return (
        "QPushButton { background: #059669; border: none; border-radius: 7px; "
        "color: #fff; font-size: 12px; font-weight: 500; padding: 0 18px; }"
        "QPushButton:hover { background: #047857; }"
    )
