from __future__ import annotations

import re
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import ui.theme as theme
from core.data_loader import (
    get_sheet_as_dataframe,
    load_excel_sheets,
    save_as_csv,
    save_as_json,
)
from core.project_manager import open_project, save_project_json
from ui.popups.popup_sheet_selector import select_sheets


def normalize_table_name(sheet_name: str) -> str:
    """Convert a sheet name into a safe table name."""
    normalized = re.sub(r"[^a-z0-9]+", "_", sheet_name.strip().lower()).strip("_")
    if not normalized:
        normalized = "table"
    if normalized[0].isdigit():
        normalized = f"table_{normalized}"
    return normalized


def find_duplicate_table_names(
    selected_rows: list[dict], existing_table_names: set[str]
) -> set[str]:
    """Return normalized names that would collide with existing or selected rows."""
    seen = set(existing_table_names)
    duplicates = set()
    for row in selected_rows:
        name = normalize_table_name(row.get("sheet_name", ""))
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return duplicates


def validate_confirm_requirements(source_rows: list[dict]) -> str | None:
    """Return an error message if Screen 1 confirm requirements are not met."""
    if not source_rows:
        return "Add at least one file before continuing."

    tx_count = 0
    dim_count = 0
    for source in source_rows:
        for sheet in source.get("sheets", []):
            category = str(sheet.get("category", "")).strip()
            if category == "Transaction":
                tx_count += 1
            elif category == "Dimension":
                dim_count += 1
            else:
                return "Every selected sheet must have a category."

    if tx_count == 0:
        return "At least one transaction sheet is required."
    if dim_count == 0:
        return "At least one dimension sheet is required."
    return None


