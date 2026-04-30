from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

import ui.theme as theme
import ui.popups.msgbox as msgbox
from core.mapping_manager import get_mappings
from core.project_manager import create_project, open_project, validate_project_name
from ui.workers import LoadingOverlay, ScreenBase, Worker, clear_layout, make_scroll_area

_SIDEBAR_W = 340

# Avatar color palette: (text_color, bg_color) — cycled by name hash
_AVATAR_COLORS = [
    ("#60a5fa", "rgba(59,130,246,0.15)"),
    ("#22d3ee", "rgba(34,211,238,0.1)"),
    ("#fb923c", "rgba(251,146,60,0.1)"),
    ("#a78bfa", "rgba(167,139,250,0.1)"),
    ("#34d399", "rgba(52,211,153,0.1)"),
    ("#f472b6", "rgba(244,114,182,0.1)"),
    ("#fbbf24", "rgba(251,191,36,0.1)"),
    ("#94a3b8", "rgba(148,163,184,0.12)"),
]


def _row_label_html(name: str, company: str, selected: bool) -> str:
    name_color = "#93c5fd" if selected else "#94a3b8"
    company_part = (
        f"<br><span style='color:#94a3b8; font-size:13px; letter-spacing:0.5px;'>{company}</span>"
        if company else ""
    )
    return (
        f"<span style='color:{name_color}; font-size:15px; font-weight:500;'>{name}</span>"
        f"{company_part}"
    )


def _avatar_colors(name: str) -> tuple[str, str]:
    idx = sum(ord(c) for c in name) % len(_AVATAR_COLORS)
    return _AVATAR_COLORS[idx]


def _initials(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][0]).upper()
    return name[:2].upper() if len(name) >= 2 else (name[0].upper() if name else "?")


class _HeroFrame(QFrame):
    """Brand hero panel — paints an optional background image scaled to cover,
    with a semi-transparent dark overlay so text stays readable.
    Without an image it just shows the solid #13161e background.
    Recommended image size: 940 × 200 px.
    """

    def __init__(self, bg_pixmap: QPixmap | None = None, parent=None):
        super().__init__(parent)
        self._bg = bg_pixmap

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._bg:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        scaled = self._bg.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = (scaled.width() - self.width()) // 2
        y = (scaled.height() - self.height()) // 2
        painter.drawPixmap(-x, -y, scaled)
        # Dark overlay so text remains readable
        painter.fillRect(self.rect(), QColor(13, 17, 23, 200))
        painter.end()


class _DarkModeToggle(QFrame):
    """Clickable pill toggle — visually on/off, emits toggled(bool)."""

    toggled = Signal(bool)

    def __init__(self, on: bool = True, parent=None):
        super().__init__(parent)
        self._on = on
        self.setFixedSize(36, 20)
        self.setCursor(Qt.PointingHandCursor)
        self.setObjectName("dm_track")

        self._thumb = QFrame(self)
        self._thumb.setObjectName("dm_thumb")
        self._thumb.setFixedSize(14, 14)
        self._thumb.setStyleSheet(
            "QFrame#dm_thumb { background: white; border-radius: 7px; border: none; }"
        )
        self._refresh()

    def _refresh(self):
        track = "#3b82f6" if self._on else "rgba(255,255,255,0.18)"
        self.setStyleSheet(
            f"QFrame#dm_track {{ background: {track}; border-radius: 10px; border: none; }}"
        )
        self._thumb.move(19 if self._on else 3, 3)
        self._thumb.raise_()

    def mousePressEvent(self, event):
        self._on = not self._on
        self._refresh()
        self.toggled.emit(self._on)


def _format_modified(project_path: str) -> str:
    try:
        mtime = (Path(project_path) / "project.json").stat().st_mtime
        dt = datetime.fromtimestamp(mtime)
        delta = datetime.now() - dt
        if delta.days == 0:
            return "Today"
        elif delta.days == 1:
            return "Yesterday"
        elif delta.days < 7:
            return f"{delta.days} days ago"
        else:
            return dt.strftime("%d %b %Y")
    except OSError:
        return "Unknown"


