from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
import ui.popups.msgbox as msgbox
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


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color: #475569; font-size: 11px; font-weight: 600; "
        "background: transparent; border: none;"
    )
    return lbl


def _field_input(value: str = "", placeholder: str = "", readonly: bool = False) -> QLineEdit:
    e = QLineEdit()
    e.setText(value)
    e.setPlaceholderText(placeholder)
    e.setFixedHeight(38)
    if readonly:
        e.setEnabled(False)
        e.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; "
            "color: #64748b; font-size: 13px; padding: 0 12px; }"
        )
    else:
        e.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; "
            "color: #64748b; font-size: 13px; padding: 0 12px; }"
            "QLineEdit:focus { border-color: rgba(59,130,246,0.5); }"
        )
    return e


class ViewSettings(ScreenBase):
    """Project settings view."""

    def __init__(self, parent, project: dict, on_project_changed):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Topbar ───────────────────────────────────────────────────────
        topbar = QFrame()
        topbar.setFixedHeight(64)
        topbar.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(28, 0, 28, 0)

        tb_text = QVBoxLayout()
        tb_text.setSpacing(2)
        title_lbl = QLabel("Settings")
        title_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 15px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel(
            "Update project details and history preference, then save to apply changes."
        )
        meta_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: transparent; border: none;"
        )
        tb_text.addWidget(title_lbl)
        tb_text.addWidget(meta_lbl)
        tb_lay.addLayout(tb_text, 1)
        outer.addWidget(topbar)

        # ── Settings body (scrollable) ────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #0f1117; border: none; }")

        body = QWidget()
        body.setStyleSheet("background: #0f1117;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(28, 28, 28, 28)
        body_lay.setSpacing(0)
        body_lay.setAlignment(Qt.AlignTop)

        # Form constrained to max 520px width
        form_wrap = QWidget()
        form_wrap.setFixedWidth(620)
        form_wrap.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form_wrap)
        form_lay.setContentsMargins(0, 0, 0, 0)
        form_lay.setSpacing(0)

        # Project Name
        form_lay.addWidget(_field_label("PROJECT NAME"))
        form_lay.addSpacing(8)
        self._name_entry = _field_input(
            value=str(project.get("project_name", "")),
            placeholder="Enter project name"
        )
        form_lay.addWidget(self._name_entry)
        form_lay.addSpacing(20)

        # Company Name
        form_lay.addWidget(_field_label("COMPANY NAME"))
        form_lay.addSpacing(8)
        self._company_entry = _field_input(
            value=str(project.get("company", "")),
            placeholder="Enter company name"
        )
        form_lay.addWidget(self._company_entry)
        form_lay.addSpacing(20)

        # Project Path (readonly)
        form_lay.addWidget(_field_label("PROJECT FOLDER PATH"))
        form_lay.addSpacing(8)
        self._path_entry = _field_input(
            value=str(project.get("project_path", "")),
            readonly=True
        )
        form_lay.addWidget(self._path_entry)
        form_lay.addSpacing(20)

        # Divider
        div = QFrame()
        div.setFixedHeight(1)
        div.setStyleSheet("background: rgba(255,255,255,0.06); border: none;")
        form_lay.addWidget(div)
        form_lay.addSpacing(20)

        # History toggle row
        history_enabled = bool(project.get("settings", {}).get("history_enabled", True))
        toggle_row = QHBoxLayout()
        toggle_row.setSpacing(12)

        hist_text = QVBoxLayout()
        hist_text.setSpacing(3)
        hist_title = QLabel("Enable History")
        hist_title.setStyleSheet(
            "color: #94a3b8; font-size: 13px; background: transparent; border: none;"
        )
        hist_sub = QLabel(
            "When enabled, a snapshot is created after each table update or revert."
        )
        hist_sub.setStyleSheet(
            "color: #475569; font-size: 11px; background: transparent; border: none;"
        )
        hist_text.addWidget(hist_title)
        hist_text.addWidget(hist_sub)
        toggle_row.addLayout(hist_text, 1)

        self._history_check = QCheckBox()
        self._history_check.setChecked(history_enabled)
        self._history_check.setStyleSheet(
            "QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; "
            "border: 1.5px solid rgba(255,255,255,0.15); background: rgba(255,255,255,0.04); }"
            "QCheckBox::indicator:checked { background: #3b82f6; border-color: #3b82f6; }"
        )
        toggle_row.addWidget(self._history_check, 0, Qt.AlignVCenter)
        form_lay.addLayout(toggle_row)

        body_lay.addWidget(form_wrap)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        # ── Settings footer ───────────────────────────────────────────────
        footer = QFrame()
        footer.setFixedHeight(52)
        footer.setStyleSheet(
            "QFrame { background: #13161e; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        ft_lay = QHBoxLayout(footer)
        ft_lay.setContentsMargins(28, 0, 28, 0)
        ft_lay.setSpacing(10)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            "color: #f87171; font-size: 11px; background: transparent; border: none;"
        )
        ft_lay.addWidget(self._error_lbl, 1)

        save_btn = QPushButton("Save Changes")
        save_btn.setFixedHeight(34)
        save_btn.setFixedWidth(120)
        save_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; border: none; border-radius: 7px; "
            "color: white; font-size: 12px; font-weight: 500; }"
            "QPushButton:hover { background: #2563eb; }"
            "QPushButton:pressed { background: #1d4ed8; }"
        )
        save_btn.clicked.connect(self._on_save)
        ft_lay.addWidget(save_btn)
        outer.addWidget(footer)

        self._setup_overlay("Saving settings...")

    # ------------------------------------------------------------------

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
            reply = msgbox.question(
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
            msgbox.information(self, "Saved", "Settings saved successfully.")
            self.on_project_changed(target_key="settings")

        self._run_background(worker, on_success,
                             lambda exc: msgbox.critical(
                                 self, "Error", f"Could not save settings:\n{exc}"
                             ))
