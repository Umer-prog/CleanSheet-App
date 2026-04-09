from datetime import datetime
from pathlib import Path
import shutil
from tkinter import filedialog, messagebox

import customtkinter as ctk

import ui.theme as theme
from core.project_manager import create_project, open_project

_PANEL_W = 340  # left sidebar width in px


class Screen0Launcher(ctk.CTkFrame):
    """Project launcher screen - left project list, right action panel."""

    def __init__(self, parent, app):
        super().__init__(parent, fg_color=theme.get("secondary"), corner_radius=0)
        self.app = app
        self._selected_path: str | None = None
        self._selected_card: ctk.CTkFrame | None = None

        self.grid_columnconfigure(0, weight=0, minsize=_PANEL_W)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._left = self._build_left_panel()
        self._right = self._build_right_panel()
        self._load_and_render_projects()

    # ------------------------------------------------------------------
    # Layout builders
    # ------------------------------------------------------------------

    def _build_left_panel(self) -> ctk.CTkFrame:
        """Build and return the left sidebar frame."""
        panel = ctk.CTkFrame(self, fg_color=theme.get("sidebar_bg"), corner_radius=0)
        panel.grid(row=0, column=0, sticky="nsew")

        ctk.CTkLabel(
            panel, text="Projects",
            font=theme.font(14, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(padx=16, pady=(20, 10), anchor="w")

        self._list_frame = ctk.CTkScrollableFrame(
            panel, fg_color="transparent",
            scrollbar_button_color=theme.get("primary"),
        )
        self._list_frame.pack(fill="both", expand=True, padx=6, pady=(0, 8))
        return panel

    def _build_right_panel(self) -> ctk.CTkFrame:
        """Build and return the right action panel frame."""
        panel = ctk.CTkFrame(self, fg_color=theme.get("secondary"), corner_radius=0)
        panel.grid(row=0, column=1, sticky="nsew")

        inner = ctk.CTkFrame(panel, fg_color="transparent")
        inner.place(relx=0.5, rely=0.45, anchor="center")

        ctk.CTkLabel(
            inner, text=theme.company_name(),
            font=theme.font(30, weight="bold"),
            text_color=theme.get("primary"),
        ).pack(pady=(0, 6))

        ctk.CTkLabel(
            inner, text="Select a project or create a new one.",
            font=theme.font(13),
            text_color=theme.get("text_dark"),
        ).pack(pady=(0, 36))

        self._dark_mode_switch = ctk.CTkSwitch(
            inner,
            text="Dark Mode",
            text_color=theme.get("text_dark"),
            progress_color=theme.get("primary"),
            button_color=theme.get("primary"),
            button_hover_color=theme.get("primary"),
            command=self._on_toggle_dark_mode,
        )
        if self.app.is_dark_mode_enabled():
            self._dark_mode_switch.select()
        else:
            self._dark_mode_switch.deselect()
        self._dark_mode_switch.pack(pady=(0, 16), anchor="w")

        ctk.CTkButton(
            inner, text="+ New Project",
            width=240, height=46,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            font=theme.font(14, weight="bold"),
            command=self._on_new_click,
        ).pack(pady=8)

        self._open_btn = ctk.CTkButton(
            inner, text="Open Selected",
            width=240, height=46,
            fg_color="transparent",
            border_width=2,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            font=theme.font(14),
            state="disabled",
            command=self._on_open_click,
        )
        self._open_btn.pack(pady=8)

        self._delete_btn = ctk.CTkButton(
            inner, text="Delete Selected",
            width=240, height=42,
            fg_color="transparent",
            border_width=1,
            border_color=theme.get("accent"),
            text_color=theme.get("accent"),
            font=theme.font(13),
            state="disabled",
            command=self._on_delete_click,
        )
        self._delete_btn.pack(pady=(4, 0))
        return panel

    # ------------------------------------------------------------------
    # Project list
    # ------------------------------------------------------------------

    def _load_and_render_projects(self) -> None:
        """Load known projects from the registry and populate the list."""
        for widget in self._list_frame.winfo_children():
            widget.destroy()
        self._selected_path = None
        self._selected_card = None
        self._open_btn.configure(state="disabled")
        self._delete_btn.configure(state="disabled")

        paths = self.app.get_known_projects()
        loaded = []
        for p in paths:
            try:
                state = open_project(Path(p))
                loaded.append(state)
            except (FileNotFoundError, ValueError):
                continue

        if not loaded:
            ctk.CTkLabel(
                self._list_frame, text="No projects yet.",
                font=theme.font(12),
                text_color=theme.get("text_light"),
            ).pack(padx=8, pady=12, anchor="w")
            return

        for state in loaded:
            card = self._make_project_card(self._list_frame, state)
            card.pack(fill="x", padx=4, pady=3)

    def _make_project_card(self, parent, state: dict) -> ctk.CTkFrame:
        """Create and return a clickable project card frame."""
        path = state.get("project_path", "")
        modified = state.get("settings", {}).get("last_modified", "")

        card = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=6, cursor="hand2")
        card.columnconfigure(0, weight=1)

        name_lbl = ctk.CTkLabel(
            card, text=state.get("project_name", "Untitled"),
            font=theme.font(13, weight="bold"),
            text_color=theme.get("text_light"), anchor="w",
        )
        name_lbl.grid(row=0, column=0, padx=10, pady=(8, 0), sticky="w")

        company_lbl = ctk.CTkLabel(
            card, text=state.get("company", ""),
            font=theme.font(11),
            text_color=theme.get("text_light"), anchor="w",
        )
        company_lbl.grid(row=1, column=0, padx=10, pady=(0, 6), sticky="w")

        def on_click(_event=None):
            self._select_card(path, card, [name_lbl, company_lbl])

        card.bind("<Button-1>", on_click)
        for lbl in (name_lbl, company_lbl):
            lbl.bind("<Button-1>", on_click)

        return card

    def _select_card(self, path: str, card: ctk.CTkFrame, labels: list) -> None:
        """Deselect the previously selected card and highlight the new one."""
        if self._selected_card and self._selected_card.winfo_exists():
            self._selected_card.configure(fg_color="transparent")
            for child in self._selected_card.winfo_children():
                if isinstance(child, ctk.CTkLabel):
                    child.configure(text_color=theme.get("text_light"))

        card.configure(fg_color=theme.selection_color())
        for lbl in labels:
            lbl.configure(text_color=theme.get("primary"))

        self._selected_path = path
        self._selected_card = card
        self._open_btn.configure(state="normal")
        self._delete_btn.configure(state="normal")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_click(self) -> None:
        """Load the selected project state and navigate to Screen 3."""
        if not self._selected_path:
            return
        try:
            state = open_project(Path(self._selected_path))
            self.app.set_current_project(state)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not open project:\n{exc}")
            return
        try:
            from ui.screen3_main import Screen3Main
            self.app.show_screen(Screen3Main, project=state)
            return
        except ImportError:
            # Fall back to Screen 1 while Screen 3 is not available.
            pass

        try:
            from ui.screen1_sources import Screen1Sources
            self.app.show_screen(Screen1Sources, project=state)
        except ImportError:
            messagebox.showerror(
                "Navigation Error",
                "Could not open project screen. Neither Screen 3 nor Screen 1 is available.",
            )

    def _on_new_click(self) -> None:
        """Open the New Project creation dialog."""
        NewProjectDialog(self, self.app, on_success=self._after_project_created)

    def _on_toggle_dark_mode(self) -> None:
        """Set global app appearance and refresh launcher visuals."""
        enabled = bool(self._dark_mode_switch.get())
        self.app.set_global_dark_mode(enabled)
        self.app.show_screen(Screen0Launcher)

    def _on_delete_click(self) -> None:
        """Delete the selected project/workspace after explicit confirmation."""
        if not self._selected_path:
            return

        project_path = Path(self._selected_path)
        project_name = project_path.name
        confirmed = messagebox.askyesno(
            "Confirm Delete",
            (
                f"Delete project '{project_name}'?\n\n"
                "This will permanently delete the workspace folder and all project data."
            ),
        )
        if not confirmed:
            return

        try:
            if project_path.exists():
                shutil.rmtree(project_path)
            self.app.unregister_project(str(project_path))
        except Exception as exc:
            messagebox.showerror("Error", f"Could not delete project:\n{exc}")
            return

        self._load_and_render_projects()

    def _after_project_created(self, project_state: dict) -> None:
        """Register the newly created project and navigate to Screen 1."""
        self.app.set_current_project(project_state)
        self.app.register_project(project_state["project_path"])
        try:
            from ui.screen1_sources import Screen1Sources
            self.app.show_screen(Screen1Sources, project=project_state)
        except ImportError:
            self._load_and_render_projects()  # stay on Screen 0, refresh list


# ---------------------------------------------------------------------------
# New Project Dialog
# ---------------------------------------------------------------------------

class NewProjectDialog(ctk.CTkToplevel):
    """Modal dialog for creating a new project."""

    def __init__(self, parent, app, on_success):
        super().__init__(parent)
        self.app = app
        self.on_success = on_success

        self.title("New Project")
        self.geometry("520x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=theme.get("secondary"))

        self._folder_var = ctk.StringVar()
        self._error_lbl = None

        self._build_header()
        self._build_footer()   # footer pinned first so it anchors bottom
        self._build_body()
        self.after(50, self.lift)

    def _build_header(self) -> None:
        """Build the coloured top header bar."""
        header = ctk.CTkFrame(self, fg_color=theme.get("primary"),
                              corner_radius=0, height=68)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="New Project",
            font=theme.font(20, weight="bold"),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=28, pady=0)

        ctk.CTkLabel(
            header,
            text="Fill in the details below to create a new workspace.",
            font=theme.font(11),
            text_color=theme.get("text_light"),
        ).pack(side="left", padx=(0, 20))

    def _build_footer(self) -> None:
        """Build the button row pinned to the bottom."""
        footer = ctk.CTkFrame(self, fg_color=theme.get("secondary"),
                              corner_radius=0, height=68)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self._error_lbl = ctk.CTkLabel(
            footer, text="",
            text_color=theme.get("accent"),
            font=theme.font(11),
        )
        self._error_lbl.pack(side="left", padx=28)

        ctk.CTkButton(
            footer, text="Create Project", width=140, height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            font=theme.font(13, weight="bold"),
            command=self._on_create,
        ).pack(side="right", padx=(8, 24), pady=15)

        ctk.CTkButton(
            footer, text="Cancel", width=100, height=38,
            fg_color="transparent", border_width=1,
            border_color=theme.get("primary"),
            text_color=theme.get("primary"),
            font=theme.font(13),
            command=self.destroy,
        ).pack(side="right", pady=15)

    def _build_body(self) -> None:
        """Build the form fields in the scrollable middle area."""
        body = ctk.CTkFrame(self, fg_color=theme.card_color(), corner_radius=10)
        body.pack(fill="both", expand=True, padx=20, pady=16)

        def field(label_text, row):
            ctk.CTkLabel(
                body, text=label_text,
                font=theme.font(12, weight="bold"),
                text_color=theme.get("text_dark"), anchor="w",
            ).grid(row=row, column=0, padx=24, pady=(18, 4), sticky="w")

        field("Project Name", 0)
        self._name_entry = ctk.CTkEntry(
            body, placeholder_text="e.g. Sales Module",
            height=38, corner_radius=8,
            border_color=theme.get("primary"),
        )
        self._name_entry.grid(row=1, column=0, padx=24, pady=(0, 4), sticky="ew")

        field("Company Name", 2)
        self._company_entry = ctk.CTkEntry(
            body, placeholder_text="e.g. Acme Corp",
            height=38, corner_radius=8,
            border_color=theme.get("primary"),
        )
        self._company_entry.grid(row=3, column=0, padx=24, pady=(0, 4), sticky="ew")

        field("Save Location", 4)
        path_row = ctk.CTkFrame(body, fg_color="transparent")
        path_row.grid(row=5, column=0, padx=24, pady=(0, 18), sticky="ew")
        path_row.columnconfigure(0, weight=1)

        ctk.CTkEntry(
            path_row, textvariable=self._folder_var,
            placeholder_text="Choose a folder...",
            height=38, corner_radius=8,
            border_color=theme.get("primary"),
        ).grid(row=0, column=0, sticky="ew")

        ctk.CTkButton(
            path_row, text="Browse...", width=90, height=38,
            fg_color=theme.get("primary"),
            text_color=theme.get("text_light"),
            corner_radius=8,
            command=self._on_browse,
        ).grid(row=0, column=1, padx=(10, 0))

        body.columnconfigure(0, weight=1)

    def _on_browse(self) -> None:
        """Open a folder browser and populate the path entry."""
        folder = filedialog.askdirectory(title="Choose save location")
        if folder:
            self._folder_var.set(folder)

    def _on_create(self) -> None:
        """Validate inputs, create the project on disk, and call on_success."""
        name = self._name_entry.get().strip()
        company = self._company_entry.get().strip()
        folder = self._folder_var.get().strip()

        if not name:
            self._show_error("Project name is required.")
            return
        if not company:
            self._show_error("Company name is required.")
            return
        if not folder:
            self._show_error("Please choose a save location.")
            return
        if not Path(folder).exists():
            self._show_error("Save location does not exist.")
            return

        try:
            project_path = create_project(name, company, Path(folder))
            state = open_project(project_path)
        except Exception as exc:
            self._show_error(f"Could not create project: {exc}")
            return

        self.destroy()
        self.on_success(state)

    def _show_error(self, msg: str) -> None:
        """Display an inline validation error in the footer."""
        if self._error_lbl:
            self._error_lbl.configure(text=msg)

