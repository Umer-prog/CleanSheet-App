from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

import ui.theme as theme
from core.data_loader import get_sheet_as_dataframe, load_excel_sheets, save_as_json
from core.project_manager import save_project_json
from ui.popups.popup_single_sheet import select_single_sheet
from ui.screen1_sources import normalize_table_name


def has_dim_name_conflict(project: dict, dim_name: str) -> bool:
    return (
        dim_name in set(project.get("dim_tables", []))
        or dim_name in set(project.get("transaction_tables", []))
    )


class ViewDSources(ctk.CTkFrame):
    """Dimension source management view."""

    def __init__(self, parent, project: dict, on_project_changed, on_go_mapping_setup):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self.on_go_mapping_setup = on_go_mapping_setup
        self._loading_count = 0
        self._loading_anim_job = None
        self._loading_anim_value = 0.0
        self._loading_anim_direction = 1

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_list()
        self._build_loading_overlay()
        self._render_rows()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="Dimension Sources",
            text_color=theme.get("text_dark"),
            font=theme.font(22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr,
            text="Add Dimension Table",
            width=180,
            height=40,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_add_dim_table,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            hdr,
            text="How to use: Add new dimension tables here. Existing dimension tables are locked and cannot be replaced or deleted.",
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
            text="Current dimension tables",
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

        dims = list(self.project.get("dim_tables", []))
        if not dims:
            ctk.CTkLabel(
                self._rows,
                text="No dimension tables found.",
                text_color=theme.get("text_dark"),
                font=theme.font(12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        for dim in dims:
            row = ctk.CTkFrame(self._rows, fg_color=theme.card_color(), corner_radius=8)
            row.pack(fill="x", padx=6, pady=5)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row,
                text=dim,
                text_color=theme.get("text_dark"),
                font=theme.font(12, weight="bold"),
            ).grid(row=0, column=0, sticky="w", padx=10, pady=8)

            ctk.CTkButton(
                row,
                text="Locked",
                width=90,
                height=32,
                fg_color="transparent",
                border_width=1,
                border_color=theme.get("primary"),
                text_color=theme.get("primary"),
                state="disabled",
            ).grid(row=0, column=1, padx=(0, 8), pady=6)

            ctk.CTkLabel(
                row,
                text="Cannot delete or replace",
                text_color=theme.get("text_dark"),
                font=theme.font(11),
            ).grid(row=0, column=2, padx=(0, 10), pady=6)

    def _on_add_dim_table(self) -> None:
        self._set_error("")
        file_path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel Files", "*.xlsx *.xlsm *.xls")],
        )
        if not file_path:
            return
        excel_path = Path(file_path)
        def load_sheets_worker():
            return load_excel_sheets(excel_path)

        def on_sheets_loaded(sheets):
            selected_sheet = select_single_sheet(self, excel_path, sheets, title="Select Dimension Sheet")
            if not selected_sheet:
                return
            dim_name = normalize_table_name(selected_sheet)
            if has_dim_name_conflict(self.project, dim_name):
                self._set_error(f"Dimension table already exists: {dim_name}")
                return

            def add_worker():
                df = get_sheet_as_dataframe(excel_path, selected_sheet)
                save_as_json(df, self.project_path / "data" / "dim" / f"{dim_name}.json")

                project_data = {
                    "project_name": self.project.get("project_name", ""),
                    "created_at": self.project.get("created_at", ""),
                    "company": self.project.get("company", ""),
                    "transaction_tables": list(self.project.get("transaction_tables", [])),
                    "dim_tables": [*self.project.get("dim_tables", []), dim_name],
                }
                save_project_json(self.project_path, project_data)

            def on_add_done(_result):
                go_setup = messagebox.askyesno("Mapping Setup", "Go to mapping setup for the new table now?")
                self.on_project_changed(target_key="d_sources")
                if go_setup:
                    self.on_go_mapping_setup()

            def on_add_error(exc):
                messagebox.showerror("Error", f"Could not add dimension table:\n{exc}")

            self._run_background(add_worker, on_add_done, on_add_error)

        def on_sheets_error(exc):
            messagebox.showerror("Error", f"Could not add dimension table:\n{exc}")

        self._run_background(load_sheets_worker, on_sheets_loaded, on_sheets_error)

    def _set_error(self, msg: str) -> None:
        self._error_lbl.configure(text=msg)

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
            text="Working...",
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