class Screen1Sources(ctk.CTkFrame):
    """Stage 1 screen for adding Excel files and categorizing their sheets."""

    def __init__(self, parent, app, project: dict):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.app = app
        self.project = project
        self.project_path = Path(project["project_path"])
        self._sources: list[dict] = []

        self.grid_columnconfigure(0, weight=0, minsize=300)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()
        self._render_sources()

    def _build_left_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=theme.get("sidebar_bg"), corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            panel,
            text="Data Loader",
            text_color=theme.get("text_light"),
            font=theme.font(20, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(26, 10))

        ctk.CTkLabel(
            panel,
            text="Add Excel files and mark each selected sheet\nas Transaction or Dimension.",
            text_color=theme.get("text_light"),
            justify="left",
            font=theme.font(12),
        ).pack(anchor="w", padx=20, pady=(0, 16))

        ctk.CTkButton(
            panel,
            text="Back To Projects",
            width=180,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("text_light"),
            text_color=theme.get("text_light"),
            command=self._go_back,
        ).pack(anchor="w", padx=20, pady=(0, 0))

    def _build_right_panel(self) -> None:
        panel = ctk.CTkFrame(self, fg_color=theme.get("secondary"), corner_radius=0)
        panel.grid(row=0, column=1, sticky="nsew")
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(panel, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=22, pady=(20, 8))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Data Loader",
            text_color=theme.get("text_dark"),
            font=theme.font(22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header,
            text="Add File",
            width=120,
            height=40,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_add_file,
        ).grid(row=0, column=1, sticky="e")

        tip = ctk.CTkFrame(panel, fg_color=theme.card_color(), corner_radius=10)
        tip.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 6))
        ctk.CTkLabel(
            tip,
            text="How to use: Add files, pick sheets, and assign Transaction or Dimension. Confirm when both categories are present.",
            text_color=theme.get("text_dark"),
            font=theme.font(11),
            justify="left",
            wraplength=760,
        ).pack(anchor="w", padx=12, pady=8)

        self._list_frame = ctk.CTkScrollableFrame(panel, fg_color=theme.card_color(), corner_radius=10)
        self._list_frame.grid(row=2, column=0, sticky="nsew", padx=22, pady=(4, 8))

        footer = ctk.CTkFrame(panel, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=22, pady=(6, 20))
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
            text="Confirm & Continue",
            width=180,
            height=42,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_confirm_continue,
        ).grid(row=0, column=1, sticky="e")

    def _go_back(self) -> None:
        from ui.screen0_launcher import Screen0Launcher

        self.app.show_screen(Screen0Launcher)

    def _on_add_file(self) -> None:
        self._set_error("")
        selected_file = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel Files", "*.xlsx *.xlsm *.xls")],
        )
        if not selected_file:
            return

        excel_path = Path(selected_file)
        try:
            sheet_names = load_excel_sheets(excel_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not read Excel file:\n{exc}")
            return

        picked_rows = select_sheets(self, excel_path=excel_path, sheet_names=sheet_names)
        if not picked_rows:
            return

        existing = self._all_known_table_names()
        duplicates = find_duplicate_table_names(picked_rows, existing_table_names=existing)
        if duplicates:
            names = ", ".join(sorted(duplicates))
            self._set_error(f"Duplicate table name(s): {names}")
            return

        self._sources.append(
            {
                "file_path": str(excel_path),
                "sheets": picked_rows,
            }
        )
        self._render_sources()

    def _all_known_table_names(self) -> set[str]:
        names = set(self.project.get("transaction_tables", []))
        names.update(self.project.get("dim_tables", []))
        for source in self._sources:
            for sheet in source.get("sheets", []):
                names.add(normalize_table_name(sheet["sheet_name"]))
        return names

    def _on_remove_file(self, file_index: int) -> None:
        self._set_error("")
        if 0 <= file_index < len(self._sources):
            self._sources.pop(file_index)
            self._render_sources()

    def _on_remove_sheet(self, file_index: int, sheet_index: int) -> None:
        self._set_error("")
        if not (0 <= file_index < len(self._sources)):
            return
        sheets = self._sources[file_index]["sheets"]
        if 0 <= sheet_index < len(sheets):
            sheets.pop(sheet_index)
        if not sheets:
            self._sources.pop(file_index)
        self._render_sources()

    def _render_sources(self) -> None:
        for widget in self._list_frame.winfo_children():
            widget.destroy()

        if not self._sources:
            ctk.CTkLabel(
                self._list_frame,
                text="No files added yet. Click Add File to begin.",
                text_color=theme.get("text_dark"),
                font=theme.font(12),
            ).pack(anchor="w", padx=16, pady=14)
            return

        for file_index, source in enumerate(self._sources):
            card = ctk.CTkFrame(self._list_frame, fg_color=theme.get("secondary"), corner_radius=10)
            card.pack(fill="x", padx=10, pady=8)

            top = ctk.CTkFrame(card, fg_color="transparent")
            top.pack(fill="x", padx=12, pady=(10, 6))
            top.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                top,
                text=Path(source["file_path"]).name,
                text_color=theme.get("text_dark"),
                font=theme.font(13, weight="bold"),
                anchor="w",
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkButton(
                top,
                text="Remove File",
                width=98,
                height=30,
                fg_color="transparent",
                border_width=1,
                border_color=theme.get("accent"),
                text_color=theme.get("accent"),
                command=lambda i=file_index: self._on_remove_file(i),
            ).grid(row=0, column=1, sticky="e")

            for sheet_index, sheet in enumerate(source.get("sheets", [])):
                row = ctk.CTkFrame(card, fg_color="transparent")
                row.pack(fill="x", padx=12, pady=(0, 8))
                row.grid_columnconfigure(0, weight=1)

                table_name = normalize_table_name(sheet["sheet_name"])
                ctk.CTkLabel(
                    row,
                    text=f"{sheet['sheet_name']}  ->  {sheet['category']}  ({table_name})",
                    text_color=theme.get("text_dark"),
                    font=theme.font(12),
                    anchor="w",
                ).grid(row=0, column=0, sticky="w")

                ctk.CTkButton(
                    row,
                    text="Remove",
                    width=74,
                    height=28,
                    fg_color="transparent",
                    border_width=1,
                    border_color=theme.get("primary"),
                    text_color=theme.get("primary"),
                    command=lambda fi=file_index, si=sheet_index: self._on_remove_sheet(fi, si),
                ).grid(row=0, column=1, sticky="e")

    def _on_confirm_continue(self) -> None:
        error = validate_confirm_requirements(self._sources)
        if error:
            self._set_error(error)
            return
        try:
            self._persist_sources()
            updated_state = open_project(self.project_path)
            self.app.set_current_project(updated_state)
            self.project = updated_state
            self._sources.clear()
            self._render_sources()
            self._set_error("")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save selected sheets:\n{exc}")
            return

        try:
            from ui.screen2_mappings import Screen2Mappings

            self.app.show_screen(Screen2Mappings, project=updated_state)
        except ImportError:
            messagebox.showinfo(
                "Screen 2",
                "Data sources saved successfully. Screen 2 is not built yet.",
            )

    def _persist_sources(self) -> None:
        project_data = {
            "project_name": self.project.get("project_name", ""),
            "created_at": self.project.get("created_at", ""),
            "company": self.project.get("company", ""),
            "transaction_tables": list(self.project.get("transaction_tables", [])),
            "dim_tables": list(self.project.get("dim_tables", [])),
        }

        tx_names = list(project_data["transaction_tables"])
        dim_names = list(project_data["dim_tables"])

        for source in self._sources:
            file_path = Path(source["file_path"])
            for sheet in source.get("sheets", []):
                table_name = normalize_table_name(sheet["sheet_name"])
                df = get_sheet_as_dataframe(file_path, sheet["sheet_name"])
                if sheet["category"] == "Transaction":
                    save_as_csv(df, self.project_path / "data" / "transactions" / f"{table_name}.csv")
                    if table_name not in tx_names:
                        tx_names.append(table_name)
                elif sheet["category"] == "Dimension":
                    save_as_json(df, self.project_path / "data" / "dim" / f"{table_name}.json")
                    if table_name not in dim_names:
                        dim_names.append(table_name)

        project_data["transaction_tables"] = tx_names
        project_data["dim_tables"] = dim_names
        save_project_json(self.project_path, project_data)

    def _set_error(self, message: str) -> None:
        self._error_lbl.configure(text=message)

