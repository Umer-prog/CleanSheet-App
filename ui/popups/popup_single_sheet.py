from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

import ui.theme as theme


class PopupSingleSheet(ctk.CTkToplevel):
    """Modal popup for selecting one sheet from an Excel file."""

    def __init__(self, parent, excel_path: Path, sheet_names: list[str], title: str = "Select Sheet"):
        super().__init__(parent)
        self._result: str | None = None
        self._sheet_names = sheet_names

        self.title(title)
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.get("secondary"))

        self._error_lbl = None
        self._menu = None
        self._build_header(excel_path.name, title)
        self._build_footer()
        self._build_body()
        self.after(50, self.lift)

    @property
    def result(self) -> str | None:
        return self._result

    def _build_header(self, file_name: str, title: str) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.get("primary"), corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text=title,
            font=theme.font(20, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=(24, 12))

        ctk.CTkLabel(
            header,
            text=file_name,
            font=theme.font(11),
            text_color=theme.get("text_light"),
        ).pack(side="left")

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color=theme.get("secondary"), corner_radius=0, height=68)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self._error_lbl = ctk.CTkLabel(
            footer,
            text="",
            text_color=theme.get("accent"),
            font=theme.font(11),
        )
        self._error_lbl.pack(side="left", padx=24)

        ctk.CTkButton(
            footer,
            text="OK",
            width=100,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_ok,
        ).pack(side="right", padx=(8, 24), pady=15)

        ctk.CTkButton(
            footer,
            text="Cancel",
            width=100,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            command=self.destroy,
        ).pack(side="right", pady=15)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Choose a sheet",
            text_color=theme.get("text_dark"),
            font=theme.font(12, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(18, 6))

        values = self._sheet_names or ["No sheets found"]
        self._menu = ctk.CTkOptionMenu(
            body,
            values=values,
            fg_color=theme.get("primary"),
            button_color=theme.get("primary"),
            button_hover_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            height=38,
        )
        self._menu.set(values[0])
        self._menu.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 18))

    def _on_ok(self) -> None:
        if not self._sheet_names:
            self._show_error("No sheets available in this file.")
            return
        choice = self._menu.get().strip()
        if not choice:
            self._show_error("Select a sheet.")
            return
        self._result = choice
        self.destroy()

    def _show_error(self, msg: str) -> None:
        if self._error_lbl:
            self._error_lbl.configure(text=msg)


def select_single_sheet(parent, excel_path: Path, sheet_names: list[str], title: str = "Select Sheet") -> str | None:
    dialog = PopupSingleSheet(parent, excel_path=excel_path, sheet_names=sheet_names, title=title)
    dialog.wait_window()
    return dialog.result


