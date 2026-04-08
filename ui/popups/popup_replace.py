from __future__ import annotations

import customtkinter as ctk

import ui.theme as theme


class PopupReplace(ctk.CTkToplevel):
    """Modal popup for selecting a replacement value from dim values."""

    def __init__(self, parent, bad_value: str, valid_values: list[str], on_confirm):
        super().__init__(parent)
        self._on_confirm = on_confirm
        self._valid_values = valid_values

        self.title("Replace Value")
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.get("secondary"))

        self._error_lbl = None
        self._value_menu = None

        self._build_header(bad_value)
        self._build_footer()
        self._build_body()
        self.after(50, self.lift)

    def _build_header(self, bad_value: str) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.get("primary"), corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Replace Error Value",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=(24, 12))

        ctk.CTkLabel(
            header,
            text=f"Current: {bad_value}",
            font=ctk.CTkFont(size=11),
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
            font=ctk.CTkFont(size=11),
        )
        self._error_lbl.pack(side="left", padx=24)

        ctk.CTkButton(
            footer,
            text="Replace",
            width=120,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._submit,
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
        body = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            body,
            text="Select replacement value",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=theme.get("text_dark"),
        ).grid(row=0, column=0, padx=24, pady=(18, 6), sticky="w")

        values = self._valid_values or ["No Values Available"]
        self._value_menu = ctk.CTkOptionMenu(
            body,
            values=values,
            fg_color=theme.get("primary"),
            button_color=theme.get("primary"),
            button_hover_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            height=38,
        )
        self._value_menu.set(values[0])
        self._value_menu.grid(row=1, column=0, padx=24, pady=(0, 18), sticky="ew")

    def _submit(self) -> None:
        selected = self._value_menu.get().strip()
        if not self._valid_values:
            self._show_error("No valid values available.")
            return
        if not selected:
            self._show_error("Select a replacement value.")
            return
        self._on_confirm(selected)
        self.destroy()

    def _show_error(self, message: str) -> None:
        if self._error_lbl:
            self._error_lbl.configure(text=message)

