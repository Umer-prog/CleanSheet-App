import json
import logging
import re
from datetime import date
from pathlib import Path

from core.project_paths import internal_path

_log = logging.getLogger(__name__)

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def validate_project_name(name: str) -> str | None:
    """Return a user-facing error message if *name* is not a valid folder name, else None."""
    name = name.strip()
    if not name:
        return "Project name is required."
    if len(name) > 100:
        return "Project name must be 100 characters or fewer."
    if _ILLEGAL_CHARS.search(name):
        return 'Project name cannot contain:  < > : " / \\ | ? *'
    if name.upper() in _RESERVED_NAMES:
        return f"'{name}' is a reserved Windows name. Please choose a different name."
    if name[-1] in (".", " "):
        return "Project name cannot end with a period or space."
    return None


def create_project(name: str, company: str, root_path: Path, storage_format: str = "parquet") -> Path:
    """Create a new project folder structure on disk and return the project path."""
    project_path = Path(root_path) / name

    if project_path.exists():
        raise ValueError(
            f"A project named '{name}' already exists. "
            f"Choose a different name or open the existing project."
        )

    ip = internal_path(project_path)

    # Create all required subdirectories inside "project metadata/"
    try:
        for sub in [
            "metadata/data/transactions",
            "metadata/data/dim",
            "metadata/mappings",
            "history",
        ]:
            (ip / sub).mkdir(parents=True, exist_ok=True)
        # final/ lives at project root, separate from internal files
        (project_path / "final").mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create project folder structure: {e}") from e

    # Write project.json inside "project metadata/"
    project_json = {
        "project_name": name,
        "created_at": str(date.today()),
        "company": company,
        "storage_format": storage_format,
        "transaction_tables": [],
        "dim_tables": [],
    }
    try:
        with open(ip / "project.json", "w", encoding="utf-8") as f:
            json.dump(project_json, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write project.json: {e}") from e

    # Write settings.json inside "project metadata/"
    settings_json = {
        "history_enabled": True,
        "current_manifest": None,
        "project_path": str(project_path),
    }
    try:
        with open(ip / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings_json, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write settings.json: {e}") from e

    # Write empty mapping store
    mapping_store = {"mappings": []}
    try:
        with open(ip / "metadata" / "mappings" / "mapping_store.json", "w", encoding="utf-8") as f:
            json.dump(mapping_store, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write mapping_store.json: {e}") from e

    _log.info("Project created: '%s' at %s", name, project_path)
    return project_path


def open_project(project_path: Path) -> dict:
    """Read project.json and settings.json and return merged project state."""
    project_path = Path(project_path)
    ip = internal_path(project_path)

    project_file = ip / "project.json"
    if not project_file.exists():
        raise FileNotFoundError(f"No project.json found at {ip}")

    try:
        with open(project_file, encoding="utf-8") as f:
            project_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read project.json: {e}") from e

    settings_file = ip / "settings.json"
    settings_data = {}
    if settings_file.exists():
        try:
            with open(settings_file, encoding="utf-8") as f:
                settings_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to read settings.json: {e}") from e

    _log.info("Project opened: '%s'", project_data.get("project_name", project_path.name))
    return {**project_data, "settings": settings_data, "project_path": str(project_path)}


def list_projects(root_path: Path) -> list:
    """Scan root_path for project folders and return a list of project metadata dicts."""
    root_path = Path(root_path)
    projects = []

    if not root_path.exists():
        return projects

    for child in root_path.iterdir():
        if not child.is_dir():
            continue
        project_file = internal_path(child) / "project.json"
        if not project_file.exists():
            continue
        try:
            with open(project_file, encoding="utf-8") as f:
                data = json.load(f)
            projects.append({
                "project_name": data.get("project_name", child.name),
                "company": data.get("company", ""),
                "created_at": data.get("created_at", ""),
                "last_modified": project_file.stat().st_mtime,
                "project_path": str(child),
            })
        except (OSError, json.JSONDecodeError):
            continue

    projects.sort(key=lambda p: p["last_modified"], reverse=True)
    return projects


_RUNTIME_ONLY_KEYS = {"_validation_cache"}


def save_project_json(project_path: Path, project_data: dict) -> None:
    """Write updated project.json to disk.

    Runtime-only keys (e.g. _validation_cache) are stripped automatically
    so callers never need to worry about non-serialisable values.
    """
    project_path = Path(project_path)
    clean = {k: v for k, v in project_data.items() if k not in _RUNTIME_ONLY_KEYS}
    try:
        with open(internal_path(project_path) / "project.json", "w", encoding="utf-8") as f:
            json.dump(clean, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to save project.json: {e}") from e


def save_settings_json(project_path: Path, settings_data: dict) -> None:
    """Write updated settings.json to disk."""
    project_path = Path(project_path)
    try:
        with open(internal_path(project_path) / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to save settings.json: {e}") from e
