from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from core.snapshot_manager import (
    create_snapshot,
    get_current_commit_id,
    list_manifests,
    revert_to_manifest,
    update_manifest_label,
)
import ui.popups.msgbox as msgbox
from ui.workers import ScreenBase, clear_layout, make_scroll_area


def _commit_display_id(manifest: dict) -> str:
    """Return the display ID, normalising legacy 'manifest_NNN' → 'commit_NNN'."""
    mid = str(manifest.get("manifest_id", "")).strip()
    return mid.replace("manifest_", "commit_")


def commit_title(manifest: dict) -> str:
    created = str(manifest.get("created_at", "")).strip()
    return f"{_commit_display_id(manifest)}  ·  {created}"


def commit_tables_text(manifest: dict) -> str:
    tables = manifest.get("tables", [])
    if not tables:
        return "(No tables)"
    return "\n".join(f"  {name}" for name in tables)


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


class _SnapshotLabelDialog:
    """Minimal dialog asking for a snapshot description before committing."""

    def __init__(self, parent):
        self.label: str | None = None

        self._dlg = QDialog(parent)
        self._dlg.setWindowTitle("Take Snapshot")
        self._dlg.setFixedSize(480, 210)
        self._dlg.setModal(True)
        self._dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self._dlg.setStyleSheet("QDialog { background-color: #0f1117; }")

        outer = QVBoxLayout(self._dlg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(52)
        header.setStyleSheet("QFrame { background: #3b82f6; }")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(22, 0, 22, 0)
        h_lbl = QLabel("Take Snapshot")
        h_lbl.setStyleSheet(
            "color: #fff; font-size: 14px; font-weight: 700; "
            "background: transparent; border: none;"
        )
        h_lay.addWidget(h_lbl)
        outer.addWidget(header)

        body = QFrame()
        body.setStyleSheet("QFrame { background: #13161e; }")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(22, 18, 22, 18)
        b_lay.setSpacing(10)

        desc = QLabel("Enter a description for this snapshot:")
        desc.setStyleSheet(
            "color: #94a3b8; font-size: 12px; background: transparent; border: none;"
        )
        b_lay.addWidget(desc)

        self._entry = QLineEdit()
        self._entry.setPlaceholderText("e.g. Before Q2 mapping review")
        self._entry.setFixedHeight(36)
        self._entry.setStyleSheet(
            "QLineEdit { background: rgba(255,255,255,0.05); "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 7px; "
            "color: #f1f5f9; font-size: 13px; padding: 0 10px; }"
            "QLineEdit:focus { border-color: rgba(59,130,246,0.5); }"
        )
        self._entry.returnPressed.connect(self._confirm)
        b_lay.addWidget(self._entry)

        self._err_lbl = QLabel("")
        self._err_lbl.setStyleSheet(
            "color: #f87171; font-size: 11px; background: transparent; border: none;"
        )
        b_lay.addWidget(self._err_lbl)
        outer.addWidget(body, 1)

        footer = QFrame()
        footer.setFixedHeight(56)
        footer.setStyleSheet("QFrame { background: #0f1117; }")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(22, 0, 22, 0)
        f_lay.setSpacing(8)
        f_lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(34)
        cancel_btn.setStyleSheet(
            "QPushButton { background: transparent; "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 7px; "
            "color: #64748b; font-size: 12px; padding: 0 18px; }"
            "QPushButton:hover { border-color: rgba(255,255,255,0.22); color: #94a3b8; }"
        )
        cancel_btn.clicked.connect(self._dlg.reject)
        f_lay.addWidget(cancel_btn)

        create_btn = QPushButton("Create Snapshot")
        create_btn.setFixedHeight(34)
        create_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; border: none; border-radius: 7px; "
            "color: #fff; font-size: 12px; font-weight: 600; padding: 0 18px; }"
            "QPushButton:hover { background: #2563eb; }"
        )
        create_btn.clicked.connect(self._confirm)
        f_lay.addWidget(create_btn)
        outer.addWidget(footer)

    def _confirm(self) -> None:
        text = self._entry.text().strip()
        if not text:
            self._err_lbl.setText("Description is required.")
            return
        self.label = text
        self._dlg.accept()

    def exec(self) -> None:
        self._dlg.exec()


