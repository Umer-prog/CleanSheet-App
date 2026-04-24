from pathlib import Path

import pandas as pd

from core.data_loader import get_storage_format, read_table, write_table
from core.project_paths import active_dim_dir


def _dim_path(project_path: Path, dim_table: str) -> Path:
    """Return the preferred path for a dim table based on the project's storage format."""
    fmt = get_storage_format(project_path)
    ext = ".parquet" if fmt == "parquet" else ".csv"
    return active_dim_dir(Path(project_path)) / f"{dim_table}{ext}"


def _find_dim_file(project_path: Path, dim_table: str) -> Path | None:
    """Return the actual on-disk path for a dim table (CSV or Parquet), or None."""
    base = active_dim_dir(Path(project_path)) / dim_table
    for suffix in (".csv", ".parquet"):
        candidate = base.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return None


def dim_exists(project_path: Path, dim_table: str) -> bool:
    """Return True if a dim table with this name already exists on disk."""
    return _find_dim_file(project_path, dim_table) is not None


def get_dim_dataframe(project_path: Path, dim_table: str) -> pd.DataFrame:
    """Load a dim table and return it as a DataFrame."""
    path = _find_dim_file(Path(project_path), dim_table)
    if path is None:
        raise FileNotFoundError(f"Dim table not found: '{dim_table}'")
    try:
        return read_table(path)
    except Exception as e:
        raise ValueError(f"Failed to load dim table '{dim_table}': {e}") from e


def get_dim_columns(project_path: Path, dim_table: str) -> list:
    """Return the column names of a dim table."""
    df = get_dim_dataframe(project_path, dim_table)
    return list(df.columns)


def delete_dim_table(project_path: Path, dim_table: str) -> None:
    """Delete a dim table file from disk (CSV or Parquet)."""
    path = _find_dim_file(Path(project_path), dim_table)
    if path is None:
        return
    try:
        path.unlink()
    except OSError as e:
        raise OSError(f"Failed to delete dim table '{dim_table}': {e}") from e


def append_dim_row(project_path: Path, dim_table: str, row: dict) -> None:
    """Append a new row to an existing dim table.

    row must contain all columns present in the dim table.
    Raises FileNotFoundError if the dim table does not exist.
    """
    project_path = Path(project_path)
    path = _find_dim_file(project_path, dim_table)
    if path is None:
        raise FileNotFoundError(f"Dim table not found: '{dim_table}'")
    try:
        df = read_table(path)
    except Exception as e:
        raise ValueError(f"Failed to read dim table '{dim_table}': {e}") from e

    new_row = {str(k): str(v) for k, v in row.items()}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    try:
        write_table(df, path)
    except OSError as e:
        raise OSError(f"Failed to write dim table '{dim_table}': {e}") from e


def save_dim_dataframe(project_path: Path, dim_table: str, df: pd.DataFrame) -> None:
    """Write a DataFrame to disk as a new dim table.

    Raises FileExistsError if the dim table already exists.
    """
    project_path = Path(project_path)
    if dim_exists(project_path, dim_table):
        raise FileExistsError(
            f"Dim table '{dim_table}' already exists. "
            "Dim tables cannot be replaced once added."
        )
    path = _dim_path(project_path, dim_table)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        write_table(df.astype(str), path)
    except OSError as e:
        raise OSError(f"Failed to save dim table '{dim_table}': {e}") from e
