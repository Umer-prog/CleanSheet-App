from __future__ import annotations

import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd

import ui.theme as theme
from core.data_loader import load_dim_json
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
        self._loading_count = 0
        self._loading_anim_job = None
        self._loading_anim_value = 0.0
        self._loading_anim_direction = 1

        self.grid_columnconfigure(0, weight=0, minsize=320)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()
        self._build_loading_overlay()
        self._refresh_tables()
        self._refresh_mappings()

    def _build_left_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=theme.get("sidebar_bg"), corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="Mapper",
            text_color=theme.get("text_light"),
            font=theme.font(20, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(26, 10))

        ctk.CTkLabel(
            panel,
            text="Map transaction tables\nwith dimension tables\nusing selected columns.",
            text_color=theme.get("text_light"),
            justify="left",
            font=theme.font(12),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkButton(
            panel,
            text="Back To Data Loader",
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
        panel.grid_rowconfigure(4, weight=1)

        ctk.CTkLabel(
            panel,
            text="Mapper",
            text_color=theme.get("text_dark"),
            font=theme.font(22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(18, 10))

        tip = ctk.CTkFrame(panel, fg_color=theme.card_color(), corner_radius=10)
        tip.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 8))
        ctk.CTkLabel(
            tip,
            text="How to use: Select one table on each side, pick columns, then confirm. Repeat until every table is mapped.",
            text_color=theme.get("text_dark"),
            font=theme.font(11),
            justify="left",
            wraplength=700,
        ).pack(anchor="w", padx=12, pady=8)

        top_grid = ctk.CTkFrame(panel, fg_color="transparent")
        top_grid.grid(row=2, column=0, sticky="ew", padx=22)
        top_grid.grid_columnconfigure(0, weight=1)
        top_grid.grid_columnconfigure(1, weight=1)

        self._dim_list = ctk.CTkScrollableFrame(top_grid, fg_color=theme.card_color(), corner_radius=10, height=150)
        self._dim_list.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        self._tx_list = ctk.CTkScrollableFrame(top_grid, fg_color=theme.card_color(), corner_radius=10, height=150)
        self._tx_list.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        ctk.CTkLabel(
            self._dim_list,
            text="Dimension Tables",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 6))
        ctk.CTkLabel(
            self._tx_list,
            text="Transaction Tables",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(8, 6))

        selector = ctk.CTkFrame(panel, fg_color=theme.card_color(), corner_radius=10)
        selector.grid(row=3, column=0, sticky="ew", padx=22, pady=(8, 8))
        selector.grid_columnconfigure(0, weight=1)
        selector.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            selector,
            text="Dimension Column",
            text_color=theme.get("text_dark"),
            font=theme.font(12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        ctk.CTkLabel(
            selector,
            text="Transaction Column",
            text_color=theme.get("text_dark"),
            font=theme.font(12, weight="bold"),
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

        mappings_card = ctk.CTkFrame(panel, fg_color=theme.card_color(), corner_radius=10)
        mappings_card.grid(row=4, column=0, sticky="nsew", padx=22, pady=(0, 10))
        mappings_card.grid_columnconfigure(0, weight=1)
        mappings_card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            mappings_card,
            text="Confirmed Mappings",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._mapping_list = ctk.CTkScrollableFrame(mappings_card, fg_color=theme.get("secondary"), corner_radius=8)
        self._mapping_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.grid(row=5, column=0, sticky="ew", padx=22, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        self._error_lbl = ctk.CTkLabel(
            footer,
            text="",
            text_color=theme.get("accent"),
            font=theme.font(12),
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
        self._dim_column_menu.configure(values=["Loading..."])
        self._dim_column_menu.set("Loading...")

        def worker():
            return self._load_dim_columns(table_name)

        def on_success(columns):
            if self._selected_dim_table != table_name:
                return
            self._dim_columns = columns
            self._dim_column_menu.configure(values=self._dim_columns or ["Select Column"])
            self._dim_column_menu.set("Select Column")

        def on_error(exc):
            if self._selected_dim_table != table_name:
                return
            self._dim_columns = []
            self._dim_column_menu.configure(values=["Select Column"])
            self._dim_column_menu.set("Select Column")
            messagebox.showerror("Error", f"Could not load dim table '{table_name}':\n{exc}")

        self._run_background(worker, on_success, on_error)

    def _select_transaction_table(self, table_name: str) -> None:
        self._set_error("")
        self._selected_transaction_table = table_name
        self._set_button_selection(self._transaction_buttons, table_name, is_dim=False)
        self._tx_column_menu.configure(values=["Loading..."])
        self._tx_column_menu.set("Loading...")

        def worker():
            return self._load_transaction_columns(table_name)

        def on_success(columns):
            if self._selected_transaction_table != table_name:
                return
            self._transaction_columns = columns
            self._tx_column_menu.configure(values=self._transaction_columns or ["Select Column"])
            self._tx_column_menu.set("Select Column")

        def on_error(exc):
            if self._selected_transaction_table != table_name:
                return
            self._transaction_columns = []
            self._tx_column_menu.configure(values=["Select Column"])
            self._tx_column_menu.set("Select Column")
            messagebox.showerror("Error", f"Could not load transaction table '{table_name}':\n{exc}")

        self._run_background(worker, on_success, on_error)

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
        df = load_dim_json(path)
        return list(df.columns)

    def _load_transaction_columns(self, table_name: str) -> list[str]:
        path = self.project_path / "data" / "transactions" / f"{table_name}.csv"
        cols = pd.read_csv(path, dtype=str, encoding="utf-8", nrows=0).columns
        return [str(c) for c in cols]

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
        self._clear_current_selection()

    def _clear_current_selection(self) -> None:
        self._selected_dim_table = None
        self._selected_transaction_table = None
        self._selected_dim_button = None
        self._selected_transaction_button = None
        self._set_button_selection(self._dim_buttons, "__none__", is_dim=True)
        self._set_button_selection(self._transaction_buttons, "__none__", is_dim=False)
        self._dim_columns = []
        self._transaction_columns = []
        self._dim_column_menu.configure(values=["Select Column"])
        self._tx_column_menu.configure(values=["Select Column"])
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
                font=theme.font(12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        for idx, mapping in enumerate(self._pending_mappings):
            row = ctk.CTkFrame(self._mapping_list, fg_color=theme.card_color(), corner_radius=8)
            row.pack(fill="x", padx=6, pady=5)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=(
                    f"{mapping['transaction_table']}.{mapping['transaction_column']}  <->  "
                    f"{mapping['dim_table']}.{mapping['dim_column']}"
                ),
                text_color=theme.get("text_dark"),
                font=theme.font(12),
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
        def load_existing_worker():
            return get_mappings(self.project_path)

        def on_existing_loaded(existing_mappings):
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

            def save_worker():
                existing_keys = {mapping_key(m) for m in existing_mappings}
                for mapping in self._pending_mappings:
                    if mapping_key(mapping) not in existing_keys:
                        add_mapping(self.project_path, mapping)
                        existing_keys.add(mapping_key(mapping))

            def on_save_success(_result):
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

            def on_save_error(exc):
                messagebox.showerror("Error", f"Could not save mappings:\n{exc}")

            self._run_background(save_worker, on_save_success, on_save_error)

        def on_existing_error(exc):
            messagebox.showerror("Error", f"Could not read existing mappings:\n{exc}")

        self._run_background(load_existing_worker, on_existing_loaded, on_existing_error)

    def _set_error(self, message: str) -> None:
        self._error_lbl.configure(text=message)

    def _build_loading_overlay(self) -> None:
        self._loading_overlay = ctk.CTkFrame(
            self,
            fg_color=theme.get("secondary"),
            corner_radius=0,
        )

        overlay_card = ctk.CTkFrame(self._loading_overlay, fg_color=theme.card_color(), corner_radius=12)
        overlay_card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            overlay_card,
            text="Loading...",
            text_color=theme.get("text_dark"),
            font=theme.font(14, weight="bold"),
        ).pack(padx=20, pady=(14, 8))

        self._loading_bar = ctk.CTkProgressBar(overlay_card, mode="determinate", width=260)
        self._loading_bar.set(0.0)
        self._loading_bar.pack(padx=20, pady=(0, 14))

    def _run_background(self, worker, on_success=None, on_error=None) -> None:
        self._show_loading()

        def _finish_success(result):
            self._hide_loading()
            if on_success:
                on_success(result)

        def _finish_error(exc):
            self._hide_loading()
            if on_error:
                on_error(exc)
            else:
                self._set_error(str(exc))

        def _task():
            try:
                result = worker()
            except Exception as exc:
                try:
                    self.after(0, lambda err=exc: _finish_error(err))
                except Exception:
                    pass
                return
            try:
                self.after(0, lambda value=result: _finish_success(value))
            except Exception:
                pass

        threading.Thread(target=_task, daemon=True).start()

    def _show_loading(self) -> None:
        self._loading_count += 1
        if self._loading_count != 1:
            return
        self._loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self._loading_overlay.lift()
        self._start_loading_animation()

    def _hide_loading(self) -> None:
        self._loading_count = max(0, self._loading_count - 1)
        if self._loading_count != 0:
            return
        self._stop_loading_animation()
        self._loading_overlay.place_forget()

    def _start_loading_animation(self) -> None:
        if self._loading_anim_job is not None:
            return
        self._loading_anim_value = 0.0
        self._loading_anim_direction = 1
        self._loading_bar.set(self._loading_anim_value)
        self._loading_anim_job = self.after(16, self._animate_loading_bar)

    def _stop_loading_animation(self) -> None:
        if self._loading_anim_job is not None:
            self.after_cancel(self._loading_anim_job)
            self._loading_anim_job = None
        self._loading_anim_value = 0.0
        self._loading_anim_direction = 1
        self._loading_bar.set(0.0)

    def _animate_loading_bar(self) -> None:
        step = 0.015
        self._loading_anim_value += step * self._loading_anim_direction
        if self._loading_anim_value >= 1.0:
            self._loading_anim_value = 1.0
            self._loading_anim_direction = -1
        elif self._loading_anim_value <= 0.0:
            self._loading_anim_value = 0.0
            self._loading_anim_direction = 1
        self._loading_bar.set(self._loading_anim_value)
        self._loading_anim_job = self.after(16, self._animate_loading_bar)