class Screen0Launcher(ScreenBase):
    """Project launcher — left list panel + right brand/detail panel."""

    def __init__(self, app, **kwargs):
        super().__init__()
        self.app = app
        self._selected_path: str | None = None
        self._selected_row: QFrame | None = None
        self._selected_name_lbl: QLabel | None = None
        self._project_rows: list[tuple[dict, QFrame]] = []  # (state, row_widget)

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Left panel ────────────────────────────────────────────────
        left = QFrame()
        left.setObjectName("launcher_left")
        left.setFixedWidth(_SIDEBAR_W)
        left.setStyleSheet(
            "QFrame#launcher_left { background: #13161e; "
            "border-right: 1px solid rgba(255,255,255,0.06); }"
        )
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Header: "All Projects" + count pill
        header = QFrame()
        header.setFixedHeight(64)
        header.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(18, 0, 18, 0)
        h_lay.setSpacing(0)

        title_lbl = QLabel("All Projects")
        title_lbl.setFont(theme.font(15, "bold"))
        title_lbl.setStyleSheet("color: #f1f5f9; background: transparent; border: none;")
        h_lay.addWidget(title_lbl)
        h_lay.addStretch()

        self._count_pill = QLabel("0 projects")
        self._count_pill.setFont(theme.font(13))
        self._count_pill.setFixedHeight(30)
        self._count_pill.setStyleSheet(
            "color: #cbd5e1; background: rgba(255,255,255,0.05); "
            "padding: 0px 8px; border-radius: 10px; border: none;"
        )
        h_lay.addWidget(self._count_pill)
        left_layout.addWidget(header)

        # Search bar
        search_frame = QFrame()
        search_frame.setFixedHeight(54)
        search_frame.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        s_lay = QHBoxLayout(search_frame)
        s_lay.setContentsMargins(12, 10, 12, 10)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search projects…")
        self._search.setFixedHeight(34)
        self._search.textChanged.connect(self._on_search)
        s_lay.addWidget(self._search)
        left_layout.addWidget(search_frame)

        # Project list (scroll area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(0)
        self._list_layout.setAlignment(Qt.AlignTop)
        scroll.setWidget(self._list_container)
        left_layout.addWidget(scroll, 1)

        # Footer: New Project only
        footer = QFrame()
        footer.setFixedHeight(60)
        footer.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(12, 12, 12, 12)

        new_btn = QPushButton("+ New Project")
        new_btn.setObjectName("btn_primary")
        new_btn.setFixedHeight(36)
        new_btn.setFont(theme.font(13, "bold"))
        new_btn.clicked.connect(self._on_new_click)
        f_lay.addWidget(new_btn)
        left_layout.addWidget(footer)

        root.addWidget(left)

        # ── Right panel ───────────────────────────────────────────────
        right = QFrame()
        right.setObjectName("launcher_right")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Brand hero (200px) — supports optional background image via branding.json
        _hero_bg: QPixmap | None = None
        _bg_path = theme.hero_bg_path()
        if _bg_path:
            from utils.paths import resource_path
            _abs_bg = resource_path(str(_bg_path))
            if _abs_bg.exists():
                _hero_bg = QPixmap(str(_abs_bg))

        hero = _HeroFrame(_hero_bg)
        hero.setObjectName("brand_hero")
        hero.setFixedHeight(240)
        hero.setStyleSheet(
            "QFrame#brand_hero { background: #13161e; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); }"
        )
        hero_lay = QHBoxLayout(hero)
        hero_lay.setContentsMargins(48, 0, 48, 0)
        hero_lay.setSpacing(24)
        hero_lay.setAlignment(Qt.AlignVCenter)

        # Logo box — show branding image inside, or initials fallback
        logo_box = QFrame()
        logo_box.setFixedSize(76, 76)
        logo_box.setStyleSheet(
            "QFrame { background: #2161AC; border-radius: 18px; border: none; }"
        )
        logo_inner = QVBoxLayout(logo_box)
        logo_inner.setContentsMargins(4, 4, 4, 4)

        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignCenter)
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        _logo_path = theme.logo_path()
        if _logo_path:
            from utils.paths import resource_path
            _abs_logo = resource_path(str(_logo_path))
            if _abs_logo.exists():
                px = QPixmap(str(_abs_logo)).scaled(
                    62, 62, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                logo_lbl.setPixmap(px)
            else:
                logo_lbl.setText("CS")
                logo_lbl.setStyleSheet(
                    "color: white; background: transparent; border: none; "
                    "font-size: 18px; font-weight: 700;"
                )
        else:
            logo_lbl.setText("CS")
            logo_lbl.setStyleSheet(
                "color: white; background: transparent; border: none; "
                "font-size: 18px; font-weight: 700;"
            )
        logo_inner.addWidget(logo_lbl)
        hero_lay.addWidget(logo_box)

        # App name + subtitle — font sizes set via stylesheet to override global QSS
        text_block = QVBoxLayout()
        text_block.setSpacing(4)
        text_block.setAlignment(Qt.AlignVCenter)

        app_name_lbl = QLabel(theme.company_name())
        app_name_lbl.setStyleSheet(
            "color: #f1f5f9; background: transparent; border: none; "
            "font-size: 34px; font-weight: 700; letter-spacing: 0px;"
        )
        text_block.addWidget(app_name_lbl)

        app_sub_lbl = QLabel("Data Cleansing and Standardization Tool.")
        app_sub_lbl.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; font-size: 17px;"
        )
        text_block.addWidget(app_sub_lbl)
        hero_lay.addLayout(text_block)
        hero_lay.addStretch()
        right_layout.addWidget(hero)

        # Detail area (expanding)
        detail_area = QFrame()
        detail_area.setObjectName("detail_area")
        detail_lay = QVBoxLayout(detail_area)
        detail_lay.setContentsMargins(32, 28, 32, 16)
        detail_lay.setSpacing(14)

        section_lbl = QLabel("SELECTED PROJECT")
        section_lbl.setFont(theme.font(10, "bold"))
        section_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; letter-spacing: 1px;"
        )
        detail_lay.addWidget(section_lbl)

        # Detail card
        detail_card = QFrame()
        detail_card.setObjectName("detail_card")
        detail_card.setStyleSheet(
            "QFrame#detail_card { background: rgba(255,255,255,0.02); "
            "border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; }"
        )
        card_lay = QVBoxLayout(detail_card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        def _detail_row(key: str, last: bool = False) -> tuple[QFrame, QLabel]:
            row = QFrame()
            sep = "" if last else "border-bottom: 1px solid rgba(255,255,255,0.04);"
            row.setStyleSheet(
                f"QFrame {{ background: transparent; border: none; {sep} }}"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(18, 11, 18, 11)
            rl.setSpacing(0)

            k = QLabel(key)
            k.setFont(theme.font(12))
            k.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
            k.setFixedWidth(130)
            rl.addWidget(k)

            v = QLabel("—")
            v.setFont(theme.font(12, "bold"))
            v.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
            rl.addWidget(v, 1)
            return row, v

        r1, self._v_name = _detail_row("Project Name")
        r2, self._v_company = _detail_row("Company")
        r3, self._v_modified = _detail_row("Last Modified")

        # Path row — info only
        r4, self._v_path = _detail_row("Folder Path")
        self._v_path.setFont(theme.font(11))
        self._v_path.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-family: 'Courier New', monospace;"
        )

        # Final file row
        _btn_ss = (
            "QPushButton { background: transparent; border: 1px solid rgba(255,255,255,0.12); "
            "border-radius: 6px; color: #94a3b8; font-size: 10px; font-weight: 500; }"
            "QPushButton:hover { border-color: rgba(255,255,255,0.28); color: #f1f5f9; }"
            "QPushButton:disabled { opacity: 0.35; }"
        )
        r5 = QFrame()
        r5.setStyleSheet("QFrame { background: transparent; border: none; }")
        r5_lay = QHBoxLayout(r5)
        r5_lay.setContentsMargins(18, 11, 18, 11)
        r5_lay.setSpacing(0)
        r5_key = QLabel("Final File")
        r5_key.setFont(theme.font(12))
        r5_key.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        r5_key.setFixedWidth(130)
        r5_lay.addWidget(r5_key)
        self._v_final = QLabel("—")
        self._v_final.setFont(theme.font(11))
        self._v_final.setStyleSheet(
            "color: #cbd5e1; background: transparent; border: none; "
            "font-family: 'Courier New', monospace;"
        )
        r5_lay.addWidget(self._v_final, 1)
        self._open_final_btn = QPushButton("Open Folder")
        self._open_final_btn.setFixedHeight(26)
        self._open_final_btn.setFixedWidth(88)
        self._open_final_btn.setEnabled(False)
        self._open_final_btn.setStyleSheet(_btn_ss)
        r5_lay.addWidget(self._open_final_btn)

        for r in (r1, r2, r3, r4, r5):
            card_lay.addWidget(r)
        detail_lay.addWidget(detail_card)

        # Action buttons: Open Project + Delete
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._open_btn = QPushButton("Open Project")
        self._open_btn.setObjectName("btn_primary")
        self._open_btn.setFixedHeight(38)
        self._open_btn.setFont(theme.font(13))
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._on_open_click)
        btn_row.addWidget(self._open_btn, 1)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("btn_danger")
        self._delete_btn.setFixedHeight(38)
        self._delete_btn.setFixedWidth(90)
        self._delete_btn.setFont(theme.font(13))
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete_click)
        btn_row.addWidget(self._delete_btn)
        detail_lay.addLayout(btn_row)
        detail_lay.addStretch()

        right_layout.addWidget(detail_area, 1)

        # Status bar (36px)
        status_bar = QFrame()
        status_bar.setObjectName("status_bar")
        status_bar.setFixedHeight(36)
        status_bar.setStyleSheet(
            "QFrame#status_bar { background: #13161e; "
            "border-top: 1px solid rgba(255,255,255,0.06); }"
        )
        sb_lay = QHBoxLayout(status_bar)
        sb_lay.setContentsMargins(28, 0, 28, 0)
        sb_lay.setSpacing(8)

        self._status_lbl = QLabel(f"{theme.company_name()} v1.0 · 0 projects loaded")
        self._status_lbl.setFont(theme.font(11))
        self._status_lbl.setStyleSheet("color: #1e293b; background: transparent; border: none;")
        sb_lay.addWidget(self._status_lbl)
        sb_lay.addStretch()

        dm_lbl = QLabel("Dark Mode")
        dm_lbl.setFont(theme.font(11))
        dm_lbl.setStyleSheet("color: #94a3b8; background: transparent; border: none;")
        sb_lay.addWidget(dm_lbl)

        self._dark_toggle = _DarkModeToggle(on=self.app.is_dark_mode_enabled())
        self._dark_toggle.toggled.connect(self.app.set_dark_mode)
        sb_lay.addWidget(self._dark_toggle)

        right_layout.addWidget(status_bar)
        root.addWidget(right, 1)

        self._setup_overlay("Working...")
        self._load_and_render_projects()

    # ------------------------------------------------------------------
    # Project list
    # ------------------------------------------------------------------

    def _load_and_render_projects(self) -> None:
        clear_layout(self._list_layout)
        self._project_rows.clear()
        self._selected_path = None
        self._selected_row = None
        self._selected_name_lbl = None
        self._open_btn.setEnabled(False)
        self._delete_btn.setEnabled(False)
        self._clear_detail_card()

        paths = self.app.get_known_projects()

        def _load():
            loaded = []
            for p in paths:
                try:
                    loaded.append(open_project(Path(p)))
                except (FileNotFoundError, ValueError):
                    continue
            return loaded

        def _render(loaded):
            count = len(loaded)
            self._count_pill.setText(f"{count} project{'s' if count != 1 else ''}")
            self._status_lbl.setText(
                f"{theme.company_name()} v1.0 · {count} project{'s' if count != 1 else ''} loaded"
            )
            if not loaded:
                lbl = QLabel("No projects yet.")
                lbl.setFont(theme.font(12))
                lbl.setStyleSheet("color: #94a3b8; padding: 16px 18px; background: transparent;")
                self._list_layout.addWidget(lbl)
                return
            for state in loaded:
                row = self._make_project_row(state)
                self._list_layout.addWidget(row)
                self._project_rows.append((state, row))

        self._run_background(_load, on_success=_render)

    def _make_project_row(self, state: dict) -> QFrame:
        path = state.get("project_path", "")
        name = state.get("project_name", "Untitled")
        company = state.get("company", "")
        text_col, bg_col = _avatar_colors(name)
        inits = _initials(name)

        row = QFrame()
        row.setFixedHeight(66)
        row.setCursor(Qt.PointingHandCursor)
        row.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-left: 2px solid transparent; "
            "border-bottom: 1px solid rgba(255,255,255,0.03); }"
        )

        rl = QHBoxLayout(row)
        rl.setContentsMargins(18, 0, 18, 0)
        rl.setSpacing(11)

        avatar = QLabel(inits)
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setFont(theme.font(12, "bold"))
        avatar.setStyleSheet(
            f"QLabel {{ background: {bg_col}; color: {text_col}; "
            "border-radius: 9px; border: none; }}"
        )
        rl.addWidget(avatar)

        name_lbl = QLabel()
        name_lbl.setTextFormat(Qt.RichText)
        name_lbl.setText(_row_label_html(name, company, selected=False))
        name_lbl.setStyleSheet("background: transparent; border: none;")
        name_lbl._proj_name = name
        name_lbl._proj_company = company
        rl.addWidget(name_lbl, 1)

        def _click(event=None, p=path, r=row, nl=name_lbl, s=state):
            self._select_row(p, r, nl, s)

        row.mousePressEvent = _click
        avatar.mousePressEvent = _click
        name_lbl.mousePressEvent = _click

        return row

    def _select_row(self, path: str, row: QFrame, name_lbl: QLabel, state: dict) -> None:
        # Deselect previous
        if self._selected_row:
            self._selected_row.setStyleSheet(
                "QFrame { background: transparent; border: none; "
                "border-left: 2px solid transparent; "
                "border-bottom: 1px solid rgba(255,255,255,0.03); }"
            )
        if self._selected_name_lbl:
            lbl = self._selected_name_lbl
            lbl.setText(_row_label_html(lbl._proj_name, lbl._proj_company, selected=False))

        # Select new row
        row.setStyleSheet(
            "QFrame { background: rgba(59,130,246,0.09); border: none; "
            "border-left: 2px solid #3b82f6; "
            "border-bottom: 1px solid rgba(255,255,255,0.03); }"
        )
        name_lbl.setText(_row_label_html(name_lbl._proj_name, name_lbl._proj_company, selected=True))

        self._selected_path = path
        self._selected_row = row
        self._selected_name_lbl = name_lbl
        self._open_btn.setEnabled(True)
        self._delete_btn.setEnabled(True)
        self._update_detail_card(state)

    def _update_detail_card(self, state: dict) -> None:
        self._v_name.setText(state.get("project_name", "—"))
        self._v_company.setText(state.get("company", "—"))
        self._v_modified.setText(_format_modified(state.get("project_path", "")))
        path = state.get("project_path", "—")
        self._v_path.setText(path)
        folder = Path(path)

        try:
            self._open_final_btn.clicked.disconnect()
        except RuntimeError:
            pass

        final_path = folder / "final" / "final_updated.xlsx"
        self._v_final.setText(str(final_path))

        def _open_final(p=final_path):
            if p.exists():
                subprocess.Popen(["explorer", "/select,", str(p)])
            else:
                d = p.parent
                d.mkdir(parents=True, exist_ok=True)
                subprocess.Popen(["explorer", str(d)])

        self._open_final_btn.setEnabled(folder.exists())
        if folder.exists():
            self._open_final_btn.clicked.connect(lambda: _open_final())

    def _clear_detail_card(self) -> None:
        for lbl in (self._v_name, self._v_company, self._v_modified, self._v_path, self._v_final):
            lbl.setText("—")
        self._open_final_btn.setEnabled(False)
        try:
            self._open_final_btn.clicked.disconnect()
        except RuntimeError:
            pass

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _on_search(self, text: str) -> None:
        term = text.strip().lower()
        for state, row in self._project_rows:
            name = state.get("project_name", "").lower()
            row.setVisible(not term or term in name)

    # ------------------------------------------------------------------
    # Actions (logic unchanged)
    # ------------------------------------------------------------------

    def _on_open_click(self) -> None:
        if not self._selected_path:
            return
        selected_path = self._selected_path

        def _load():
            state = open_project(Path(selected_path))
            project_path = Path(state["project_path"])
            try:
                mappings = get_mappings(project_path)
            except Exception:
                mappings = []
            return state, mappings

        def _on_success(result):
            state, mappings = result
            self.app.set_current_project(state)
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
                msgbox.critical(self, "Navigation Error",
                                f"A required screen could not be loaded.\n\nDetail: {exc}")

        def _on_error(exc):
            msgbox.critical(self, "Failed to Open Project",
                            f"The project could not be opened. The file may be missing or corrupted.\n\nDetail: {exc}")

        self._run_background(_load, on_success=_on_success, on_error=_on_error)

    def _on_new_click(self) -> None:
        self.app.show_screen(NewProjectScreen)

    def _on_delete_click(self) -> None:
        if not self._selected_path:
            return
        project_path = Path(self._selected_path)
        reply = msgbox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete <b>{project_path.name}</b>?<br><br>"
            "The project folder and all its data will be permanently removed. "
            "This action cannot be undone.",
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
            msgbox.critical(self, "Failed to Delete Project",
                            f"The project could not be deleted. Check that no files are open.\n\nDetail: {exc}")
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
# New Project Screen — full 1280×720 backdrop with centred card
# ---------------------------------------------------------------------------

