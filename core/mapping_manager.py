import json
from pathlib import Path

from core.project_paths import active_mappings_dir


def _store_path(project_path: Path) -> Path:
    """Return the path to the active mapping_store.json."""
    return active_mappings_dir(Path(project_path)) / "mapping_store.json"


def _read_store(project_path: Path) -> dict:
    """Load mapping_store.json and return its contents."""
    path = _store_path(project_path)
    if not path.exists():
        return {"mappings": []}
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read mapping_store.json: {e}") from e


def _write_store(project_path: Path, store: dict) -> None:
    """Write store dict to the active mapping_store.json."""
    path = _store_path(project_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)
    except OSError as e:
        raise OSError(f"Failed to write mapping_store.json: {e}") from e


def _next_mapping_id(mappings: list) -> str:
    """Return the next sequential mapping ID (e.g. 'map_003')."""
    numbers = []
    for m in mappings:
        try:
            numbers.append(int(m["id"].split("_")[1]))
        except (KeyError, IndexError, ValueError):
            continue
    return f"map_{max(numbers, default=0) + 1:03d}"


def add_mapping(project_path: Path, mapping: dict) -> str:
    """Add a new mapping to the store and return its assigned ID.

    mapping must contain: transaction_table, transaction_column,
    dim_table, dim_column. The id field is assigned automatically.
    """
    project_path = Path(project_path)
    store = _read_store(project_path)
    mapping_id = _next_mapping_id(store["mappings"])
    entry = {
        "id": mapping_id,
        "transaction_table": mapping["transaction_table"],
        "transaction_column": mapping["transaction_column"],
        "dim_table": mapping["dim_table"],
        "dim_column": mapping["dim_column"],
    }
    store["mappings"].append(entry)
    _write_store(project_path, store)
    return mapping_id


def get_mappings(project_path: Path) -> list:
    """Return the full list of mappings from the store."""
    return _read_store(Path(project_path))["mappings"]


def get_mapping_by_id(project_path: Path, mapping_id: str) -> dict | None:
    """Return a single mapping by its ID, or None if not found."""
    target = mapping_id.strip()
    for m in get_mappings(project_path):
        if m["id"].strip() == target:
            return m
    return None


def delete_mapping(project_path: Path, mapping_id: str) -> None:
    """Remove a mapping from the store by its ID. Silently ignores unknown IDs."""
    project_path = Path(project_path)
    target = mapping_id.strip()
    store = _read_store(project_path)
    store["mappings"] = [m for m in store["mappings"] if m["id"].strip() != target]
    _write_store(project_path, store)


def get_active_dim_tables(project_path: Path) -> set:
    """Return the set of dim_table names referenced by at least one active mapping."""
    return {m["dim_table"] for m in get_mappings(project_path)}


def delete_mappings_for_table(project_path: Path, table_name: str) -> int:
    """Remove all mappings that reference table_name (transaction or dim side).

    Returns the number of mappings deleted.
    """
    project_path = Path(project_path)
    store = _read_store(project_path)
    before = len(store["mappings"])
    target = table_name.strip()
    store["mappings"] = [
        m for m in store["mappings"]
        if m["transaction_table"].strip() != target and m["dim_table"].strip() != target
    ]
    _write_store(project_path, store)
    return before - len(store["mappings"])
