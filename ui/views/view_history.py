from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
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


def _btn_ghost(text: str, height: int = 34) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setStyleSheet(
        "QPushButton { background: rgba(255,255,255,0.04); "
        "border: 1px solid rgba(255,255,255,0.09); border-radius: 7px; "
        "color: #94a3b8; font-size: 12px; padding: 0 14px; }"
        "QPushButton:hover { background: rgba(255,255,255,0.08); color: #cbd5e1; }"
        "QPushButton:disabled { opacity: 0.4; }"
    )
    return b


def _btn_revert(text: str, height: int = 34) -> QPushButton:
    b = QPushButton(text)
    b.setFixedHeight(height)
    b.setStyleSheet(
        "QPushButton { background: rgba(59,130,246,0.12); "
        "border: 1px solid rgba(59,130,246,0.25); border-radius: 7px; "
        "color: #60a5fa; font-size: 12px; padding: 0 14px; }"
        "QPushButton:hover { background: rgba(59,130,246,0.2); }"
        "QPushButton:disabled { opacity: 0.35; }"
    )
    return b


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
        tb_lay.setSpacing(16)

        tb_text = QVBoxLayout()
        tb_text.setSpacing(2)
        title_lbl = QLabel("History / Revert")
        title_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 15px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel(
            "Select a snapshot to inspect its details, edit the label, "
            "or revert the project to that version."
        )
        meta_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: transparent; border: none;"
        )
        tb_text.addWidget(title_lbl)
        tb_text.addWidget(meta_lbl)
        tb_lay.addLayout(tb_text, 1)

        refresh_btn = _btn_ghost("Refresh", height=34)
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self._load_manifests)
        tb_lay.addWidget(refresh_btn)
        outer.addWidget(topbar)

        # ── Split content ─────────────────────────────────────────────────
        split = QHBoxLayout()
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(0)

        # Left — snapshot list
        left = QFrame()
        left.setFixedWidth(340)
        left.setStyleSheet(
            "QFrame { background: #0f1117; border: none; "
            "border-right: 1px solid rgba(255,255,255,0.06); }"
        )
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        # Left header
        lh = QFrame()
        lh.setFixedHeight(44)
        lh.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        lh_lay = QHBoxLayout(lh)
        lh_lay.setContentsMargins(18, 0, 18, 0)
        lh_title = QLabel("SNAPSHOTS")
        lh_title.setStyleSheet(
            "color: #475569; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        lh_lay.addWidget(lh_title, 1)
        self._snap_count_lbl = QLabel("")
        self._snap_count_lbl.setFixedHeight(20)
        self._snap_count_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: rgba(255,255,255,13); "
            "border-radius: 10px; padding: 2px 8px; border: none;"
        )
        self._snap_count_lbl.setVisible(False)
        lh_lay.addWidget(self._snap_count_lbl)
        left_lay.addWidget(lh)

        # Left scroll
        self._list_scroll, _, self._list_layout = make_scroll_area()
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        left_lay.addWidget(self._list_scroll, 1)
        split.addWidget(left)

        # Right — detail panel
        right = QFrame()
        right.setStyleSheet("QFrame { background: #0f1117; border: none; }")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        # Right header
        rh = QFrame()
        rh.setFixedHeight(44)
        rh.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        rh_lay = QHBoxLayout(rh)
        rh_lay.setContentsMargins(18, 0, 18, 0)
        rh_title = QLabel("SNAPSHOT DETAILS")
        rh_title.setStyleSheet(
            "color: #475569; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        rh_lay.addWidget(rh_title)
        right_lay.addWidget(rh)

        # Right body
        right_body = QWidget()
        right_body.setStyleSheet("background: transparent;")
        rb_lay = QVBoxLayout(right_body)
        rb_lay.setContentsMargins(18, 16, 18, 16)
        rb_lay.setSpacing(10)

        self._detail_title = QLabel("Select a snapshot")
        self._detail_title.setStyleSheet(
            "color: #f1f5f9; font-size: 13px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        rb_lay.addWidget(self._detail_title)

        self._detail_box = QTextEdit()
        self._detail_box.setReadOnly(True)
        self._detail_box.setStyleSheet(
            "QTextEdit { background: rgba(255,255,255,5); "
            "border: 1px solid rgba(255,255,255,0.07); "
            "border-radius: 8px; color: #94a3b8; font-size: 12px; padding: 8px; }"
        )
        rb_lay.addWidget(self._detail_box, 1)
        right_lay.addWidget(right_body, 1)

        # Right footer — label + revert
        right_footer = QFrame()
        right_footer.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        rf_lay = QHBoxLayout(right_footer)
        rf_lay.setContentsMargins(18, 12, 18, 12)
        rf_lay.setSpacing(8)

        self._label_entry = QLineEdit()
        self._label_entry.setPlaceholderText("Edit label…")
        self._label_entry.setFixedHeight(34)
        self._label_entry.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 7px; "
            "color: #94a3b8; font-size: 12px; padding: 0 10px; }"
            "QLineEdit:focus { border-color: rgba(59,130,246,0.4); }"
        )
        rf_lay.addWidget(self._label_entry, 1)

        save_label_btn = _btn_ghost("Save Label")
        save_label_btn.setFixedWidth(100)
        save_label_btn.clicked.connect(self._save_label)
        rf_lay.addWidget(save_label_btn)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            "color: #f87171; font-size: 11px; background: transparent; border: none;"
        )
        rf_lay.addWidget(self._error_lbl, 1)

        self._revert_btn = _btn_revert("Revert To This Version")
        self._revert_btn.setFixedWidth(170)
        self._revert_btn.setEnabled(False)
        self._revert_btn.clicked.connect(self._confirm_revert)
        rf_lay.addWidget(self._revert_btn)
        right_lay.addWidget(right_footer)

        split.addWidget(right, 1)

        split_widget = QWidget()
        split_widget.setStyleSheet("background: #0f1117;")
        split_widget.setLayout(split)
        outer.addWidget(split_widget, 1)

        self._setup_overlay("Loading history...")
        self._load_manifests()

    # ------------------------------------------------------------------

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def _load_manifests(self) -> None:
        self._set_error("")
        self._selected_manifest = None
        self._selected_row_frame = None
        self._revert_btn.setEnabled(False)
        self._label_entry.clear()
        self._detail_title.setText("Select a snapshot")
        self._detail_box.clear()
        self._snap_count_lbl.setVisible(False)

        clear_layout(self._list_layout)

        history_enabled = bool(self.project.get("settings", {}).get("history_enabled", True))
        if not history_enabled:
            lbl = QLabel("History is OFF in settings.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #334155; font-size: 12px; background: transparent; "
                "padding: 32px; border: none;"
            )
            self._list_layout.addWidget(lbl)
            return

        def worker():
            return list_manifests(self.project_path)

        def on_success(manifests):
            self._manifests = manifests
            count = len(manifests)
            self._snap_count_lbl.setText(str(count))
            self._snap_count_lbl.setVisible(count > 0)
            self._render_manifest_rows()

        self._run_background(worker, on_success,
                             lambda exc: self._set_error(f"Could not load manifests: {exc}"))

    def _render_manifest_rows(self) -> None:
        if not self._manifests:
            lbl = QLabel("No snapshots available.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #334155; font-size: 12px; background: transparent; "
                "padding: 32px; border: none;"
            )
            self._list_layout.addWidget(lbl)
            return

        for manifest in self._manifests:
            row = QFrame()
            row.setStyleSheet(
                "QFrame { background: transparent; border: none; "
                "border-bottom: 1px solid rgba(255,255,255,0.04); "
                "border-radius: 0; }"
            )
            row.setCursor(Qt.PointingHandCursor)
            row_lay = QVBoxLayout(row)
            row_lay.setContentsMargins(18, 10, 18, 10)
            row_lay.setSpacing(3)

            title = manifest_title(manifest)
            label_text = str(manifest.get("label", "")).strip() or "(no label)"

            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(
                "color: #cbd5e1; font-size: 12px; font-weight: 500; "
                "background: transparent; border: none;"
            )
            row_lay.addWidget(title_lbl)

            label_lbl = QLabel(label_text)
            label_lbl.setStyleSheet(
                "color: #475569; font-size: 11px; background: transparent; border: none;"
            )
            row_lay.addWidget(label_lbl)

            def _click(event=None, m=manifest, frame=row):
                self._select_manifest(m, frame)

            row.mousePressEvent  = _click
            title_lbl.mousePressEvent = _click
            label_lbl.mousePressEvent = _click

            self._list_layout.addWidget(row)

    def _select_manifest(self, manifest: dict, frame: QFrame) -> None:
        # Deselect previous
        if self._selected_row_frame and self._selected_row_frame is not frame:
            self._selected_row_frame.setStyleSheet(
                "QFrame { background: transparent; border: none; "
                "border-bottom: 1px solid rgba(255,255,255,0.04); border-radius: 0; }"
            )
            for lbl in self._selected_row_frame.findChildren(QLabel):
                if lbl.font().bold() or lbl.styleSheet().find("font-weight: 500") != -1:
                    lbl.setStyleSheet(
                        "color: #cbd5e1; font-size: 12px; font-weight: 500; "
                        "background: transparent; border: none;"
                    )
                else:
                    lbl.setStyleSheet(
                        "color: #475569; font-size: 11px; background: transparent; border: none;"
                    )

        self._selected_manifest = manifest
        self._selected_row_frame = frame
        frame.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.08); border: none; "
            "border-left: 2px solid #3b82f6; border-bottom: 1px solid rgba(255,255,255,0.04); "
            "border-radius: 0; }"
        )
        for lbl in frame.findChildren(QLabel):
            lbl.setStyleSheet("color: #93c5fd; background: transparent; border: none; font-size: 12px;")

        self._revert_btn.setEnabled(True)
        self._label_entry.setText(str(manifest.get("label", "")))
        self._detail_title.setText(manifest_title(manifest))
        self._detail_box.setPlainText(manifest_tables_text(manifest))

    def _save_label(self) -> None:
        if not self._selected_manifest:
            self._set_error("Select a snapshot first.")
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
            self._set_error("Select a snapshot first.")
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
