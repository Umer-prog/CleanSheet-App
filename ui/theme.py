import json
from pathlib import Path

from PySide6.QtGui import QFont

_branding: dict = {}

# Fixed dark-theme color palette used for inline overrides
_COLORS = {
    "primary":        "#3b82f6",
    "secondary":      "#0f1117",
    "accent":         "#f87171",
    "text_dark":      "#f1f5f9",
    "text_light":     "#f1f5f9",
    "sidebar_bg":     "#13161e",
    "sidebar_text":   "#f1f5f9",
    "card":           "#13161e",
    # Foreground ramp (dark): primary -> secondary -> muted -> subtle
    "text_secondary": "#cbd5e1",
    "text_muted":     "#94a3b8",
    "text_subtle":    "#64748b",
    "selection":      "rgba(59,130,246,0.10)",
}

# Global QSS — dark (default)
DARK_QSS = """
QMainWindow, QWidget {
    background-color: #0f1117;
    color: #f1f5f9;
    font-family: 'Segoe UI';
    font-size: 13px;
}
QFrame#sidebar {
    background-color: #13161e;
    border-right: 1px solid rgba(255,255,255,0.07);
}
QFrame#topbar {
    background-color: #13161e;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
QLineEdit {
    background-color: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 7px;
    padding: 4px 10px;
    color: #f1f5f9;
    min-height: 32px;
}
QLineEdit:focus { border-color: #3b82f6; }
QLineEdit:disabled { color: rgba(148,163,184,0.55); }
QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 7px;
    color: #f1f5f9;
    padding: 6px 14px;
}
QPushButton#btn_primary {
    background-color: #3b82f6;
    color: white;
    font-weight: 600;
}
QPushButton#btn_primary:hover { background-color: #2563eb; }
QPushButton#btn_primary:disabled { background-color: rgba(59,130,246,0.35); color: rgba(255,255,255,0.5); }
QPushButton#btn_ghost {
    background-color: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.09);
    color: #cbd5e1;
}
QPushButton#btn_ghost:hover { background-color: rgba(255,255,255,0.07); }
QPushButton#btn_ghost:disabled { color: rgba(148,163,184,0.4); }
QPushButton#btn_danger {
    background-color: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.2);
    color: #f87171;
}
QPushButton#btn_danger:hover { background-color: rgba(239,68,68,0.13); }
QPushButton#btn_danger:disabled { color: rgba(248,113,113,0.35); border-color: rgba(239,68,68,0.1); }
QPushButton#btn_outline {
    border: 1px solid #3b82f6;
    color: #3b82f6;
}
QPushButton#btn_outline:hover { background-color: rgba(59,130,246,0.08); }
QPushButton#btn_outline:disabled { border-color: rgba(59,130,246,0.3); color: rgba(59,130,246,0.3); }
QTableView {
    background-color: transparent;
    border: none;
    gridline-color: rgba(255,255,255,0.04);
    selection-background-color: rgba(59,130,246,0.12);
    selection-color: #93c5fd;
    outline: none;
}
QTableView::item { padding: 8px 12px; border-bottom: 1px solid rgba(255,255,255,0.04); }
QHeaderView::section {
    background-color: #13161e;
    color: #cbd5e1;
    font-size: 11px;
    padding: 6px 12px;
    border: none;
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
QScrollBar:vertical {
    background: rgba(255,255,255,0.03);
    width: 8px;
    margin: 2px 2px 2px 0;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(255,255,255,0.22);
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: rgba(255,255,255,0.38); }
QScrollBar::handle:vertical:pressed { background: rgba(255,255,255,0.50); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background: rgba(255,255,255,0.03);
    height: 8px;
    margin: 0 2px 2px 2px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: rgba(255,255,255,0.22);
    border-radius: 4px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: rgba(255,255,255,0.38); }
QScrollBar::handle:horizontal:pressed { background: rgba(255,255,255,0.50); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 10px 18px; border-left: 2px solid transparent; color: #cbd5e1; }
QListWidget::item:selected { background: rgba(59,130,246,0.10); border-left-color: #3b82f6; color: #93c5fd; }
QListWidget::item:hover { background: rgba(255,255,255,0.03); }
QDialog, QDialog QWidget { background-color: #0f1117; }
QComboBox {
    background-color: #3b82f6;
    border: none;
    border-radius: 7px;
    color: white;
    padding: 4px 12px;
    font-weight: 600;
    min-height: 34px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox::down-arrow { width: 0; height: 0; }
QComboBox QAbstractItemView {
    background-color: #13161e;
    color: #f1f5f9;
    border: 1px solid rgba(255,255,255,0.07);
    selection-background-color: rgba(59,130,246,0.20);
    outline: none;
}
QTextEdit, QPlainTextEdit {
    background-color: #13161e;
    color: #f1f5f9;
    border: none;
    border-radius: 7px;
    padding: 4px;
}
QCheckBox { color: #f1f5f9; spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 4px;
    background: rgba(255,255,255,0.04);
}
QCheckBox::indicator:checked { background: #3b82f6; border-color: #3b82f6; }
QProgressBar {
    background: rgba(255,255,255,0.06);
    border: none;
    border-radius: 3px;
    text-align: center;
}
QProgressBar::chunk { background: #3b82f6; border-radius: 3px; }
"""

