from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

MAX_COMMITS = 30


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------

def hash_dataframe(df: pd.DataFrame) -> str:
    """Return an 8-character MD5 hash of the dataframe's CSV content."""
    content = df.to_csv(index=False).encode()
    return hashlib.md5(content).hexdigest()[:8]


def _hash_json(data) -> str:
    """Return an 8-character MD5 hash of a JSON-serialisable object."""
    content = json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
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
# File writers
# ---------------------------------------------------------------------------

def _write_snapshot_files(manifest_dir: Path, tables: dict) -> dict:
    """Write hashed CSV files for each transaction table. Returns {name: filename}."""
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


def _write_dim_snapshot_files(manifest_dir: Path, dim_tables: dict) -> dict:
    """Write hashed JSON files for each dim table. Returns {name: filename}."""
    refs = {}
    for name, records in dim_tables.items():
        content_hash = _hash_json(records)
        filename = f"dim_{name}_{content_hash}.json"
        dest = manifest_dir / filename
        try:
            if not dest.exists():
                with open(dest, "w", encoding="utf-8") as f:
                    json.dump(records, f, ensure_ascii=False)
        except OSError as e:
            raise OSError(f"Failed to write dim snapshot file '{filename}': {e}") from e
        refs[name] = filename
    return refs


def _write_manifest_json(manifest_dir: Path, manifest_data: dict) -> None:
    try:
        with open(manifest_dir / "manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write manifest.json: {e}") from e


# ---------------------------------------------------------------------------
# On-disk data loaders (used when building a snapshot)
# ---------------------------------------------------------------------------

def _load_dim_tables(project_path: Path) -> dict:
    """Load all dim tables from data/dim/*.json. Returns {name: records list}."""
    dim_dir = project_path / "data" / "dim"
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


def _load_mappings(project_path: Path) -> list:
    """Load current mappings list from mapping_store.json."""
    store_path = project_path / "mappings" / "mapping_store.json"
    if not store_path.exists():
        return []
    try:
        with open(store_path, encoding="utf-8") as f:
            return json.load(f).get("mappings", [])
    except Exception:
        return []