class NewProjectScreen(ScreenBase):
    """Full-window screen: dark backdrop + centred 480px card for creating a project."""

    def __init__(self, app, **kwargs):
        super().__init__()
        self.app = app

        # Dark backdrop fills the full window
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setAlignment(Qt.AlignCenter)

        # ── Card ──────────────────────────────────────────────────────
        card = QFrame()
        card.setFixedWidth(540)
        card.setStyleSheet(
            "QFrame { background: #13161e; "
            "border: 1px solid rgba(255,255,255,0.09); border-radius: 12px; }"
        )
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(80)
        header.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-bottom: 1px solid rgba(255,255,255,0.06); border-radius: 0; }"
        )
        h_lay = QHBoxLayout(header)
        h_lay.setContentsMargins(22, 0, 18, 0)
        h_lay.setSpacing(12)

        icon_box = QFrame()
        icon_box.setFixedSize(34, 34)
        icon_box.setStyleSheet(
            "QFrame { background: #3b82f6; border-radius: 8px; border: none; }"
        )
        ib_lay = QVBoxLayout(icon_box)
        ib_lay.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("+")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setContentsMargins(0, 0, 0, 6)
        icon_lbl.setStyleSheet(
            "color: white; background: transparent; border: none; "
            "font-size: 25px; font-weight: 700;"
        )
        ib_lay.addWidget(icon_lbl)
        h_lay.addWidget(icon_box)

        header_lbl = QLabel(
            "<span style='color:#f1f5f9; font-size:16px; font-weight:600;'>New Project</span>"
            "<br>"
            "<span style='color:#94a3b8; font-size:13px;'>Fill in the details to create a new workspace</span>"
        )
        header_lbl.setTextFormat(Qt.RichText)
        header_lbl.setStyleSheet("background: transparent; border: none;")
        h_lay.addWidget(header_lbl, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.04); "
            "border: 1px solid rgba(255,255,255,0.08); border-radius: 6px; "
            "color: #cbd5e1; font-size: 12px; padding: 0; }"
            "QPushButton:hover { background: rgba(239,68,68,0.15); color: #f87171; }"
        )
        close_btn.clicked.connect(self._go_back)
        h_lay.addWidget(close_btn)
        card_lay.addWidget(header)

        # Body — form fields
        body = QFrame()
        body.setStyleSheet("QFrame { background: transparent; border: none; }")
        b_lay = QVBoxLayout(body)
        b_lay.setContentsMargins(28, 30, 28, 30)
        b_lay.setSpacing(24)

        def _field(label_text: str) -> tuple[QFrame, QLineEdit]:
            wrap = QFrame()
            wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
            wl = QVBoxLayout(wrap)
            wl.setContentsMargins(0, 0, 0, 0)
            wl.setSpacing(7)
            lbl = QLabel(label_text.upper())
            lbl.setStyleSheet(
                "color: #94a3b8; background: transparent; border: none; "
                "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
            )
            wl.addWidget(lbl)
            entry = QLineEdit()
            entry.setMinimumHeight(42)
            entry.setStyleSheet("QLineEdit { padding: 2px 10px; }")
            wl.addWidget(entry)
            return wrap, entry

        name_wrap, self._name_entry = _field("Project Name")
        self._name_entry.setPlaceholderText("e.g. Sales Module")
        self._name_entry.setMaxLength(100)
        b_lay.addWidget(name_wrap)

        company_wrap, self._company_entry = _field("Company Name")
        self._company_entry.setPlaceholderText("e.g. Acme Corp")
        self._company_entry.setMaxLength(100)
        b_lay.addWidget(company_wrap)

        # Save location row
        loc_wrap = QFrame()
        loc_wrap.setStyleSheet("QFrame { background: transparent; border: none; }")
        lw_lay = QVBoxLayout(loc_wrap)
        lw_lay.setContentsMargins(0, 0, 0, 0)
        lw_lay.setSpacing(7)
        loc_lbl = QLabel("SAVE LOCATION")
        loc_lbl.setStyleSheet(
            "color: #94a3b8; background: transparent; border: none; "
            "font-size: 10px; font-weight: 600; letter-spacing: 1px;"
        )
        lw_lay.addWidget(loc_lbl)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self._folder_entry = QLineEdit()
        self._folder_entry.setPlaceholderText("Choose a folder…")
        self._folder_entry.setMinimumHeight(42)
        self._folder_entry.setStyleSheet("QLineEdit { padding: 2px 10px; }")
        self._folder_entry.setReadOnly(True)
        path_row.addWidget(self._folder_entry, 1)
        browse_btn = QPushButton("Browse…")
        browse_btn.setObjectName("btn_primary")
        browse_btn.setFixedHeight(42)
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(browse_btn)
        lw_lay.addLayout(path_row)
        b_lay.addWidget(loc_wrap)

        card_lay.addWidget(body)

        # Footer
        footer = QFrame()
        footer.setFixedHeight(66)
        footer.setStyleSheet(
            "QFrame { background: transparent; border: none; "
            "border-top: 1px solid rgba(255,255,255,0.06); border-radius: 0; }"
        )
        f_lay = QHBoxLayout(footer)
        f_lay.setContentsMargins(22, 0, 22, 0)
        f_lay.setSpacing(8)
        f_lay.setAlignment(Qt.AlignVCenter)

        self._error_lbl = QLabel("")
        self._error_lbl.setStyleSheet(
            "color: #f87171; background: transparent; border: none; font-size: 11px;"
        )
        f_lay.addWidget(self._error_lbl, 1)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("btn_ghost")
        cancel_btn.setFixedHeight(36)
        cancel_btn.setFixedWidth(90)
        cancel_btn.clicked.connect(self._go_back)
        f_lay.addWidget(cancel_btn, 0, Qt.AlignVCenter)

        create_btn = QPushButton("Create Project")
        create_btn.setObjectName("btn_primary")
        create_btn.setFixedHeight(36)
        create_btn.setFixedWidth(130)
        create_btn.clicked.connect(self._on_create)
        f_lay.addWidget(create_btn, 0, Qt.AlignVCenter)
        card_lay.addWidget(footer)

        root.addWidget(card)
        self._setup_overlay("Creating project…")

    # ── Actions ───────────────────────────────────────────────────────

    def _go_back(self) -> None:
        self.app.show_screen(Screen0Launcher)

    def _on_browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose save location")
        if folder:
            self._folder_entry.setText(folder)

    def _on_create(self) -> None:
        name = self._name_entry.text().strip()
        company = self._company_entry.text().strip()
        folder = self._folder_entry.text().strip()

        name_error = validate_project_name(name)
        if name_error:
            self._error_lbl.setText(name_error)
            return
        if not company:
            self._error_lbl.setText("Company name is required.")
            return
        if not folder:
            self._error_lbl.setText("Please choose a save location.")
            return
        if not Path(folder).exists():
            self._error_lbl.setText("Save location does not exist.")
            return
        self._error_lbl.setText("")

        storage_format = self.app.get_default_storage_format()

        def worker():
            project_path = create_project(name, company, Path(folder), storage_format)
            return open_project(project_path)

        def on_success(state):
            self.app.set_current_project(state)
            self.app.register_project(state["project_path"])
            try:
                from ui.screen1_sources import Screen1Sources
                self.app.show_screen(Screen1Sources, project=state)
            except ImportError:
                self.app.show_screen(Screen0Launcher)

        def on_error(exc):
            self._error_lbl.setText(f"Could not create project: {exc}")

        self._run_background(worker, on_success, on_error)