class ViewHistory(ScreenBase):
    """Commit history list and revert view."""

    def __init__(self, parent, project: dict, on_project_changed):
        super().__init__(parent)
        self.project = project
        self.project_path = Path(project["project_path"])
        self.on_project_changed = on_project_changed
        self._selected_manifest: dict | None = None
        self._selected_row_frame: QFrame | None = None
        self._manifests: list[dict] = []
        self._current_commit_id: str | None = None

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
        title_lbl = QLabel("Commit History")
        title_lbl.setStyleSheet(
            "color: #f1f5f9; font-size: 15px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        meta_lbl = QLabel(
            "Select a commit to inspect its details, edit the label, or revert — "
            "reverting restores transactions, dimension tables, and mappings together."
        )
        meta_lbl.setStyleSheet(
            "color: #334155; font-size: 11px; background: transparent; border: none;"
        )
        tb_text.addWidget(title_lbl)
        tb_text.addWidget(meta_lbl)
        tb_lay.addLayout(tb_text, 1)

        snapshot_btn = QPushButton("+ Take Snapshot")
        snapshot_btn.setFixedHeight(34)
        snapshot_btn.setStyleSheet(
            "QPushButton { background: #3b82f6; border: none; border-radius: 7px; "
            "color: white; font-size: 12px; font-weight: 500; padding: 0 16px; }"
            "QPushButton:hover { background: #2563eb; }"
            "QPushButton:pressed { background: #1d4ed8; }"
        )
        snapshot_btn.clicked.connect(self._on_take_snapshot)
        tb_lay.addWidget(snapshot_btn)

        refresh_btn = _btn_ghost("Refresh", height=34)
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self._load_manifests)
        tb_lay.addWidget(refresh_btn)
        outer.addWidget(topbar)

        # ── Split content ─────────────────────────────────────────────────
        split = QHBoxLayout()
        split.setContentsMargins(0, 0, 0, 0)
        split.setSpacing(0)

        # Left — commit list
        left = QFrame()
        left.setFixedWidth(380)
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
        lh_title = QLabel("COMMITS")
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
        rh_lay.setSpacing(12)
        rh_title = QLabel("COMMIT DETAILS")
        rh_title.setStyleSheet(
            "color: #475569; font-size: 11px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        rh_lay.addWidget(rh_title, 1)

        # HEAD badge — shows the current checked-out commit
        self._head_badge = QLabel("")
        self._head_badge.setFixedHeight(30)
        self._head_badge.setStyleSheet(
            "color: #34d399; background: rgba(5,150,105,0.12); "
            "border: 1px solid rgba(5,150,105,0.25); border-radius: 5px; "
            "font-size: 10px; font-weight: 600; padding: 2px 8px;"
        )
        self._head_badge.setVisible(False)
        rh_lay.addWidget(self._head_badge)
        right_lay.addWidget(rh)

        # Right body
        right_body = QWidget()
        right_body.setStyleSheet("background: transparent;")
        rb_lay = QVBoxLayout(right_body)
        rb_lay.setContentsMargins(18, 16, 18, 16)
        rb_lay.setSpacing(10)

        self._detail_title = QLabel("Select a commit")
        self._detail_title.setStyleSheet(
            "color: #f1f5f9; font-size: 13px; font-weight: 600; "
            "background: transparent; border: none;"
        )
        rb_lay.addWidget(self._detail_title)

        # Current commit status line
        self._current_commit_lbl = QLabel("")
        self._current_commit_lbl.setTextFormat(Qt.RichText)
        self._current_commit_lbl.setStyleSheet(
            "color: #475569; font-size: 11px; background: transparent; border: none;"
        )
        self._current_commit_lbl.setVisible(False)
        rb_lay.addWidget(self._current_commit_lbl)

        self._detail_box = QTextEdit()
        self._detail_box.setReadOnly(True)
        self._detail_box.setStyleSheet(
            "QTextEdit { background: rgba(255,255,255,5); "
            "border: 1px solid rgba(255,255,255,0.07); "
            "border-radius: 8px; color: #94a3b8; font-size: 12px; padding: 8px; "
            "font-family: 'Courier New'; }"
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

        self._revert_btn = _btn_revert("Revert to This Commit")
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

    def _on_take_snapshot(self) -> None:
        """Ask user for a description then create a full-project snapshot."""
        dlg = _SnapshotLabelDialog(self)
        dlg.exec()
        label = dlg.label
        if label is None:
            return

        project_path = self.project_path
        tx_tables = list(self.project.get("transaction_tables", []))

        def worker():
            import pandas as pd
            live_tx = project_path / "metadata" / "data" / "transactions"
            tables: dict = {}
            for name in tx_tables:
                csv = live_tx / f"{name}.csv"
                if csv.exists():
                    tables[name] = pd.read_csv(csv)
            create_snapshot(project_path, tables, label=label)

        self._run_background(
            worker,
            lambda _: self._load_manifests(),
            lambda exc: msgbox.critical(self, "Error", f"Could not create snapshot:\n{exc}"),
        )

    # ------------------------------------------------------------------

    def _set_error(self, msg: str) -> None:
        self._error_lbl.setText(msg)

    def _load_manifests(self) -> None:
        self._set_error("")
        self._selected_manifest = None
        self._selected_row_frame = None
        self._revert_btn.setEnabled(False)
        self._label_entry.clear()
        self._detail_title.setText("Select a commit")
        self._detail_box.clear()
        self._current_commit_lbl.setVisible(False)
        self._head_badge.setVisible(False)
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
            return list_manifests(self.project_path), get_current_commit_id(self.project_path)

        def on_success(result):
            manifests, current_id = result
            self._manifests = manifests
            self._current_commit_id = current_id
            count = len(manifests)
            self._snap_count_lbl.setText(str(count))
            self._snap_count_lbl.setVisible(count > 0)
            # Update the persistent HEAD badge in the panel header
            if current_id:
                display = current_id.replace("manifest_", "commit_")
                self._head_badge.setText(f"HEAD  →  {display}")
                self._head_badge.setVisible(True)
            self._render_manifest_rows()

        self._run_background(worker, on_success,
                             lambda exc: self._set_error(f"Could not load commits: {exc}"))

    def _render_manifest_rows(self) -> None:
        if not self._manifests:
            lbl = QLabel("No commits yet.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(
                "color: #334155; font-size: 12px; background: transparent; "
                "padding: 32px; border: none;"
            )
            self._list_layout.addWidget(lbl)
            return

        for manifest in reversed(self._manifests):   # newest first
            raw_id = str(manifest.get("manifest_id", ""))
            is_current = (raw_id == self._current_commit_id)

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

            # Top row: commit id + HEAD badge
            top_row = QHBoxLayout()
            top_row.setSpacing(8)
            top_row.setContentsMargins(0, 0, 0, 0)

            display_id = _commit_display_id(manifest)
            created = str(manifest.get("created_at", "")).strip()
            id_lbl = QLabel(f"{display_id}  ·  {created}")
            id_lbl.setStyleSheet(
                "color: #cbd5e1; font-size: 12px; font-weight: 500; "
                "background: transparent; border: none;"
            )
            top_row.addWidget(id_lbl, 1)

            if is_current:
                head_lbl = QLabel("HEAD")
                head_lbl.setStyleSheet(
                    "color: #34d399; background: rgba(5,150,105,0.12); "
                    "border: 1px solid rgba(5,150,105,0.25); border-radius: 4px; "
                    "font-size: 10px; font-weight: 600; padding: 1px 6px;"
                )
                top_row.addWidget(head_lbl)

            top_widget = QWidget()
            top_widget.setStyleSheet("background: transparent;")
            top_widget.setLayout(top_row)
            row_lay.addWidget(top_widget)

            label_text = str(manifest.get("label", "")).strip() or "(no label)"
            label_lbl = QLabel(label_text)
            label_lbl.setStyleSheet(
                "color: #475569; font-size: 11px; background: transparent; border: none;"
            )
            row_lay.addWidget(label_lbl)

            def _click(_=None, m=manifest, frame=row):
                self._select_manifest(m, frame)

            row.mousePressEvent   = _click
            top_widget.mousePressEvent = _click
            id_lbl.mousePressEvent    = _click
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
                ss = lbl.styleSheet()
                if "font-weight: 500" in ss or "font-size: 12px" in ss:
                    lbl.setStyleSheet(
                        "color: #cbd5e1; font-size: 12px; font-weight: 500; "
                        "background: transparent; border: none;"
                    )
                elif "34d399" not in ss:   # leave the HEAD pill alone
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
            if "34d399" not in lbl.styleSheet():   # leave HEAD pill colour
                lbl.setStyleSheet("color: #93c5fd; background: transparent; border: none; font-size: 12px;")

        # Build detail text
        raw_id = str(manifest.get("manifest_id", ""))
        display_id = _commit_display_id(manifest)
        is_current = (raw_id == self._current_commit_id)

        self._detail_title.setText(commit_title(manifest))

        if is_current:
            self._current_commit_lbl.setText(
                f"<span style='color:#34d399;'>●  HEAD</span>"
                f"  <span style='color:#334155;'>— this is the currently active commit</span>"
            )
        else:
            current_display = (
                self._current_commit_id.replace("manifest_", "commit_")
                if self._current_commit_id else "none"
            )
            self._current_commit_lbl.setText(
                f"<span style='color:#475569;'>Current HEAD:</span>"
                f"  <span style='color:#60a5fa;'>{current_display}</span>"
            )
        self._current_commit_lbl.setVisible(True)

        label_val = str(manifest.get("label", "")).strip()
        tables = manifest.get("tables", [])
        dim_tables = manifest.get("dim_tables", [])
        mappings = manifest.get("mappings", [])

        lines = [
            f"commit    {display_id}",
            f"date      {manifest.get('created_at', '')}",
            f"label     {label_val or '(none)'}",
            "",
            f"transactions  ({len(tables)})",
        ]
        for name in tables:
            lines.append(f"  {name}")

        lines.append("")
        lines.append(f"dimensions  ({len(dim_tables)})")
        if dim_tables:
            for name in dim_tables:
                lines.append(f"  {name}")
        else:
            lines.append("  (not captured — legacy commit)")

        lines.append("")
        lines.append(f"mappings  ({len(mappings)})")
        if mappings:
            for m in mappings:
                lines.append(
                    f"  {m.get('transaction_table', '?')}.{m.get('transaction_column', '?')}"
                    f"  →  {m.get('dim_table', '?')}.{m.get('dim_column', '?')}"
                )
        else:
            lines.append("  (not captured — legacy commit)")

        self._detail_box.setPlainText("\n".join(lines))

        self._revert_btn.setEnabled(not is_current)
        self._revert_btn.setToolTip(
            "Already at this commit." if is_current else ""
        )
        self._label_entry.setText(label_val)

    def _save_label(self) -> None:
        if not self._selected_manifest:
            self._set_error("Select a commit first.")
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
            self._set_error("Select a commit first.")
            return
        manifest_id = self._selected_manifest["manifest_id"]
        display_id = _commit_display_id(self._selected_manifest)

        from ui.popups.popup_revert_confirm import PopupRevertConfirm

        def do_revert():
            def worker():
                revert_to_manifest(self.project_path, manifest_id)

            self._run_background(
                worker,
                lambda _: (
                    msgbox.information(
                        self, "Reverted",
                        f"Reverted to {display_id}.\n"
                        f"Transactions, dimension tables, and mappings have been restored."
                    ),
                    self.on_project_changed(target_key="history"),
                ),
                lambda exc: msgbox.critical(
                    self, "Error", f"Could not revert:\n{exc}"
                ),
            )

        dlg = PopupRevertConfirm(self, manifest_id=display_id, on_confirm=do_revert)
        dlg.exec()
