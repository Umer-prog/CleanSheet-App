from __future__ import annotations

import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

import ui.theme as theme
from core.project_manager import save_project_json, save_settings_json


def merged_project_payload(project: dict, project_name: str, company: str) -> dict:
    return {
        "project_name": project_name,
        "created_at": project.get("created_at", ""),
        "company": company,
        "transaction_tables": list(project.get("transaction_tables", [])),
        "dim_tables": list(project.get("dim_tables", [])),
    }


def merged_settings_payload(project: dict, history_enabled: bool) -> dict:
    base_settings = dict(project.get("settings", {}))
    base_settings["history_enabled"] = bool(history_enabled)
    base_settings["project_path"] = str(project.get("project_path", ""))
    return base_settings


class ViewSettings(ctk.CTkFrame):
    """Project settings view."""

    def __init__(self, parent, project: dict, on_project_changed):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self._loading_count = 0
        self._loading_anim_job = None
        self._loading_anim_value = 0.0
        self._loading_anim_direction = 1

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_form()
        self._build_loading_overlay()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))

        ctk.CTkLabel(
            hdr,
            text="Settings",
            text_color=theme.get("text_dark"),
            font=theme.font(22, weight="bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            hdr,
            text="How to use: Update project details and history preference, then click Save to apply changes.",
            text_color=theme.get("text_dark"),
            font=theme.font(11),
            justify="left",
            wraplength=760,
        ).pack(anchor="w", pady=(6, 0))

    def _build_form(self) -> None:
        card = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 18))
        card.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Project Name",
            text_color=theme.get("text_dark"),
            font=theme.font(12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(14, 4))
        self._name_entry = ctk.CTkEntry(
            card,
            height=38,
            corner_radius=8,
            border_color=theme.get("primary"),
        )
        self._name_entry.insert(0, str(self.project.get("project_name", "")))
        self._name_entry.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))

        ctk.CTkLabel(
            card,
            text="Company Name",
            text_color=theme.get("text_dark"),
            font=theme.font(12, weight="bold"),
        ).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 4))
        self._company_entry = ctk.CTkEntry(
            card,
            height=38,
            corner_radius=8,
            border_color=theme.get("primary"),
        )
        self._company_entry.insert(0, str(self.project.get("company", "")))
        self._company_entry.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 10))

        ctk.CTkLabel(
            card,
            text="Project Folder Path (read-only)",
            text_color=theme.get("text_dark"),
            font=theme.font(12, weight="bold"),
        ).grid(row=4, column=0, sticky="w", padx=18, pady=(0, 4))
        self._path_entry = ctk.CTkEntry(
            card,
            height=38,
            corner_radius=8,
            border_color=theme.get("primary"),
            state="normal",
        )
        self._path_entry.insert(0, str(self.project.get("project_path", "")))
        self._path_entry.configure(state="disabled")
        self._path_entry.grid(row=5, column=0, sticky="ew", padx=18, pady=(0, 12))

        history_enabled = bool(self.project.get("settings", {}).get("history_enabled", True))
        self._history_switch = ctk.CTkSwitch(
            card,
            text="History Enabled",
            text_color=theme.get("text_dark"),
            progress_color=theme.get("primary"),
            button_color=theme.get("primary"),
            button_hover_color=theme.get("primary"),
        )
        if history_enabled:
            self._history_switch.select()
        else:
            self._history_switch.deselect()
        self._history_switch.grid(row=6, column=0, sticky="w", padx=18, pady=(0, 8))

        footer = ctk.CTkFrame(card, fg_color="transparent")
        footer.grid(row=7, column=0, sticky="ew", padx=18, pady=(0, 14))
        footer.grid_columnconfigure(0, weight=1)

        self._error_lbl = ctk.CTkLabel(
            footer,
            text="",
            text_color=theme.get("accent"),
            font=theme.font(11),
        )
        self._error_lbl.grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            footer,
            text="Save",
            width=120,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_save,
        ).grid(row=0, column=1, sticky="e")

    def _on_save(self) -> None:
        self._set_error("")
        project_name = self._name_entry.get().strip()
        company = self._company_entry.get().strip()
        history_enabled = bool(self._history_switch.get())

        if not project_name:
            self._set_error("Project name is required.")
            return
        if not company:
            self._set_error("Company name is required.")
            return

        previous_history = bool(self.project.get("settings", {}).get("history_enabled", True))
        if previous_history and not history_enabled:
            accepted = messagebox.askyesno(
                "History Off Warning",
                "Existing history will be kept but no new snapshots will be created. Continue?",
            )
            if not accepted:
                self._history_switch.select()
                return

        def worker():
            save_project_json(
                self.project_path,
                merged_project_payload(self.project, project_name, company),
            )
            save_settings_json(
                self.project_path,
                merged_settings_payload(self.project, history_enabled),
            )

        def on_success(_result):
            messagebox.showinfo("Saved", "Settings saved successfully.")
            self.on_project_changed(target_key="settings")

        def on_error(exc):
            messagebox.showerror("Error", f"Could not save settings:\n{exc}")

        self._run_background(worker, on_success, on_error)

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
            text="Saving settings...",
            text_color=theme.get("text_dark"),
            font=theme.font(14, weight="bold"),
        ).pack(padx=20, pady=(14, 8))

        self._loading_bar = ctk.CTkProgressBar(overlay_card, mode="determinate", width=240)
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


