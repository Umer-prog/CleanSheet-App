import json
from pathlib import Path

import customtkinter as ctk

import ui.theme as theme

_APP_CONFIG = Path(__file__).parent.parent / "app_config.json"


class App(ctk.CTk):
    """Main application window and navigation controller.

    Owns the 1280x720 window, manages frame switching, holds the
    currently open project state, and maintains the project registry.
    """

    def __init__(self):
        super().__init__()
        self._app_config_cache = self._read_app_config()
        ctk.set_appearance_mode("dark" if self.is_dark_mode_enabled() else "light")

        self.title(theme.company_name())
        self.geometry("1280x720")
        self.resizable(False, False)

        self._current_frame = None
        self._current_project: dict | None = None
        self._icon_photo = None

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
            pass

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
    # App config and project registry (app_config.json)
    # ------------------------------------------------------------------

    def _read_app_config(self) -> dict:
        if not _APP_CONFIG.exists():
            return {"projects": [], "dark_mode": False}
        try:
            with open(_APP_CONFIG, encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("projects", [])
            data.setdefault("dark_mode", False)
            return data
        except (OSError, json.JSONDecodeError):
            return {"projects": [], "dark_mode": False}

    def _write_app_config(self, config: dict) -> None:
        try:
            with open(_APP_CONFIG, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            self._app_config_cache = config
        except OSError:
            pass

    def is_dark_mode_enabled(self) -> bool:
        return bool(self._read_app_config().get("dark_mode", False))

    def set_global_dark_mode(self, enabled: bool) -> None:
        config = self._read_app_config()
        config["dark_mode"] = bool(enabled)
        self._write_app_config(config)
        ctk.set_appearance_mode("dark" if enabled else "light")

    def get_known_projects(self) -> list:
        """Return the list of registered project path strings."""
        return list(self._read_app_config().get("projects", []))

    def register_project(self, project_path: str) -> None:
        """Add project_path to the registry if not already present."""
        config = self._read_app_config()
        projects = list(config.get("projects", []))
        if project_path not in projects:
            projects.append(project_path)
            config["projects"] = projects
            self._write_app_config(config)

    def unregister_project(self, project_path: str) -> None:
        """Remove project_path from the registry if present."""
        config = self._read_app_config()
        config["projects"] = [p for p in config.get("projects", []) if p != project_path]
        self._write_app_config(config)
