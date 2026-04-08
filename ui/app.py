import json
from pathlib import Path

import customtkinter as ctk

import ui.theme as theme

_APP_CONFIG = Path(__file__).parent.parent / "app_config.json"


class App(ctk.CTk):
    """Main application window and navigation controller.

    Owns the 1280Ã—720 window, manages frame switching, holds the
    currently open project state, and maintains the project registry.
    """

    def __init__(self):
        super().__init__()
        self.title(theme.company_name())
        self.geometry("1280x720")
        self.resizable(False, False)

        self._current_frame = None
        self._current_project: dict | None = None
        self._icon_photo = None  # keep PIL reference alive

        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True)

        self.after(100, self._set_icon)

        from ui.screen0_launcher import Screen0Launcher
        self.show_screen(Screen0Launcher)

    def _set_icon(self) -> None:
        """Load the branding logo as the window icon via ICO conversion (Windows-safe)."""
        try:
            import tempfile
            from PIL import Image
            logo = theme.logo_path()
            if not logo:
                return
            # Resolve relative paths against the project root
            root = Path(__file__).parent.parent
            if not logo.is_absolute():
                logo = root / logo
            if not logo.exists():
                return
            img = Image.open(logo).convert("RGBA").resize((32, 32), Image.LANCZOS)
            ico_path = Path(tempfile.gettempdir()) / "_veriflow_icon.ico"
            img.save(str(ico_path), format="ICO")
            self.iconbitmap(str(ico_path))
        except Exception:
            pass  # icon is non-critical

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_screen(self, frame_class, **kwargs) -> None:
        """Destroy the current screen and show frame_class in its place."""
        if self._current_frame is not None:
            self._current_frame.destroy()
        self._current_frame = frame_class(self._container, self, **kwargs)
        self._current_frame.pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    # Project state
    # ------------------------------------------------------------------

    def set_current_project(self, project_state: dict) -> None:
        """Store the currently open project state dict."""
        self._current_project = project_state

    def get_current_project(self) -> dict | None:
        """Return the currently open project state, or None."""
        return self._current_project

    # ------------------------------------------------------------------
    # Project registry  (app_config.json)
    # ------------------------------------------------------------------

    def get_known_projects(self) -> list:
        """Return the list of registered project path strings."""
        if not _APP_CONFIG.exists():
            return []
        try:
            with open(_APP_CONFIG, encoding="utf-8") as f:
                return json.load(f).get("projects", [])
        except (OSError, json.JSONDecodeError):
            return []

    def register_project(self, project_path: str) -> None:
        """Add project_path to the registry if not already present."""
        projects = self.get_known_projects()
        if project_path not in projects:
            projects.append(project_path)
            try:
                with open(_APP_CONFIG, "w", encoding="utf-8") as f:
                    json.dump({"projects": projects}, f, indent=2)
            except OSError:
                pass  # non-critical â€” project still created, just not persisted

    def unregister_project(self, project_path: str) -> None:
        """Remove project_path from the registry if present."""
        projects = [p for p in self.get_known_projects() if p != project_path]
        try:
            with open(_APP_CONFIG, "w", encoding="utf-8") as f:
                json.dump({"projects": projects}, f, indent=2)
        except OSError:
            pass  # non-critical
