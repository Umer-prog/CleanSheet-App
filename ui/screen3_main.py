from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
from core.error_detector import detect_errors
from core.mapping_manager import delete_mapping, get_active_dim_tables, get_mappings
from core.project_manager import open_project
from ui.screen2_mappings import Screen2Mappings
from ui.workers import Worker

_NAV_WIDTH = 260

# Icon characters for bottom nav items
_NAV_ICONS = {
    "t_sources": "◧",
    "d_sources": "◨",
    "history":   "◷",
    "settings":  "⚙",
}


def mapping_nav_label(mapping: dict) -> str:
    tx  = str(mapping.get("transaction_table", "")).strip() or "unknown_tx"
    dim = str(mapping.get("dim_table",         "")).strip() or "unknown_dim"
    return f"{tx} → {dim}"


def build_nav_items(mappings: list[dict]) -> list[dict]:
    items: list[dict] = []
    for mapping in mappings:
        items.append({
            "kind":    "mapping",
            "key":     str(mapping.get("id", "")).strip() or mapping_nav_label(mapping),
            "label":   mapping_nav_label(mapping),
            "mapping": mapping,
        })
    items.extend([
        {"kind": "separator"},
        {"kind": "section_label", "label": "TABLES"},
        {"kind": "view", "key": "t_sources", "label": "Transaction Tables"},
        {"kind": "view", "key": "d_sources", "label": "Dimension Tables"},
        {"kind": "section_label", "label": "MANAGE"},
        {"kind": "view", "key": "history",   "label": "History / Revert"},
        {"kind": "view", "key": "settings",  "label": "Settings"},
    ])
    return items


