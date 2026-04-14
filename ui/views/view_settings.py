from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.project_manager import save_project_json, save_settings_json
from ui.workers import ScreenBase


def merged_project_payload(project: dict, project_name: str, company: str) -> dict:
    return {
        "project_name": project_name,
        "created_at": project.get("created_at", ""),
        "company": company,
        "transaction_tables": list(project.get("transaction_tables", [])),
        "dim_tables": list(project.get("dim_tables", [])),
    }


def merged_settings_payload(project: dict, history_enabled: bool) -> dict:
    base = dict(project.get("settings", {}))
    base["history_enabled"] = bool(history_enabled)
    base["project_path"] = str(project.get("project_path", ""))
    return base


class ViewSettings(ScreenBase):
    """Project settings view."""

    def __init__(self, parent, project: dict, on_project_changed):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 18)
        outer.setSpacing(8)

        # Header
        title = QLabel("Settings")
        title.setFont(theme.font(22, "bold"))
        title.setStyleSheet("color: #f1f5f9;")
        outer.addWidget(title)

        hint = QLabel(
            "How to use: Update project details and history preference, "
            "then click Save to apply changes."
        )
        hint.setFont(theme.font(11))
        hint.setStyleSheet("color: #475569;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # Form card
        card = QFrame()
        card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 14, 18, 14)
        card_layout.setSpacing(6)

        def field_label(text: str) -> QLabel:
            lbl = QLabel(text)
            lbl.setFont(theme.font(12, "bold"))
            lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            return lbl

        card_layout.addWidget(field_label("Project Name"))
        self._name_entry = QLineEdit()
        self._name_entry.setText(str(project.get("project_name", "")))
        self._name_entry.setFixedHeight(38)
        card_layout.addWidget(self._name_entry)
        card_layout.addSpacing(6)

        card_layout.addWidget(field_label("Company Name"))
        self._company_entry = QLineEdit()
        self._company_entry.setText(str(project.get("company", "")))
        self._company_entry.setFixedHeight(38)
        card_layout.addWidget(self._company_entry)
        card_layout.addSpacing(6)

        card_layout.addWidget(field_label("Project Folder Path (read-only)"))
        self._path_entry = QLineEdit()
        self._path_entry.setText(str(project.get("project_path", "")))
        self._path_entry.setFixedHeight(38)
        self._path_entry.setEnabled(False)
        card_layout.addWidget(self._path_entry)
        card_layout.addSpacing(10)

        history_enabled = bool(project.get("settings", {}).get("history_enabled", True))
        self._history_check = QCheckBox("History Enabled")
        self._history_check.setFont(theme.font(13))
        self._history_check.setChecked(history_enabled)
        card_layout.addWidget(self._history_check)
        card_layout.addSpacing(10)

        # Footer inside card
        footer_row = QHBoxLayout()
        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(11))
        self._error_lbl.setStyleSheet("color: #f87171; background: transparent;")
        footer_row.addWidget(self._error_lbl, 1)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("btn_primary")
        save_btn.setFixedSize(120, 38)
        save_btn.clicked.connect(self._on_save)
        footer_row.addWidget(save_btn)
        card_layout.addLayout(footer_row)

        outer.addWidget(card, 1)

        self._setup_overlay("Saving settings...")

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def _on_save(self) -> None:
        self._set_error("")
        project_name = self._name_entry.text().strip()
        company = self._company_entry.text().strip()
        history_enabled = self._history_check.isChecked()

        if not project_name:
            self._set_error("Project name is required.")
            return
        if not company:
            self._set_error("Company name is required.")
            return

        prev_history = bool(self.project.get("settings", {}).get("history_enabled", True))
        if prev_history and not history_enabled:
            reply = QMessageBox.question(
                self, "History Off Warning",
                "Existing history will be kept but no new snapshots will be created. Continue?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                self._history_check.setChecked(True)
                return

        def worker():
            save_project_json(
                self.project_path,
                merged_project_payload(self.project, project_name, company),
            )
            save_settings_json(
                self.project_path,
                merged_settings_payload(self.project, history_enabled),
            )

        def on_success(_):
            QMessageBox.information(self, "Saved", "Settings saved successfully.")
            self.on_project_changed(target_key="settings")

        self._run_background(worker, on_success,
                             lambda exc: QMessageBox.critical(
                                 self, "Error", f"Could not save settings:\n{exc}"
                             ))
