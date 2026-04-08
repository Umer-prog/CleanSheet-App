from __future__ import annotations

from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

import ui.theme as theme
from core.mapping_manager import get_mappings
from core.project_manager import open_project
from ui.screen2_mappings import Screen2Mappings
from ui.views.view_d_sources import ViewDSources
from ui.views.view_history import ViewHistory
from ui.views.view_settings import ViewSettings
from ui.views.view_t_sources import ViewTSources
from ui.views.view_mapping import ViewMapping

_NAV_WIDTH = 340


def mapping_nav_label(mapping: dict) -> str:
    tx = str(mapping.get("transaction_table", "")).strip() or "unknown_tx"
    dim = str(mapping.get("dim_table", "")).strip() or "unknown_dim"
    return f"{tx} -> {dim}"


def build_nav_items(mappings: list[dict]) -> list[dict]:
    items: list[dict] = []
    for mapping in mappings:
        items.append(
            {
                "kind": "mapping",
                "key": str(mapping.get("id", "")).strip() or mapping_nav_label(mapping),
                "label": mapping_nav_label(mapping),
                "mapping": mapping,
            }
        )

    items.extend(
        [
            {"kind": "separator", "key": "sep_sources"},
            {"kind": "view", "key": "t_sources", "label": "T Sources"},
            {"kind": "view", "key": "d_sources", "label": "D Sources"},
            {"kind": "separator", "key": "sep_misc"},
            {"kind": "view", "key": "history", "label": "History / Revert"},
            {"kind": "view", "key": "settings", "label": "Settings"},
        ]
    )
    return items


class _PlaceholderView(ctk.CTkFrame):
    def __init__(self, parent, title: str, subtitle: str):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        card = ctk.CTkFrame(self, fg_color="white", corner_radius=12)
        card.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(
            card,
            text=title,
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(anchor="w", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            card,
            text=subtitle,
            text_color=theme.get("text_dark"),
            justify="left",
            font=ctk.CTkFont(size=13),
        ).pack(anchor="w", padx=24, pady=(0, 24))


class Screen3Main(ctk.CTkFrame):
    """Main workspace shell with left navbar and right content area."""

    def __init__(self, parent, app, project: dict, initial_nav_key: str | None = None):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.app = app
        self.project = project
        self.project_path = Path(project["project_path"])
        self.initial_nav_key = initial_nav_key

        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._active_nav_key: str | None = None
        self._active_view = None

        self._mappings = self._load_mappings()
        self._nav_items = build_nav_items(self._mappings)

        self.grid_columnconfigure(0, weight=0, minsize=_NAV_WIDTH)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_navbar()
        self._build_content()
        self._select_default_view()

    def _load_mappings(self) -> list[dict]:
        try:
            return get_mappings(self.project_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load mappings:\n{exc}")
            return []

    def _build_navbar(self) -> None:
        self._sidebar = ctk.CTkFrame(self, fg_color=theme.get("sidebar_bg"), corner_radius=0)
        self._sidebar.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            self._sidebar,
            text="Workspace",
            text_color=theme.get("text_light"),
            font=ctk.CTkFont(size=21, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(20, 4))

        ctk.CTkLabel(
            self._sidebar,
            text=str(self.project.get("project_name", "Project")),
            text_color=theme.get("text_light"),
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=18, pady=(0, 10))

        ctk.CTkButton(
            self._sidebar,
            text="Back To Launcher",
            width=150,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("text_light"),
            text_color=theme.get("text_light"),
            command=self._go_to_launcher,
        ).pack(anchor="w", padx=18, pady=(0, 10))

        nav_scroll = ctk.CTkScrollableFrame(self._sidebar, fg_color="transparent")
        nav_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        for item in self._nav_items:
            if item["kind"] == "separator":
                sep = ctk.CTkFrame(nav_scroll, fg_color=theme.get("text_light"), height=1, corner_radius=0)
                sep.pack(fill="x", padx=10, pady=10)
                continue

            key = item["key"]
            button = ctk.CTkButton(
                nav_scroll,
                text=item["label"],
                height=38,
                fg_color="transparent",
                border_width=0,
                text_color=theme.get("text_light"),
                anchor="w",
                hover=False,
                command=lambda selected=item: self._on_nav_click(selected),
            )
            button.pack(fill="x", padx=6, pady=3)
            self._nav_buttons[key] = button

    def _build_content(self) -> None:
        self._content_host = ctk.CTkFrame(self, fg_color=theme.get("secondary"), corner_radius=0)
        self._content_host.grid(row=0, column=1, sticky="nsew")

    def _select_default_view(self) -> None:
        if self.initial_nav_key:
            initial = next(
                (item for item in self._nav_items if item.get("key") == self.initial_nav_key),
                None,
            )
            if initial:
                self._on_nav_click(initial)
                return

        first_mapping = next((item for item in self._nav_items if item["kind"] == "mapping"), None)
        if first_mapping:
            self._on_nav_click(first_mapping)
            return
        t_sources = next((item for item in self._nav_items if item.get("key") == "t_sources"), None)
        if t_sources:
            self._on_nav_click(t_sources)

    def _reload_from_disk(self, target_key: str | None = None) -> None:
        try:
            updated = open_project(self.project_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not refresh project:\n{exc}")
            return
        self.app.set_current_project(updated)
        self.app.show_screen(Screen3Main, project=updated, initial_nav_key=target_key)

    def _go_to_mapping_setup(self) -> None:
        try:
            updated = open_project(self.project_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not refresh project:\n{exc}")
            return
        self.app.set_current_project(updated)
        self.app.show_screen(Screen2Mappings, project=updated)

    def _go_to_launcher(self) -> None:
        from ui.screen0_launcher import Screen0Launcher

        self.app.show_screen(Screen0Launcher)

    def _on_nav_click(self, item: dict) -> None:
        key = item["key"]
        self._set_active_nav(key)
        self._show_item_view(item)

    def _set_active_nav(self, active_key: str) -> None:
        for key, button in self._nav_buttons.items():
            if key == active_key:
                button.configure(fg_color="white", text_color=theme.get("primary"))
            else:
                button.configure(fg_color="transparent", text_color=theme.get("text_light"))
        self._active_nav_key = active_key

    def _show_item_view(self, item: dict) -> None:
        if self._active_view is not None:
            self._active_view.destroy()

        if item["kind"] == "mapping":
            mapping = item["mapping"]
            self._active_view = ViewMapping(self._content_host, project=self.project, mapping=mapping)
            self._active_view.pack(fill="both", expand=True)
            return
        elif item["key"] == "t_sources":
            self._active_view = ViewTSources(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
                on_go_mapping_setup=self._go_to_mapping_setup,
            )
            self._active_view.pack(fill="both", expand=True)
            return
        elif item["key"] == "d_sources":
            self._active_view = ViewDSources(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
                on_go_mapping_setup=self._go_to_mapping_setup,
            )
            self._active_view.pack(fill="both", expand=True)
            return
        elif item["key"] == "history":
            self._active_view = ViewHistory(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
            )
            self._active_view.pack(fill="both", expand=True)
            return
        else:
            self._active_view = ViewSettings(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
            )
            self._active_view.pack(fill="both", expand=True)
            return

        self._active_view = _PlaceholderView(self._content_host, title=title, subtitle=subtitle)
        self._active_view.pack(fill="both", expand=True)
