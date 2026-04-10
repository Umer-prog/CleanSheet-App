from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

import ui.theme as theme
from core.snapshot_manager import (
    list_manifests,
    revert_to_manifest,
    update_manifest_label,
)
from ui.popups.popup_revert_confirm import PopupRevertConfirm


def manifest_title(manifest: dict) -> str:
    manifest_id = str(manifest.get("manifest_id", "")).strip()
    created_at = str(manifest.get("created_at", "")).strip()
    return f"{manifest_id} | {created_at}"


def manifest_tables_text(manifest: dict) -> str:
    tables = manifest.get("tables", {})
    if not tables:
        return "(No tables)"
    lines = [f"{name} -> {filename}" for name, filename in tables.items()]
    return "\n".join(lines)


class ViewHistory(ctk.CTkFrame):
    """History list and revert view."""

    def __init__(self, parent, project: dict, on_project_changed):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self._selected_manifest: dict | None = None
        self._selected_row = None
        self._manifests: list[dict] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._load_manifests()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text="History / Revert",
            text_color=theme.get("text_dark"),
            font=theme.font(22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr,
            text="Refresh",
            width=100,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._load_manifests,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            hdr,
            text="How to use: Select a manifest to inspect details, edit label if needed, then revert when you want to restore that version.",
            text_color=theme.get("text_dark"),
            font=theme.font(11),
            justify="left",
            wraplength=760,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 18))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color=theme.card_color(), corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.grid_columnconfigure(0, weight=1)
        left.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            left,
            text="Manifests",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._list = ctk.CTkScrollableFrame(left, fg_color=theme.get("secondary"), corner_radius=8)
        self._list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))

        right = ctk.CTkFrame(body, fg_color=theme.card_color(), corner_radius=10)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            right,
            text="Manifest Details",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._detail_title = ctk.CTkLabel(
            right,
            text="Select a manifest",
            text_color=theme.get("text_dark"),
            font=theme.font(12, weight="bold"),
        )
        self._detail_title.grid(row=1, column=0, sticky="w", padx=12, pady=(0, 6))

        self._detail_box = ctk.CTkTextbox(
            right,
            fg_color=theme.get("secondary"),
            text_color=theme.get("text_dark"),
        )
        self._detail_box.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 8))

        label_row = ctk.CTkFrame(right, fg_color="transparent")
        label_row.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 8))
        label_row.grid_columnconfigure(0, weight=1)

        self._label_entry = ctk.CTkEntry(
            label_row,
            placeholder_text="Label",
            height=36,
            corner_radius=8,
            border_color=theme.get("primary"),
        )
        self._label_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        ctk.CTkButton(
            label_row,
            text="Save Label",
            width=110,
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            command=self._save_label,
        ).grid(row=0, column=1, sticky="e")

        footer = ctk.CTkFrame(right, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=12, pady=(0, 10))
        footer.grid_columnconfigure(0, weight=1)

        self._error_lbl = ctk.CTkLabel(
            footer,
            text="",
            text_color=theme.get("accent"),
            font=theme.font(11),
        )
        self._error_lbl.grid(row=0, column=0, sticky="w")

        self._revert_btn = ctk.CTkButton(
            footer,
            text="Revert To This Version",
            width=180,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            state="disabled",
            command=self._confirm_revert,
        )
        self._revert_btn.grid(row=0, column=1, sticky="e")

    def _load_manifests(self) -> None:
        self._set_error("")
        self._selected_manifest = None
        self._selected_row = None
        self._revert_btn.configure(state="disabled")
        self._label_entry.delete(0, "end")
        self._detail_title.configure(text="Select a manifest")
        self._detail_box.delete("1.0", "end")

        history_enabled = bool(self.project.get("settings", {}).get("history_enabled", True))
        for w in self._list.winfo_children():
            w.destroy()

        if not history_enabled:
            ctk.CTkLabel(
                self._list,
                text="History is OFF in settings.",
                text_color=theme.get("text_dark"),
                font=theme.font(12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        try:
            self._manifests = list_manifests(self.project_path)
        except Exception as exc:
            self._set_error(f"Could not load manifests: {exc}")
            return

        if not self._manifests:
            ctk.CTkLabel(
                self._list,
                text="No manifests available.",
                text_color=theme.get("text_dark"),
                font=theme.font(12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        for manifest in self._manifests:
            row = ctk.CTkFrame(self._list, fg_color=theme.card_color(), corner_radius=8, cursor="hand2")
            row.pack(fill="x", padx=6, pady=5)
            row.grid_columnconfigure(0, weight=1)

            title = manifest_title(manifest)
            label = str(manifest.get("label", "")).strip() or "(no label)"
            lbl = ctk.CTkLabel(
                row,
                text=f"{title}\n{label}",
                justify="left",
                anchor="w",
                text_color=theme.get("text_dark"),
                font=theme.font(12),
            )
            lbl.grid(row=0, column=0, sticky="w", padx=10, pady=8)

            def on_click(_event=None, m=manifest, frame=row, label_widget=lbl):
                self._select_manifest(m, frame, label_widget)

            row.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)

    def _select_manifest(self, manifest: dict, frame: ctk.CTkFrame, label_widget: ctk.CTkLabel) -> None:
        self._selected_manifest = manifest
        self._selected_row = frame
        self._revert_btn.configure(state="normal")
        self._label_entry.delete(0, "end")
        self._label_entry.insert(0, str(manifest.get("label", "")))
        self._detail_title.configure(text=manifest_title(manifest))
        self._detail_box.delete("1.0", "end")
        self._detail_box.insert("1.0", manifest_tables_text(manifest))

        for child in self._list.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                child.configure(fg_color=theme.card_color())
                for gchild in child.winfo_children():
                    if isinstance(gchild, ctk.CTkLabel):
                        gchild.configure(text_color=theme.get("text_dark"))

        frame.configure(fg_color=theme.get("primary"))
        label_widget.configure(text_color=theme.get("text_light"))

    def _save_label(self) -> None:
        if not self._selected_manifest:
            self._set_error("Select a manifest first.")
            return
        new_label = self._label_entry.get().strip()
        try:
            update_manifest_label(
                self.project_path,
                self._selected_manifest["manifest_id"],
                new_label,
            )
        except Exception as exc:
            self._set_error(f"Could not update label: {exc}")
            return

        self.on_project_changed(target_key="history")

    def _confirm_revert(self) -> None:
        if not self._selected_manifest:
            self._set_error("Select a manifest first.")
            return

        manifest_id = self._selected_manifest["manifest_id"]

        def do_revert():
            try:
                revert_to_manifest(self.project_path, manifest_id)
            except Exception as exc:
                messagebox.showerror("Error", f"Could not revert manifest:\n{exc}")
                return
            messagebox.showinfo("Reverted", f"Project reverted to {manifest_id}.")
            self.on_project_changed(target_key="history")

        PopupRevertConfirm(self, manifest_id=manifest_id, on_confirm=do_revert)

    def _set_error(self, msg: str) -> None:
        self._error_lbl.configure(text=msg)


