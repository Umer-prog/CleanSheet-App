from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
import ui.popups.msgbox as msgbox
from core.app_logger import get_log_file_path
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
        "color: #cbd5e1; font-size: 11px; font-weight: 600; "
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
            "color: #94a3b8; font-size: 13px; padding: 0 12px; }"
        )
    else:
        e.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.05); "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; "
            "color: #f1f5f9; font-size: 13px; padding: 0 12px; }"
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
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
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
            "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
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

        form_lay.addSpacing(20)

        # Divider
        div2 = QFrame()
        div2.setFixedHeight(1)
        div2.setStyleSheet("background: rgba(255,255,255,0.06); border: none;")
        form_lay.addWidget(div2)
        form_lay.addSpacing(20)

        # Log file location row
        form_lay.addWidget(_field_label("LOG FILE LOCATION"))
        form_lay.addSpacing(8)
        log_path = get_log_file_path()
        log_path_str = str(log_path) if log_path else "Logging not initialised"
        log_row = QHBoxLayout()
        log_row.setSpacing(8)
        log_path_entry = _field_input(value=log_path_str, readonly=True)
        log_row.addWidget(log_path_entry, 1)
        open_log_btn = QPushButton("Open Folder")
        open_log_btn.setFixedHeight(38)
        open_log_btn.setFixedWidth(100)
        open_log_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.12); "
            "border-radius: 8px; color: #94a3b8; font-size: 11px; font-weight: 500; }"
            "QPushButton:hover { border-color: rgba(255,255,255,0.25); color: #f1f5f9; }"
        )
        if log_path:
            open_log_btn.clicked.connect(lambda: subprocess.Popen(
                ["explorer", "/select,", str(log_path)]
            ))
        else:
            open_log_btn.setEnabled(False)
        log_row.addWidget(open_log_btn)
        form_lay.addLayout(log_row)

        form_lay.addSpacing(20)

        div3 = QFrame()
        div3.setFixedHeight(1)
        div3.setStyleSheet("background: rgba(255,255,255,0.06); border: none;")
        form_lay.addWidget(div3)
        form_lay.addSpacing(20)

        # Final file location row
        form_lay.addWidget(_field_label("FINAL FILE LOCATION"))
        form_lay.addSpacing(8)
        final_path = self.project_path / "final" / "final_updated.xlsx"
        final_row = QHBoxLayout()
        final_row.setSpacing(8)
        final_path_entry = _field_input(value=str(final_path), readonly=True)
        final_row.addWidget(final_path_entry, 1)
        open_final_btn = QPushButton("Open Folder")
        open_final_btn.setFixedHeight(38)
        open_final_btn.setFixedWidth(100)
        open_final_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.12); "
            "border-radius: 8px; color: #94a3b8; font-size: 11px; font-weight: 500; }"
            "QPushButton:hover { border-color: rgba(255,255,255,0.25); color: #f1f5f9; }"
        )

        def _open_final_folder(p=final_path):
            if p.exists():
                subprocess.Popen(["explorer", "/select,", str(p)])
            else:
                folder = p.parent
                folder.mkdir(parents=True, exist_ok=True)
                subprocess.Popen(["explorer", str(folder)])

        open_final_btn.clicked.connect(lambda: _open_final_folder())
        final_row.addWidget(open_final_btn)
        form_lay.addLayout(final_row)

        form_lay.addSpacing(20)

        div4 = QFrame()
        div4.setFixedHeight(1)
        div4.setStyleSheet("background: rgba(255,255,255,0.06); border: none;")
        form_lay.addWidget(div4)
        form_lay.addSpacing(20)

        # License info section
        form_lay.addWidget(_field_label("LICENSE"))
        form_lay.addSpacing(8)
        lic_card = QFrame()
        lic_card.setStyleSheet(
            "QFrame { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.07); border-radius: 8px; }"
        )
        lic_lay = QVBoxLayout(lic_card)
        lic_lay.setContentsMargins(14, 12, 14, 12)
        lic_lay.setSpacing(6)

        try:
            from core.license_validator import validate_license, get_days_until_expiry
            _lic = validate_license()
            _days = get_days_until_expiry(_lic)
            if _lic.valid:
                _expiry_str = str(_lic.expiry_date) if _lic.expiry_date else "Unknown"
                _client = _lic.client_name or "Unknown"
                if _days <= 0:
                    _status_text = "Expired"
                    _status_color = "#f87171"
                    _badge_bg = "rgba(239,68,68,0.10)"
                    _badge_border = "rgba(239,68,68,0.25)"
                elif _days < 14:
                    _status_text = f"Expiring soon — {_days} day{'s' if _days != 1 else ''} left"
                    _status_color = "#fbbf24"
                    _badge_bg = "rgba(217,119,6,0.10)"
                    _badge_border = "rgba(217,119,6,0.25)"
                else:
                    _status_text = f"Active — {_days} day{'s' if _days != 1 else ''} remaining"
                    _status_color = "#34d399"
                    _badge_bg = "rgba(34,211,153,0.08)"
                    _badge_border = "rgba(34,211,153,0.20)"

                status_row = QHBoxLayout()
                status_row.setSpacing(10)
                status_dot = QLabel("●")
                status_dot.setStyleSheet(
                    f"color: {_status_color}; font-size: 11px; background: transparent; border: none;"
                )
                status_row.addWidget(status_dot)
                status_lbl = QLabel(_status_text)
                status_lbl.setStyleSheet(
                    f"color: {_status_color}; font-size: 12px; font-weight: 600; "
                    "background: transparent; border: none;"
                )
                status_row.addWidget(status_lbl)
                status_badge = QLabel("LICENSED")
                status_badge.setStyleSheet(
                    f"color: {_status_color}; background: {_badge_bg}; "
                    f"border: 1px solid {_badge_border}; border-radius: 4px; "
                    "font-size: 10px; font-weight: 600; padding: 1px 8px;"
                )
                status_row.addWidget(status_badge)
                status_row.addStretch()
                lic_lay.addLayout(status_row)

                client_lbl = QLabel(f"Licensed to:  {_client}")
                client_lbl.setStyleSheet(
                    "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
                )
                lic_lay.addWidget(client_lbl)

                expiry_lbl = QLabel(f"Expiry date:  {_expiry_str}")
                expiry_lbl.setStyleSheet(
                    "color: #94a3b8; font-size: 11px; background: transparent; border: none;"
                )
                lic_lay.addWidget(expiry_lbl)
            else:
                err_lbl = QLabel("No valid license found. Please contact support@gd365.com.")
                err_lbl.setStyleSheet(
                    "color: #f87171; font-size: 12px; background: transparent; border: none;"
                )
                lic_lay.addWidget(err_lbl)
        except Exception:
            err_lbl = QLabel("Unable to read license information.")
            err_lbl.setStyleSheet(
                "color: #94a3b8; font-size: 12px; background: transparent; border: none;"
            )
            lic_lay.addWidget(err_lbl)

        form_lay.addWidget(lic_card)

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

        about_btn = QPushButton("About")
        about_btn.setFixedHeight(34)
        about_btn.setFixedWidth(80)
        about_btn.setStyleSheet(
            "QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.12); "
            "border-radius: 7px; color: #94a3b8; font-size: 12px; font-weight: 500; }"
            "QPushButton:hover { border-color: rgba(255,255,255,0.25); color: #f1f5f9; }"
        )
        about_btn.clicked.connect(self._show_about)
        ft_lay.addWidget(about_btn)

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

    def _show_about(self) -> None:
        from ui.popups.popup_about import PopupAbout
        dlg = PopupAbout(self)
        dlg.exec()

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
            if not msgbox.warning_question(
                self, "Disable History Tracking?",
                "Turning off history will stop new snapshots from being created.<br><br>"
                "Your existing snapshots will be kept and you can re-enable history at any time.",
                confirm_label="Disable",
            ):
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
            msgbox.information(self, "Settings Saved", "Your project settings have been saved.")
            self.on_project_changed(target_key="settings")

        self._run_background(worker, on_success,
                             lambda exc: msgbox.critical(
                                 self, "Failed to Save Settings",
                                 f"Your settings could not be saved. Check that the project folder is accessible.\n\nDetail: {exc}"
                             ))