# Alias kept for any existing references
QSS = DARK_QSS

LIGHT_QSS = """
QMainWindow, QWidget {
    background-color: #f1f5f9;
    color: #0f172a;
    font-family: 'Segoe UI';
    font-size: 13px;
}
QFrame#sidebar, QFrame#launcher_left {
    background-color: #ffffff;
    border-right: 1px solid rgba(0,0,0,0.08);
}
QFrame#topbar, QFrame#brand_hero, QFrame#status_bar {
    background-color: #ffffff;
    border-color: rgba(0,0,0,0.07);
}
QLineEdit {
    background-color: #ffffff;
    border: 1px solid rgba(0,0,0,0.12);
    border-radius: 7px;
    padding: 4px 10px;
    color: #0f172a;
    min-height: 32px;
}
QLineEdit:focus { border-color: #3b82f6; }
QLineEdit:disabled { color: #94a3b8; }
QPushButton {
    background-color: transparent;
    border: none;
    border-radius: 7px;
    color: #0f172a;
    padding: 6px 14px;
}
QPushButton#btn_primary {
    background-color: #3b82f6;
    color: white;
    font-weight: 600;
}
QPushButton#btn_primary:hover { background-color: #2563eb; }
QPushButton#btn_primary:disabled { background-color: rgba(59,130,246,0.35); color: rgba(255,255,255,0.6); }
QPushButton#btn_ghost {
    background-color: rgba(0,0,0,0.04);
    border: 1px solid rgba(0,0,0,0.1);
    color: #475569;
}
QPushButton#btn_ghost:hover { background-color: rgba(0,0,0,0.07); }
QPushButton#btn_ghost:disabled { color: rgba(71,85,105,0.4); }
QPushButton#btn_danger {
    background-color: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.2);
    color: #dc2626;
}
QPushButton#btn_danger:hover { background-color: rgba(239,68,68,0.12); }
QPushButton#btn_danger:disabled { color: rgba(220,38,38,0.35); }
QPushButton#btn_outline {
    border: 1px solid #3b82f6;
    color: #3b82f6;
}
QPushButton#btn_outline:hover { background-color: rgba(59,130,246,0.08); }
QTableView {
    background-color: #ffffff;
    border: none;
    gridline-color: rgba(0,0,0,0.05);
    selection-background-color: rgba(59,130,246,0.1);
    selection-color: #1d4ed8;
    outline: none;
}
QTableView::item { padding: 8px 12px; border-bottom: 1px solid rgba(0,0,0,0.05); }
QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    font-size: 11px;
    padding: 6px 12px;
    border: none;
    border-bottom: 1px solid rgba(0,0,0,0.07);
}
QScrollBar:vertical {
    background: rgba(0,0,0,0.05);
    width: 8px;
    margin: 2px 2px 2px 0;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: rgba(0,0,0,0.22);
    border-radius: 4px;
    min-height: 32px;
}
QScrollBar::handle:vertical:hover { background: rgba(0,0,0,0.38); }
QScrollBar::handle:vertical:pressed { background: rgba(0,0,0,0.50); }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal {
    background: rgba(0,0,0,0.05);
    height: 8px;
    margin: 0 2px 2px 2px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: rgba(0,0,0,0.22);
    border-radius: 4px;
    min-width: 32px;
}
QScrollBar::handle:horizontal:hover { background: rgba(0,0,0,0.38); }
QScrollBar::handle:horizontal:pressed { background: rgba(0,0,0,0.50); }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QScrollArea { border: none; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QListWidget { background: transparent; border: none; outline: none; }
QListWidget::item { padding: 10px 18px; border-left: 2px solid transparent; color: #475569; }
QListWidget::item:selected { background: rgba(59,130,246,0.08); border-left-color: #3b82f6; color: #1d4ed8; }
QListWidget::item:hover { background: rgba(0,0,0,0.03); }
QDialog, QDialog QWidget { background-color: #f1f5f9; }
QComboBox {
    background-color: #3b82f6;
    border: none;
    border-radius: 7px;
    color: white;
    padding: 4px 12px;
    font-weight: 600;
    min-height: 34px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #0f172a;
    border: 1px solid rgba(0,0,0,0.08);
    selection-background-color: rgba(59,130,246,0.12);
    outline: none;
}
QCheckBox { color: #0f172a; spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px;
    border: 1px solid rgba(0,0,0,0.2);
    border-radius: 4px;
    background: #ffffff;
}
QCheckBox::indicator:checked { background: #3b82f6; border-color: #3b82f6; }
QProgressBar {
    background: rgba(0,0,0,0.06);
    border: none;
    border-radius: 3px;
    text-align: center;
}
QProgressBar::chunk { background: #3b82f6; border-radius: 3px; }
"""

