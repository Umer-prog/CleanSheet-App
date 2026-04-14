from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import load_csv, save_as_csv
from core.dim_manager import append_dim_row, get_dim_columns, get_dim_dataframe
from core.error_detector import detect_errors
from core.final_export_manager import export_final_workbook
from core.mapping_manager import get_mappings
from ui.workers import ScreenBase, clear_layout, make_scroll_area


def format_dataframe_preview(df: pd.DataFrame) -> str:
    if df.empty:
        return "(No rows)"
    preview = df.fillna("")
    cols = list(preview.columns)
    col_widths = {
        col: max(len(str(col)), max((len(str(v)) for v in preview[col]), default=0))
        for col in cols
    }
    max_row_num = int(preview.index[-1]) + 1 if len(preview) > 0 else 1
    row_num_w = max(1, len(str(max_row_num)))

    def _row(label, values) -> str:
        parts = [f"{str(label):<{row_num_w}}"] + [
            f"{str(v):<{col_widths[c]}}" for c, v in zip(cols, values)
        ]
        return " | ".join(parts)

    sep = "-+-".join(["-" * row_num_w] + ["-" * col_widths[c] for c in cols])
    lines = [_row("0", cols), sep]
    for idx, row_data in preview.iterrows():
        lines.append(_row(int(idx) + 1, [row_data[c] for c in cols]))
    return "\n".join(lines)


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
    mask = df[t_col].astype(str).str.strip() == str(old_value)
    count = int(mask.sum())
    if count:
        df.loc[mask, t_col] = str(new_value)
        save_as_csv(df, csv_path)
    return count


