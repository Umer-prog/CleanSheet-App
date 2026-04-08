from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

import ui.theme as theme
from core.data_loader import load_csv, load_dim_json
from core.mapping_manager import add_mapping, get_mappings


def mapping_key(mapping: dict) -> tuple[str, str, str, str]:
    return (
        mapping.get("transaction_table", "").strip(),
        mapping.get("transaction_column", "").strip(),
        mapping.get("dim_table", "").strip(),
        mapping.get("dim_column", "").strip(),
    )


def validate_mapping_selection(
    transaction_table: str | None,
    dim_table: str | None,
    transaction_column: str | None,
    dim_column: str | None,
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
    transaction_tables: list[str],
    dim_tables: list[str],
    mappings: list[dict],
) -> tuple[list[str], list[str]]:
    mapped_transactions = {m.get("transaction_table", "").strip() for m in mappings}
    mapped_dimensions = {m.get("dim_table", "").strip() for m in mappings}

    missing_tx = [name for name in transaction_tables if name not in mapped_transactions]
    missing_dim = [name for name in dim_tables if name not in mapped_dimensions]
    return missing_tx, missing_dim


class Screen2Mappings(ctk.CTkFrame):
    """Stage 1 screen to define dim/transaction column mappings."""

    def __init__(self, parent, app, project: dict):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.app = app
        self.project = project
        self.project_path = Path(project["project_path"])

        self._transaction_tables = list(project.get("transaction_tables", []))
        self._dim_tables = list(project.get("dim_tables", []))
        self._pending_mappings: list[dict] = []

        self._selected_dim_table: str | None = None
        self._selected_transaction_table: str | None = None
        self._dim_columns: list[str] = []
        self._transaction_columns: list[str] = []

        self._selected_dim_button = None
        self._selected_transaction_button = None
        self._dim_buttons: dict[str, ctk.CTkButton] = {}
        self._transaction_buttons: dict[str, ctk.CTkButton] = {}

        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()
        self._refresh_tables()
        self._refresh_mappings()

    def _build_left_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=theme.get("sidebar_bg"), corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="Stage 1 Setup",
            text_color=theme.get("text_light"),
            font=ctk.CTkFont(size=20, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(26, 10))

        ctk.CTkLabel(
            panel,
            text="Screen 2: Define mappings\nbetween transaction and\ndimension columns.",
            text_color=theme.get("text_light"),
            justify="left",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkButton(
            panel,
            text="Back To Screen 1",
            width=180,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("text_light"),
            text_color=theme.get("text_light"),
            command=self._go_back,
        ).pack(anchor="w", padx=20)

    def _build_right_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=theme.get("secondary"), corner_radius=0)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            panel,
            text="Screen 2: Define Mappings",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 10))

        top_grid = ctk.CTkFrame(panel, fg_color="transparent")
        top_grid.grid(row=1, column=0, sticky="ew", padx=22)
        top_grid.grid_columnconfigure(0, weight=1)
        top_grid.grid_columnconfigure(1, weight=1)

        self._dim_list = ctk.CTkScrollableFrame(top_grid, fg_color="white", corner_radius=10, height=175)
        self._dim_list.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._tx_list = ctk.CTkScrollableFrame(top_grid, fg_color="white", corner_radius=10, height=175)
        self._tx_list.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(
            self._dim_list,
            text="Dimension Tables",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 6))
        ctk.CTkLabel(
            self._tx_list,
            text="Transaction Tables",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 6))

        selector = ctk.CTkFrame(panel, fg_color="white", corner_radius=10)
        selector.grid(row=2, column=0, sticky="ew", padx=22, pady=(12, 10))
        selector.grid_columnconfigure(0, weight=1)
        selector.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            selector,
            text="Dimension Column",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            selector,
            text="Transaction Column",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=12, weight="bold"),
        ).grid(row=0, column=1, sticky="w", padx=12, pady=(10, 4))

        self._dim_column_menu = ctk.CTkOptionMenu(
            selector,
            values=["Select Column"],
            fg_color=theme.get("primary"),
            button_color=theme.get("primary"),
            button_hover_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            height=38,
        )
        self._dim_column_menu.set("Select Column")
        self._dim_column_menu.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 12))

        self._tx_column_menu = ctk.CTkOptionMenu(
            selector,
            values=["Select Column"],
            fg_color=theme.get("primary"),
            button_color=theme.get("primary"),
            button_hover_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            height=38,
        )
        self._tx_column_menu.set("Select Column")
        self._tx_column_menu.grid(row=1, column=1, sticky="ew", padx=12, pady=(0, 12))

        ctk.CTkButton(
            selector,
            text="Confirm Mapping",
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_confirm_mapping,
        ).grid(row=2, column=1, sticky="e", padx=12, pady=(0, 12))

        mappings_card = ctk.CTkFrame(panel, fg_color="white", corner_radius=10)
        mappings_card.grid(row=3, column=0, sticky="nsew", padx=22, pady=(0, 10))
        mappings_card.grid_columnconfigure(0, weight=1)
        mappings_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            mappings_card,
            text="Confirmed Mappings",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._mapping_list = ctk.CTkScrollableFrame(mappings_card, fg_color=theme.get("secondary"), corner_radius=8)
        self._mapping_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        self._error_lbl = ctk.CTkLabel(
            footer,
            text="",
            text_color=theme.get("accent"),
            font=ctk.CTkFont(size=12),
        )
        self._error_lbl.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer,
            text="Finish Setup",
            width=150,
            height=42,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_finish_setup,
        ).grid(row=0, column=1, sticky="e")

    def _go_back(self) -> None:
        from ui.screen1_sources import Screen1Sources

        self.app.show_screen(Screen1Sources, project=self.project)

    def _refresh_tables(self) -> None:
        for table_name in self._dim_tables:
            btn = ctk.CTkButton(
                self._dim_list,
                text=table_name,
                height=34,
                fg_color="transparent",
                border_width=1,
                border_color=theme.get("primary"),
                text_color=theme.get("primary"),
                command=lambda t=table_name: self._select_dim_table(t),
            )
            btn.pack(fill="x", padx=10, pady=4)
            self._dim_buttons[table_name] = btn

        for table_name in self._transaction_tables:
            btn = ctk.CTkButton(
                self._tx_list,
                text=table_name,
                height=34,
                fg_color="transparent",
                border_width=1,
                border_color=theme.get("primary"),
                text_color=theme.get("primary"),
                command=lambda t=table_name: self._select_transaction_table(t),
            )
            btn.pack(fill="x", padx=10, pady=4)
            self._transaction_buttons[table_name] = btn

    def _select_dim_table(self, table_name: str) -> None:
        self._set_error("")
        self._selected_dim_table = table_name
        self._set_button_selection(self._dim_buttons, table_name, is_dim=True)
        self._dim_columns = self._load_dim_columns(table_name)
        self._dim_column_menu.configure(values=self._dim_columns or ["Select Column"])
        self._dim_column_menu.set("Select Column")

    def _select_transaction_table(self, table_name: str) -> None:
        self._set_error("")
        self._selected_transaction_table = table_name
        self._set_button_selection(self._transaction_buttons, table_name, is_dim=False)
        self._transaction_columns = self._load_transaction_columns(table_name)
        self._tx_column_menu.configure(values=self._transaction_columns or ["Select Column"])
        self._tx_column_menu.set("Select Column")

    def _set_button_selection(self, button_map: dict[str, ctk.CTkButton], selected_name: str, is_dim: bool) -> None:
        for name, button in button_map.items():
            if name == selected_name:
                button.configure(fg_color=theme.get("primary"), text_color=theme.get("text_light"))
                if is_dim:
                    self._selected_dim_button = button
                else:
                    self._selected_transaction_button = button
            else:
                button.configure(
                    fg_color="transparent",
                    border_width=1,
                    border_color=theme.get("primary"),
                    text_color=theme.get("primary"),
                )

    def _load_dim_columns(self, table_name: str) -> list[str]:
        path = self.project_path / "data" / "dim" / f"{table_name}.json"
        try:
            df = load_dim_json(path)
            return list(df.columns)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load dim table '{table_name}':\n{exc}")
            return []

    def _load_transaction_columns(self, table_name: str) -> list[str]:
        path = self.project_path / "data" / "transactions" / f"{table_name}.csv"
        try:
            df = load_csv(path)
            return list(df.columns)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load transaction table '{table_name}':\n{exc}")
            return []

    def _on_confirm_mapping(self) -> None:
        dim_column = self._dim_column_menu.get().strip()
        tx_column = self._tx_column_menu.get().strip()
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
            self._set_error("This mapping already exists in the list.")
            return

        self._pending_mappings.append(candidate)
        self._set_error("")
        self._refresh_mappings()

        self._dim_column_menu.set("Select Column")
        self._tx_column_menu.set("Select Column")

    def _refresh_mappings(self) -> None:
        for widget in self._mapping_list.winfo_children():
            widget.destroy()

        if not self._pending_mappings:
            ctk.CTkLabel(
                self._mapping_list,
                text="No mappings added yet.",
                text_color=theme.get("text_dark"),
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        for idx, mapping in enumerate(self._pending_mappings):
            row = ctk.CTkFrame(self._mapping_list, fg_color="white", corner_radius=8)
            row.pack(fill="x", padx=6, pady=5)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=(
                    f"{mapping['transaction_table']}.{mapping['transaction_column']}  <->  "
                    f"{mapping['dim_table']}.{mapping['dim_column']}"
                ),
                text_color=theme.get("text_dark"),
                font=ctk.CTkFont(size=12),
                anchor="w",
            ).grid(row=0, column=0, sticky="w", padx=10, pady=8)

            ctk.CTkButton(
                row,
                text="X",
                width=32,
                height=28,
                fg_color="transparent",
                border_width=1,
                border_color=theme.get("accent"),
                text_color=theme.get("accent"),
                command=lambda i=idx: self._delete_pending_mapping(i),
            ).grid(row=0, column=1, padx=8, pady=6)

    def _delete_pending_mapping(self, index: int) -> None:
        if 0 <= index < len(self._pending_mappings):
            self._pending_mappings.pop(index)
            self._refresh_mappings()

    def _on_finish_setup(self) -> None:
        try:
            existing_mappings = get_mappings(self.project_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not read existing mappings:\n{exc}")
            return

        combined_mappings = [*existing_mappings, *self._pending_mappings]
        missing_tx, missing_dim = find_unmapped_tables(
            transaction_tables=self._transaction_tables,
            dim_tables=self._dim_tables,
            mappings=combined_mappings,
        )
        if missing_tx or missing_dim:
            chunks = []
            if missing_tx:
                chunks.append(f"Unmapped transaction tables: {', '.join(missing_tx)}")
            if missing_dim:
                chunks.append(f"Unmapped dimension tables: {', '.join(missing_dim)}")
            self._set_error(" | ".join(chunks))
            return

        try:
            existing_keys = {mapping_key(m) for m in existing_mappings}
            for mapping in self._pending_mappings:
                if mapping_key(mapping) not in existing_keys:
                    add_mapping(self.project_path, mapping)
                    existing_keys.add(mapping_key(mapping))
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save mappings:\n{exc}")
            return

        self._pending_mappings.clear()
        self._refresh_mappings()
        self._set_error("")
        try:
            from ui.screen3_main import Screen3Main

            self.app.show_screen(Screen3Main, project=self.project)
        except ImportError:
            messagebox.showinfo(
                "Setup Complete",
                "Mappings saved successfully. Screen 3 is not built yet.",
            )

    def _set_error(self, message: str) -> None:
        self._error_lbl.configure(text=message)
