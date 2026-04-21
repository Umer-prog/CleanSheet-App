from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.data_loader import load_csv
from core.project_manager import open_project
from core.project_paths import active_dim_dir, active_transactions_dir


def _safe_sheet_name(name: str) -> str:
    cleaned = str(name).replace(":", "_").replace("\\", "_").replace("/", "_").replace("?", "_")
    cleaned = cleaned.replace("*", "_").replace("[", "_").replace("]", "_")
    return cleaned[:31] if len(cleaned) > 31 else cleaned


def export_final_workbook(project_path: Path, file_name: str = "final_updated.xlsx") -> Path:
    """Export current transaction and dimension tables into one Excel workbook.

    Output location:
      <project_path>/final/<file_name>
    """
    project_path = Path(project_path)
    project = open_project(project_path)
    tx_tables = list(project.get("transaction_tables", []))
    dim_tables = list(project.get("dim_tables", []))

    final_dir = project_path / "final"
    output_path = final_dir / file_name

    try:
        final_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create final export directory: {e}") from e

    written = 0
    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for table in tx_tables:
                csv_path = active_transactions_dir(project_path) / f"{table}.csv"
                if not csv_path.exists():
                    continue
                df = load_csv(csv_path)
                df.to_excel(writer, sheet_name=_safe_sheet_name(table), index=False)
                written += 1

            for table in dim_tables:
                csv_path = active_dim_dir(project_path) / f"{table}.csv"
                if not csv_path.exists():
                    continue
                df = load_csv(csv_path)
                df.to_excel(writer, sheet_name=_safe_sheet_name(table), index=False)
                written += 1
    except OSError as e:
        raise OSError(f"Failed to write final workbook: {e}") from e

    if written == 0:
        raise ValueError("No transaction/dimension tables were available to export.")

    return output_path

