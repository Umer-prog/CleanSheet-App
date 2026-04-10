from __future__ import annotations

import customtkinter as ctk

import ui.theme as theme


class PopupAdd(ctk.CTkToplevel):
    """Modal popup to add a new row to a dim table."""

    def __init__(self, parent, dim_table: str, dim_columns: list[str], mapped_column: str, bad_value: str, on_confirm):
        super().__init__(parent)
        self._dim_columns = dim_columns
        self._mapped_column = mapped_column
        self._bad_value = bad_value
        self._on_confirm = on_confirm
        self._entries: dict[str, ctk.CTkEntry] = {}

        self.title("Add To Dimension")
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.get("secondary"))

        self._error_lbl = None
        self._build_header(dim_table)
        self._build_footer()
        self._build_body()
        self.after(50, self.lift)

    def _build_header(self, dim_table: str) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.get("primary"), corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Add New Dimension Row",
            font=theme.font(20, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=(24, 12))

        ctk.CTkLabel(
            header,
            text=f"Table: {dim_table}",
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
            text="Add Row",
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
        body = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.columnconfigure(0, weight=1)

        fields = ctk.CTkScrollableFrame(body, fg_color="transparent")
        fields.pack(fill="both", expand=True, padx=8, pady=8)
        fields.grid_columnconfigure(0, weight=1)
        fields.grid_columnconfigure(1, weight=1)

        row = 0
        for col in self._dim_columns:
            ctk.CTkLabel(
                fields,
                text=col,
                font=theme.font(12, weight="bold"),
                text_color=theme.get("text_dark"),
            ).grid(row=row, column=0, padx=18, pady=(10, 4), sticky="w")

            entry = ctk.CTkEntry(
                fields,
                height=38,
                corner_radius=8,
                border_color=theme.get("primary"),
                placeholder_text=f"Enter {col}",
            )
            if col == self._mapped_column:
                entry.insert(0, self._bad_value)
            entry.grid(row=row, column=1, padx=18, pady=(10, 4), sticky="ew")
            self._entries[col] = entry
            row += 1

    def _submit(self) -> None:
        row: dict[str, str] = {}
        for col, entry in self._entries.items():
            value = entry.get().strip()
            if not value:
                self._show_error("All fields are required.")
                return
            row[col] = value

        self._on_confirm(row)
        self.destroy()

    def _show_error(self, message: str) -> None:
        if self._error_lbl:
            self._error_lbl.configure(text=message)


