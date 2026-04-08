from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd

import ui.theme as theme
from core.data_loader import load_csv, save_as_csv
from core.dim_manager import append_dim_row, get_dim_columns, get_dim_dataframe
from core.error_detector import detect_errors
from ui.popups.popup_add import PopupAdd
from ui.popups.popup_replace import PopupReplace


def format_dataframe_preview(df: pd.DataFrame, max_rows: int = 40) -> str:
    if df.empty:
        return "(No rows)"
    preview = df.head(max_rows).fillna("")
    return preview.to_string(index=True)


def get_valid_dim_values(project_path: Path, dim_table: str, dim_column: str) -> list[str]:
    df = get_dim_dataframe(project_path, dim_table)
    values = sorted({str(v).strip() for v in df[dim_column].tolist() if str(v).strip()})
    return values


def replace_transaction_value(
    project_path: Path,
    mapping: dict,
    row_index: int,
    new_value: str,
) -> None:
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    csv_path = Path(project_path) / "data" / "transactions" / f"{t_table}.csv"

    df = load_csv(csv_path)
    if t_col not in df.columns:
        raise ValueError(f"Column '{t_col}' not found in '{t_table}'.")
    if row_index < 0 or row_index >= len(df):
        raise IndexError(f"Row index {row_index} out of bounds.")

    df.at[row_index, t_col] = str(new_value)
    save_as_csv(df, csv_path)


class ViewMapping(ctk.CTkFrame):
    """Mapping view with transaction preview, error list, replace/add actions."""

    def __init__(self, parent, project: dict, mapping: dict):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.project = project
        self.mapping = mapping
        self.project_path = Path(project["project_path"])

        self._selected_error: dict | None = None
        self._errors: list[dict] = []

        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_transaction_panel()
        self._build_error_panel()
        self._reload_data()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text=(
                f"{self.mapping['transaction_table']}.{self.mapping['transaction_column']}  ->  "
                f"{self.mapping['dim_table']}.{self.mapping['dim_column']}"
            ),
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr,
            text="Refresh",
            width=90,
            height=34,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._reload_data,
        ).grid(row=0, column=1, sticky="e")

    def _build_transaction_panel(self) -> None:
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 8))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Transaction Data (Preview)",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._data_box = ctk.CTkTextbox(card, fg_color=theme.get("secondary"), text_color=theme.get("text_dark"))
        self._data_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 12))

    def _build_error_panel(self) -> None:
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        card.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 18))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Errors",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._error_list = ctk.CTkScrollableFrame(card, fg_color=theme.get("secondary"), corner_radius=8)
        self._error_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        actions.grid_columnconfigure(0, weight=1)

        self._error_lbl = ctk.CTkLabel(
            actions,
            text="",
            text_color=theme.get("accent"),
            font=ctk.CTkFont(size=11),
        )
        self._error_lbl.grid(row=0, column=0, sticky="w")

        self._replace_btn = ctk.CTkButton(
            actions,
            text="Replace",
            width=100,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            state="disabled",
            command=self._on_replace,
        )
        self._replace_btn.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self._add_btn = ctk.CTkButton(
            actions,
            text="Add",
            width=100,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            state="disabled",
            command=self._on_add,
        )
        self._add_btn.grid(row=0, column=2, sticky="e")

    def _reload_data(self) -> None:
        self._set_error("")
        self._selected_error = None
        self._replace_btn.configure(state="disabled")
        self._add_btn.configure(state="disabled")

        try:
            csv_path = (
                self.project_path
                / "data"
                / "transactions"
                / f"{self.mapping['transaction_table']}.csv"
            )
            tx_df = load_csv(csv_path)
            self._data_box.delete("1.0", "end")
            self._data_box.insert("1.0", format_dataframe_preview(tx_df))
        except Exception as exc:
            self._data_box.delete("1.0", "end")
            self._data_box.insert("1.0", f"Could not load transaction data:\n{exc}")

        try:
            self._errors = detect_errors(self.project_path, self.mapping)
        except Exception as exc:
            self._errors = []
            self._set_error(f"Error detection failed: {exc}")
        self._render_errors()

    def _render_errors(self) -> None:
        for child in self._error_list.winfo_children():
            child.destroy()

        if not self._errors:
            ctk.CTkLabel(
                self._error_list,
                text="No errors found for this mapping.",
                text_color=theme.get("text_dark"),
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        for error in self._errors:
            row = ctk.CTkFrame(self._error_list, fg_color="white", corner_radius=8, cursor="hand2")
            row.pack(fill="x", padx=6, pady=5)
            row.grid_columnconfigure(0, weight=1)

            text = (
                f"Row {error['row_index'] + 2} | "
                f"Column: {error['transaction_column']} | "
                f"Bad value: {error['bad_value']}"
            )
            lbl = ctk.CTkLabel(
                row,
                text=text,
                text_color=theme.get("text_dark"),
                anchor="w",
                font=ctk.CTkFont(size=12),
            )
            lbl.grid(row=0, column=0, sticky="w", padx=10, pady=8)

            def on_click(_event=None, err=error, frame=row, label=lbl):
                self._select_error(err, frame, label)

            row.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)

    def _select_error(self, error: dict, frame: ctk.CTkFrame, label: ctk.CTkLabel) -> None:
        self._selected_error = error
        for child in self._error_list.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                child.configure(fg_color="white")
                for gchild in child.winfo_children():
                    if isinstance(gchild, ctk.CTkLabel):
                        gchild.configure(text_color=theme.get("text_dark"))

        frame.configure(fg_color=theme.get("primary"))
        label.configure(text_color=theme.get("text_light"))
        self._replace_btn.configure(state="normal")
        self._add_btn.configure(state="normal")

    def _on_replace(self) -> None:
        if not self._selected_error:
            self._set_error("Select an error first.")
            return

        try:
            values = get_valid_dim_values(
                self.project_path,
                self.mapping["dim_table"],
                self.mapping["dim_column"],
            )
        except Exception as exc:
            self._set_error(f"Could not load dim values: {exc}")
            return

        def on_confirm(new_value: str) -> None:
            try:
                replace_transaction_value(
                    self.project_path,
                    self.mapping,
                    row_index=int(self._selected_error["row_index"]),
                    new_value=new_value,
                )
                self._reload_data()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not replace value:\n{exc}")

        PopupReplace(
            self,
            bad_value=str(self._selected_error.get("bad_value", "")),
            valid_values=values,
            on_confirm=on_confirm,
        )

    def _on_add(self) -> None:
        if not self._selected_error:
            self._set_error("Select an error first.")
            return

        try:
            dim_columns = get_dim_columns(self.project_path, self.mapping["dim_table"])
        except Exception as exc:
            self._set_error(f"Could not load dim columns: {exc}")
            return

        def on_confirm(row: dict) -> None:
            try:
                append_dim_row(self.project_path, self.mapping["dim_table"], row)
                self._reload_data()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not append dim row:\n{exc}")

        PopupAdd(
            self,
            dim_table=self.mapping["dim_table"],
            dim_columns=dim_columns,
            mapped_column=self.mapping["dim_column"],
            bad_value=str(self._selected_error.get("bad_value", "")),
            on_confirm=on_confirm,
        )

    def _set_error(self, message: str) -> None:
        self._error_lbl.configure(text=message)

