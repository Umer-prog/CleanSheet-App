"""Unified CSV writer for chained sheets.

Reads each chain entry in order, applies column mappings, merges all rows,
appends a `source` column, and writes to disk.  Called every time a chain
link is confirmed or removed so the output file stays in sync.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from core.data_loader import get_sheet_as_dataframe, get_storage_format, read_table, write_table
from core.project_paths import internal_path


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
        # Collapsed / single-source — write plain file, no source column
        if chain:
            df = _load(chain[0]["file_path"], chain[0]["sheet_name"], chain[0].get("header_row"))
        else:
            df = pd.DataFrame()
        try:
            write_table(df, out_path)
        except OSError as e:
            raise OSError(f"chain_writer: could not write {out_path}: {e}") from e
        return out_path

    # ── Multi-entry merge ─────────────────────────────────────────────

    primary_entry = chain[0]
    primary_df = _load(primary_entry["file_path"], primary_entry["sheet_name"], primary_entry.get("header_row"))
    primary_cols: list[str] = primary_df.columns.tolist()

    # Collect extra columns: secondary cols that are NOT mapped to any primary col,
    # in the order they are first encountered across all secondary entries.
    extra_cols: list[str] = []
    seen_extra: set[str] = set()
    for entry in chain[1:]:
        mapping: dict[str, str] = entry.get("column_mapping") or {}
        mapped_secondary_vals: set[str] = set(mapping.values())
        sec_df = _load(entry["file_path"], entry["sheet_name"], entry.get("header_row"))
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
        sec_df = _load(entry["file_path"], entry["sheet_name"], entry.get("header_row"))
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
        write_table(merged, out_path)
    except OSError as e:
        raise OSError(f"chain_writer: could not write {out_path}: {e}") from e

    return out_path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load(file_path: str, sheet_name: str, header_row: int | None = None) -> pd.DataFrame:
    try:
        return get_sheet_as_dataframe(Path(file_path), sheet_name, header_row=header_row)
    except Exception as e:
        raise ValueError(f"chain_writer: could not read '{sheet_name}' from '{file_path}': {e}") from e


def _output_path(project_path: Path, table_name: str, category: str) -> Path:
    fmt = get_storage_format(project_path)
    ext = ".parquet" if fmt == "parquet" else ".csv"
    if category == "Dimension":
        return internal_path(project_path) / "metadata" / "data" / "dim" / f"{table_name}{ext}"
    return internal_path(project_path) / "metadata" / "data" / "transactions" / f"{table_name}{ext}"


# ── Screen 3 append-only path ─────────────────────────────────────────────────

def append_sheet_to_existing_chain(
    project_path: Path,
    table_name: str,
    category: str,
    sheet_meta: dict,
    new_entry: dict,
) -> Path:
    """Append a new sheet to an existing chain WITHOUT re-reading previous sources.

    Used exclusively by Screen 3's "Append" flow. The already-processed chain
    file (parquet/CSV) is loaded as-is, then only the new sheet is read from
    disk and merged in. Previously chained sheets are never re-read from their
    original Excel files, so resolved errors are not re-introduced.

    For first-time chain creation (Screen 1 → 1.5 → Chainer flow), use
    write_unified_csv instead — this function must not be called from that path.
    """
    project_path = Path(project_path)
    out_path = _output_path(project_path, table_name, category)

    # If the processed file doesn't exist yet, fall back to full rewrite.
    if not out_path.exists():
        return write_unified_csv(project_path, table_name, category, sheet_meta)

    existing_df = read_table(out_path)

    # Read only the newly appended sheet from disk.
    new_df = _load(
        new_entry["file_path"],
        new_entry["sheet_name"],
        new_entry.get("header_row"),
    )

    if new_df.empty:
        return out_path

    # Determine output columns from the existing processed file so new rows
    # conform to the established schema (including source/sheet_name columns).
    all_output_cols = list(existing_df.columns)
    mapping: dict[str, str] = new_entry.get("column_mapping") or {}
    mapped_secondary_vals: set[str] = set(mapping.values())

    n = len(new_df)
    out = pd.DataFrame("", index=range(n), columns=all_output_cols)

    # Apply column mapping: secondary col name → primary col name.
    for primary_col, sec_col in mapping.items():
        if sec_col in new_df.columns and primary_col in out.columns:
            out[primary_col] = new_df[sec_col].values

    # Pass through any extra secondary columns that land in the existing schema
    # (columns not part of the mapping but already present in the output file).
    for col in new_df.columns:
        if col not in mapped_secondary_vals and col in out.columns:
            out[col] = new_df[col].values

    if "source" in out.columns:
        out["source"] = new_entry.get("label", "")
    if "sheet_name" in out.columns:
        out["sheet_name"] = new_entry.get("sheet_name", "")

    merged = pd.concat([existing_df, out[all_output_cols]], ignore_index=True)

    try:
        write_table(merged, out_path)
    except OSError as e:
        raise OSError(f"chain_writer: could not append to '{out_path}': {e}") from e

    return out_path
