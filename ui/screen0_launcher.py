from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.mapping_manager import get_mappings
from core.project_manager import create_project, open_project
from ui.workers import LoadingOverlay, ScreenBase, Worker, clear_layout, make_scroll_area

_SIDEBAR_W = 340


class Screen0Launcher(ScreenBase):
    """Project launcher — left sidebar project list, right action panel."""

    def __init__(self, app, **kwargs):
        super().__init__()
        self.app = app
        self._selected_path: str | None = None
        self._selected_card: QFrame | None = None
        self._selected_labels: list[QLabel] = []

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- Sidebar ---
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(_SIDEBAR_W)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 20, 16, 16)
        sb_layout.setSpacing(8)

        title = QLabel("Projects")
        title.setFont(theme.font(14, "bold"))
        title.setStyleSheet("color: #f1f5f9;")
        sb_layout.addWidget(title)

        scroll, self._list_container, self._list_layout = make_scroll_area()
        self._list_layout.setSpacing(4)
        sb_layout.addWidget(scroll, 1)
        root.addWidget(sidebar)

        # --- Content ---
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignCenter)

        inner = QWidget()
        inner.setFixedWidth(320)
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(0)

        co_lbl = QLabel(theme.company_name())
        co_lbl.setFont(theme.font(30, "bold"))
        co_lbl.setStyleSheet("color: #3b82f6;")
        inner_layout.addWidget(co_lbl)
        inner_layout.addSpacing(8)

        subtitle = QLabel("Select a project or create a new one.")
        subtitle.setFont(theme.font(13))
        subtitle.setStyleSheet("color: #94a3b8;")
        inner_layout.addWidget(subtitle)
        inner_layout.addSpacing(32)

        hint = QLabel(
            "How to use: Select a project on the left, then Open Selected. "
            "Use New Project to create a fresh workspace."
        )
        hint.setFont(theme.font(11))
        hint.setStyleSheet("color: #475569;")
        hint.setWordWrap(True)
        inner_layout.addWidget(hint)
        inner_layout.addSpacing(24)

        new_btn = QPushButton("+ New Project")
        new_btn.setObjectName("btn_primary")
        new_btn.setFixedHeight(46)
        new_btn.setFont(theme.font(14, "bold"))
        new_btn.clicked.connect(self._on_new_click)
        inner_layout.addWidget(new_btn)
        inner_layout.addSpacing(8)

        self._open_btn = QPushButton("Open Selected")
        self._open_btn.setObjectName("btn_outline")
        self._open_btn.setFixedHeight(46)
        self._open_btn.setFont(theme.font(14))
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._on_open_click)
        inner_layout.addWidget(self._open_btn)
        inner_layout.addSpacing(8)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setObjectName("btn_danger")
        self._delete_btn.setFixedHeight(42)
        self._delete_btn.setFont(theme.font(13))
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_click)
        inner_layout.addWidget(self._delete_btn)

        content_layout.addWidget(inner)
        root.addWidget(content, 1)

        self._setup_overlay("Working...")
        self._load_and_render_projects()

    # ------------------------------------------------------------------
    # Project list
    # ------------------------------------------------------------------

    def _load_and_render_projects(self) -> None:
        clear_layout(self._list_layout)
        self._selected_path = None
        self._selected_card = None
        self._selected_labels = []
        self._open_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)

        paths = self.app.get_known_projects()
        loaded = []
        for p in paths:
            try:
                loaded.append(open_project(Path(p)))
            except (FileNotFoundError, ValueError):
                continue

        if not loaded:
            lbl = QLabel("No projects yet.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; padding: 12px 8px;")
            self._list_layout.addWidget(lbl)
            return

        for state in loaded:
            self._list_layout.addWidget(self._make_project_card(state))

    def _make_project_card(self, state: dict) -> QFrame:
        path = state.get("project_path", "")

        card = QFrame()
        card.setStyleSheet("QFrame { background: transparent; border-radius: 6px; }")
        card.setCursor(Qt.PointingHandCursor)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(2)

        name_lbl = QLabel(state.get("project_name", "Untitled"))
        name_lbl.setFont(theme.font(13, "bold"))
        name_lbl.setStyleSheet("color: #94a3b8;")
        card_layout.addWidget(name_lbl)

        company_lbl = QLabel(state.get("company", ""))
        company_lbl.setFont(theme.font(11))
        company_lbl.setStyleSheet("color: #94a3b8;")
        card_layout.addWidget(company_lbl)

        labels = [name_lbl, company_lbl]

        def _click(event=None, p=path, c=card, lbls=labels):
            self._select_card(p, c, lbls)

        card.mousePressEvent = _click
        name_lbl.mousePressEvent = _click
        company_lbl.mousePressEvent = _click

        return card

    def _select_card(self, path: str, card: QFrame, labels: list) -> None:
        if self._selected_card:
            self._selected_card.setStyleSheet(
                "QFrame { background: transparent; border-radius: 6px; }"
            )
            for lbl in self._selected_labels:
                lbl.setStyleSheet("color: #94a3b8;")

        card.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.12); border-radius: 6px; }"
        )
        for lbl in labels:
            lbl.setStyleSheet("color: #3b82f6;")

        self._selected_path = path
        self._selected_card = card
        self._selected_labels = labels
        self._open_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_open_click(self) -> None:
        if not self._selected_path:
            return
        try:
            state = open_project(Path(self._selected_path))
            self.app.set_current_project(state)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open project:\n{exc}")
            return

        project_path = Path(state["project_path"])
        try:
            mappings = get_mappings(project_path)
        except Exception:
            mappings = []

        tx_tables = list(state.get("transaction_tables", []))
        dim_tables = list(state.get("dim_tables", []))

        if not tx_tables or not dim_tables:
            target = "screen1"
        elif not mappings:
            target = "screen2"
        else:
            target = "screen3"

        try:
            if target == "screen1":
                from ui.screen1_sources import Screen1Sources
                self.app.show_screen(Screen1Sources, project=state)
            elif target == "screen2":
                from ui.screen2_mappings import Screen2Mappings
                self.app.show_screen(Screen2Mappings, project=state)
            else:
                from ui.screen3_main import Screen3Main
                self.app.show_screen(Screen3Main, project=state)
        except ImportError as exc:
            QMessageBox.critical(self, "Navigation Error", str(exc))

    def _on_new_click(self) -> None:
        dialog = NewProjectDialog(self, self.app)
        dialog.exec()
        if dialog.created_state:
            self._after_project_created(dialog.created_state)

    def _on_delete_click(self) -> None:
        if not self._selected_path:
            return
        project_path = Path(self._selected_path)
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete project '{project_path.name}'?\n\n"
            "This will permanently delete the workspace folder and all project data.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        try:
            if project_path.exists():
                shutil.rmtree(project_path)
            self.app.unregister_project(str(project_path))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not delete project:\n{exc}")
            return
        self._load_and_render_projects()

    def _after_project_created(self, project_state: dict) -> None:
        self.app.set_current_project(project_state)
        self.app.register_project(project_state["project_path"])
        try:
            from ui.screen1_sources import Screen1Sources
            self.app.show_screen(Screen1Sources, project=project_state)
        except ImportError:
            self._load_and_render_projects()


