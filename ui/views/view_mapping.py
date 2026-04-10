from __future__ import annotations

import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import pandas as pd

import ui.theme as theme
from core.data_loader import load_csv, save_as_csv
from core.dim_manager import append_dim_row, get_dim_columns, get_dim_dataframe
from core.error_detector import detect_errors
from core.final_export_manager import export_final_workbook
from core.mapping_manager import get_mappings
from ui.popups.popup_add import PopupAdd
from ui.popups.popup_replace import PopupReplace


def format_dataframe_preview(df: pd.DataFrame) -> str:
    """Return a pipe-separated text table with row numbers matching Excel (header = row 1, data starts at row 2)."""
    if df.empty:
        return "(No rows)"
    preview = df.fillna("")
    cols = list(preview.columns)

    col_widths = {
        col: max(len(str(col)), max((len(str(v)) for v in preview[col]), default=0))
        for col in cols
    }
    max_row_num = int(preview.index[-1]) + 1 if len(preview) > 0 else 1
    row_num_w = max(1, len(str(max_row_num)))

    def _row(label, values) -> str:
        parts = [f"{str(label):<{row_num_w}}"] + [
            f"{str(v):<{col_widths[c]}}" for c, v in zip(cols, values)
        ]
        return " | ".join(parts)

    sep = "-+-".join(["-" * row_num_w] + ["-" * col_widths[c] for c in cols])

    lines = [_row("0", cols), sep]
    for idx, row_data in preview.iterrows():
        row_num = int(idx) + 1  # row 0 = header, data rows start at 1
        lines.append(_row(row_num, [row_data[c] for c in cols]))
    return "\n".join(lines)


def get_valid_dim_values(project_path: Path, dim_table: str, dim_column: str) -> list[str]:
    df = get_dim_dataframe(project_path, dim_table)
    values = sorted({str(v).strip() for v in df[dim_column].tolist() if str(v).strip()})
    return values


def replace_transaction_value(
    project_path: Path,
    mapping: dict,
    row_index: int,
    new_value: str,
) -> None:
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    csv_path = Path(project_path) / "data" / "transactions" / f"{t_table}.csv"

    df = load_csv(csv_path)
    if t_col not in df.columns:
        raise ValueError(f"Column '{t_col}' not found in '{t_table}'.")
    if row_index < 0 or row_index >= len(df):
        raise IndexError(f"Row index {row_index} out of bounds.")

    df.at[row_index, t_col] = str(new_value)
    save_as_csv(df, csv_path)


def replace_transaction_values_bulk(
    project_path: Path,
    mapping: dict,
    old_value: str,
    new_value: str,
) -> int:
    """Replace every row in transaction_column where the stripped value equals old_value.

    Returns the number of rows changed.
    """
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    csv_path = Path(project_path) / "data" / "transactions" / f"{t_table}.csv"

    df = load_csv(csv_path)
    if t_col not in df.columns:
        raise ValueError(f"Column '{t_col}' not found in '{t_table}'.")

    mask = df[t_col].astype(str).str.strip() == str(old_value)
    count = int(mask.sum())
    if count:
        df.loc[mask, t_col] = str(new_value)
        save_as_csv(df, csv_path)
    return count


