from __future__ import annotations

import customtkinter as ctk

import ui.theme as theme


class PopupRevertConfirm(ctk.CTkToplevel):
    """Confirmation popup before reverting to a selected manifest."""

    def __init__(self, parent, manifest_id: str, on_confirm):
        super().__init__(parent)
        self._on_confirm = on_confirm

        self.title("Confirm Revert")
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.get("secondary"))

        self._build_header(manifest_id)
        self._build_footer()
        self._build_body(manifest_id)
        self.after(50, self.lift)

    def _build_header(self, manifest_id: str) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.get("primary"), corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Revert Confirmation",
            font=theme.font(20, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=(24, 12))

        ctk.CTkLabel(
            header,
            text=manifest_id,
            font=theme.font(11),
            text_color=theme.get("text_light"),
        ).pack(side="left")

    def _build_body(self, manifest_id: str) -> None:
        body = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        ctk.CTkLabel(
            body,
            text=(
                f"Revert current transaction data to '{manifest_id}'?\n\n"
                "This will restore files in data/transactions from the selected manifest.\n"
                "Newer manifests will remain in history."
            ),
            justify="left",
            text_color=theme.get("text_dark"),
            font=theme.font(13),
        ).pack(anchor="w", padx=24, pady=24)

    def _build_footer(self) -> None:
        footer = ctk.CTkFrame(self, fg_color=theme.get("secondary"), corner_radius=0, height=68)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkButton(
            footer,
            text="Revert",
            width=120,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._confirm,
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

    def _confirm(self) -> None:
        self._on_confirm()
        self.destroy()


