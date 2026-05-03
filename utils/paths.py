import os
import sys
from pathlib import Path


def resource_path(relative: str) -> Path:
    """Return the absolute path to a bundled read-only resource.

    In frozen (installer) mode, resources live in the one-dir bundle folder
    alongside the exe (sys._MEIPASS points there).  In dev mode, they live
    at the project root.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.parent))
    return base / relative


def user_data_path(relative: str) -> Path:
    """Return the absolute path to a writable runtime data file.

    Frozen (installer): %PROGRAMDATA%\\CleanSheet\\  — the installer creates
    this directory with Users-modify permissions, so it is always writable.

    Dev: project root — unchanged from the previous behaviour so local runs
    keep reading app_config.json, logs/, etc. from the repo directory.
    """
    if getattr(sys, "frozen", False):
        program_data = os.environ.get("PROGRAMDATA", "C:/ProgramData")
        base = Path(program_data) / "CleanSheet"
    else:
        base = Path(__file__).parent.parent
    return base / relative