def _load_project_json(project_path: Path) -> dict:
    """Read project.json. Returns empty dict on failure."""
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
    """Delete oldest commits beyond max_commits, then clean up orphaned data files."""
    commits = sorted(
        d for d in history_path.iterdir()
        if d.is_dir() and (d.name.startswith("commit_") or d.name.startswith("manifest_"))
    )
    # Delete the oldest commits
    for commit_dir in commits[: max(0, len(commits) - max_commits)]:
        shutil.rmtree(commit_dir, ignore_errors=True)

    # Collect all files still referenced by surviving commits
    referenced: set[Path] = set()
    for commit_dir in history_path.iterdir():
        if not commit_dir.is_dir():
            continue
        manifest_file = commit_dir / "manifest.json"
        if not manifest_file.exists():
            continue
        try:
            with open(manifest_file, encoding="utf-8") as f:
                m = json.load(f)
            for fname in m.get("tables", {}).values():
                referenced.add(commit_dir / fname)
            for fname in m.get("dim_tables", {}).values():
                referenced.add(commit_dir / fname)
        except Exception:
            continue

    # Delete unreferenced data files
    for commit_dir in history_path.iterdir():
        if not commit_dir.is_dir():
            continue
        for fpath in commit_dir.iterdir():
            if fpath.name == "manifest.json":
                continue
            if fpath not in referenced:
                try:
                    fpath.unlink(missing_ok=True)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_snapshot(
    project_path: Path,
    tables: dict,
    label: str = "",
) -> str | None:
    """Save transaction tables and create a history commit capturing the full project state.

    The commit captures:
    - All transaction table data (passed as ``tables``)
    - All dimension table data (read from disk at commit time)
    - The full mapping registry (read from disk at commit time)

    Returns the new commit_id, or None if history is disabled.
    """
    project_path = Path(project_path)
    settings = _read_settings(project_path)
    history_enabled = settings.get("history_enabled", True)

    # Always persist transaction data to disk
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
        commit_id = _next_commit_id(history_path)
        commit_dir = history_path / commit_id
        commit_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create commit folder: {e}") from e

    table_refs = _write_snapshot_files(commit_dir, tables)
    dim_data = _load_dim_tables(project_path)
    dim_refs = _write_dim_snapshot_files(commit_dir, dim_data)
    mappings = _load_mappings(project_path)

    _write_manifest_json(commit_dir, {
        "manifest_id": commit_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "label": label,
        "tables": table_refs,
        "dim_tables": dim_refs,
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
    """Create the first commit from existing transaction CSVs if no commits exist yet.

    Safe to call multiple times — does nothing if a commit already exists.
    Returns the new commit_id or None if skipped / history disabled.
    """
    project_path = Path(project_path)
    settings = _read_settings(project_path)
    if not settings.get("history_enabled", True):
        return None

    if list_manifests(project_path):
        return None

    transactions_dir = project_path / "data" / "transactions"
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
    """Read and return the manifest.json for the given commit id."""
    project_path = Path(project_path)
    manifest_file = project_path / "history" / manifest_id / "manifest.json"
    if not manifest_file.exists():
        raise FileNotFoundError(f"manifest.json not found for '{manifest_id}'")
    try:
        with open(manifest_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read commit '{manifest_id}': {e}") from e


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
        manifest_file = folder / "manifest.json"
        if not manifest_file.exists():
            continue
        try:
            with open(manifest_file, encoding="utf-8") as f:
                manifests.append(json.load(f))
        except (OSError, json.JSONDecodeError):
            continue
    return manifests


def get_missing_dim_sources(project_path: Path, manifest_id: str) -> list[str]:
    """Return dim table names in the manifest that were explicitly deleted from this project.

    Used to warn the user before a revert that some dim sources cannot be restored.
    """
    project_path = Path(project_path)
    try:
        manifest = get_manifest(project_path, manifest_id)
    except Exception:
        return []
    snapshot_dims = set(manifest.get("dim_tables", {}).keys())
    deleted_dims = set(_load_project_json(project_path).get("deleted_dim_tables", []))
    return sorted(snapshot_dims & deleted_dims)


def revert_to_manifest(project_path: Path, manifest_id: str) -> None:
    """Restore the full project state from a commit.

    Restores:
    - Transaction tables → data/transactions/
    - Dimension tables   → data/dim/   (skips any explicitly-deleted dim sources)
    - Mapping registry   → mappings/mapping_store.json
    - Updates project.json dim_tables and transaction_tables lists
    - Updates settings.json current_manifest
    """
    project_path = Path(project_path)
    manifest_dir = project_path / "history" / manifest_id
    if not manifest_dir.exists():
        raise FileNotFoundError(f"Commit not found: '{manifest_id}'")

    manifest = get_manifest(project_path, manifest_id)
    project_data = _load_project_json(project_path)
    deleted_dims: set[str] = set(project_data.get("deleted_dim_tables", []))

    transactions_dir = project_path / "data" / "transactions"
    dim_dir = project_path / "data" / "dim"
    mappings_dir = project_path / "mappings"

    # --- Validate all snapshot files exist before touching anything ---
    for filename in manifest.get("tables", {}).values():
        src = manifest_dir / filename
        if not src.exists():
            raise FileNotFoundError(
                f"Snapshot file missing: '{src}'. Cannot revert '{manifest_id}'."
            )
    for table_name, filename in manifest.get("dim_tables", {}).items():
        if table_name in deleted_dims:
            continue   # will be skipped — no need to validate
        src = manifest_dir / filename
        if not src.exists():
            raise FileNotFoundError(
                f"Dim snapshot file missing: '{src}'. Cannot revert '{manifest_id}'."
            )

    # --- Restore transaction tables ---
    try:
        transactions_dir.mkdir(parents=True, exist_ok=True)
        for table_name, filename in manifest.get("tables", {}).items():
            shutil.copy2(manifest_dir / filename, transactions_dir / f"{table_name}.csv")
    except OSError as e:
        raise OSError(f"Failed to restore transaction data: {e}") from e

    # --- Restore dim tables (skip explicitly-deleted sources) ---
    restored_dims: list[str] = []
    try:
        dim_dir.mkdir(parents=True, exist_ok=True)
        for table_name, filename in manifest.get("dim_tables", {}).items():
            if table_name in deleted_dims:
                continue
            src = manifest_dir / filename
            shutil.copy2(src, dim_dir / f"{table_name}.json")
            restored_dims.append(table_name)
    except OSError as e:
        raise OSError(f"Failed to restore dimension data: {e}") from e

    # --- Restore mapping registry ---
    mappings_list = manifest.get("mappings", [])
    try:
        mappings_dir.mkdir(parents=True, exist_ok=True)
        with open(mappings_dir / "mapping_store.json", "w", encoding="utf-8") as f:
            json.dump({"mappings": mappings_list}, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to restore mappings: {e}") from e

    # --- Update project.json lists to reflect reverted state ---
    if project_data:
        project_data["transaction_tables"] = list(manifest.get("tables", {}).keys())
        project_data["dim_tables"] = restored_dims
        # Preserve deleted_dim_tables — we never un-delete explicitly removed sources
        _write_project_json(project_path, project_data)

    settings = _read_settings(project_path)
    settings["current_manifest"] = manifest_id
    _write_settings(project_path, settings)


def update_manifest_label(project_path: Path, manifest_id: str, label: str) -> None:
    """Update the human-readable label for a commit."""
    project_path = Path(project_path)
    manifest_dir = project_path / "history" / manifest_id
    if not manifest_dir.exists():
        raise FileNotFoundError(f"Commit not found: '{manifest_id}'")
    manifest = get_manifest(project_path, manifest_id)
    manifest["label"] = str(label)
    _write_manifest_json(manifest_dir, manifest)
