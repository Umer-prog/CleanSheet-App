from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

import pandas as pd

_log = logging.getLogger(__name__)

from core.data_loader import read_table
from core.project_manager import open_project
from core.project_paths import active_dim_dir, active_transactions_dir


def _safe_sheet_name(name: str) -> str:
    cleaned = str(name).replace(":", "_").replace("\\", "_").replace("/", "_").replace("?", "_")
    cleaned = cleaned.replace("*", "_").replace("[", "_").replace("]", "_")
    return cleaned[:31] if len(cleaned) > 31 else cleaned


def export_final_workbook(
    project_path: Path,
    file_name: str = "final_updated.xlsx",
    report_progress: Callable[[int, int], None] | None = None,
) -> Path:
    """Export current transaction and dimension tables into one Excel workbook.

    Output location:
      <project_path>/final/<file_name>

    report_progress(done, total) is called from the background thread after
    each table is written so the UI can animate a progress bar.
    """
    def _report(done: int, total: int) -> None:
        if report_progress:
            report_progress(done, total)

    project_path = Path(project_path)
    project = open_project(project_path)
    tx_tables = list(project.get("transaction_tables", []))
    dim_tables = list(project.get("dim_tables", []))

    # total steps = one per table + one final step for closing/flushing the file
    total_steps = len(tx_tables) + len(dim_tables) + 1
    _report(0, total_steps)

    final_dir = project_path / "final"
    output_path = final_dir / file_name

    try:
        final_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create final export directory: {e}") from e

    written = 0
    step = 0
    try:
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            for table in tx_tables:
                try:
                    df = read_table(active_transactions_dir(project_path) / f"{table}.csv")
                except FileNotFoundError:
                    step += 1
                    _report(step, total_steps)
                    continue
                df.to_excel(writer, sheet_name=_safe_sheet_name(table), index=False)
                written += 1
                step += 1
                _report(step, total_steps)

            for table in dim_tables:
                try:
                    df = read_table(active_dim_dir(project_path) / f"{table}.csv")
                except FileNotFoundError:
                    step += 1
                    _report(step, total_steps)
                    continue
                df.to_excel(writer, sheet_name=_safe_sheet_name(table), index=False)
                written += 1
                step += 1
                _report(step, total_steps)

        # File is now closed/flushed — final step
        _report(total_steps, total_steps)
    except OSError as e:
        raise OSError(f"Failed to write final workbook: {e}") from e

    if written == 0:
        raise ValueError("No transaction/dimension tables were available to export.")

    _log.info("Export completed: %s (%d tables written)", output_path, written)
    return output_path

