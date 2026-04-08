import json
from pathlib import Path

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
    return scheme.get(key, fallback)


def company_name() -> str:
    """Return the company name from branding, or the default app name."""
    return _branding.get("company_name") or _DEFAULTS["company_name"]


def logo_path():
    """Return a Path to the logo file, or None if no logo is configured."""
    p = _branding.get("logo_path") or _DEFAULTS.get("logo_path")
    return Path(p) if p else None
