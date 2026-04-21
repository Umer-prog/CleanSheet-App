"""Unified CSV writer for chained sheets.

Reads each chain entry in order, applies column mappings, merges all rows,
appends a `source` column, and writes to disk.  Called every time a chain
link is confirmed or removed so the output file stays in sync.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_unified_csv(
    project_path: Path,
    table_name: str,
    category: str,
    sheet_meta: dict,
) -> Path:
    """Produce the merged output file for a chained sheet.

    If the chain collapses back to a single entry the output is a plain
    CSV without a `source` column, matching a normal non-chained sheet.

    Returns the path of the written file.
    """
    project_path = Path(project_path)
    chain: list[dict] = sheet_meta.get("chain", [])

    out_path = _output_path(project_path, table_name, category)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if len(chain) <= 1:
        # Collapsed / single-source — write plain CSV, no source column
        if chain:
            df = _load(chain[0]["file_path"], chain[0]["sheet_name"])
        else:
            df = pd.DataFrame()
        try:
            df.to_csv(out_path, index=False)
        except OSError as e:
            raise OSError(f"chain_writer: could not write {out_path}: {e}") from e
        return out_path

    # ── Multi-entry merge ─────────────────────────────────────────────

    primary_entry = chain[0]
    primary_df = _load(primary_entry["file_path"], primary_entry["sheet_name"])
    primary_cols: list[str] = primary_df.columns.tolist()

    # Collect extra columns: secondary cols that are NOT mapped to any primary col,
    # in the order they are first encountered across all secondary entries.
    extra_cols: list[str] = []
    seen_extra: set[str] = set()
    for entry in chain[1:]:
        mapping: dict[str, str] = entry.get("column_mapping") or {}
        mapped_secondary_vals: set[str] = set(mapping.values())
        sec_df = _load(entry["file_path"], entry["sheet_name"])
        for col in sec_df.columns:
            if col not in mapped_secondary_vals and col not in seen_extra:
                extra_cols.append(col)
                seen_extra.add(col)

    all_output_cols: list[str] = primary_cols + extra_cols + ["source", "sheet_name"]

    frames: list[pd.DataFrame] = []

    # Primary rows — fill extra cols with empty string
    p_frame = primary_df.copy()
    for ec in extra_cols:
        p_frame[ec] = ""
    p_frame["source"] = primary_entry["label"]
    p_frame["sheet_name"] = primary_entry["sheet_name"]
    frames.append(p_frame[all_output_cols])

    # Secondary rows
    for entry in chain[1:]:
        mapping = entry.get("column_mapping") or {}
        sec_df = _load(entry["file_path"], entry["sheet_name"])
        mapped_secondary_vals = set(mapping.values())

        n = len(sec_df)
        out = pd.DataFrame("", index=range(n), columns=all_output_cols)

        # Rename mapped secondary columns → primary column names
        for primary_col, sec_col in mapping.items():
            if sec_col in sec_df.columns and primary_col in out.columns:
                out[primary_col] = sec_df[sec_col].values

        # Fill extra columns contributed by this secondary entry
        for col in sec_df.columns:
            if col not in mapped_secondary_vals and col in seen_extra:
                out[col] = sec_df[col].values

        out["source"] = entry["label"]
        out["sheet_name"] = entry["sheet_name"]
        frames.append(out)

    merged = pd.concat(frames, ignore_index=True)[all_output_cols]

    try:
        merged.to_csv(out_path, index=False)
    except OSError as e:
        raise OSError(f"chain_writer: could not write {out_path}: {e}") from e

    return out_path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(file_path: str, sheet_name: str) -> pd.DataFrame:
    try:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        raise ValueError(f"chain_writer: could not read '{sheet_name}' from '{file_path}': {e}") from e


def _output_path(project_path: Path, table_name: str, category: str) -> Path:
    if category == "Dimension":
        return project_path / "metadata" / "data" / "dim" / f"{table_name}.csv"
    return project_path / "metadata" / "data" / "transactions" / f"{table_name}.csv"
