from __future__ import annotations

import json
from pathlib import Path


def get_current_commit_id(project_path: Path) -> str | None:
    """Read the active commit ID from settings.json, or None if none exists."""
    settings_file = Path(project_path) / "settings.json"
    if not settings_file.exists():
        return None
    try:
        with open(settings_file, encoding="utf-8") as f:
            return json.load(f).get("current_manifest")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Active-path helpers — metadata/ is always the live working area.
# All reads and writes for current data go here. History commits are
# immutable snapshots copied FROM here; revert copies back INTO here.
# ---------------------------------------------------------------------------

def active_transactions_dir(project_path: Path) -> Path:
    """Return the live transactions directory (always metadata/data/transactions/)."""
    return Path(project_path) / "metadata" / "data" / "transactions"


def active_dim_dir(project_path: Path) -> Path:
    """Return the live dimensions directory (always metadata/data/dim/)."""
    return Path(project_path) / "metadata" / "data" / "dim"


def active_mappings_dir(project_path: Path) -> Path:
    """Return the live mappings directory (always metadata/mappings/)."""
    return Path(project_path) / "metadata" / "mappings"


# ---------------------------------------------------------------------------
# Convenience aliases (same paths — kept for call-site clarity).
# ---------------------------------------------------------------------------

def metadata_transactions_dir(project_path: Path) -> Path:
    return Path(project_path) / "metadata" / "data" / "transactions"


def metadata_dim_dir(project_path: Path) -> Path:
    return Path(project_path) / "metadata" / "data" / "dim"


def metadata_mappings_dir(project_path: Path) -> Path:
    return Path(project_path) / "metadata" / "mappings"
