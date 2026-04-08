import json

import pandas as pd
from pathlib import Path


def load_excel_sheets(file_path: Path) -> list:
    """Return the list of sheet names in an Excel file."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    try:
        xl = pd.ExcelFile(file_path, engine="openpyxl")
        return xl.sheet_names
    except Exception as e:
        raise ValueError(f"Failed to open Excel file '{file_path}': {e}") from e


def get_sheet_as_dataframe(file_path: Path, sheet_name: str) -> pd.DataFrame:
    """Read a single sheet from an Excel file and return a DataFrame."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl", dtype=str)
        # Normalize: strip leading/trailing whitespace from column names
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        raise ValueError(f"Failed to read sheet '{sheet_name}' from '{file_path}': {e}") from e


def save_as_csv(df: pd.DataFrame, dest_path: Path) -> None:
    """Save a DataFrame as a CSV file."""
    dest_path = Path(dest_path)
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(dest_path, index=False, encoding="utf-8")
    except OSError as e:
        raise OSError(f"Failed to save CSV to '{dest_path}': {e}") from e


def save_as_json(df: pd.DataFrame, dest_path: Path) -> None:
    """Save a DataFrame as a JSON file (records format, one object per row)."""
    dest_path = Path(dest_path)
    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        records = df.to_dict(orient="records")
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except OSError as e:
        raise OSError(f"Failed to save JSON to '{dest_path}': {e}") from e


def load_csv(file_path: Path) -> pd.DataFrame:
    """Load a CSV file as a DataFrame (all columns as strings)."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    try:
        return pd.read_csv(file_path, dtype=str, encoding="utf-8")
    except Exception as e:
        raise ValueError(f"Failed to load CSV '{file_path}': {e}") from e


def load_dim_json(file_path: Path) -> pd.DataFrame:
    """Load a dim JSON file (records list) as a DataFrame."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dim JSON file not found: {file_path}")
    try:
        with open(file_path, encoding="utf-8") as f:
            records = json.load(f)
        return pd.DataFrame(records).astype(str)
    except Exception as e:
        raise ValueError(f"Failed to load dim JSON '{file_path}': {e}") from e
