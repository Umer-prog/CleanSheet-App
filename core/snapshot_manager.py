import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd


def hash_dataframe(df: pd.DataFrame) -> str:
    """Return an 8-character MD5 hash of the dataframe's CSV content."""
    content = df.to_csv(index=False).encode()
    return hashlib.md5(content).hexdigest()[:8]


def _read_settings(project_path: Path) -> dict:
    """Read settings.json and return its contents as a dict."""
    settings_file = project_path / "settings.json"
    if not settings_file.exists():
        return {"history_enabled": True, "current_manifest": None}
    try:
        with open(settings_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read settings.json: {e}") from e


def _write_settings(project_path: Path, settings: dict) -> None:
    """Write settings dict to settings.json."""
    try:
        with open(project_path / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write settings.json: {e}") from e


def _next_manifest_id(history_path: Path) -> str:
    """Return the next sequential manifest ID (e.g. 'manifest_003')."""
    numbers = []
    try:
        for d in history_path.iterdir():
            if d.is_dir() and d.name.startswith("manifest_"):
                try:
                    numbers.append(int(d.name.split("_")[1]))
                except (IndexError, ValueError):
                    continue
    except OSError as e:
        raise OSError(f"Failed to read history folder: {e}") from e
    return f"manifest_{max(numbers, default=0) + 1:03d}"


def _write_snapshot_files(manifest_dir: Path, tables: dict) -> dict:
    """Write hashed CSV files for each table into manifest_dir.

    Returns a dict mapping table_name to the hashed filename.
    Skips writing if a file with the same hash already exists (deduplication).
    """
    table_refs = {}
    for table_name, df in tables.items():
        file_hash = hash_dataframe(df)
        hashed_filename = f"{table_name}_{file_hash}.csv"
        dest = manifest_dir / hashed_filename
        try:
            if not dest.exists():
                df.to_csv(dest, index=False, encoding="utf-8")
        except OSError as e:
            raise OSError(f"Failed to write snapshot file '{hashed_filename}': {e}") from e
        table_refs[table_name] = hashed_filename
    return table_refs


def _write_manifest_json(manifest_dir: Path, manifest_data: dict) -> None:
    """Serialise manifest_data to manifest.json inside manifest_dir."""
    try:
        with open(manifest_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write manifest.json: {e}") from e


def create_snapshot(
    project_path: Path,
    tables: dict,
    label: str = "",
) -> str | None:
    """Save tables to data/transactions/ and optionally create a history manifest.

    tables: {table_name: pd.DataFrame}
    Returns the manifest_id if history is enabled, else None.
    Always updates data/transactions/ regardless of history setting.
    """
    project_path = Path(project_path)
    settings = _read_settings(project_path)
    history_enabled = settings.get("history_enabled", True)

    transactions_dir = project_path / "data" / "transactions"
    try:
        transactions_dir.mkdir(parents=True, exist_ok=True)
        for table_name, df in tables.items():
            df.to_csv(transactions_dir / f"{table_name}.csv", index=False, encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed to update transaction data: {e}") from e

    if not history_enabled:
        return None

    history_path = project_path / "history"
    try:
        history_path.mkdir(parents=True, exist_ok=True)
        manifest_id = _next_manifest_id(history_path)
        manifest_dir = history_path / manifest_id
        manifest_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create manifest folder: {e}") from e

    table_refs = _write_snapshot_files(manifest_dir, tables)

    _write_manifest_json(manifest_dir, {
        "manifest_id": manifest_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "label": label,
        "tables": table_refs,
    })

    settings["current_manifest"] = manifest_id
    _write_settings(project_path, settings)
    return manifest_id


def get_manifest(project_path: Path, manifest_id: str) -> dict:
    """Read and return the manifest.json for the given manifest_id."""
    project_path = Path(project_path)
    manifest_file = project_path / "history" / manifest_id / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"manifest.json not found for '{manifest_id}'")
    try:
        with open(manifest_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read manifest '{manifest_id}': {e}") from e


def list_manifests(project_path: Path) -> list:
    """Return all manifests in chronological order (oldest first)."""
    project_path = Path(project_path)
    history_path = project_path / "history"
    if not history_path.exists():
        return []

    try:
        folders = sorted(history_path.iterdir())
    except OSError as e:
        raise OSError(f"Failed to read history folder: {e}") from e

    manifests = []
    for folder in folders:
        if not folder.is_dir() or not folder.name.startswith("manifest_"):
            continue
        manifest_file = folder / "manifest.json"
        if not manifest_file.exists():
            continue
        try:
            with open(manifest_file, encoding="utf-8") as f:
                manifests.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    return manifests


def revert_to_manifest(project_path: Path, manifest_id: str) -> None:
    """Restore transaction files from a manifest back into data/transactions/.

    Updates settings.json current_manifest. Does not delete newer manifests.
    """
    project_path = Path(project_path)
    manifest_dir = project_path / "history" / manifest_id
    if not manifest_dir.exists():
        raise FileNotFoundError(f"Manifest not found: '{manifest_id}'")

    manifest = get_manifest(project_path, manifest_id)
    transactions_dir = project_path / "data" / "transactions"

    # Validate all snapshot files exist before touching anything
    for table_name, filename in manifest["tables"].items():
        src = manifest_dir / filename
        if not src.exists():
            raise FileNotFoundError(
                f"Snapshot file missing: '{src}'. Cannot revert '{manifest_id}'."
            )

    try:
        transactions_dir.mkdir(parents=True, exist_ok=True)
        for table_name, filename in manifest["tables"].items():
            shutil.copy2(manifest_dir / filename, transactions_dir / f"{table_name}.csv")
    except OSError as e:
        raise OSError(f"Failed to revert to manifest '{manifest_id}': {e}") from e

    settings = _read_settings(project_path)
    settings["current_manifest"] = manifest_id
    _write_settings(project_path, settings)


def update_manifest_label(project_path: Path, manifest_id: str, label: str) -> None:
    """Update the human-readable label for a manifest."""
    project_path = Path(project_path)
    manifest_dir = project_path / "history" / manifest_id
    if not manifest_dir.exists():
        raise FileNotFoundError(f"Manifest not found: '{manifest_id}'")

    manifest = get_manifest(project_path, manifest_id)
    manifest["label"] = str(label)
    _write_manifest_json(manifest_dir, manifest)
