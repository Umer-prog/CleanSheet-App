from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.snapshot_manager import list_manifests, revert_to_manifest, update_manifest_label
from ui.workers import ScreenBase, clear_layout, make_scroll_area


def manifest_title(manifest: dict) -> str:
    mid = str(manifest.get("manifest_id", "")).strip()
    created = str(manifest.get("created_at", "")).strip()
    return f"{mid} | {created}"


def manifest_tables_text(manifest: dict) -> str:
    tables = manifest.get("tables", {})
    if not tables:
        return "(No tables)"
    return "\n".join(f"{name} → {filename}" for name, filename in tables.items())


class ViewHistory(ScreenBase):
    """History list and revert view."""

    def __init__(self, parent, project: dict, on_project_changed):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self._selected_manifest: dict | None = None
        self._selected_row_frame: QFrame | None = None
        self._manifests: list[dict] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 18)
        outer.setSpacing(8)

        # Header
        hdr = QHBoxLayout()
        title = QLabel("History / Revert")
        title.setFont(theme.font(22, "bold"))
        title.setStyleSheet("color: #f1f5f9;")
        hdr.addWidget(title, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("btn_primary")
        refresh_btn.setFixedSize(100, 38)
        refresh_btn.clicked.connect(self._load_manifests)
        hdr.addWidget(refresh_btn)
        outer.addLayout(hdr)

        hint = QLabel(
            "How to use: Select a manifest to inspect details, edit label if needed, "
            "then revert to restore that version."
        )
        hint.setFont(theme.font(11))
        hint.setStyleSheet("color: #475569;")
        hint.setWordWrap(True)
        outer.addWidget(hint)

        # Body — left list | right detail
        body = QHBoxLayout()
        body.setSpacing(12)

        # Left: manifest list
        left_card = QFrame()
        left_card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        left_layout = QVBoxLayout(left_card)
        left_layout.setContentsMargins(12, 10, 12, 10)
        left_layout.setSpacing(6)

        left_title = QLabel("Manifests")
        left_title.setFont(theme.font(13, "bold"))
        left_title.setStyleSheet("color: #f1f5f9; background: transparent;")
        left_layout.addWidget(left_title)

        self._list_scroll, _, self._list_layout = make_scroll_area()
        self._list_layout.setContentsMargins(4, 4, 4, 4)
        self._list_layout.setSpacing(4)
        left_layout.addWidget(self._list_scroll, 1)
        body.addWidget(left_card, 1)

        # Right: detail panel
        right_card = QFrame()
        right_card.setStyleSheet("QFrame { background-color: #13161e; border-radius: 10px; }")
        right_layout = QVBoxLayout(right_card)
        right_layout.setContentsMargins(12, 10, 12, 10)
        right_layout.setSpacing(6)

        right_title = QLabel("Manifest Details")
        right_title.setFont(theme.font(13, "bold"))
        right_title.setStyleSheet("color: #f1f5f9; background: transparent;")
        right_layout.addWidget(right_title)

        self._detail_title = QLabel("Select a manifest")
        self._detail_title.setFont(theme.font(12, "bold"))
        self._detail_title.setStyleSheet("color: #f1f5f9; background: transparent;")
        right_layout.addWidget(self._detail_title)

        self._detail_box = QTextEdit()
        self._detail_box.setReadOnly(True)
        self._detail_box.setStyleSheet(
            "QTextEdit { background-color: #0f1117; color: #94a3b8; border-radius: 6px; }"
        )
        right_layout.addWidget(self._detail_box, 1)

        # Label edit row
        label_row = QHBoxLayout()
        label_row.setSpacing(8)
        self._label_entry = QLineEdit()
        self._label_entry.setPlaceholderText("Label")
        self._label_entry.setFixedHeight(36)
        label_row.addWidget(self._label_entry, 1)

        save_label_btn = QPushButton("Save Label")
        save_label_btn.setObjectName("btn_outline")
        save_label_btn.setFixedSize(110, 36)
        save_label_btn.clicked.connect(self._save_label)
        label_row.addWidget(save_label_btn)
        right_layout.addLayout(label_row)

        # Footer
        footer_row = QHBoxLayout()
        self._error_lbl = QLabel("")
        self._error_lbl.setFont(theme.font(11))
        self._error_lbl.setStyleSheet("color: #f87171; background: transparent;")
        footer_row.addWidget(self._error_lbl, 1)

        self._revert_btn = QPushButton("Revert To This Version")
        self._revert_btn.setObjectName("btn_primary")
        self._revert_btn.setFixedSize(180, 38)
        self._revert_btn.setEnabled(False)
        self._revert_btn.clicked.connect(self._confirm_revert)
        footer_row.addWidget(self._revert_btn)
        right_layout.addLayout(footer_row)

        body.addWidget(right_card, 1)
        outer.addLayout(body, 1)

        self._setup_overlay("Loading history...")
        self._load_manifests()

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    # ------------------------------------------------------------------

    def _load_manifests(self) -> None:
        self._set_error("")
        self._selected_manifest = None
        self._selected_row_frame = None
        self._revert_btn.setEnabled(False)
        self._label_entry.clear()
        self._detail_title.setText("Select a manifest")
        self._detail_box.clear()

        clear_layout(self._list_layout)

        history_enabled = bool(self.project.get("settings", {}).get("history_enabled", True))
        if not history_enabled:
            lbl = QLabel("History is OFF in settings.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self._list_layout.addWidget(lbl)
            return

        def worker():
            return list_manifests(self.project_path)

        def on_success(manifests):
            self._manifests = manifests
            self._render_manifest_rows()

        self._run_background(worker, on_success,
                             lambda exc: self._set_error(f"Could not load manifests: {exc}"))

    def _render_manifest_rows(self) -> None:
        if not self._manifests:
            lbl = QLabel("No manifests available.")
            lbl.setFont(theme.font(12))
            lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            self._list_layout.addWidget(lbl)
            return

        for manifest in self._manifests:
            row = QFrame()
            row.setStyleSheet("QFrame { background-color: #0f1117; border-radius: 8px; }")
            row.setCursor(
                __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.PointingHandCursor
            )
            row_layout = QVBoxLayout(row)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(2)

            title = manifest_title(manifest)
            label_text = str(manifest.get("label", "")).strip() or "(no label)"

            title_lbl = QLabel(title)
            title_lbl.setFont(theme.font(12, "bold"))
            title_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
            row_layout.addWidget(title_lbl)

            label_lbl = QLabel(label_text)
            label_lbl.setFont(theme.font(11))
            label_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
            row_layout.addWidget(label_lbl)

            def _click(event=None, m=manifest, frame=row):
                self._select_manifest(m, frame)

            row.mousePressEvent = _click
            title_lbl.mousePressEvent = _click
            label_lbl.mousePressEvent = _click

            self._list_layout.addWidget(row)

    def _select_manifest(self, manifest: dict, frame: QFrame) -> None:
        if self._selected_row_frame:
            self._selected_row_frame.setStyleSheet(
                "QFrame { background-color: #0f1117; border-radius: 8px; }"
            )
            for lbl in self._selected_row_frame.findChildren(QLabel):
                lbl.setStyleSheet("color: #f1f5f9; background: transparent;" if
                                  lbl.font().bold() else "color: #94a3b8; background: transparent;")

        self._selected_manifest = manifest
        self._selected_row_frame = frame
        frame.setStyleSheet("QFrame { background-color: #3b82f6; border-radius: 8px; }")
        for lbl in frame.findChildren(QLabel):
            lbl.setStyleSheet("color: white; background: transparent;")

        self._revert_btn.setEnabled(True)
        self._label_entry.setText(str(manifest.get("label", "")))
        self._detail_title.setText(manifest_title(manifest))
        self._detail_box.setPlainText(manifest_tables_text(manifest))

    def _save_label(self) -> None:
        if not self._selected_manifest:
            self._set_error("Select a manifest first.")
            return
        new_label = self._label_entry.text().strip()
        manifest_id = self._selected_manifest["manifest_id"]

        def worker():
            update_manifest_label(self.project_path, manifest_id, new_label)

        self._run_background(worker,
                             lambda _: self.on_project_changed(target_key="history"),
                             lambda exc: self._set_error(f"Could not update label: {exc}"))

    def _confirm_revert(self) -> None:
        if not self._selected_manifest:
            self._set_error("Select a manifest first.")
            return
        manifest_id = self._selected_manifest["manifest_id"]

        from ui.popups.popup_revert_confirm import PopupRevertConfirm

        def do_revert():
            def worker():
                revert_to_manifest(self.project_path, manifest_id)

            self._run_background(
                worker,
                lambda _: (
                    QMessageBox.information(self, "Reverted", f"Reverted to {manifest_id}."),
                    self.on_project_changed(target_key="history"),
                ),
                lambda exc: QMessageBox.critical(
                    self, "Error", f"Could not revert:\n{exc}"
                ),
            )

        dlg = PopupRevertConfirm(self, manifest_id=manifest_id, on_confirm=do_revert)
        dlg.exec()
