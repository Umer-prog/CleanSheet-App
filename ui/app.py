from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QMainWindow, QWidget

import ui.theme as theme

_APP_CONFIG = Path(__file__).parent.parent / "app_config.json"


class App(QMainWindow):
    """Main application window and navigation controller.

    Fixed at 1280×720. Owns the project registry and the current project state.
    Screens are set as the central widget — switching screens replaces the widget.
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_project: dict | None = None
        self._current_screen: QWidget | None = None

        self.setWindowTitle(theme.company_name())
        self.setFixedSize(1280, 720)

        from ui.screen0_launcher import Screen0Launcher
        self.show_screen(Screen0Launcher)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def show_screen(self, screen_class, **kwargs) -> None:
        """Replace the current central widget with a new screen instance."""
        new_screen = screen_class(app=self, **kwargs)
        old = self.centralWidget()
        self.setCentralWidget(new_screen)
        if old:
            old.deleteLater()
        self._current_screen = new_screen

    # ------------------------------------------------------------------
    # Project state
    # ------------------------------------------------------------------

    def set_current_project(self, project_state: dict) -> None:
        self._current_project = project_state

    def get_current_project(self) -> dict | None:
        return self._current_project

    # ------------------------------------------------------------------
    # App config / project registry  (app_config.json)
    # ------------------------------------------------------------------

    def _read_app_config(self) -> dict:
        if not _APP_CONFIG.exists():
            return {"projects": []}
        try:
            with open(_APP_CONFIG, encoding="utf-8") as f:
                data = json.load(f)
            data.setdefault("projects", [])
            return data
        except (OSError, json.JSONDecodeError):
            return {"projects": []}

    def _write_app_config(self, config: dict) -> None:
        try:
            with open(_APP_CONFIG, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except OSError:
            pass

    def is_dark_mode_enabled(self) -> bool:
        """Always True — the app uses a fixed dark theme."""
        return True

    def get_known_projects(self) -> list:
        return list(self._read_app_config().get("projects", []))

    def register_project(self, project_path: str) -> None:
        config = self._read_app_config()
        projects = list(config.get("projects", []))
        if project_path not in projects:
            projects.append(project_path)
            config["projects"] = projects
            self._write_app_config(config)

    def unregister_project(self, project_path: str) -> None:
        config = self._read_app_config()
        config["projects"] = [p for p in config.get("projects", []) if p != project_path]
        self._write_app_config(config)
