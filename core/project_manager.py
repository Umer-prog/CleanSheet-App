import json
from datetime import date
from pathlib import Path


def create_project(name: str, company: str, root_path: Path) -> Path:
    """Create a new project folder structure on disk and return the project path."""
    project_path = Path(root_path) / name

    if project_path.exists():
        raise ValueError(
            f"A project named '{name}' already exists. "
            f"Choose a different name or open the existing project."
        )

    # Create all required subdirectories
    try:
        for sub in [
            "metadata/data/transactions",
            "metadata/data/dim",
            "metadata/mappings",
            "history",
        ]:
            (project_path / sub).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create project folder structure: {e}") from e

    # Write project.json
    project_json = {
        "project_name": name,
        "created_at": str(date.today()),
        "company": company,
        "storage_format": "parquet",
        "transaction_tables": [],
        "dim_tables": [],
    }
    try:
        with open(project_path / "project.json", "w", encoding="utf-8") as f:
            json.dump(project_json, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write project.json: {e}") from e

    # Write settings.json
    settings_json = {
        "history_enabled": True,
        "current_manifest": None,
        "project_path": str(project_path),
    }
    try:
        with open(project_path / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings_json, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write settings.json: {e}") from e

    # Write empty mapping store
    mapping_store = {"mappings": []}
    try:
        with open(project_path / "metadata" / "mappings" / "mapping_store.json", "w", encoding="utf-8") as f:
            json.dump(mapping_store, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write mapping_store.json: {e}") from e

    return project_path


def open_project(project_path: Path) -> dict:
    """Read project.json and settings.json and return merged project state."""
    project_path = Path(project_path)

    project_file = project_path / "project.json"
    if not project_file.exists():
        raise FileNotFoundError(f"No project.json found at {project_path}")

    try:
        with open(project_file, encoding="utf-8") as f:
            project_data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read project.json: {e}") from e

    settings_file = project_path / "settings.json"
    settings_data = {}
    if settings_file.exists():
        try:
            with open(settings_file, encoding="utf-8") as f:
                settings_data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            raise ValueError(f"Failed to read settings.json: {e}") from e

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
        project_file = child / "project.json"
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


def save_project_json(project_path: Path, project_data: dict) -> None:
    """Write updated project.json to disk."""
    project_path = Path(project_path)
    try:
        with open(project_path / "project.json", "w", encoding="utf-8") as f:
            json.dump(project_data, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to save project.json: {e}") from e


def save_settings_json(project_path: Path, settings_data: dict) -> None:
    """Write updated settings.json to disk."""
    project_path = Path(project_path)
    try:
        with open(project_path / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings_data, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to save settings.json: {e}") from e
