import json
from pathlib import Path

import pandas as pd


def _dim_path(project_path: Path, dim_table: str) -> Path:
    """Return the path to a dim table's JSON file."""
    return Path(project_path) / "data" / "dim" / f"{dim_table}.json"


def dim_exists(project_path: Path, dim_table: str) -> bool:
    """Return True if a dim table with this name already exists on disk."""
    return _dim_path(project_path, dim_table).exists()


def get_dim_dataframe(project_path: Path, dim_table: str) -> pd.DataFrame:
    """Load a dim table JSON file and return it as a DataFrame."""
    path = _dim_path(Path(project_path), dim_table)
    if not path.exists():
        raise FileNotFoundError(f"Dim table not found: '{dim_table}'")
    try:
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
        return pd.DataFrame(records).astype(str)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to load dim table '{dim_table}': {e}") from e


def get_dim_columns(project_path: Path, dim_table: str) -> list:
    """Return the column names of a dim table."""
    df = get_dim_dataframe(project_path, dim_table)
    return list(df.columns)


def append_dim_row(project_path: Path, dim_table: str, row: dict) -> None:
    """Append a new row to an existing dim table JSON file.

    row must contain all columns present in the dim table.
    Raises ValueError if the dim table does not exist.
    """
    project_path = Path(project_path)
    path = _dim_path(project_path, dim_table)
    if not path.exists():
        raise FileNotFoundError(f"Dim table not found: '{dim_table}'")
    try:
        with open(path, encoding="utf-8") as f:
            records = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to read dim table '{dim_table}': {e}") from e

    records.append({str(k): str(v) for k, v in row.items()})

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to write dim table '{dim_table}': {e}") from e


def save_dim_dataframe(project_path: Path, dim_table: str, df: pd.DataFrame) -> None:
    """Write a DataFrame to disk as a new dim table JSON file.

    Raises FileExistsError if the dim table already exists (dim tables are immutable).
    """
    project_path = Path(project_path)
    path = _dim_path(project_path, dim_table)
    if path.exists():
        raise FileExistsError(
            f"Dim table '{dim_table}' already exists. "
            "Dim tables cannot be replaced once added."
        )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        records = df.astype(str).to_dict(orient="records")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to save dim table '{dim_table}': {e}") from e
