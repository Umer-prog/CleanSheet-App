from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
import ui.popups.msgbox as msgbox
from core.error_detector import detect_errors
from core.mapping_manager import delete_mapping, get_active_dim_tables, get_mappings
from core.project_manager import open_project
from core.project_paths import internal_path
from ui.screen2_mappings import Screen2Mappings
from ui.workers import Worker

_NAV_WIDTH = 350

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
        # Nav keys whose badge has been confirmed by ViewMapping (takes priority
        # over the background badge scan so we never overwrite a known-good state).
        self._nav_keys_confirmed: set[str] = set()

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
            msgbox.critical(self, "Failed to Load Mappings",
                            f"Mappings could not be read. The mappings file may be missing or corrupted.\n\nDetail: {exc}")
            return []

    def _init_mapping_badges(self) -> None:
        """Run error detection for every mapping in background and update nav badges.

        Intentionally does NOT write to the validation cache — the cache is only
        populated by ViewMapping._reload_data so that navigating to a mapping always
        runs a fresh detect_errors call, regardless of what the badge scan found.
        This prevents stale cache hits after re-uploads or dimension table changes.
        """
        mapping_items = [i for i in self._nav_items if i["kind"] == "mapping"]
        if not mapping_items:
            return

        project_path = self.project_path

        def worker():
            import json as _json
            from concurrent.futures import ThreadPoolExecutor

            # Parse the ignored_errors.json — supports both legacy format
            # {table.col: [row_indices]} and the new format
            # {"rows": {table.col: [...]}, "values": {table.col: [...]}}.
            ignored_file = internal_path(project_path) / "metadata" / "data" / "ignored_errors.json"
            ignored_rows_map: dict[str, set[int]] = {}
            ignored_vals_map: dict[str, set[str]] = {}
            try:
                with open(ignored_file, encoding="utf-8") as fh:
                    raw = _json.load(fh)
                if "rows" in raw or "values" in raw:
                    ignored_rows_map = {k: set(v) for k, v in raw.get("rows", {}).items()}
                    ignored_vals_map = {k: set(v) for k, v in raw.get("values", {}).items()}
                else:
                    # Legacy format: keys are "table.col", values are lists of row indices
                    ignored_rows_map = {k: set(v) for k, v in raw.items()}
            except Exception:
                pass

            def _detect_one(item: dict):
                try:
                    m = item["mapping"]
                    key = f"{m.get('transaction_table', '')}.{m.get('transaction_column', '')}"
                    ign_vals = frozenset(ignored_vals_map.get(key, set()))
                    errors, total = detect_errors(project_path, m, ignored_values=ign_vals)
                    ignored_rows = ignored_rows_map.get(key, set())
                    visible_count = sum(
                        1 for e in errors if int(e["row_index"]) not in ignored_rows
                    )
                    badge_count = max(0, total - (len(errors) - visible_count))
                    return item["key"], badge_count
                except Exception:
                    return item["key"], 0

            results: dict[str, int] = {}
            n_workers = min(4, len(mapping_items))
            with ThreadPoolExecutor(max_workers=n_workers) as pool:
                for nav_key, badge_count in pool.map(_detect_one, mapping_items):
                    results[nav_key] = badge_count
            return results

        def on_done(results: dict):
            for nav_key, count in results.items():
                # Skip any key already confirmed by ViewMapping — the view's
                # result is authoritative and must not be overwritten by the
                # background scan which may have finished later.
                if nav_key not in self._nav_keys_confirmed:
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
            "QFrame { background: #EDF3FB; border-radius: 9px; border: none; }"
        )
        logo_inner = QVBoxLayout(logo_box)
        logo_inner.setContentsMargins(0, 0, 0, 0)
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        _logo_px = theme.logo_pixmap_rounded(34, 9)
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
            "<span style='color:#94a3b8; font-size:10px; letter-spacing:1px;'>Data Preparation Tool</span>"
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
            "color: #cbd5e1; background: transparent; border: none; "
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
            "color: #94a3b8; background: transparent; border: none; font-size: 11px;"
        )
        wi_lay.addWidget(ws_company)
        lay.addWidget(ws_info)

        # ── MAPPINGS header (fixed, not scrollable) ──────────────────
        mh_wrap = QWidget()
        mh_wrap.setStyleSheet("background: transparent;")
        mh_lay = QHBoxLayout(mh_wrap)
        mh_lay.setContentsMargins(18, 14, 12, 6)
        mh_lay.setSpacing(0)

        m_lbl = QLabel("MAPPINGS")
        m_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        mh_lay.addWidget(m_lbl, 1)

        self._add_map_btn = QPushButton("+")
        self._add_map_btn.setFixedSize(18, 18)
        self._add_map_btn.setCursor(Qt.PointingHandCursor)
        self._add_map_btn.setToolTip("Add new mapping")
        self._add_map_btn.setStyleSheet(
            "QPushButton { background: rgba(59,130,246,0.15); border: none; "
            "border-radius: 4px; color: #60a5fa; font-size: 14px; font-weight: 700; padding: 0; }"
            "QPushButton:hover { background: rgba(59,130,246,0.3); color: #93c5fd; }"
            "QPushButton:disabled { background: rgba(59,130,246,0.04); color: rgba(96,165,250,0.25); }"
        )
        self._add_map_btn.clicked.connect(self._go_to_mapping_setup)
        mh_lay.addWidget(self._add_map_btn)
        self._sync_add_map_btn()
        lay.addWidget(mh_wrap)

        # ── Scrollable mappings only ─────────────────────────────────
        mapping_scroll = QScrollArea()
        mapping_scroll.setWidgetResizable(True)
        mapping_scroll.setFrameStyle(QFrame.NoFrame)
        mapping_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        mapping_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        mapping_container = QWidget()
        mapping_container.setStyleSheet("background: transparent;")
        mapping_lay = QVBoxLayout(mapping_container)
        mapping_lay.setContentsMargins(0, 0, 0, 4)
        mapping_lay.setSpacing(0)
        mapping_lay.setAlignment(Qt.AlignTop)
        mapping_scroll.setWidget(mapping_container)
        lay.addWidget(mapping_scroll, 1)

        # ── Fixed bottom nav items (separator + views) ───────────────
        bottom_nav = QWidget()
        bottom_nav.setStyleSheet("background: transparent;")
        bottom_nav_lay = QVBoxLayout(bottom_nav)
        bottom_nav_lay.setContentsMargins(0, 0, 0, 0)
        bottom_nav_lay.setSpacing(0)
        lay.addWidget(bottom_nav)

        # populate mapping rows into scrollable area; views into fixed bottom
        in_views = False
        for item in self._nav_items:
            if item["kind"] == "separator":
                in_views = True
                sep = QFrame()
                sep.setFixedHeight(1)
                sep.setStyleSheet(
                    "QFrame { background: rgba(255,255,255,0.05); border: none; margin: 6px 0; }"
                )
                bottom_nav_lay.addWidget(sep)
                continue

            if item["kind"] == "section_label":
                sec = QLabel(item["label"])
                sec.setStyleSheet(
                    "color: #cbd5e1; background: transparent; border: none; "
                    "font-size: 10px; font-weight: 600; letter-spacing: 1px; "
                    "padding: 14px 18px 6px 18px;"
                )
                bottom_nav_lay.addWidget(sec)
                continue

            key = item["key"]
            if item["kind"] == "mapping":
                frame = self._make_mapping_nav_item(item)
                mapping_lay.addWidget(frame)
            else:
                frame = self._make_view_nav_item(item)
                bottom_nav_lay.addWidget(frame)

            self._nav_frames[key] = frame

        # ── Back button (pinned to bottom) ───────────────────────────
        back_wrap = QFrame()
        back_wrap.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        bw_lay = QHBoxLayout(back_wrap)
        bw_lay.setContentsMargins(12, 8, 12, 10)
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

        return sidebar

    # ------------------------------------------------------------------

    def _make_mapping_nav_item(self, item: dict) -> QFrame:
        key   = item["key"]
        frame = QFrame()
        frame.setFixedHeight(48)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-left: 2px solid transparent; }"
        )
        f_lay = QHBoxLayout(frame)
        f_lay.setContentsMargins(14, 0, 12, 0)
        f_lay.setSpacing(6)

        # Delete button — before label so it stays visible with long names
        del_btn = QPushButton("×")
        del_btn.setFixedSize(20, 20)
        del_btn.setCursor(Qt.PointingHandCursor)
        del_btn.setStyleSheet(
            "QPushButton { background: rgba(239,68,68,0.0); border: none; "
            "border-radius: 4px; color: #94a3b8; font-size: 14px; font-weight: 700; "
            "padding: 0; }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); color: #f87171; }"
        )
        del_btn.clicked.connect(
            lambda _=None, m=item["mapping"]: self._on_delete_mapping(m)
        )
        f_lay.addWidget(del_btn)

        # Start in neutral loading state — background scan will update to ✓ or count.
        badge = QLabel("…")
        badge.setFixedHeight(18)
        badge.setStyleSheet(
            "color: #94a3b8; background: rgba(255,255,255,0.05); "
            "border-radius: 9px; font-size: 10px; padding: 0 5px; border: none;"
        )
        f_lay.addWidget(badge)
        self._nav_badges[key] = badge

        lbl = QLabel(item["label"])
        lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; font-size: 12px;"
        )
        f_lay.addWidget(lbl, 1)
        self._nav_labels[key] = lbl

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
        frame.setFixedHeight(42)
        frame.setCursor(Qt.PointingHandCursor)
        frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-left: 2px solid transparent; }"
        )
        f_lay = QHBoxLayout(frame)
        f_lay.setContentsMargins(18, 0, 18, 0)
        f_lay.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setFixedWidth(16)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; font-size: 11px;"
        )
        f_lay.addWidget(icon_lbl)
        self._nav_icons[key] = icon_lbl

        lbl = QLabel(item["label"])
        lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; font-size: 13px;"
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
                            "color: #60a5fa; background: transparent; border: none; font-size: 12px;"
                        )
                else:
                    frame.setStyleSheet(
                        "QFrame { background: transparent; border: none; "
                        "border-left: 2px solid transparent; }"
                    )
                    if key in self._nav_labels:
                        self._nav_labels[key].setStyleSheet(
                            "color: #cbd5e1; background: transparent; border: none; font-size: 12px;"
                        )
            else:
                if is_active:
                    frame.setStyleSheet(
                        "QFrame { background: rgba(59,130,246,0.1); border: none; "
                        "border-left: 2px solid #3b82f6; }"
                    )
                    if key in self._nav_labels:
                        self._nav_labels[key].setStyleSheet(
                            "color: #93c5fd; background: transparent; border: none; font-size: 13px;"
                        )
                    if key in self._nav_icons:
                        self._nav_icons[key].setStyleSheet(
                            "color: #93c5fd; background: transparent; border: none; font-size: 11px;"
                        )
                else:
                    frame.setStyleSheet(
                        "QFrame { background: transparent; border: none; "
                        "border-left: 2px solid transparent; }"
                    )
                    if key in self._nav_labels:
                        self._nav_labels[key].setStyleSheet(
                            "color: #cbd5e1; background: transparent; border: none; font-size: 13px;"
                        )
                    if key in self._nav_icons:
                        self._nav_icons[key].setStyleSheet(
                            "color: #94a3b8; background: transparent; border: none; font-size: 11px;"
                        )

        self._active_nav_key = active_key

    def update_mapping_badge(self, nav_key: str, error_count: int) -> None:
        """Update the sidebar badge for a mapping. Called by background scan and ViewMapping."""
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

    def confirm_mapping_badge(self, nav_key: str, error_count: int) -> None:
        """Called by ViewMapping after a full validation load completes.

        Marks the nav key as authoritative so the background scan cannot
        overwrite it with a stale or incorrectly-filtered count.
        """
        self._nav_keys_confirmed.add(nav_key)
        self.update_mapping_badge(nav_key, error_count)

    # ------------------------------------------------------------------
    # Mapping deletion
    # ------------------------------------------------------------------

    def _on_delete_mapping(self, mapping: dict) -> None:
        """Show confirmation popup, delete the mapping, then check for orphaned dims."""
        tx_t = mapping.get("transaction_table", "")
        tx_c = mapping.get("transaction_column", "")
        dim_t = mapping.get("dim_table", "")
        dim_c = mapping.get("dim_column", "")
        confirmed = msgbox.critical_question(
            self,
            "Delete Mapping",
            f"This will permanently remove the mapping:<br><br>"
            f"<b style='color:#60a5fa;'>{tx_t}.{tx_c}</b>"
            f"<span style='color:#94a3b8;'>  →  </span>"
            f"<b style='color:#60a5fa;'>{dim_t}.{dim_c}</b><br><br>"
            f"If this was the only mapping referencing the dimension table, "
            f"it will become orphaned and eligible for deletion.",
            confirm_label="Delete Mapping",
        )
        if not confirmed:
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
                go_to_dims = msgbox.warning_question(
                    self,
                    "Dimension Table No Longer In Use",
                    f"<b>{dim_table}</b> is no longer referenced by any mapping.<br><br>"
                    f"You can go to the <b>Dimension Tables</b> panel to delete it and "
                    f"free up space, or leave it for now.",
                    confirm_label="View Tables",
                    cancel_label="Later",
                )
            else:
                go_to_dims = False

            target = "d_sources" if go_to_dims else None
            self._reload_from_disk(target_key=target)

        w = Worker(worker)
        w.finished.connect(on_done)
        w.errored.connect(
            lambda exc: msgbox.critical(
                self, "Failed to Delete Mapping",
                f"The mapping could not be deleted. Check that the project files are accessible.\n\nDetail: {exc}"
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
            # Stop background workers on the outgoing view before destroying it
            if hasattr(self._active_view, "abandon_workers"):
                self._active_view.abandon_workers()
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
                on_badge_update=self.confirm_mapping_badge,
            )
        elif item["key"] == "t_sources":
            from ui.views.view_t_sources import ViewTSources
            self._active_view = ViewTSources(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
                on_go_mapping_setup=self._go_to_mapping_setup,
                on_go_screen1=self._go_to_screen1,
                on_chain_append=self._on_chain_append,
            )
        elif item["key"] == "d_sources":
            from ui.views.view_d_sources import ViewDSources
            self._active_view = ViewDSources(
                self._content_host,
                project=self.project,
                on_project_changed=self._reload_from_disk,
                on_go_mapping_setup=self._go_to_mapping_setup,
                on_go_screen1=self._go_to_screen1,
                on_chain_append=self._on_chain_append,
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

    def _sync_add_map_btn(self) -> None:
        has_t = bool(self.project.get("transaction_tables"))
        has_d = bool(self.project.get("dim_tables"))
        enabled = has_t and has_d
        self._add_map_btn.setEnabled(enabled)
        tip = "Add new mapping" if enabled else "No tables to map — add transaction and dimension tables first"
        self._add_map_btn.setToolTip(tip)

    def _reload_from_disk(self, target_key: str | None = None) -> None:
        try:
            updated = open_project(self.project_path)
        except Exception as exc:
            msgbox.critical(self, "Failed to Reload Project",
                            f"The project data could not be reloaded from disk. Try restarting the app if this persists.\n\nDetail: {exc}")
            return
        self.app.set_current_project(updated)
        self.app.show_screen(Screen3Main, project=updated, initial_nav_key=target_key)

    def _go_to_mapping_setup(self) -> None:
        try:
            updated = open_project(self.project_path)
        except Exception as exc:
            msgbox.critical(self, "Failed to Reload Project",
                            f"The project data could not be reloaded from disk. Try restarting the app if this persists.\n\nDetail: {exc}")
            return
        self.app.set_current_project(updated)
        self.app.show_screen(Screen2Mappings, project=updated, from_screen3=True)

    def _go_to_screen1(self) -> None:
        try:
            updated = open_project(self.project_path)
        except Exception as exc:
            msgbox.critical(self, "Failed to Reload Project",
                            f"The project data could not be reloaded from disk. Try restarting the app if this persists.\n\nDetail: {exc}")
            return
        self.app.set_current_project(updated)
        from ui.screen1_sources import Screen1Sources
        self.app.show_screen(Screen1Sources, project=updated, sources=[], from_screen3=True)

    def _on_chain_append(self, chain_context: dict) -> None:
        from ui.screen15_chain_mapper import Screen15ChainMapper
        self.app.show_screen(
            Screen15ChainMapper,
            project=self.project,
            chain_context=chain_context,
            sources=[],
        )

    def _go_to_launcher(self) -> None:
        from ui.screen0_launcher import Screen0Launcher
        self.app.show_screen(Screen0Launcher)