# ---------------------------------------------------------------------------
# New Project Dialog
# ---------------------------------------------------------------------------

class NewProjectDialog(QDialog):
    """Modal dialog for creating a new project workspace."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.created_state: dict | None = None
        self._workers: list[Worker] = []
        self._loading_count = 0

        self.setWindowTitle("New Project")
        self.setFixedSize(520, 440)
        self.setModal(True)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(68)
        header.setStyleSheet("QFrame { background-color: #3b82f6; }")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(28, 0, 20, 0)
        h_layout.setSpacing(12)

        title_lbl = QLabel("New Project")
        title_lbl.setFont(theme.font(20, "bold"))
        title_lbl.setStyleSheet("color: white;")
        h_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Fill in the details below to create a new workspace.")
        sub_lbl.setFont(theme.font(11))
        sub_lbl.setStyleSheet("color: rgba(255,255,255,0.8);")
        h_layout.addWidget(sub_lbl)
        h_layout.addStretch()
        outer.addWidget(header)

        # Body
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 0, 24, 0)
        body_layout.setSpacing(4)

        def field_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setFont(theme.font(12, "bold"))
            lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            return lbl

        def entry(placeholder: str) -> QLineEdit:
            e = QLineEdit()
            e.setPlaceholderText(placeholder)
            e.setFixedHeight(38)
            return e

        body_layout.addSpacing(18)
        body_layout.addWidget(field_label("Project Name"))
        body_layout.addSpacing(4)
        self._name_entry = entry("e.g. Sales Module")
        body_layout.addWidget(self._name_entry)

        body_layout.addSpacing(10)
        body_layout.addWidget(field_label("Company Name"))
        body_layout.addSpacing(4)
        self._company_entry = entry("e.g. Acme Corp")
        body_layout.addWidget(self._company_entry)

        body_layout.addSpacing(10)
        body_layout.addWidget(field_label("Save Location"))
        body_layout.addSpacing(4)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)
        self._folder_entry = QLineEdit()
        self._folder_entry.setPlaceholderText("Choose a folder...")
        self._folder_entry.setFixedHeight(38)
        path_row.addWidget(self._folder_entry, 1)

        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("btn_primary")
        browse_btn.setFixedSize(90, 38)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        body_layout.addLayout(path_row)
        body_layout.addStretch()
        outer.addWidget(body, 1)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(68)
        footer.setStyleSheet("QFrame { background-color: #0f1117; }")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(28, 0, 24, 0)
        f_layout.setSpacing(8)

        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(11))
        self._error_lbl.setStyleSheet("color: #f87171; background: transparent;")
        f_layout.addWidget(self._error_lbl, 1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_outline")
        cancel_btn.setFixedSize(100, 38)
        cancel_btn.clicked.connect(self.reject)
        f_layout.addWidget(cancel_btn)

        create_btn = QPushButton("Create Project")
        create_btn.setObjectName("btn_primary")
        create_btn.setFixedSize(140, 38)
        create_btn.clicked.connect(self._on_create)
        f_layout.addWidget(create_btn)
        outer.addWidget(footer)

        self._overlay = LoadingOverlay(self, "Creating project...")

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose save location")
        if folder:
            self._folder_entry.setText(folder)

    def _on_create(self) -> None:
        name = self._name_entry.text().strip()
        company = self._company_entry.text().strip()
        folder = self._folder_entry.text().strip()

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

        def worker():
            project_path = create_project(name, company, Path(folder))
            return open_project(project_path)

        self._loading_count += 1
        if self._loading_count == 1:
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_()
            self._overlay.show()

        w = Worker(worker)
        self._workers.append(w)

        def _done(state):
            if w in self._workers:
                self._workers.remove(w)
            self._loading_count = max(0, self._loading_count - 1)
            if self._loading_count == 0:
                self._overlay.hide()
            self.created_state = state
            self.accept()

        def _fail(exc):
            if w in self._workers:
                self._workers.remove(w)
            self._loading_count = max(0, self._loading_count - 1)
            if self._loading_count == 0:
                self._overlay.hide()
            self._show_error(f"Could not create project: {exc}")

        w.finished.connect(_done)
        w.errored.connect(_fail)
        w.start()

    def _show_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._overlay and self._overlay.isVisible():
            self._overlay.setGeometry(self.rect())
