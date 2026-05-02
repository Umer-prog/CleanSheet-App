from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow,
    QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.constants import APP_NAME, APP_VERSION
from utils.paths import user_data_path

_APP_CONFIG   = user_data_path("app_config.json")
_TITLEBAR_H   = 32


# ---------------------------------------------------------------------------
# Custom title bar
# ---------------------------------------------------------------------------

class _TitleBar(QWidget):
    """Frameless drag-to-move title bar with minimize and close buttons."""

    def __init__(self, window: QMainWindow) -> None:
        super().__init__(window)
        self._window   = window
        self._drag_pos: QPoint | None = None

        self.setFixedHeight(_TITLEBAR_H)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "QWidget { background: #0a0d13; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.05); }"
        )

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 4, 0)
        lay.setSpacing(0)

        app_lbl = QLabel(f"{APP_NAME}  v{APP_VERSION}")
        app_lbl.setStyleSheet(
            "color: #94a3b8; font-size: 11px; font-weight: 500; "
            "background: transparent; border: none;"
        )
        lay.addWidget(app_lbl, 1)

        min_btn = QPushButton("−")
        min_btn.setFixedSize(36, _TITLEBAR_H)
        min_btn.setCursor(Qt.PointingHandCursor)
        min_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "color: #94a3b8; font-size: 18px; font-weight: 300; }"
            "QPushButton:hover { background: rgba(255,255,255,0.07); color: #94a3b8; }"
        )
        min_btn.clicked.connect(window.showMinimized)
        lay.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(36, _TITLEBAR_H)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(
            "QPushButton { background: transparent; border: none; "
            "color: #94a3b8; font-size: 11px; }"
            "QPushButton:hover { background: rgba(239,68,68,0.18); color: #f87171; }"
        )
        close_btn.clicked.connect(window.close)
        lay.addWidget(close_btn)

    # -- drag to move --

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self._window.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self._window.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------

class App(QMainWindow):
    """Main application window and navigation controller.

    Fixed at 1280×(720+titlebar). Owns the project registry and current project state.
    Screens are placed inside _content — switching screens swaps the child widget.
    """

    def __init__(self) -> None:
        super().__init__()
        self._current_project: dict | None = None
        self._current_screen:  QWidget    | None = None

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(1600, 920 + _TITLEBAR_H)

        # Permanent wrapper: title bar on top, content area below
        wrapper = QWidget()
        wrapper.setObjectName("app_wrapper")
        wrapper.setAttribute(Qt.WA_StyledBackground, True)
        wrapper.setStyleSheet("QWidget#app_wrapper { background: #0f1117; }")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(_TitleBar(self))

        self._content = QWidget()
        self._content.setObjectName("app_content")
        self._content.setStyleSheet("QWidget#app_content { background: #0f1117; }")
        self._content_lay = QVBoxLayout(self._content)
        self._content_lay.setContentsMargins(0, 0, 0, 0)
        self._content_lay.setSpacing(0)
        outer.addWidget(self._content, 1)

        self.setCentralWidget(wrapper)

        # Apply persisted theme before showing any screen
        theme.apply_theme(QApplication.instance(), self.is_dark_mode_enabled())

        from ui.screen0_launcher import Screen0Launcher
        self.show_screen(Screen0Launcher)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def closeEvent(self, event: QCloseEvent) -> None:
        """Guard against closing while a background operation is running."""
        if self._is_app_busy():
            import ui.popups.msgbox as msgbox
            if not msgbox.warning_question(
                self,
                "Operation in Progress",
                "A background operation is still running.<br><br>"
                "Closing the app now may corrupt your data. Are you sure you want to exit?",
                confirm_label="Exit Anyway",
            ):
                event.ignore()
                return
        event.accept()

    def _is_app_busy(self) -> bool:
        """Return True if the active screen or its active sub-view is busy."""
        screen = self._current_screen
        if screen is None:
            return False
        if hasattr(screen, "is_busy") and screen.is_busy():
            return True
        # Screen3 hosts a sub-view — check it too
        if hasattr(screen, "_active_view"):
            view = screen._active_view
            if view is not None and hasattr(view, "is_busy") and view.is_busy():
                return True
        return False

    def show_screen(self, screen_class, **kwargs) -> None:
        """Swap the active screen inside the content area."""
        # Hide the outgoing screen immediately to prevent a visual flash while
        # the new screen is constructed and before deleteLater fires.
        if self._current_screen is not None:
            self._current_screen.setVisible(False)
            if hasattr(self._current_screen, "abandon_workers"):
                self._current_screen.abandon_workers()

        new_screen = screen_class(app=self, **kwargs)

        while self._content_lay.count():
            item = self._content_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._content_lay.addWidget(new_screen)
        self._current_screen = new_screen

    # ------------------------------------------------------------------
    # Project state
    # ------------------------------------------------------------------

    def set_current_project(self, project_state: dict) -> None:
        self._current_project = project_state
        # Runtime-only cache: not persisted, reset when a new project is opened
        self._current_project.setdefault("_validation_cache", {})

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
        """Return saved dark-mode preference (defaults to True)."""
        return bool(self._read_app_config().get("dark_mode", True))

    def set_dark_mode(self, dark: bool) -> None:
        """Persist the dark-mode preference and immediately swap the stylesheet."""
        config = self._read_app_config()
        config["dark_mode"] = dark
        self._write_app_config(config)
        theme.apply_theme(QApplication.instance(), dark)

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

    def get_default_storage_format(self) -> str:
        """Return the default storage format for new projects (from app_config.json)."""
        return self._read_app_config().get("default_storage_format", "parquet")