class ViewMapping(ScreenBase):
    """Mapping view — transaction preview, error list, Replace / Add / Generate."""

    def __init__(self, parent, project: dict, mapping: dict):
        super().__init__(parent)
        self.project = project
        self.mapping = mapping
        self.project_path = Path(project["project_path"])

        self._selected_error: dict | None = None
        self._selected_error_frame: QFrame | None = None
        self._errors: list[dict] = []
        self._transaction_df: pd.DataFrame | None = None
        self._page_size = 500
        self._current_page = 0
        self._generate_mode = False
        self._generate_check_token = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 18)
        outer.setSpacing(8)

        # Header
        hdr_row = QHBoxLayout()
        mapping_lbl = QLabel(
            f"{mapping['transaction_table']}.{mapping['transaction_column']}  →  "
            f"{mapping['dim_table']}.{mapping['dim_column']}"
        )
        mapping_lbl.setFont(theme.font(18, "bold"))
        mapping_lbl.setStyleSheet("color: #f1f5f9;")
        hdr_row.addWidget(mapping_lbl, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("btn_primary")
        refresh_btn.setFixedSize(90, 34)
        refresh_btn.clicked.connect(self._reload_data)
        hdr_row.addWidget(refresh_btn)
        outer.addLayout(hdr_row)

        hint = QLabel(
            "How to use: Select an error, then use Replace to fix transaction values "
            "or Add to append missing dim values."
        )
        hint.setFont(theme.font(11))
        hint.setStyleSheet("color: #475569;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # Transaction data card
        tx_card = QFrame()
        tx_card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        tx_layout = QVBoxLayout(tx_card)
        tx_layout.setContentsMargins(12, 10, 12, 12)
        tx_layout.setSpacing(6)

        tx_top = QHBoxLayout()
        tx_title = QLabel("Transaction Data (Preview)")
        tx_title.setFont(theme.font(13, "bold"))
        tx_title.setStyleSheet("color: #f1f5f9; background: transparent;")
        tx_top.addWidget(tx_title, 1)

        pagination = QHBoxLayout()
        pagination.setSpacing(6)
        self._tx_range_lbl = QLabel("row 0–0 of 0")
        self._tx_range_lbl.setFont(theme.font(11))
        self._tx_range_lbl.setStyleSheet("color: #475569; background: transparent;")
        pagination.addWidget(self._tx_range_lbl)

        self._prev_btn = QPushButton("Prev")
        self._prev_btn.setObjectName("btn_outline")
        self._prev_btn.setFixedSize(64, 30)
        self._prev_btn.setEnabled(False)
        self._prev_btn.clicked.connect(self._go_prev_page)
        pagination.addWidget(self._prev_btn)

        self._next_btn = QPushButton("Next")
        self._next_btn.setObjectName("btn_outline")
        self._next_btn.setFixedSize(64, 30)
        self._next_btn.setEnabled(False)
        self._next_btn.clicked.connect(self._go_next_page)
        pagination.addWidget(self._next_btn)
        tx_top.addLayout(pagination)
        tx_layout.addLayout(tx_top)

        self._data_box = QTextEdit()
        self._data_box.setReadOnly(True)
        self._data_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._data_box.setFont(QFont("Courier New", 11))
        self._data_box.setStyleSheet(
            "QTextEdit { background-color: #0f1117; color: #94a3b8; border-radius: 6px; }"
        )
        tx_layout.addWidget(self._data_box)
        outer.addWidget(tx_card, 1)

        # Error panel card
        err_card = QFrame()
        err_card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        err_layout = QVBoxLayout(err_card)
        err_layout.setContentsMargins(12, 10, 12, 10)
        err_layout.setSpacing(6)

        err_title = QLabel("Errors")
        err_title.setFont(theme.font(13, "bold"))
        err_title.setStyleSheet("color: #f1f5f9; background: transparent;")
        err_layout.addWidget(err_title)

        self._err_scroll, _, self._err_list_layout = make_scroll_area()
        self._err_list_layout.setContentsMargins(6, 4, 6, 4)
        self._err_list_layout.setSpacing(4)
        err_layout.addWidget(self._err_scroll, 1)

        actions = QHBoxLayout()
        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(11))
        self._error_lbl.setStyleSheet("color: #f87171;")
        actions.addWidget(self._error_lbl, 1)

        self._generate_msg_lbl = QLabel("All errors resolved — generate final file.")
        self._generate_msg_lbl.setFont(theme.font(11, "bold"))
        self._generate_msg_lbl.setStyleSheet("color: #f1f5f9;")
        self._generate_msg_lbl.setVisible(False)
        actions.addWidget(self._generate_msg_lbl)

        self._replace_btn = QPushButton("Replace")
        self._replace_btn.setObjectName("btn_outline")
        self._replace_btn.setFixedSize(100, 38)
        self._replace_btn.setEnabled(False)
        self._replace_btn.clicked.connect(self._on_replace)
        actions.addWidget(self._replace_btn)

        self._add_btn = QPushButton("Add")
        self._add_btn.setObjectName("btn_primary")
        self._add_btn.setFixedSize(100, 38)
        self._add_btn.setEnabled(False)
        self._add_btn.clicked.connect(self._on_add)
        actions.addWidget(self._add_btn)

        self._generate_btn = QPushButton("Generate")
        self._generate_btn.setObjectName("btn_primary")
        self._generate_btn.setFixedSize(110, 38)
        self._generate_btn.setVisible(False)
        self._generate_btn.clicked.connect(self._on_generate_final_file)
        actions.addWidget(self._generate_btn)

        err_layout.addLayout(actions)
        outer.addWidget(err_card, 1)

        self._setup_overlay("Loading...")
        self._reload_data()

    # ------------------------------------------------------------------

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def _reload_data(self) -> None:
        self._set_error("")
        self._selected_error = None
        self._selected_error_frame = None
        self._set_generate_mode(False)
        self._transaction_df = None
        self._update_transaction_preview()
        self._error_list_set_loading()

        def worker():
            csv_path = (
                self.project_path / "data" / "transactions"
                / f"{self.mapping['transaction_table']}.csv"
            )
            tx_df = load_csv(csv_path)
            errors = detect_errors(self.project_path, self.mapping)
            return tx_df, errors

        def on_success(result):
            tx_df, errors = result
            self._transaction_df = tx_df
            self._current_page = 0
            self._errors = errors
            self._update_transaction_preview()
            self._render_errors()
            self._refresh_generate_state()

        def on_error(exc):
            self._transaction_df = None
            self._errors = []
            self._update_transaction_preview(f"Could not load mapping data:\n{exc}")
            self._set_error(f"Load failed: {exc}")
            self._render_errors()
            self._set_generate_mode(False)

        self._run_background(worker, on_success, on_error)

    # ------------------------------------------------------------------
    # Transaction preview
    # ------------------------------------------------------------------

    def _update_transaction_preview(self, message: str | None = None) -> None:
        self._data_box.clear()
        if message:
            self._data_box.setPlainText(message)
            self._tx_range_lbl.setText("row 0–0 of 0")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            return

        if self._transaction_df is None:
            self._data_box.setPlainText("Loading transaction data...")
            self._tx_range_lbl.setText("row 0–0 of 0")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            return

        total_rows = len(self._transaction_df)
        if total_rows == 0:
            self._data_box.setPlainText("(No rows)")
            self._tx_range_lbl.setText("row 0–0 of 0")
            self._prev_btn.setEnabled(False)
            self._next_btn.setEnabled(False)
            return

        max_page = (total_rows - 1) // self._page_size
        self._current_page = min(self._current_page, max_page)
        start = self._current_page * self._page_size
        end = min(start + self._page_size, total_rows)
        page_df = self._transaction_df.iloc[start:end].copy()
        self._data_box.setPlainText(format_dataframe_preview(page_df))
        self._tx_range_lbl.setText(f"row {start + 1}–{end} of {total_rows}")
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page < max_page)

    def _go_prev_page(self) -> None:
        if self._transaction_df is None or self._current_page <= 0:
            return
        self._current_page -= 1
        self._update_transaction_preview()

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
        self._update_transaction_preview()

    # ------------------------------------------------------------------
    # Error list
    # ------------------------------------------------------------------

    def _error_list_set_loading(self) -> None:
        clear_layout(self._err_list_layout)
        lbl = QLabel("Loading errors...")
        lbl.setFont(theme.font(12))
        lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        self._err_list_layout.addWidget(lbl)

    def _render_errors(self) -> None:
        clear_layout(self._err_list_layout)

        if not self._errors:
            lbl = QLabel("No errors found for this mapping.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self._err_list_layout.addWidget(lbl)
            return

        for error in self._errors:
            row = QFrame()
            row.setStyleSheet("QFrame { background-color: #0f1117; border-radius: 8px; }")
            row.setCursor(Qt.PointingHandCursor)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)

            text = (
                f"Row {error['row_index'] + 1}  |  "
                f"Column: {error['transaction_column']}  |  "
                f"Bad value: {error['bad_value']}"
            )
            lbl = QLabel(text)
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            row_layout.addWidget(lbl)

            def _click(event=None, err=error, frame=row):
                self._select_error(err, frame)

            row.mousePressEvent = _click
            lbl.mousePressEvent = _click

            self._err_list_layout.addWidget(row)

    def _select_error(self, error: dict, frame: QFrame) -> None:
        if self._generate_mode:
            return

        # Deselect previous
        if self._selected_error_frame:
            self._selected_error_frame.setStyleSheet(
                "QFrame { background-color: #0f1117; border-radius: 8px; }"
            )
            for lbl in self._selected_error_frame.findChildren(QLabel):
                lbl.setStyleSheet("color: #f1f5f9; background: transparent;")

        self._selected_error = error
        self._selected_error_frame = frame
        frame.setStyleSheet("QFrame { background-color: #3b82f6; border-radius: 8px; }")
        for lbl in frame.findChildren(QLabel):
            lbl.setStyleSheet("color: white; background: transparent;")

        self._replace_btn.setEnabled(True)
        has_value = bool(str(error.get("bad_value", "")).strip())
        self._add_btn.setEnabled(has_value)

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

                    self._run_background(apply_worker, lambda _: self._reload_data(),
                                         lambda exc: QMessageBox.critical(
                                             self, "Error", f"Could not replace:\n{exc}"
                                         ))

                dlg = PopupReplace(
                    self, bad_value=bad_value, valid_values=values,
                    on_confirm=on_confirm, dim_df=dim_df,
                    dim_table=self.mapping["dim_table"],
                )
                dlg.exec()

            if same_count > 1:
                from ui.views.view_mapping import _BulkScopePopup
                dlg = _BulkScopePopup(self, bad_value, same_count, row_index + 1)
                dlg.exec()
                if dlg.choice:
                    open_replace_popup(dlg.choice)
            else:
                open_replace_popup("single")

        self._run_background(worker, on_success,
                             lambda exc: self._set_error(f"Could not load dim values: {exc}"))

    def _on_add(self) -> None:
        if not self._selected_error:
            self._set_error("Select an error first.")
            return

        def worker():
            return get_dim_columns(self.project_path, self.mapping["dim_table"])

        def on_success(dim_columns):
            from ui.popups.popup_add import PopupAdd

            def on_confirm(row: dict) -> None:
                def apply_worker():
                    append_dim_row(self.project_path, self.mapping["dim_table"], row)

                self._run_background(apply_worker, lambda _: self._reload_data(),
                                     lambda exc: QMessageBox.critical(
                                         self, "Error", f"Could not append row:\n{exc}"
                                     ))

            dlg = PopupAdd(
                self,
                dim_table=self.mapping["dim_table"],
                dim_columns=dim_columns,
                mapped_column=self.mapping["dim_column"],
                bad_value=str(self._selected_error.get("bad_value", "")),
                on_confirm=on_confirm,
            )
            dlg.exec()

        self._run_background(worker, on_success,
                             lambda exc: self._set_error(f"Could not load dim columns: {exc}"))

    # ------------------------------------------------------------------
    # Generate mode
    # ------------------------------------------------------------------

    def _set_generate_mode(self, enabled: bool) -> None:
        self._generate_mode = bool(enabled)
        self._replace_btn.setVisible(not enabled)
        self._add_btn.setVisible(not enabled)
        self._generate_msg_lbl.setVisible(enabled)
        self._generate_btn.setVisible(enabled)

        if not enabled:
            if self._selected_error:
                self._replace_btn.setEnabled(True)
                has_val = bool(str(self._selected_error.get("bad_value", "")).strip())
                self._add_btn.setEnabled(has_val)
            else:
                self._replace_btn.setEnabled(False)
                self._add_btn.setEnabled(False)

    def _refresh_generate_state(self) -> None:
        if self._errors:
            self._set_generate_mode(False)
            return

        self._generate_check_token += 1
        token = self._generate_check_token

        def worker():
            mappings = get_mappings(self.project_path)
            return not any(detect_errors(self.project_path, m) for m in mappings)

        def on_success(all_clear):
            if token != self._generate_check_token:
                return
            self._set_generate_mode(bool(all_clear))
            if not all_clear:
                self._set_error("No errors here. Resolve remaining mappings to enable export.")

        self._run_background(worker, on_success,
                             lambda exc: self._set_error(f"Could not verify: {exc}"))

    def _on_generate_final_file(self) -> None:
        if not self._generate_mode:
            return

        def worker():
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
        lbl.setFont(theme.font(18, "bold"))
        lbl.setStyleSheet("color: white;")
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
        msg.setFont(theme.font(13))
        msg.setStyleSheet("color: #f1f5f9; background: transparent;")
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