class _MappingDeleteConfirm:
    """Dark-themed confirmation dialog for deleting a mapping."""

    def __init__(self, parent, mapping: dict):
        self._dlg = QDialog(parent)
        self._dlg.setWindowTitle("Delete Mapping")
        self._dlg.setFixedSize(500, 250)
        self._dlg.setModal(True)
        self._dlg.setStyleSheet("QDialog { background-color: #0f1117; }")
        self.confirmed = False

        tx_t = mapping.get("transaction_table", "")
        tx_c = mapping.get("transaction_column", "")
        dim_t = mapping.get("dim_table", "")
        dim_c = mapping.get("dim_column", "")

        outer = QVBoxLayout(self._dlg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet("QFrame { background-color: #ef4444; }")
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(22, 0, 22, 0)
        h_lbl = QLabel("Delete Mapping")
        h_lbl.setStyleSheet(
            "color: #fff; font-size: 15px; font-weight: 700; "
            "background: transparent; border: none;"
        )
        h_lay.addWidget(h_lbl)
        outer.addWidget(header)

        # Body
        body = QFrame()
        body.setStyleSheet("QFrame { background-color: #13161e; }")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(22, 18, 22, 18)
        b_lay.setSpacing(12)

        mapping_lbl = QLabel(
            f"<span style='color:#94a3b8;'>Mapping to delete:</span><br>"
            f"<span style='color:#60a5fa; font-weight:600;'>{tx_t}.{tx_c}</span>"
            f"<span style='color:#334155;'>  →  </span>"
            f"<span style='color:#60a5fa; font-weight:600;'>{dim_t}.{dim_c}</span>"
        )
        mapping_lbl.setTextFormat(Qt.RichText)
        mapping_lbl.setStyleSheet("background: transparent; border: none;")
        b_lay.addWidget(mapping_lbl)

        warn_lbl = QLabel(
            "This mapping will be permanently removed. If this was the only mapping "
            "referencing the dimension table, it will become orphaned and eligible for deletion."
        )
        warn_lbl.setWordWrap(True)
        warn_lbl.setStyleSheet(
            "color: #64748b; font-size: 12px; background: transparent; border: none;"
        )
        b_lay.addWidget(warn_lbl)
        outer.addWidget(body, 1)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet("QFrame { background-color: #0f1117; }")
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(22, 0, 22, 0)
        f_lay.setSpacing(8)
        f_lay.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet(
            "QPushButton { background: transparent; "
            "border: 1px solid rgba(255,255,255,0.12); border-radius: 7px; "
            "color: #64748b; font-size: 13px; padding: 0 18px; }"
            "QPushButton:hover { border-color: rgba(255,255,255,0.22); color: #94a3b8; }"
        )
        cancel_btn.clicked.connect(self._dlg.reject)
        f_lay.addWidget(cancel_btn)

        delete_btn = QPushButton("Delete Mapping")
        delete_btn.setFixedHeight(36)
        delete_btn.setStyleSheet(
            "QPushButton { background: #ef4444; border: none; border-radius: 7px; "
            "color: #fff; font-size: 13px; font-weight: 600; padding: 0 18px; }"
            "QPushButton:hover { background: #dc2626; }"
        )
        delete_btn.clicked.connect(self._confirm)
        f_lay.addWidget(delete_btn)
        outer.addWidget(footer)

    def _confirm(self) -> None:
        self.confirmed = True
        self._dlg.accept()

    def exec(self) -> None:
        self._dlg.exec()


class Screen3Main(QWidget):
    """Main workspace shell — left navbar + right content area."""

    def __init__(self, app, project: dict, initial_nav_key: str | None = None, **kwargs):
        super().__init__()
        self.app             = app
        self.project         = project
        self.project_path    = Path(project["project_path"])
        self.initial_nav_key = initial_nav_key

        # nav state
        self._nav_frames:  dict[str, QFrame]  = {}
        self._nav_labels:  dict[str, QLabel]  = {}
        self._nav_badges:  dict[str, QLabel]  = {}
        self._nav_icons:   dict[str, QLabel]  = {}
        self._active_nav_key: str | None = None
        self._active_view:    QWidget  | None = None

        self._mappings  = self._load_mappings()
        self._nav_items = build_nav_items(self._mappings)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_navbar())

        self._content_host = QWidget()
        self._content_host.setStyleSheet("background: #0f1117;")
        cl = QVBoxLayout(self._content_host)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        root.addWidget(self._content_host, 1)

        self._select_default_view()
        self._init_mapping_badges()

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------

    def _load_mappings(self) -> list[dict]:
        try:
            return get_mappings(self.project_path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not load mappings:\n{exc}")
            return []

    def _init_mapping_badges(self) -> None:
        """Run error detection for every mapping in background and seed the nav badges."""
        mapping_items = [i for i in self._nav_items if i["kind"] == "mapping"]
        if not mapping_items:
            return

        project_path = self.project_path

        def worker():
            import json as _json
            ignored_file = project_path / "metadata" / "data" / "ignored_errors.json"
            try:
                with open(ignored_file, encoding="utf-8") as fh:
                    ignored_map = {k: set(v) for k, v in _json.load(fh).items()}
            except Exception:
                ignored_map = {}

            results: dict[str, int] = {}
            for item in mapping_items:
                try:
                    errors, total = detect_errors(project_path, item["mapping"])
                    m = item["mapping"]
                    key = f"{m.get('transaction_table', '')}.{m.get('transaction_column', '')}"
                    ignored = ignored_map.get(key, set())
                    visible_count = len([e for e in errors if int(e["row_index"]) not in ignored])
                    results[item["key"]] = max(0, total - (len(errors) - visible_count))
                except Exception:
                    results[item["key"]] = 0
            return results

        def on_done(results: dict):
            for nav_key, count in results.items():
                self.update_mapping_badge(nav_key, count)

        w = Worker(worker)
        w.finished.connect(on_done)
        w.start()
        self._badge_worker = w  # hold reference so GC doesn't collect it

    # ------------------------------------------------------------------
    # Navbar builder
    # ------------------------------------------------------------------

    def _build_navbar(self) -> QFrame:
        sidebar = QFrame()
        sidebar.setObjectName("s3_sidebar")
        sidebar.setFixedWidth(_NAV_WIDTH)
        sidebar.setStyleSheet(
            "QFrame#s3_sidebar { background: #13161e; border: none; "
            "border-right: 1px solid rgba(255,255,255,0.06); }"
        )
        lay = QVBoxLayout(sidebar)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # ── Brand block (same pattern as screen1 / screen2) ─────────
        brand = QFrame()
        brand.setFixedHeight(64)
        brand.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        b_lay = QHBoxLayout(brand)
        b_lay.setContentsMargins(18, 0, 18, 0)
        b_lay.setSpacing(11)

        logo_box = QFrame()
        logo_box.setFixedSize(34, 34)
        logo_box.setStyleSheet(
            "QFrame { background: #2161AC; border-radius: 9px; border: none; }"
        )
        logo_inner = QVBoxLayout(logo_box)
        logo_inner.setContentsMargins(0, 0, 0, 0)
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        _logo_px = theme.logo_pixmap(24)
        if _logo_px:
            logo_lbl.setPixmap(_logo_px)
        else:
            logo_lbl.setText("▦")
            logo_lbl.setContentsMargins(0, 0, 0, 3)
            logo_lbl.setStyleSheet(
                "color: white; background: transparent; border: none; font-size: 30px;"
            )
        logo_inner.addWidget(logo_lbl)
        b_lay.addWidget(logo_box)

        brand_lbl = QLabel(
            f"<span style='color:#f1f5f9; font-size:15px; font-weight:600;'>"
            f"{theme.company_name()}</span>"
            "<br>"
            "<span style='color:#475569; font-size:10px; letter-spacing:1px;'>DATA MAPPING</span>"
        )
        brand_lbl.setTextFormat(Qt.RichText)
        brand_lbl.setStyleSheet("background: transparent; border: none;")
        b_lay.addWidget(brand_lbl, 1)
        lay.addWidget(brand)

        # ── Workspace info block ─────────────────────────────────────
        ws_info = QFrame()
        ws_info.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        wi_lay = QVBoxLayout(ws_info)
        wi_lay.setContentsMargins(12, 10, 12, 10)
        wi_lay.setSpacing(2)

        ws_section = QLabel("WORKSPACE")
        ws_section.setStyleSheet(
            "color: #334155; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        wi_lay.addWidget(ws_section)

        ws_name = QLabel(str(self.project.get("project_name", "Project")))
        ws_name.setStyleSheet(
            "color: #f1f5f9; background: transparent; border: none; "
            "font-size: 13px; font-weight: 600;"
        )
        wi_lay.addWidget(ws_name)

        ws_company = QLabel(str(self.project.get("company", "")))
        ws_company.setStyleSheet(
            "color: #475569; background: transparent; border: none; font-size: 11px;"
        )
        wi_lay.addWidget(ws_company)
        lay.addWidget(ws_info)

        # ── Back button ──────────────────────────────────────────────
        back_wrap = QFrame()
        back_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        bw_lay = QHBoxLayout(back_wrap)
        bw_lay.setContentsMargins(12, 8, 12, 4)
        back_btn = QPushButton("← Back to Launcher")
        back_btn.setFixedHeight(32)
        back_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 7px; "
            "color: #94a3b8; font-size: 11px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.08); }"
        )
        back_btn.clicked.connect(self._go_to_launcher)
        bw_lay.addWidget(back_btn)
        lay.addWidget(back_wrap)

        # ── Scrollable nav ───────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameStyle(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        nav_lay = QVBoxLayout(nav_container)
        nav_lay.setContentsMargins(0, 0, 0, 8)
        nav_lay.setSpacing(0)
        nav_lay.setAlignment(Qt.AlignTop)
        scroll.setWidget(nav_container)
        lay.addWidget(scroll, 1)

        # "MAPPINGS" section label
        if any(i["kind"] == "mapping" for i in self._nav_items):
            m_lbl = QLabel("MAPPINGS")
            m_lbl.setStyleSheet(
                "color: #334155; background: transparent; border: none; "
                "font-size: 10px; font-weight: 600; letter-spacing: 1px; "
                "padding: 14px 18px 6px 18px;"
            )
            nav_lay.addWidget(m_lbl)

        for item in self._nav_items:
            if item["kind"] == "separator":
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet(
                    "QFrame { background: rgba(255,255,255,0.05); border: none; margin: 6px 0; }"
                )
                nav_lay.addWidget(sep)
                continue

            if item["kind"] == "section_label":
                sec = QLabel(item["label"])
                sec.setStyleSheet(
                    "color: #334155; background: transparent; border: none; "
                    "font-size: 10px; font-weight: 600; letter-spacing: 1px; "
                    "padding: 14px 18px 6px 18px;"
                )
                nav_lay.addWidget(sec)
                continue

            key = item["key"]
            if item["kind"] == "mapping":
                frame = self._make_mapping_nav_item(item)
            else:
                frame = self._make_view_nav_item(item)

            nav_lay.addWidget(frame)
            self._nav_frames[key] = frame

        return sidebar

    # ------------------------------------------------------------------

    def _make_mapping_nav_item(self, item: dict) -> QFrame:
        key   = item["key"]
        frame = QFrame()
        frame.setFixedHeight(44)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-left: 2px solid transparent; }"
        )
        f_lay = QHBoxLayout(frame)
        f_lay.setContentsMargins(26, 0, 10, 0)
        f_lay.setSpacing(5)

        lbl = QLabel(item["label"])
        lbl.setStyleSheet(
            "color: #475569; background: transparent; border: none; font-size: 11px;"
        )
        f_lay.addWidget(lbl, 1)
        self._nav_labels[key] = lbl

        # Delete button — clicking it does NOT navigate, only deletes
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton { background: rgba(239,68,68,0.0); border: none; "
            "border-radius: 4px; color: #475569; font-size: 14px; font-weight: 700; "
            "padding: 0; }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); color: #f87171; }"
        )
        del_btn.clicked.connect(
            lambda _=None, m=item["mapping"]: self._on_delete_mapping(m)
        )
        f_lay.addWidget(del_btn)

        badge = QLabel("✓")
        badge.setFixedHeight(18)
        badge.setStyleSheet(
            "color: #34d399; background: rgba(34,211,153,0.1); "
            "border: 1px solid rgba(34,211,153,0.2); border-radius: 9px; "
            "font-size: 10px; padding: 0 5px; border: none;"
        )
        f_lay.addWidget(badge)
        self._nav_badges[key] = badge

        def _click(_=None, it=item):
            self._on_nav_click(it)

        frame.mousePressEvent  = _click
        lbl.mousePressEvent    = _click
        badge.mousePressEvent  = _click
        return frame

    def _make_view_nav_item(self, item: dict) -> QFrame:
        key   = item["key"]
        icon  = _NAV_ICONS.get(key, "◈")
        frame = QFrame()
        frame.setFixedHeight(38)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-left: 2px solid transparent; }"
        )
        f_lay = QHBoxLayout(frame)
        f_lay.setContentsMargins(16, 0, 16, 0)
        f_lay.setSpacing(9)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(14)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #475569; background: transparent; border: none; font-size: 10px;"
        )
        f_lay.addWidget(icon_lbl)
        self._nav_icons[key] = icon_lbl

        lbl = QLabel(item["label"])
        lbl.setStyleSheet(
            "color: #64748b; background: transparent; border: none; font-size: 12px;"
        )
        f_lay.addWidget(lbl, 1)
        self._nav_labels[key] = lbl

        def _click(_=None, it=item):
            self._on_nav_click(it)

        frame.mousePressEvent    = _click
        icon_lbl.mousePressEvent = _click
        lbl.mousePressEvent      = _click
        return frame

    # ------------------------------------------------------------------
    # Nav state
    # ------------------------------------------------------------------

    def _set_active_nav(self, active_key: str) -> None:
        for key, frame in self._nav_frames.items():
            item     = next((i for i in self._nav_items if i.get("key") == key), None)
            is_active = key == active_key

            if item and item["kind"] == "mapping":
                if is_active:
                    frame.setStyleSheet(
                        "QFrame { background: rgba(59,130,246,0.08); border: none; "
                        "border-left: 2px solid #3b82f6; }"
                    )
                    if key in self._nav_labels:
                        self._nav_labels[key].setStyleSheet(
                            "color: #60a5fa; background: transparent; border: none; font-size: 11px;"
                        )
                else:
                    frame.setStyleSheet(
                        "QFrame { background: transparent; border: none; "
                        "border-left: 2px solid transparent; }"
                    )
                    if key in self._nav_labels:
                        self._nav_labels[key].setStyleSheet(
                            "color: #475569; background: transparent; border: none; font-size: 11px;"
                        )
            else:
                if is_active:
                    frame.setStyleSheet(
                        "QFrame { background: rgba(59,130,246,0.1); border: none; "
                        "border-left: 2px solid #3b82f6; }"
                    )
                    if key in self._nav_labels:
                        self._nav_labels[key].setStyleSheet(
                            "color: #93c5fd; background: transparent; border: none; font-size: 12px;"
                        )
                    if key in self._nav_icons:
                        self._nav_icons[key].setStyleSheet(
                            "color: #93c5fd; background: transparent; border: none; font-size: 10px;"
                        )
                else:
                    frame.setStyleSheet(
                        "QFrame { background: transparent; border: none; "
                        "border-left: 2px solid transparent; }"
                    )
                    if key in self._nav_labels:
                        self._nav_labels[key].setStyleSheet(
                            "color: #64748b; background: transparent; border: none; font-size: 12px;"
                        )
                    if key in self._nav_icons:
                        self._nav_icons[key].setStyleSheet(
                            "color: #475569; background: transparent; border: none; font-size: 10px;"
                        )

        self._active_nav_key = active_key

    def update_mapping_badge(self, nav_key: str, error_count: int) -> None:
        """Called by ViewMapping after errors are loaded to update the sidebar badge."""
        if nav_key not in self._nav_badges:
            return
        badge = self._nav_badges[nav_key]
        if error_count == 0:
            badge.setText("✓")
            badge.setStyleSheet(
                "color: #34d399; background: rgba(34,211,153,0.1); "
                "border: 1px solid rgba(34,211,153,0.2); border-radius: 9px; "
                "font-size: 10px; padding: 0 5px;"
            )
        else:
            badge.setText(str(error_count))
            badge.setStyleSheet(
                "color: #f87171; background: rgba(239,68,68,0.1); "
                "border: 1px solid rgba(239,68,68,0.2); border-radius: 9px; "
                "font-size: 10px; padding: 0 5px;"
            )

    # ------------------------------------------------------------------
    # Mapping deletion
    # ------------------------------------------------------------------

    def _on_delete_mapping(self, mapping: dict) -> None:
        """Show confirmation popup, delete the mapping, then check for orphaned dims."""
        dlg = _MappingDeleteConfirm(self, mapping)
        dlg.exec()
        if not dlg.confirmed:
            return

        mapping_id   = mapping["id"]
        dim_table    = mapping.get("dim_table", "")
        project_path = self.project_path

        def worker():
            # Capture which dim tables were active BEFORE deletion
            active_before = get_active_dim_tables(project_path)
            delete_mapping(project_path, mapping_id)
            active_after = get_active_dim_tables(project_path)
            # Newly orphaned = was active before, not active now, and matches our dim
            newly_orphaned = (active_before - active_after) & {dim_table}
            return newly_orphaned

        def on_done(newly_orphaned: set):
            if newly_orphaned:
                answer = QMessageBox.information(
                    self,
                    "Dimension Table Now Orphaned",
                    f"The dimension table <b>{dim_table}</b> is no longer referenced "
                    f"by any mapping.<br><br>"
                    f"It can now be permanently deleted from the "
                    f"<b>Dimension Tables</b> panel.",
                    QMessageBox.Ok | QMessageBox.Ignore,
                    QMessageBox.Ok,
                )
                # Navigate to d_sources if user clicked Ok (not Ignore)
                go_to_dims = (answer == QMessageBox.Ok)
            else:
                go_to_dims = False

            target = "d_sources" if go_to_dims else None
            self._reload_from_disk(target_key=target)

        w = Worker(worker)
        w.finished.connect(on_done)
        w.errored.connect(
            lambda exc: QMessageBox.critical(
                self, "Error", f"Could not delete mapping:\n{exc}"
            )
        )
        w.start()
        self._delete_worker = w   # keep reference

    # ------------------------------------------------------------------
    # Navigation & view switching
    # ------------------------------------------------------------------

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

    def _on_nav_click(self, item: dict) -> None:
        self._set_active_nav(item["key"])
        self._show_item_view(item)

    def _show_item_view(self, item: dict) -> None:
        if self._active_view is not None:
            self._active_view.setParent(None)
            self._active_view.deleteLater()

        layout = self._content_host.layout()

        if item["kind"] == "mapping":
            from ui.views.view_mapping import ViewMapping
            self._active_view = ViewMapping(
                self._content_host,
                project=self.project,
                mapping=item["mapping"],
                nav_key=item["key"],
                on_badge_update=self.update_mapping_badge,
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

    # ------------------------------------------------------------------
    # Project navigation
    # ------------------------------------------------------------------

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
