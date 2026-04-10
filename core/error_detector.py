"""
Error detection pipeline for mapped columns.

Adding a new check:
  1. Define a function with signature: check_name(value, dim_values, **kwargs) -> dict | None
  2. Add it to ERROR_CHECKS. Nothing else changes.
"""
from pathlib import Path

import pandas as pd

from core.dim_manager import get_dim_dataframe


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def check_against_dim_values(value: str, dim_values: set, **kwargs) -> dict | None:
    """Return an error dict if value (stripped) is not present in dim_values.

    Comparison is case-sensitive and strips leading/trailing whitespace.
    A blank/null cell (empty string after strip) is treated as an error.
    """
    normalised = value.strip()
    if normalised not in dim_values:
        return {
            "type": "value_not_in_dim",
            "value": value,
            "message": f"'{value}' not found in dimension table",
        }
    return None


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

ERROR_CHECKS = [
    check_against_dim_values,
    # check_null_or_blank,    # future
    # check_numeric_format,   # future
]


def run_checks(value: str, dim_values: set, **kwargs) -> list:
    """Run all registered check functions against a single value.

    Returns a list of error dicts (empty if no errors found).
    """
    errors = []
    for check in ERROR_CHECKS:
        result = check(value, dim_values, **kwargs)
        if result:
            errors.append(result)
    return errors


# ---------------------------------------------------------------------------
# High-level detection
# ---------------------------------------------------------------------------

def _build_dim_values(project_path: Path, dim_table: str, dim_column: str) -> set:
    """Load a dim table and return the set of stripped values in dim_column."""
    df = get_dim_dataframe(project_path, dim_table)
    return set(df[dim_column].astype(str).str.strip())


def detect_errors(project_path: Path, mapping: dict) -> list:
    """Run error detection for a single mapping against current data on disk.

    mapping must contain: transaction_table, transaction_column,
    dim_table, dim_column (as stored in mapping_store.json).

    Returns a list of error dicts, each with:
      row_index, transaction_table, transaction_column,
      bad_value, dim_table, dim_column, error_type.
    """
    project_path = Path(project_path)
    t_table = mapping["transaction_table"]
    t_col = mapping["transaction_column"]
    d_table = mapping["dim_table"]
    d_col = mapping["dim_column"]

    t_path = project_path / "data" / "transactions" / f"{t_table}.csv"
    if not t_path.exists():
        raise FileNotFoundError(f"Transaction table not found: '{t_table}'")

    try:
        tx_columns = pd.read_csv(t_path, dtype=str, encoding="utf-8", nrows=0).columns
    except Exception as e:
        raise ValueError(f"Failed to load CSV '{t_path}': {e}") from e

    col_lookup = {str(c).strip(): c for c in tx_columns}
    t_col_key = t_col.strip()
    if t_col_key not in col_lookup:
        raise ValueError(f"Column '{t_col}' not found in transaction table '{t_table}'")

    dim_values = _build_dim_values(project_path, d_table, d_col)

    errors = []
    matched_col = col_lookup[t_col_key]
    row_offset = 0
    try:
        chunk_iter = pd.read_csv(
            t_path,
            dtype=str,
            encoding="utf-8",
            chunksize=5000,
        )
        for chunk in chunk_iter:
            values = chunk[matched_col].tolist() if matched_col in chunk.columns else []
            for local_idx, raw in enumerate(values):
                value = str(raw).strip() if pd.notna(raw) else ""
                for err in run_checks(value, dim_values):
                    errors.append({
                        "row_index": int(row_offset + local_idx),
                        "transaction_table": t_table,
                        "transaction_column": t_col,
                        "bad_value": value,
                        "dim_table": d_table,
                        "dim_column": d_col,
                        "error_type": err["type"],
                    })
            row_offset += len(chunk)
    except Exception as e:
        raise ValueError(f"Failed to stream CSV '{t_path}': {e}") from e
    return errors


def detect_all_errors(project_path: Path, mappings: list) -> dict:
    """Run detect_errors for every mapping and return results keyed by mapping ID.

    Returns {mapping_id: [error_dicts]}.
    Mappings whose source files are missing are skipped (empty list returned).
    """
    project_path = Path(project_path)
    results = {}
    for mapping in mappings:
        try:
            results[mapping["id"]] = detect_errors(project_path, mapping)
        except (FileNotFoundError, ValueError):
            results[mapping["id"]] = []
    return results
