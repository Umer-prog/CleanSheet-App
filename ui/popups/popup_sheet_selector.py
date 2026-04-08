from __future__ import annotations

from pathlib import Path

import customtkinter as ctk

import ui.theme as theme


class PopupSheetSelector(ctk.CTkToplevel):
    """Modal popup that lets the user select sheets and set a category for each."""

    CATEGORY_VALUES = ["Select Category", "Transaction", "Dimension"]

    def __init__(self, parent, excel_path: Path, sheet_names: list[str]):
        super().__init__(parent)
        self._result: list[dict] | None = None
        self._rows: list[dict] = []
        self._excel_path = Path(excel_path)

        self.title("Select Sheets")
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.get("secondary"))

        self._error_lbl = None
        self._build_header()
        self._build_footer()
        self._build_body(sheet_names)
        self.after(50, self.lift)

    @property
    def result(self) -> list[dict] | None:
        return self._result

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.get("primary"), corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Select Sheets",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=(24, 12))

        ctk.CTkLabel(
            header,
            text=self._excel_path.name,
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

    def _build_body(self, sheet_names: list[str]) -> None:
        body = ctk.CTkFrame(self, fg_color="white", corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            body,
            text="Choose sheets and category",
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=18, pady=(14, 8))

        list_frame = ctk.CTkScrollableFrame(body, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 12))

        for sheet_name in sheet_names:
            self._rows.append(self._build_sheet_row(list_frame, sheet_name))

    def _build_sheet_row(self, parent, sheet_name: str) -> dict:
        row = ctk.CTkFrame(parent, fg_color=theme.get("secondary"), corner_radius=8)
        row.pack(fill="x", padx=6, pady=5)
        row.columnconfigure(1, weight=1)

        checkbox = ctk.CTkCheckBox(
            row,
            text=sheet_name,
            text_color=theme.get("text_dark"),
            command=lambda: self._on_toggle_row(option_menu),
        )
        checkbox.grid(row=0, column=0, padx=(12, 8), pady=10, sticky="w")

        option_menu = ctk.CTkOptionMenu(
            row,
            values=self.CATEGORY_VALUES,
            fg_color=theme.get("primary"),
            button_color=theme.get("primary"),
            button_hover_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            width=150,
            height=32,
        )
        option_menu.set("Select Category")
        option_menu.grid(row=0, column=1, padx=(4, 12), pady=10, sticky="e")
        option_menu.grid_remove()

        return {
            "sheet_name": sheet_name,
            "checkbox": checkbox,
            "option_menu": option_menu,
        }

    def _on_toggle_row(self, option_menu: ctk.CTkOptionMenu) -> None:
        for row in self._rows:
            if row["option_menu"] == option_menu:
                if row["checkbox"].get() == 1:
                    option_menu.grid()
                else:
                    option_menu.set("Select Category")
                    option_menu.grid_remove()
                return

    def _on_ok(self) -> None:
        selections = []
        for row in self._rows:
            if row["checkbox"].get() != 1:
                continue
            category = row["option_menu"].get().strip()
            if category not in ("Transaction", "Dimension"):
                self._show_error("Please choose a category for each selected sheet.")
                return
            selections.append(
                {
                    "sheet_name": row["sheet_name"],
                    "category": category,
                }
            )

        if not selections:
            self._show_error("Select at least one sheet.")
            return

        self._result = selections
        self.destroy()

    def _show_error(self, message: str) -> None:
        if self._error_lbl:
            self._error_lbl.configure(text=message)


def select_sheets(parent, excel_path: Path, sheet_names: list[str]) -> list[dict] | None:
    """Open the sheet selector popup and return selected rows, or None if cancelled."""
    dialog = PopupSheetSelector(parent, excel_path=excel_path, sheet_names=sheet_names)
    dialog.wait_window()
    return dialog.result

