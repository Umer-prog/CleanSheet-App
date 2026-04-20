from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

from core.project_paths import (
    active_dim_dir,
    active_mappings_dir,
    metadata_transactions_dir,
)

MAX_COMMITS = 30


# ---------------------------------------------------------------------------
# Hashing helper (kept for external callers)
# ---------------------------------------------------------------------------

def hash_dataframe(df: pd.DataFrame) -> str:
    """Return an 8-character MD5 hash of the dataframe's CSV content."""
    content = df.to_csv(index=False).encode()
    return hashlib.md5(content).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _read_settings(project_path: Path) -> dict:
    settings_file = project_path / "settings.json"
    if not settings_file.exists():
        return {"history_enabled": True, "current_manifest": None}
    try:
        with open(settings_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read settings.json: {e}") from e


def _write_settings(project_path: Path, settings: dict) -> None:
    try:
        with open(project_path / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write settings.json: {e}") from e


# ---------------------------------------------------------------------------
# Commit numbering
# ---------------------------------------------------------------------------

def _next_commit_id(history_path: Path) -> str:
    """Return the next sequential commit ID (e.g. 'commit_003')."""
    numbers = []
    try:
        for d in history_path.iterdir():
            if not d.is_dir():
                continue
            for prefix in ("commit_", "manifest_"):
                if d.name.startswith(prefix):
                    try:
                        numbers.append(int(d.name.split("_")[1]))
                    except (IndexError, ValueError):
                        pass
                    break
    except OSError as e:
        raise OSError(f"Failed to read history folder: {e}") from e
    return f"commit_{max(numbers, default=0) + 1:03d}"


# ---------------------------------------------------------------------------
# Commit file I/O
# ---------------------------------------------------------------------------

def _write_commit_json(commit_dir: Path, commit_data: dict) -> None:
    try:
        with open(commit_dir / "commit.json", "w", encoding="utf-8") as f:
            json.dump(commit_data, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write commit.json: {e}") from e


def _read_commit_json(commit_dir: Path) -> dict:
    """Read commit.json (or legacy manifest.json) from a commit folder."""
    for filename in ("commit.json", "manifest.json"):
        candidate = commit_dir / filename
        if candidate.exists():
            try:
                with open(candidate, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                raise ValueError(f"Failed to read {filename}: {e}") from e
    raise FileNotFoundError(f"No commit.json found in {commit_dir}")


# ---------------------------------------------------------------------------
# Per-commit data writers
# ---------------------------------------------------------------------------


def _write_dimensions(dimensions_dir: Path, dim_data: dict) -> list[str]:
    """Write dimension JSONs. Returns list of dim names written."""
    written = []
    for name, records in dim_data.items():
        dest = dimensions_dir / f"{name}.json"
        try:
            with open(dest, "w", encoding="utf-8") as f:
                json.dump(records, f, ensure_ascii=False)
            written.append(name)
        except OSError as e:
            raise OSError(f"Failed to write dimension '{name}': {e}") from e
    return written


def _write_mappings_to_commit(mappings_dir: Path, mappings: list) -> None:
    try:
        with open(mappings_dir / "mapping_store.json", "w", encoding="utf-8") as f:
            json.dump({"mappings": mappings}, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write commit mappings: {e}") from e


# ---------------------------------------------------------------------------
# On-disk data loaders
# ---------------------------------------------------------------------------

def _load_dim_tables_from_dir(dim_dir: Path) -> dict:
    """Load all dim tables from a directory of *.json files."""
    result: dict = {}
    if not dim_dir.exists():
        return result
    for f in sorted(dim_dir.glob("*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                result[f.stem] = json.load(fh)
        except Exception:
            continue
    return result


def _load_dim_tables(project_path: Path) -> dict:
    """Load dim tables from the currently active dim directory."""
    return _load_dim_tables_from_dir(active_dim_dir(project_path))


def _load_mappings_from_dir(mappings_dir: Path) -> list:
    store_path = mappings_dir / "mapping_store.json"
    if not store_path.exists():
        return []
    try:
        with open(store_path, encoding="utf-8") as f:
            return json.load(f).get("mappings", [])
    except Exception:
        return []


def _load_mappings(project_path: Path) -> list:
    return _load_mappings_from_dir(active_mappings_dir(project_path))


def _load_project_json(project_path: Path) -> dict:
    path = project_path / "project.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _write_project_json(project_path: Path, data: dict) -> None:
    try:
        with open(project_path / "project.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write project.json: {e}") from e


# ---------------------------------------------------------------------------
# Pruning
# ---------------------------------------------------------------------------

def _prune_old_commits(history_path: Path, max_commits: int = MAX_COMMITS) -> None:
    """Delete the oldest commits beyond max_commits."""
    commits = sorted(
        d for d in history_path.iterdir()
        if d.is_dir() and (d.name.startswith("commit_") or d.name.startswith("manifest_"))
    )
    for commit_dir in commits[: max(0, len(commits) - max_commits)]:
        shutil.rmtree(commit_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_snapshot(
    project_path: Path,
    tables: dict,
    label: str = "",
) -> str | None:
    """Persist transaction data to the live working area and snapshot the full project state.

    1. Writes transaction CSVs to metadata/data/transactions/ (the live working area).
    2. Creates a self-contained commit in history/<commit_id>/ with subfolders:
         transactions/  — transaction table CSVs
         dimensions/    — dimension table JSONs (copied from metadata/data/dim/)
         mappings/      — mapping_store.json (copied from metadata/mappings/)
         ignored/       — ignored rows (reserved for future use)

    Returns the new commit_id, or None if history is disabled.
    """
    project_path = Path(project_path)
    settings = _read_settings(project_path)

    # Always write transaction data to the live working area
    live_tx_dir = project_path / "metadata" / "data" / "transactions"
    try:
        live_tx_dir.mkdir(parents=True, exist_ok=True)
        for table_name, df in tables.items():
            df.to_csv(live_tx_dir / f"{table_name}.csv", index=False, encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed to update live transaction data: {e}") from e

    if not settings.get("history_enabled", True):
        return None

    history_path = project_path / "history"
    try:
        history_path.mkdir(parents=True, exist_ok=True)
        commit_id = _next_commit_id(history_path)
        commit_dir = history_path / commit_id
        for sub in ("transactions", "dimensions", "mappings", "ignored"):
            (commit_dir / sub).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create commit folder: {e}") from e

    # Snapshot ALL transaction tables from the live dir (not only the ones passed in)
    tx_names = []
    for csv_file in sorted(live_tx_dir.glob("*.csv")):
        try:
            shutil.copy2(csv_file, commit_dir / "transactions" / csv_file.name)
            tx_names.append(csv_file.stem)
        except OSError as e:
            raise OSError(f"Failed to snapshot transaction '{csv_file.stem}': {e}") from e

    dim_data = _load_dim_tables(project_path)
    dim_names = _write_dimensions(commit_dir / "dimensions", dim_data)
    mappings = _load_mappings(project_path)
    _write_mappings_to_commit(commit_dir / "mappings", mappings)

    # Save ignored errors snapshot
    ignored_src = project_path / "metadata" / "data" / "ignored_errors.json"
    if ignored_src.exists():
        try:
            shutil.copy2(ignored_src, commit_dir / "ignored" / "ignored_errors.json")
        except OSError:
            pass  # non-critical

    parent = settings.get("current_manifest")

    _write_commit_json(commit_dir, {
        "manifest_id": commit_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "label": label,
        "parent": parent,
        "tables": tx_names,
        "dim_tables": dim_names,
        "mappings": mappings,
    })

    settings["current_manifest"] = commit_id
    _write_settings(project_path, settings)

    try:
        _prune_old_commits(history_path)
    except Exception:
        pass   # pruning failure is non-critical

    return commit_id


def create_initial_commit(project_path: Path) -> str | None:
    """Create the first commit from existing metadata transaction CSVs.

    Reads from metadata/data/transactions/ (the initial setup seed location).
    Safe to call multiple times — does nothing if a commit already exists.
    Returns the new commit_id or None if skipped / history disabled.
    """
    project_path = Path(project_path)
    settings = _read_settings(project_path)
    if not settings.get("history_enabled", True):
        return None

    if list_manifests(project_path):
        return None

    transactions_dir = metadata_transactions_dir(project_path)
    if not transactions_dir.exists():
        return None

    tables: dict = {}
    for csv_file in sorted(transactions_dir.glob("*.csv")):
        try:
            tables[csv_file.stem] = pd.read_csv(csv_file, encoding="utf-8")
        except Exception:
            continue

    if not tables:
        return None

    return create_snapshot(project_path, tables, label="Initial commit")


def get_current_commit_id(project_path: Path) -> str | None:
    """Return the commit_id currently checked out, or None."""
    try:
        return _read_settings(Path(project_path)).get("current_manifest")
    except Exception:
        return None


def get_manifest(project_path: Path, manifest_id: str) -> dict:
    """Read and return the commit data for the given commit id."""
    project_path = Path(project_path)
    commit_dir = project_path / "history" / manifest_id
    if not commit_dir.exists():
        raise FileNotFoundError(f"Commit not found: '{manifest_id}'")
    return _read_commit_json(commit_dir)


def list_manifests(project_path: Path) -> list:
    """Return all commits in chronological order (oldest first)."""
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
        if not folder.is_dir():
            continue
        if not (folder.name.startswith("commit_") or folder.name.startswith("manifest_")):
            continue
        try:
            manifests.append(_read_commit_json(folder))
        except Exception:
            continue
    return manifests


def get_missing_dim_sources(project_path: Path, manifest_id: str) -> list[str]:
    """Return dim table names in the commit that were explicitly deleted from this project."""
    project_path = Path(project_path)
    try:
        manifest = get_manifest(project_path, manifest_id)
    except Exception:
        return []
    # dim_tables is now a list of names
    snapshot_dims = set(manifest.get("dim_tables", []))
    deleted_dims = set(_load_project_json(project_path).get("deleted_dim_tables", []))
    return sorted(snapshot_dims & deleted_dims)


def revert_to_manifest(project_path: Path, manifest_id: str) -> None:
    """Restore the full project state from a commit into the live working area.

    Copies from history/<commit_id>/ back into metadata/:
      - Transactions → metadata/data/transactions/
      - Dimensions   → metadata/data/dim/  (skips explicitly-deleted dim sources)
      - Mappings     → metadata/mappings/mapping_store.json
    Updates project.json table lists and settings.json current_manifest.
    """
    project_path = Path(project_path)
    commit_dir = project_path / "history" / manifest_id
    if not commit_dir.exists():
        raise FileNotFoundError(f"Commit not found: '{manifest_id}'")

    tx_commit_dir  = commit_dir / "transactions"
    dim_commit_dir = commit_dir / "dimensions"
    map_commit_dir = commit_dir / "mappings"

    if not tx_commit_dir.exists() or not dim_commit_dir.exists():
        raise FileNotFoundError(
            f"Commit '{manifest_id}' is missing required subfolders. Cannot revert."
        )

    manifest = get_manifest(project_path, manifest_id)
    project_data = _load_project_json(project_path)

    tx_tables     = manifest.get("tables", [])
    restored_dims = list(manifest.get("dim_tables", []))  # restore ALL dims, including previously-deleted ones

    # Validate all files exist before touching anything
    for name in tx_tables:
        src = tx_commit_dir / f"{name}.csv"
        if not src.exists():
            raise FileNotFoundError(f"Snapshot file missing: '{src}'")
    for name in restored_dims:
        src = dim_commit_dir / f"{name}.json"
        if not src.exists():
            raise FileNotFoundError(f"Dim snapshot file missing: '{src}'")

    # Restore transactions → metadata/data/transactions/
    live_tx = project_path / "metadata" / "data" / "transactions"
    try:
        live_tx.mkdir(parents=True, exist_ok=True)
        for name in tx_tables:
            shutil.copy2(tx_commit_dir / f"{name}.csv", live_tx / f"{name}.csv")
    except OSError as e:
        raise OSError(f"Failed to restore transaction data: {e}") from e

    # Restore dimensions → metadata/data/dim/
    live_dim = project_path / "metadata" / "data" / "dim"
    try:
        live_dim.mkdir(parents=True, exist_ok=True)
        for name in restored_dims:
            shutil.copy2(dim_commit_dir / f"{name}.json", live_dim / f"{name}.json")
    except OSError as e:
        raise OSError(f"Failed to restore dimension data: {e}") from e

    # Restore mappings → metadata/mappings/
    live_map = project_path / "metadata" / "mappings"
    mappings_list = manifest.get("mappings", [])
    try:
        live_map.mkdir(parents=True, exist_ok=True)
        with open(live_map / "mapping_store.json", "w", encoding="utf-8") as f:
            json.dump({"mappings": mappings_list}, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to restore mappings: {e}") from e

    # Restore ignored errors — always update the live file to match the commit's state
    ignored_commit = commit_dir / "ignored" / "ignored_errors.json"
    live_ignored   = project_path / "metadata" / "data" / "ignored_errors.json"
    try:
        if ignored_commit.exists():
            shutil.copy2(ignored_commit, live_ignored)
        elif live_ignored.exists():
            live_ignored.unlink()
    except OSError:
        pass  # non-critical

    # Update project.json and pointer
    if project_data:
        project_data["transaction_tables"] = tx_tables
        project_data["dim_tables"] = restored_dims
        # Remove restored dims from deleted_dim_tables — revert brings them back
        current_deleted = set(project_data.get("deleted_dim_tables", []))
        project_data["deleted_dim_tables"] = sorted(current_deleted - set(restored_dims))
        _write_project_json(project_path, project_data)

    settings = _read_settings(project_path)
    settings["current_manifest"] = manifest_id
    _write_settings(project_path, settings)


def update_manifest_label(project_path: Path, manifest_id: str, label: str) -> None:
    """Update the human-readable label for a commit."""
    project_path = Path(project_path)
    commit_dir = project_path / "history" / manifest_id
    if not commit_dir.exists():
        raise FileNotFoundError(f"Commit not found: '{manifest_id}'")
    manifest = get_manifest(project_path, manifest_id)
    manifest["label"] = str(label)
    _write_commit_json(commit_dir, manifest)
