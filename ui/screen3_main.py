from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.mapping_manager import get_mappings
from core.project_manager import open_project
from ui.screen2_mappings import Screen2Mappings

_NAV_WIDTH = 260


def mapping_nav_label(mapping: dict) -> str:
    tx = str(mapping.get("transaction_table", "")).strip() or "unknown_tx"
    dim = str(mapping.get("dim_table", "")).strip() or "unknown_dim"
    return f"{tx} → {dim}"


def build_nav_items(mappings: list[dict]) -> list[dict]:
    items: list[dict] = []
    for mapping in mappings:
        items.append({
            "kind": "mapping",
            "key": str(mapping.get("id", "")).strip() or mapping_nav_label(mapping),
            "label": mapping_nav_label(mapping),
            "mapping": mapping,
        })
    items.extend([
        {"kind": "separator", "key": "sep_sources"},
        {"kind": "view", "key": "t_sources", "label": "T Sources"},
        {"kind": "view", "key": "d_sources", "label": "D Sources"},
        {"kind": "separator", "key": "sep_misc"},
        {"kind": "view", "key": "history", "label": "History / Revert"},
        {"kind": "view", "key": "settings", "label": "Settings"},
    ])
    return items


class Screen3Main(QWidget):
    """Main workspace shell — left navbar and right content area."""

    def __init__(self, app, project: dict, initial_nav_key: str | None = None, **kwargs):
        super().__init__()
        self.app = app
        self.project = project
        self.project_path = Path(project["project_path"])
        self.initial_nav_key = initial_nav_key

        self._nav_buttons: dict[str, QPushButton] = {}
        self._active_nav_key: str | None = None
        self._active_view: QWidget | None = None

        self._mappings = self._load_mappings()
        self._nav_items = build_nav_items(self._mappings)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_navbar())

        self._content_host = QWidget()
        content_layout = QVBoxLayout(self._content_host)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        root.addWidget(self._content_host, 1)

        self._select_default_view()

    # ------------------------------------------------------------------

    def _load_mappings(self) -> list[dict]:
        try:
            return get_mappings(self.project_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not load mappings:\n{exc}")
            return []

    def _build_navbar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(_NAV_WIDTH)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Brand header
        header = QWidget()
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(18, 20, 18, 10)
        h_layout.setSpacing(2)

        ws_lbl = QLabel("Workspace")
        ws_lbl.setFont(theme.font(17, "bold"))
        ws_lbl.setStyleSheet("color: #f1f5f9;")
        h_layout.addWidget(ws_lbl)

        proj_lbl = QLabel(str(self.project.get("project_name", "Project")))
        proj_lbl.setFont(theme.font(11))
        proj_lbl.setStyleSheet("color: #94a3b8;")
        h_layout.addWidget(proj_lbl)
        layout.addWidget(header)

        # Back button
        back_btn = QPushButton("← Back To Launcher")
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.15); "
            "border-radius: 6px; color: #94a3b8; margin: 0 18px 12px 18px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.05); }"
        )
        back_btn.clicked.connect(self._go_to_launcher)
        layout.addWidget(back_btn)

        # Nav scroll
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(8, 0, 8, 8)
        nav_layout.setSpacing(2)
        nav_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(nav_container)
        layout.addWidget(scroll, 1)

        for item in self._nav_items:
            if item["kind"] == "separator":
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet("background: rgba(255,255,255,0.08); margin: 6px 10px;")
                nav_layout.addWidget(sep)
                continue

            key = item["key"]
            btn = QPushButton(item["label"])
            btn.setFixedHeight(38)
            btn.setStyleSheet(self._nav_btn_style(active=False))
            btn.clicked.connect(lambda _=False, it=item: self._on_nav_click(it))
            nav_layout.addWidget(btn)
            self._nav_buttons[key] = btn

        return sidebar

    @staticmethod
    def _nav_btn_style(active: bool) -> str:
        if active:
            return (
                "QPushButton { background: rgba(59,130,246,0.12); color: #3b82f6; "
                "border: none; border-radius: 6px; text-align: left; "
                "padding: 0 14px; font-size: 13px; }"
            )
        return (
            "QPushButton { background: transparent; color: #94a3b8; "
            "border: none; border-radius: 6px; text-align: left; "
            "padding: 0 14px; font-size: 13px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.04); }"
        )

    def _select_default_view(self) -> None:
        if self.initial_nav_key:
            for item in self._nav_items:
                if item.get("key") == self.initial_nav_key:
                    self._on_nav_click(item)
                    return

        first_mapping = next((i for i in self._nav_items if i["kind"] == "mapping"), None)
        if first_mapping:
            self._on_nav_click(first_mapping)
            return

        t_sources = next((i for i in self._nav_items if i.get("key") == "t_sources"), None)
        if t_sources:
            self._on_nav_click(t_sources)

    def _reload_from_disk(self, target_key: str | None = None) -> None:
        try:
            updated = open_project(self.project_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not refresh project:\n{exc}")
            return
        self.app.set_current_project(updated)
        self.app.show_screen(Screen3Main, project=updated, initial_nav_key=target_key)

    def _go_to_mapping_setup(self) -> None:
        try:
            updated = open_project(self.project_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not refresh project:\n{exc}")
            return
        self.app.set_current_project(updated)
        self.app.show_screen(Screen2Mappings, project=updated)

    def _go_to_launcher(self) -> None:
        from ui.screen0_launcher import Screen0Launcher
        self.app.show_screen(Screen0Launcher)

    def _on_nav_click(self, item: dict) -> None:
        self._set_active_nav(item["key"])
        self._show_item_view(item)

    def _set_active_nav(self, active_key: str) -> None:
        for key, btn in self._nav_buttons.items():
            btn.setStyleSheet(self._nav_btn_style(active=(key == active_key)))
        self._active_nav_key = active_key

    def _show_item_view(self, item: dict) -> None:
        if self._active_view is not None:
            self._active_view.setParent(None)
            self._active_view.deleteLater()

        layout = self._content_host.layout()

        if item["kind"] == "mapping":
            from ui.views.view_mapping import ViewMapping
            self._active_view = ViewMapping(
                self._content_host, project=self.project, mapping=item["mapping"]
            )
        elif item["key"] == "t_sources":
            from ui.views.view_t_sources import ViewTSources
            self._active_view = ViewTSources(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
                on_go_mapping_setup=self._go_to_mapping_setup,
            )
        elif item["key"] == "d_sources":
            from ui.views.view_d_sources import ViewDSources
            self._active_view = ViewDSources(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
                on_go_mapping_setup=self._go_to_mapping_setup,
            )
        elif item["key"] == "history":
            from ui.views.view_history import ViewHistory
            self._active_view = ViewHistory(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
            )
        else:
            from ui.views.view_settings import ViewSettings
            self._active_view = ViewSettings(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
            )

        layout.addWidget(self._active_view)
