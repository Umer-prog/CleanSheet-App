from __future__ import annotations

import customtkinter as ctk
import pandas as pd

import ui.theme as theme


def _format_dim_table(df: pd.DataFrame, max_rows: int = 200) -> str:
    """Return a pipe-separated text table for the dimension dataframe."""
    if df.empty:
        return "(No rows)"
    preview = df.head(max_rows).fillna("")
    cols = list(preview.columns)

    col_widths = {
        col: max(len(str(col)), max((len(str(v)) for v in preview[col]), default=0))
        for col in cols
    }

    def _row(values) -> str:
        return " | ".join(f"{str(v):<{col_widths[c]}}" for c, v in zip(cols, values))

    sep = "-+-".join("-" * col_widths[c] for c in cols)
    lines = [_row(cols), sep]
    for _, row_data in preview.iterrows():
        lines.append(_row([row_data[c] for c in cols]))
    return "\n".join(lines)


class PopupReplace(ctk.CTkToplevel):
    """Modal popup for selecting a replacement value from dim values."""

    def __init__(
        self,
        parent,
        bad_value: str,
        valid_values: list[str],
        on_confirm,
        dim_df: pd.DataFrame | None = None,
        dim_table: str = "",
    ):
        super().__init__(parent)
        self._on_confirm = on_confirm
        self._valid_values = valid_values
        self._dim_df = dim_df
        self._dim_table = dim_table

        self.title("Replace Value")
        # Taller when dim table is present so it has comfortable reading space
        height = 580 if (dim_df is not None and not dim_df.empty) else 440
        self.geometry(f"580x{height}")
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
            font=theme.font(20, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=(24, 12))

        display = bad_value if bad_value else "(empty / null)"
        ctk.CTkLabel(
            header,
            text=f"Current: {display}",
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
            text="Replace",
            width=120,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            corner_radius=8,
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
            corner_radius=8,
            command=self.destroy,
        ).pack(side="right", pady=15)

    def _build_body(self) -> None:
        body = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)
        body.grid_columnconfigure(0, weight=1)

        has_table = self._dim_df is not None and not self._dim_df.empty
        r = 0

        if has_table:
            # Dim table label
            ctk.CTkLabel(
                body,
                text=f"Dimension Table - {self._dim_table}",
                font=theme.font(12, weight="bold"),
                text_color=theme.get("text_dark"),
            ).grid(row=r, column=0, padx=24, pady=(18, 4), sticky="w")
            r += 1

            # Formatted table in a scrollable monospace textbox
            body.grid_rowconfigure(r, weight=1)
            table_box = ctk.CTkTextbox(
                body,
                fg_color=theme.get("secondary"),
                text_color=theme.get("text_dark"),
                font=ctk.CTkFont(family="Courier New", size=11),
            )
            table_box.grid(row=r, column=0, padx=24, pady=(0, 10), sticky="nsew")
            table_box.insert("1.0", _format_dim_table(self._dim_df))
            table_box.configure(state="disabled")
            r += 1

            # Divider
            ctk.CTkFrame(body, fg_color=theme.get("secondary"), height=1, corner_radius=0).grid(
                row=r, column=0, sticky="ew", padx=24, pady=(0, 8)
            )
            r += 1

        # Dropdown label
        top_pad = 18 if not has_table else 4
        ctk.CTkLabel(
            body,
            text="Select replacement value",
            font=theme.font(12, weight="bold"),
            text_color=theme.get("text_dark"),
        ).grid(row=r, column=0, padx=24, pady=(top_pad, 6), sticky="w")
        r += 1

        # Dropdown
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
        self._value_menu.grid(row=r, column=0, padx=24, pady=(0, 18), sticky="ew")

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