_FONT_FAMILY = "Segoe UI"


def apply_theme(qapp, dark: bool) -> None:
    """Swap the application stylesheet between dark and light."""
    from PySide6.QtWidgets import QApplication
    qapp = qapp or QApplication.instance()
    if qapp:
        qapp.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)


def load(branding_path: Path) -> None:
    """Load branding.json. Silently uses defaults if missing or invalid."""
    global _branding
    try:
        with open(branding_path, encoding="utf-8") as f:
            _branding = json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        _branding = {}


def get(key: str, fallback: str = "#3b82f6") -> str:
    """Return a color token value."""
    return _COLORS.get(key, fallback)


def card_color() -> str:
    return _COLORS["card"]


def selection_color() -> str:
    return "rgba(59,130,246,0.10)"


def font(size: int, weight: str = "normal") -> QFont:
    """Return a QFont for the standard app typeface."""
    f = QFont(_FONT_FAMILY, size)
    if weight == "bold":
        f.setWeight(QFont.Weight.Bold)
    return f


def company_name() -> str:
    return _branding.get("company_name") or "CleanSheet"


def logo_path():
    p = _branding.get("logo_path")
    return Path(p) if p else None


def logo_pixmap(size: int = 24):
    """Return a QPixmap for the brand logo scaled to *size* × *size* px.

    Looks for ``logo_path`` in branding.json.  The path may be absolute or
    relative to the project root (one level above ``ui/``).
    Returns ``None`` if no logo is configured or the file can't be loaded.

    Usage in a sidebar brand block::

        px = theme.logo_pixmap(24)
        if px:
            lbl.setPixmap(px)
            # hide the blue box background
            logo_box.setStyleSheet("QFrame { background: transparent; border: none; }")
        else:
            lbl.setText("▦")   # fallback icon character
    """
    from PySide6.QtGui import QPixmap
    p = _branding.get("logo_path")
    if not p:
        return None
    path = Path(p)
    if not path.is_absolute():
        from utils.paths import resource_path
        path = resource_path(str(path))
    try:
        px = QPixmap(str(path))
        if px.isNull():
            return None
        return px.scaled(size, size,
                         __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.KeepAspectRatio,
                         __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.SmoothTransformation)
    except Exception:
        return None


def hero_bg_path():
    """Return Path to the brand hero background image, or None if not set.
    Add 'hero_bg' key to branding.json pointing to your image file.
    Recommended size: 940 × 200 px (the hero panel dimensions at 1280×720).
    """
    p = _branding.get("hero_bg")
    return Path(p) if p else None
