from __future__ import annotations

from pathlib import Path

import pandas as pd
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.data_loader import load_dim_json
from core.mapping_manager import add_mapping, get_mappings
from ui.workers import ScreenBase, clear_layout, make_scroll_area

_SIDEBAR_W = 320


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

        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(_SIDEBAR_W)
        sb = QVBoxLayout(sidebar)
        sb.setContentsMargins(20, 26, 20, 20)
        sb.setSpacing(10)

        t = QLabel("Mapper")
        t.setFont(theme.font(20, "bold"))
        t.setStyleSheet("color: #f1f5f9;")
        sb.addWidget(t)

        desc = QLabel("Map transaction tables with dimension tables\nusing selected columns.")
        desc.setFont(theme.font(12))
        desc.setStyleSheet("color: #94a3b8;")
        sb.addWidget(desc)
        sb.addSpacing(6)

        back_btn = QPushButton("Back To Data Loader")
        back_btn.setObjectName("btn_ghost")
        back_btn.setFixedHeight(38)
        back_btn.clicked.connect(self._go_back)
        sb.addWidget(back_btn)
        sb.addStretch()
        root.addWidget(sidebar)

        # --- Content ---
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(22, 18, 22, 18)
        c_layout.setSpacing(8)

        title = QLabel("Mapper")
        title.setFont(theme.font(22, "bold"))
        title.setStyleSheet("color: #f1f5f9;")
        c_layout.addWidget(title)

        tip = QFrame()
        tip.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        tip_layout = QVBoxLayout(tip)
        tip_layout.setContentsMargins(12, 8, 12, 8)
        tip_lbl = QLabel(
            "How to use: Select one table on each side, pick columns, then confirm. "
            "Repeat until every table is mapped."
        )
        tip_lbl.setFont(theme.font(11))
        tip_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        tip_lbl.setWordWrap(True)
        tip_layout.addWidget(tip_lbl)
        c_layout.addWidget(tip)

        # Table lists (dim | transaction)
        lists_row = QHBoxLayout()
        lists_row.setSpacing(12)

        self._dim_scroll, _, self._dim_btn_layout = make_scroll_area()
        self._dim_btn_layout.setContentsMargins(10, 8, 10, 8)
        self._dim_btn_layout.setSpacing(4)
        dim_card = self._wrap_card(self._dim_scroll, "Dimension Tables", fixed_height=150)
        lists_row.addWidget(dim_card, 1)

        self._tx_scroll, _, self._tx_btn_layout = make_scroll_area()
        self._tx_btn_layout.setContentsMargins(10, 8, 10, 8)
        self._tx_btn_layout.setSpacing(4)
        tx_card = self._wrap_card(self._tx_scroll, "Transaction Tables", fixed_height=150)
        lists_row.addWidget(tx_card, 1)
        c_layout.addLayout(lists_row)

        # Column selectors
        selector = QFrame()
        selector.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        sel_layout = QVBoxLayout(selector)
        sel_layout.setContentsMargins(12, 10, 12, 12)
        sel_layout.setSpacing(6)

        col_labels_row = QHBoxLayout()
        dim_col_lbl = QLabel("Dimension Column")
        dim_col_lbl.setFont(theme.font(12, "bold"))
        dim_col_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        tx_col_lbl = QLabel("Transaction Column")
        tx_col_lbl.setFont(theme.font(12, "bold"))
        tx_col_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        col_labels_row.addWidget(dim_col_lbl, 1)
        col_labels_row.addWidget(tx_col_lbl, 1)
        sel_layout.addLayout(col_labels_row)

        menus_row = QHBoxLayout()
        menus_row.setSpacing(12)
        self._dim_column_menu = QComboBox()
        self._dim_column_menu.addItem("Select Column")
        self._tx_column_menu = QComboBox()
        self._tx_column_menu.addItem("Select Column")
        menus_row.addWidget(self._dim_column_menu, 1)
        menus_row.addWidget(self._tx_column_menu, 1)
        sel_layout.addLayout(menus_row)

        confirm_row = QHBoxLayout()
        confirm_row.addStretch()
        confirm_mapping_btn = QPushButton("Confirm Mapping")
        confirm_mapping_btn.setObjectName("btn_primary")
        confirm_mapping_btn.setFixedHeight(38)
        confirm_mapping_btn.clicked.connect(self._on_confirm_mapping)
        confirm_row.addWidget(confirm_mapping_btn)
        sel_layout.addLayout(confirm_row)
        c_layout.addWidget(selector)

        # Mappings list
        mappings_card = QFrame()
        mappings_card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        mappings_card_layout = QVBoxLayout(mappings_card)
        mappings_card_layout.setContentsMargins(12, 10, 12, 10)
        mappings_card_layout.setSpacing(4)

        mapping_title = QLabel("Confirmed Mappings")
        mapping_title.setFont(theme.font(13, "bold"))
        mapping_title.setStyleSheet("color: #f1f5f9; background: transparent;")
        mappings_card_layout.addWidget(mapping_title)

        self._mapping_scroll, _, self._mapping_list_layout = make_scroll_area()
        self._mapping_list_layout.setContentsMargins(6, 4, 6, 4)
        self._mapping_list_layout.setSpacing(4)
        mappings_card_layout.addWidget(self._mapping_scroll, 1)
        c_layout.addWidget(mappings_card, 1)

        # Footer
        footer_row = QHBoxLayout()
        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(12))
        self._error_lbl.setStyleSheet("color: #f87171;")
        footer_row.addWidget(self._error_lbl, 1)

        finish_btn = QPushButton("Finish Setup")
        finish_btn.setObjectName("btn_primary")
        finish_btn.setFixedHeight(42)
        finish_btn.setFixedWidth(150)
        finish_btn.clicked.connect(self._on_finish_setup)
        footer_row.addWidget(finish_btn)
        c_layout.addLayout(footer_row)

        root.addWidget(content, 1)

        self._setup_overlay("Loading...")
        self._refresh_tables()
        self._refresh_mappings()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap_card(inner_widget: QWidget, label_text: str, fixed_height: int) -> QFrame:
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        card.setFixedHeight(fixed_height)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        lbl = QLabel(label_text)
        lbl.setFont(theme.font(13, "bold"))
        lbl.setStyleSheet("color: #f1f5f9; padding: 8px 10px 4px 10px; background: transparent;")
        layout.addWidget(lbl)
        layout.addWidget(inner_widget, 1)
        return card

    def _go_back(self) -> None:
        from ui.screen1_sources import Screen1Sources
        self.app.show_screen(Screen1Sources, project=self.project)

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    # ------------------------------------------------------------------
    # Table selection
    # ------------------------------------------------------------------

    def _refresh_tables(self) -> None:
        for table_name in self._dim_tables:
            btn = self._nav_btn(table_name)
            btn.clicked.connect(lambda _=False, t=table_name: self._select_dim_table(t))
            self._dim_btn_layout.addWidget(btn)
            self._dim_buttons[table_name] = btn

        for table_name in self._transaction_tables:
            btn = self._nav_btn(table_name)
            btn.clicked.connect(lambda _=False, t=table_name: self._select_transaction_table(t))
            self._tx_btn_layout.addWidget(btn)
            self._transaction_buttons[table_name] = btn

    @staticmethod
    def _nav_btn(label: str) -> QPushButton:
        btn = QPushButton(label)
        btn.setObjectName("btn_outline")
        btn.setFixedHeight(34)
        return btn

    def _set_button_selection(self, button_map: dict, selected_name: str) -> None:
        for name, btn in button_map.items():
            if name == selected_name:
                btn.setStyleSheet(
                    "QPushButton { background-color: #3b82f6; color: white; "
                    "border: none; border-radius: 7px; padding: 6px 14px; font-weight: 600; }"
                )
            else:
                btn.setObjectName("btn_outline")
                btn.setStyleSheet("")  # revert to QSS

    def _select_dim_table(self, table_name: str) -> None:
        self._set_error("")
        self._selected_dim_table = table_name
        self._set_button_selection(self._dim_buttons, table_name)
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
        self._set_button_selection(self._transaction_buttons, table_name)
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
        self._set_button_selection(self._dim_buttons, "__none__")
        self._set_button_selection(self._transaction_buttons, "__none__")
        self._dim_column_menu.clear()
        self._dim_column_menu.addItem("Select Column")
        self._tx_column_menu.clear()
        self._tx_column_menu.addItem("Select Column")

    def _refresh_mappings(self) -> None:
        clear_layout(self._mapping_list_layout)

        if not self._pending_mappings:
            lbl = QLabel("No mappings added yet.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self._mapping_list_layout.addWidget(lbl)
            return

        for idx, mapping in enumerate(self._pending_mappings):
            row = QFrame()
            row.setStyleSheet("QFrame { background-color: #0f1117; border-radius: 8px; }")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(10, 6, 8, 6)

            text = (
                f"{mapping['transaction_table']}.{mapping['transaction_column']}  ↔  "
                f"{mapping['dim_table']}.{mapping['dim_column']}"
            )
            lbl = QLabel(text)
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            row_layout.addWidget(lbl, 1)

            del_btn = QPushButton("✕")
            del_btn.setObjectName("btn_danger")
            del_btn.setFixedSize(32, 28)
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
