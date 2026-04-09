import json
from pathlib import Path

import customtkinter as ctk

_branding = {}

_DEFAULTS = {
    "company_name": "[APPNAME]",
    "logo_path": None,
    "color_scheme": {
        "primary":      "#2B5CE6",
        "secondary":    "#F5F5F5",
        "accent":       "#E63946",
        "text_dark":    "#1A1A2E",
        "text_light":   "#FFFFFF",
        "sidebar_bg":   "#2B5CE6",
        "sidebar_text": "#FFFFFF",
    },
}

_DARK_OVERRIDES = {
    # Crisp dark palette with clearer separation between sidebar and content
    "primary": "#4DA3FF",
    "secondary": "#0B1220",
    "accent": "#FF6A7D",
    "text_dark": "#EAF2FF",
    "text_light": "#F7FAFF",
    "sidebar_bg": "#0F203A",
    "sidebar_text": "#F1F6FF",
}

# Surfaces
_CARD_LIGHT = "#FFFFFF"
_CARD_DARK = "#15253D"
_SELECTION_LIGHT = "#EAF2FF"
_SELECTION_DARK = "#1D3B64"
_FONT_FAMILY = "Segoe UI"


def load(branding_path: Path) -> None:
    """Load branding.json into the module. Silently uses defaults if missing or invalid."""
    global _branding
    branding_path = Path(branding_path)
    if branding_path.exists():
        try:
            with open(branding_path, encoding="utf-8") as f:
                _branding = json.load(f)
        except (OSError, json.JSONDecodeError):
            _branding = {}
    else:
        _branding = {}


def get(key: str, fallback: str = "#2B5CE6") -> str:
    """Return a color value from the loaded color scheme, or fallback if not found."""
    scheme = _branding.get("color_scheme") or _DEFAULTS["color_scheme"]
    if ctk.get_appearance_mode().lower() == "dark":
        return _DARK_OVERRIDES.get(key, scheme.get(key, fallback))
    return scheme.get(key, fallback)


def card_color() -> str:
    """Return card/panel background color for current appearance mode."""
    return _CARD_DARK if ctk.get_appearance_mode().lower() == "dark" else _CARD_LIGHT


def selection_color() -> str:
    """Return selected-item background color for current appearance mode."""
    return _SELECTION_DARK if ctk.get_appearance_mode().lower() == "dark" else _SELECTION_LIGHT


def font(size: int, weight: str = "normal") -> ctk.CTkFont:
    """Standardized app font for consistent visual hierarchy."""
    return ctk.CTkFont(family=_FONT_FAMILY, size=size, weight=weight)


def company_name() -> str:
    """Return the company name from branding, or the default app name."""
    return _branding.get("company_name") or _DEFAULTS["company_name"]


def logo_path():
    """Return a Path to the logo file, or None if no logo is configured."""
    p = _branding.get("logo_path") or _DEFAULTS.get("logo_path")
    return Path(p) if p else None
