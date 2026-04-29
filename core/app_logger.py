"""Application-wide logging setup for CleanSheet."""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FILE: Path | None = None


def setup_logging() -> Path:
    """Configure root logger with a rotating file handler.

    Must be called once at app startup before any other imports use logging.
    Returns the path to the log file so the UI can display it to the user.
    """
    global _LOG_FILE

    if getattr(sys, "frozen", False):
        log_dir = Path("C:/ProgramData/CleanSheet/logs")
    else:
        log_dir = Path(__file__).parent.parent / "logs"

    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback to a temp directory if ProgramData is not writable
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / "CleanSheet" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / "cleansheet.log"
    _LOG_FILE = log_path

    formatter = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)

    return log_path


def get_log_file_path() -> Path | None:
    """Return the active log file path, or None if logging hasn't been set up."""
    return _LOG_FILE