class _BulkScopePopup(ctk.CTkToplevel):
    """Ask the user whether to apply a Replace action to all matching rows or just the selected one."""

    def __init__(self, parent, bad_value: str, total_count: int, selected_row: int, on_choice):
        """on_choice is called with "all" or "single"."""
        super().__init__(parent)
        self._on_choice = on_choice

        self.title("Multiple Occurrences Found")
        self.geometry("520x280")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.get("secondary"))

        # Header
        header = ctk.CTkFrame(self, fg_color=theme.get("primary"), corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header,
            text="Multiple Occurrences Found",
            font=theme.font(18, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=24)

        # Footer (packed before body so it pins to bottom)
        footer = ctk.CTkFrame(self, fg_color=theme.get("secondary"), corner_radius=0, height=68)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkButton(
            footer,
            text=f"Apply to All  ({total_count} rows)",
            width=190,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            corner_radius=8,
            command=lambda: self._pick("all"),
        ).pack(side="right", padx=(8, 24), pady=15)

        ctk.CTkButton(
            footer,
            text=f"Just Row {selected_row}",
            width=130,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            corner_radius=8,
            command=lambda: self._pick("single"),
        ).pack(side="right", pady=15)

        # Body
        body = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        display_value = bad_value if bad_value else "(empty / null)"
        msg = (
            f'The value  "{display_value}"  appears on {total_count} rows in this mapping.\n\n'
            f"Do you want to apply this replacement to all {total_count} rows, "
            f"or only to Row {selected_row}?"
        )
        ctk.CTkLabel(
            body,
            text=msg,
            font=theme.font(13),
            text_color=theme.get("text_dark"),
            wraplength=450,
            justify="left",
        ).pack(padx=24, pady=24, anchor="w")

        self.after(50, self.lift)

    def _pick(self, choice: str) -> None:
        self.destroy()
        self._on_choice(choice)


class ViewMapping(ctk.CTkFrame):
    """Mapping view with transaction preview, error list, replace/add actions."""

    def __init__(self, parent, project: dict, mapping: dict):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.project = project
        self.mapping = mapping
        self.project_path = Path(project["project_path"])

        self._selected_error: dict | None = None
        self._errors: list[dict] = []
        self._transaction_df: pd.DataFrame | None = None
        self._page_size = 500
        self._current_page = 0
        self._loading_count = 0
        self._loading_anim_job = None
        self._loading_anim_value = 0.0
        self._loading_anim_direction = 1
        self._generate_mode = False
        self._generate_check_token = 0

        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._build_header()
        self._build_transaction_panel()
        self._build_error_panel()
        self._build_loading_overlay()
        self._reload_data()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr,
            text=(
                f"{self.mapping['transaction_table']}.{self.mapping['transaction_column']}  ->  "
                f"{self.mapping['dim_table']}.{self.mapping['dim_column']}"
            ),
            text_color=theme.get("text_dark"),
            font=theme.font(18, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            hdr,
            text="Refresh",
            width=90,
            height=34,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._reload_data,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            hdr,
            text="How to use: Select an error, then use Replace to fix transaction values or Add to append missing dim values.",
            text_color=theme.get("text_dark"),
            font=theme.font(11),
            justify="left",
            wraplength=760,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))

    def _build_transaction_panel(self) -> None:
        card = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        card.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 8))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)
        card.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            card,
            text="Transaction Data (Preview)",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        pagination = ctk.CTkFrame(card, fg_color="transparent")
        pagination.grid(row=0, column=1, sticky="e", padx=12, pady=(10, 6))

        self._tx_range_lbl = ctk.CTkLabel(
            pagination,
            text="row 0-0 of 0",
            text_color=theme.get("text_dark"),
            font=theme.font(11),
        )
        self._tx_range_lbl.pack(side="left", padx=(0, 8))

        self._prev_btn = ctk.CTkButton(
            pagination,
            text="Prev",
            width=64,
            height=30,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            state="disabled",
            command=self._go_prev_page,
        )
        self._prev_btn.pack(side="left", padx=(0, 6))

        self._next_btn = ctk.CTkButton(
            pagination,
            text="Next",
            width=64,
            height=30,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            state="disabled",
            command=self._go_next_page,
        )
        self._next_btn.pack(side="left")

        self._data_box = ctk.CTkTextbox(
            card,
            fg_color=theme.get("secondary"),
            text_color=theme.get("text_dark"),
            font=ctk.CTkFont(family="Courier New", size=11),
            wrap="none",
        )
        self._data_box.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=12, pady=(0, 12))

    def _build_error_panel(self) -> None:
        card = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        card.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 18))
        card.grid_rowconfigure(1, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="Errors",
            text_color=theme.get("text_dark"),
            font=theme.font(13, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(10, 6))

        self._error_list = ctk.CTkScrollableFrame(card, fg_color=theme.get("secondary"), corner_radius=8)
        self._error_list.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        actions.grid_columnconfigure(0, weight=1)

        self._error_lbl = ctk.CTkLabel(
            actions,
            text="",
            text_color=theme.get("accent"),
            font=theme.font(11),
        )
        self._error_lbl.grid(row=0, column=0, sticky="w")

        self._replace_btn = ctk.CTkButton(
            actions,
            text="Replace",
            width=100,
            height=38,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            state="disabled",
            command=self._on_replace,
        )
        self._replace_btn.grid(row=0, column=1, sticky="e", padx=(0, 8))

        self._add_btn = ctk.CTkButton(
            actions,
            text="Add",
            width=100,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            state="disabled",
            command=self._on_add,
        )
        self._add_btn.grid(row=0, column=2, sticky="e")

        self._generate_msg_lbl = ctk.CTkLabel(
            actions,
            text="All errors are removed. Generate final file.",
            text_color=theme.get("text_dark"),
            font=theme.font(11, weight="bold"),
        )
        self._generate_msg_lbl.grid(row=0, column=1, sticky="e", padx=(0, 8))
        self._generate_msg_lbl.grid_remove()

        self._generate_btn = ctk.CTkButton(
            actions,
            text="Generate",
            width=110,
            height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            command=self._on_generate_final_file,
        )
        self._generate_btn.grid(row=0, column=2, sticky="e")
        self._generate_btn.grid_remove()

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
            text="Loading...",
            text_color=theme.get("text_dark"),
            font=theme.font(14, weight="bold"),
        ).pack(padx=20, pady=(14, 8))

        self._loading_bar = ctk.CTkProgressBar(overlay_card, mode="determinate", width=220)
        self._loading_bar.set(0.0)
        self._loading_bar.pack(padx=20, pady=(0, 14))

    def _reload_data(self) -> None:
        self._set_error("")
        self._selected_error = None
        self._set_generate_mode(False)
        self._error_list_set_loading()
        self._transaction_df = None
        self._update_transaction_preview()

        def worker():
            csv_path = (
                self.project_path
                / "data"
                / "transactions"
                / f"{self.mapping['transaction_table']}.csv"
            )
            tx_df = load_csv(csv_path)
            errors = detect_errors(self.project_path, self.mapping)
            return tx_df, errors

        def on_success(result):
            tx_df, errors = result
            self._transaction_df = tx_df
            self._current_page = 0
            self._errors = errors
            self._update_transaction_preview()
            self._render_errors()
            self._refresh_generate_state()

        def on_error(exc):
            self._transaction_df = None
            self._errors = []
            self._update_transaction_preview(f"Could not load mapping data:\n{exc}")
            self._set_error(f"Load failed: {exc}")
            self._render_errors()
            self._set_generate_mode(False)

        self._run_background(worker, on_success, on_error)

    def _render_errors(self) -> None:
        for child in self._error_list.winfo_children():
            child.destroy()

        if not self._errors:
            ctk.CTkLabel(
                self._error_list,
                text="No errors found for this mapping.",
                text_color=theme.get("text_dark"),
                font=theme.font(12),
            ).pack(anchor="w", padx=10, pady=10)
            return

        for error in self._errors:
            row = ctk.CTkFrame(self._error_list, fg_color=theme.card_color(), corner_radius=8, cursor="hand2")
            row.pack(fill="x", padx=6, pady=5)
            row.grid_columnconfigure(0, weight=1)

            text = (
                f"Row {error['row_index'] + 1} | "
                f"Column: {error['transaction_column']} | "
                f"Bad value: {error['bad_value']}"
            )
            lbl = ctk.CTkLabel(
                row,
                text=text,
                text_color=theme.get("text_dark"),
                anchor="w",
                font=theme.font(12),
            )
            lbl.grid(row=0, column=0, sticky="w", padx=10, pady=8)

            def on_click(_event=None, err=error, frame=row, label=lbl):
                self._select_error(err, frame, label)

            row.bind("<Button-1>", on_click)
            lbl.bind("<Button-1>", on_click)

    def _error_list_set_loading(self) -> None:
        for child in self._error_list.winfo_children():
            child.destroy()
        ctk.CTkLabel(
            self._error_list,
            text="Loading errors...",
            text_color=theme.get("text_dark"),
            font=theme.font(12),
        ).pack(anchor="w", padx=10, pady=10)

    def _select_error(self, error: dict, frame: ctk.CTkFrame, label: ctk.CTkLabel) -> None:
        if self._generate_mode:
            return
        self._selected_error = error
        for child in self._error_list.winfo_children():
            if isinstance(child, ctk.CTkFrame):
                child.configure(fg_color=theme.card_color())
                for gchild in child.winfo_children():
                    if isinstance(gchild, ctk.CTkLabel):
                        gchild.configure(text_color=theme.get("text_dark"))

        frame.configure(fg_color=theme.get("primary"))
        label.configure(text_color=theme.get("text_light"))
        self._replace_btn.configure(state="normal")
        # Null/empty cells have no meaningful value to add to the dim table -
        # the user must replace with an existing valid value instead.
        if str(error.get("bad_value", "")).strip():
            self._add_btn.configure(state="normal")
        else:
            self._add_btn.configure(state="disabled")

    def _on_replace(self) -> None:
        if not self._selected_error:
            self._set_error("Select an error first.")
            return

        bad_value = str(self._selected_error.get("bad_value", ""))
        row_index = int(self._selected_error["row_index"])

        def worker():
            values = get_valid_dim_values(
                self.project_path,
                self.mapping["dim_table"],
                self.mapping["dim_column"],
            )
            try:
                dim_df = get_dim_dataframe(self.project_path, self.mapping["dim_table"])
            except Exception:
                dim_df = None
            return values, dim_df

        def on_success(result):
            values, dim_df = result
            same_value_count = sum(
                1 for e in self._errors if str(e.get("bad_value", "")) == bad_value
            )

            def open_replace_popup(scope: str) -> None:
                def on_confirm(new_value: str) -> None:
                    def apply_worker():
                        if scope == "all":
                            replace_transaction_values_bulk(
                                self.project_path,
                                self.mapping,
                                old_value=bad_value,
                                new_value=new_value,
                            )
                        else:
                            replace_transaction_value(
                                self.project_path,
                                self.mapping,
                                row_index=row_index,
                                new_value=new_value,
                            )

                    def apply_success(_result):
                        self._reload_data()

                    def apply_error(exc):
                        messagebox.showerror("Error", f"Could not replace value:\n{exc}")

                    self._run_background(apply_worker, apply_success, apply_error)

                PopupReplace(
                    self,
                    bad_value=bad_value,
                    valid_values=values,
                    on_confirm=on_confirm,
                    dim_df=dim_df,
                    dim_table=self.mapping["dim_table"],
                )

            if same_value_count > 1:
                _BulkScopePopup(
                    self,
                    bad_value=bad_value,
                    total_count=same_value_count,
                    selected_row=row_index + 1,  # row 0 = header, data starts at 1
                    on_choice=open_replace_popup,
                )
            else:
                open_replace_popup("single")

        def on_error(exc):
            self._set_error(f"Could not load dim values: {exc}")

        self._run_background(worker, on_success, on_error)

    def _on_add(self) -> None:
        if not self._selected_error:
            self._set_error("Select an error first.")
            return

        def worker():
            return get_dim_columns(self.project_path, self.mapping["dim_table"])

        def on_success(dim_columns):
            def on_confirm(row: dict) -> None:
                def apply_worker():
                    append_dim_row(self.project_path, self.mapping["dim_table"], row)

                def apply_success(_result):
                    self._reload_data()

                def apply_error(exc):
                    messagebox.showerror("Error", f"Could not append dim row:\n{exc}")

                self._run_background(apply_worker, apply_success, apply_error)

            PopupAdd(
                self,
                dim_table=self.mapping["dim_table"],
                dim_columns=dim_columns,
                mapped_column=self.mapping["dim_column"],
                bad_value=str(self._selected_error.get("bad_value", "")),
                on_confirm=on_confirm,
            )

        def on_error(exc):
            self._set_error(f"Could not load dim columns: {exc}")

        self._run_background(worker, on_success, on_error)

    def _set_error(self, message: str) -> None:
        self._error_lbl.configure(text=message)

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

    def _set_generate_mode(self, enabled: bool) -> None:
        self._generate_mode = bool(enabled)
        if self._generate_mode:
            self._replace_btn.configure(state="disabled")
            self._add_btn.configure(state="disabled")
            self._replace_btn.grid_remove()
            self._add_btn.grid_remove()
            self._generate_msg_lbl.grid()
            self._generate_btn.grid()
            return

        self._generate_msg_lbl.grid_remove()
        self._generate_btn.grid_remove()
        self._replace_btn.grid()
        self._add_btn.grid()

        if self._selected_error:
            self._replace_btn.configure(state="normal")
            if str(self._selected_error.get("bad_value", "")).strip():
                self._add_btn.configure(state="normal")
            else:
                self._add_btn.configure(state="disabled")
        else:
            self._replace_btn.configure(state="disabled")
            self._add_btn.configure(state="disabled")

    def _refresh_generate_state(self) -> None:
        if self._errors:
            self._set_generate_mode(False)
            return

        self._generate_check_token += 1
        check_token = self._generate_check_token

        def worker():
            mappings = get_mappings(self.project_path)
            for mapping in mappings:
                if detect_errors(self.project_path, mapping):
                    return False
            return True

        def on_success(all_clear):
            if check_token != self._generate_check_token:
                return
            self._set_generate_mode(bool(all_clear))
            if not all_clear:
                self._set_error("No errors in this mapping. Resolve remaining mappings to enable final export.")

        def on_error(exc):
            if check_token != self._generate_check_token:
                return
            self._set_generate_mode(False)
            self._set_error(f"Could not verify mapping status: {exc}")

        self._run_background(worker, on_success, on_error)

    def _on_generate_final_file(self) -> None:
        if not self._generate_mode:
            return

        def worker():
            return export_final_workbook(self.project_path)

        def on_success(output_path):
            messagebox.showinfo("Final File Generated", f"Final file created:\n{output_path}")

        def on_error(exc):
            messagebox.showerror("Error", f"Could not generate final file:\n{exc}")

        self._run_background(worker, on_success, on_error)

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

    def _go_prev_page(self) -> None:
        if self._transaction_df is None or self._current_page <= 0:
            return
        self._current_page -= 1
        self._update_transaction_preview()

    def _go_next_page(self) -> None:
        if self._transaction_df is None:
            return
        total_rows = len(self._transaction_df)
        if total_rows == 0:
            return
        max_page = (total_rows - 1) // self._page_size
        if self._current_page >= max_page:
            return
        self._current_page += 1
        self._update_transaction_preview()

    def _update_transaction_preview(self, message: str | None = None) -> None:
        self._data_box.delete("1.0", "end")

        if message:
            self._data_box.insert("1.0", message)
            self._tx_range_lbl.configure(text="row 0-0 of 0")
            self._prev_btn.configure(state="disabled")
            self._next_btn.configure(state="disabled")
            return

        if self._transaction_df is None:
            self._data_box.insert("1.0", "Loading transaction data...")
            self._tx_range_lbl.configure(text="row 0-0 of 0")
            self._prev_btn.configure(state="disabled")
            self._next_btn.configure(state="disabled")
            return

        total_rows = len(self._transaction_df)
        if total_rows == 0:
            self._data_box.insert("1.0", "(No rows)")
            self._tx_range_lbl.configure(text="row 0-0 of 0")
            self._prev_btn.configure(state="disabled")
            self._next_btn.configure(state="disabled")
            return

        max_page = (total_rows - 1) // self._page_size
        if self._current_page > max_page:
            self._current_page = max_page

        start = self._current_page * self._page_size
        end = min(start + self._page_size, total_rows)
        page_df = self._transaction_df.iloc[start:end].copy()
        self._data_box.insert("1.0", format_dataframe_preview(page_df))
        self._tx_range_lbl.configure(text=f"row {start + 1}-{end} of {total_rows}")

        self._prev_btn.configure(state="normal" if self._current_page > 0 else "disabled")
        self._next_btn.configure(state="normal" if self._current_page < max_page else "disabled")
