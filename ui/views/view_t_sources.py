from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import ui.theme as theme
from core.data_loader import get_sheet_as_dataframe, load_excel_sheets, save_as_csv
from core.mapping_manager import delete_mappings_for_table, get_mappings
from core.project_manager import save_project_json
from core.snapshot_manager import create_snapshot
from ui.popups.popup_single_sheet import select_single_sheet
from ui.screen1_sources import normalize_table_name


def count_mappings_for_table(mappings: list[dict], table_name: str) -> int:
    target = table_name.strip()
    return sum(
        1
        for m in mappings
        if m.get("transaction_table", "").strip() == target
        or m.get("dim_table", "").strip() == target
    )


def has_table_name_conflict(project: dict, table_name: str) -> bool:
    tx = set(project.get("transaction_tables", []))
    dim = set(project.get("dim_tables", []))
    return table_name in tx or table_name in dim


class ViewTSources(ctk.CTkFrame):
    """Transaction source management view."""

    def __init__(self, parent, project: dict, on_project_changed, on_go_mapping_setup):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self.on_go_mapping_setup = on_go_mapping_setup

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_list()
        self._render_rows()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Transaction Sources",
            text_color=theme.get("text_dark"),
            font=theme.font(22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr,
            text="Add Transaction Table",
            width=190,
            height=40,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_add_transaction_table,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            hdr,
            text="How to use: Upload new versions for existing tables, delete obsolete ones, or add new transaction tables.",
            text_color=theme.get("text_dark"),
            font=theme.font(11),
            justify="left",
            wraplength=760,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_list(self) -> None:
        card = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 18))
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            card,
            text="Current transaction tables",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._rows = ctk.CTkScrollableFrame(card, fg_color=theme.get("secondary"), corner_radius=8)
        self._rows.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        self._error_lbl = ctk.CTkLabel(
            card,
            text="",
            text_color=theme.get("accent"),
            font=theme.font(11),
        )
        self._error_lbl.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 10))

    def _render_rows(self) -> None:
        for w in self._rows.winfo_children():
            w.destroy()

        tables = list(self.project.get("transaction_tables", []))
        if not tables:
            ctk.CTkLabel(
                self._rows,
                text="No transaction tables found.",
                text_color=theme.get("text_dark"),
                font=theme.font(12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        for table in tables:
            row = ctk.CTkFrame(self._rows, fg_color=theme.card_color(), corner_radius=8)
            row.pack(fill="x", padx=6, pady=5)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=table,
                text_color=theme.get("text_dark"),
                font=theme.font(12, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=10, pady=8)

            ctk.CTkButton(
                row,
                text="Upload New Version",
                width=145,
                height=32,
                fg_color="transparent",
                border_width=1,
                border_color=theme.get("primary"),
                text_color=theme.get("primary"),
                command=lambda t=table: self._on_upload_new_version(t),
            ).grid(row=0, column=1, padx=(0, 8), pady=6)

            ctk.CTkButton(
                row,
                text="Delete",
                width=90,
                height=32,
                fg_color="transparent",
                border_width=1,
                border_color=theme.get("accent"),
                text_color=theme.get("accent"),
                command=lambda t=table: self._on_delete_table(t),
            ).grid(row=0, column=2, padx=(0, 8), pady=6)

    def _on_upload_new_version(self, table_name: str) -> None:
        self._set_error("")
        file_path = filedialog.askopenfilename(
            title=f"Select Excel file for {table_name}",
            filetypes=[("Excel Files", "*.xlsx *.xlsm *.xls")],
        )
        if not file_path:
            return

        excel_path = Path(file_path)
        try:
            sheets = load_excel_sheets(excel_path)
            selected_sheet = select_single_sheet(self, excel_path, sheets, title="Select Sheet For Update")
            if not selected_sheet:
                return
            df = get_sheet_as_dataframe(excel_path, selected_sheet)
            create_snapshot(
                self.project_path,
                {table_name: df},
                label=f"Updated {table_name}",
            )
            messagebox.showinfo("Updated", f"Table '{table_name}' updated successfully.")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not update table:\n{exc}")
            return

        self.on_project_changed(target_key="t_sources")

    def _on_delete_table(self, table_name: str) -> None:
        self._set_error("")
        try:
            mappings = get_mappings(self.project_path)
        except Exception as exc:
            self._set_error(f"Could not read mappings: {exc}")
            return

        count = count_mappings_for_table(mappings, table_name)
        message = (
            f"Deleting '{table_name}' will also remove {count} mapping(s). Confirm?"
        )
        if not messagebox.askyesno("Confirm Delete", message):
            return

        try:
            csv_path = self.project_path / "data" / "transactions" / f"{table_name}.csv"
            if csv_path.exists():
                csv_path.unlink()
            delete_mappings_for_table(self.project_path, table_name)

            project_data = {
                "project_name": self.project.get("project_name", ""),
                "created_at": self.project.get("created_at", ""),
                "company": self.project.get("company", ""),
                "transaction_tables": [
                    t for t in self.project.get("transaction_tables", []) if t != table_name
                ],
                "dim_tables": list(self.project.get("dim_tables", [])),
            }
            save_project_json(self.project_path, project_data)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not delete table:\n{exc}")
            return

        self.on_project_changed(target_key="t_sources")

    def _on_add_transaction_table(self) -> None:
        self._set_error("")
        file_path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel Files", "*.xlsx *.xlsm *.xls")],
        )
        if not file_path:
            return
        excel_path = Path(file_path)
        try:
            sheets = load_excel_sheets(excel_path)
            selected_sheet = select_single_sheet(self, excel_path, sheets, title="Select Transaction Sheet")
            if not selected_sheet:
                return
            table_name = normalize_table_name(selected_sheet)
            if has_table_name_conflict(self.project, table_name):
                self._set_error(f"Table name already exists: {table_name}")
                return

            df = get_sheet_as_dataframe(excel_path, selected_sheet)
            save_as_csv(df, self.project_path / "data" / "transactions" / f"{table_name}.csv")
            create_snapshot(
                self.project_path,
                {table_name: df},
                label=f"Added {table_name}",
            )
            project_data = {
                "project_name": self.project.get("project_name", ""),
                "created_at": self.project.get("created_at", ""),
                "company": self.project.get("company", ""),
                "transaction_tables": [*self.project.get("transaction_tables", []), table_name],
                "dim_tables": list(self.project.get("dim_tables", [])),
            }
            save_project_json(self.project_path, project_data)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not add transaction table:\n{exc}")
            return

        self.on_project_changed(target_key="t_sources")
        if messagebox.askyesno("Mapping Setup", "Go to mapping setup for the new table now?"):
            self.on_go_mapping_setup()

    def _set_error(self, msg: str) -> None:
        self._error_lbl.configure(text=msg)


