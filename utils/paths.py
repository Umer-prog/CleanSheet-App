import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Return the correct absolute path to a bundled read-only resource.

    Works both during development and when frozen by PyInstaller.
    Use this for files that are shipped inside the bundle (branding.json,
    assets/, etc.) — i.e. files the app reads but never writes.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    return base / relative


def user_data_path(relative: str) -> Path:
    """Return the correct absolute path to a writable runtime data file.

    In frozen mode the file lives next to CleanSheet.exe so it persists
    between launches.  In dev mode it lives at the project root (same as
    before).  Use this for files the app reads AND writes (app_config.json).
    """
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent.parent
    return base / relative
