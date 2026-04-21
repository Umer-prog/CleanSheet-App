from pathlib import Path

import pandas as pd

from core.project_paths import active_dim_dir


def _dim_path(project_path: Path, dim_table: str) -> Path:
    """Return the path to a dim table's CSV file in the active dim directory."""
    return active_dim_dir(Path(project_path)) / f"{dim_table}.csv"


def dim_exists(project_path: Path, dim_table: str) -> bool:
    """Return True if a dim table with this name already exists on disk."""
    return _dim_path(project_path, dim_table).exists()


def get_dim_dataframe(project_path: Path, dim_table: str) -> pd.DataFrame:
    """Load a dim table CSV file and return it as a DataFrame."""
    path = _dim_path(Path(project_path), dim_table)
    if not path.exists():
        raise FileNotFoundError(f"Dim table not found: '{dim_table}'")
    try:
        return pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as e:
        raise ValueError(f"Failed to load dim table '{dim_table}': {e}") from e


def get_dim_columns(project_path: Path, dim_table: str) -> list:
    """Return the column names of a dim table."""
    df = get_dim_dataframe(project_path, dim_table)
    return list(df.columns)


def delete_dim_table(project_path: Path, dim_table: str) -> None:
    """Delete a dim table's CSV file from disk."""
    path = _dim_path(Path(project_path), dim_table)
    try:
        if path.exists():
            path.unlink()
    except OSError as e:
        raise OSError(f"Failed to delete dim table '{dim_table}': {e}") from e


def append_dim_row(project_path: Path, dim_table: str, row: dict) -> None:
    """Append a new row to an existing dim table CSV file.

    row must contain all columns present in the dim table.
    Raises FileNotFoundError if the dim table does not exist.
    """
    project_path = Path(project_path)
    path = _dim_path(project_path, dim_table)
    if not path.exists():
        raise FileNotFoundError(f"Dim table not found: '{dim_table}'")
    try:
        df = pd.read_csv(path, dtype=str, keep_default_na=False)
    except Exception as e:
        raise ValueError(f"Failed to read dim table '{dim_table}': {e}") from e

    new_row = {str(k): str(v) for k, v in row.items()}
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    try:
        df.to_csv(path, index=False, encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed to write dim table '{dim_table}': {e}") from e


def save_dim_dataframe(project_path: Path, dim_table: str, df: pd.DataFrame) -> None:
    """Write a DataFrame to disk as a new dim table CSV file.

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
        df.astype(str).to_csv(path, index=False, encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed to save dim table '{dim_table}': {e}") from e
