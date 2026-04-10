from pathlib import Path

import pandas as pd

from core.data_loader import save_as_csv
from core.dim_manager import save_dim_dataframe
from core.final_export_manager import export_final_workbook
from core.project_manager import create_project, save_project_json


def test_export_final_workbook_creates_excel_with_transaction_and_dim_sheets(tmp_path):
    project_path = create_project("ExportTest", "Corp", tmp_path)

    tx_df = pd.DataFrame({"item": ["Widget", "Gadget"], "qty": ["10", "5"]})
    dim_df = pd.DataFrame({"item_name": ["Widget", "Gadget"]})

    save_as_csv(tx_df, project_path / "data" / "transactions" / "sales.csv")
    save_dim_dataframe(project_path, "item_dim", dim_df)

    save_project_json(
        project_path,
        {
            "project_name": "ExportTest",
            "created_at": "2026-04-09",
            "company": "Corp",
            "transaction_tables": ["sales"],
            "dim_tables": ["item_dim"],
        },
    )

    output = export_final_workbook(project_path)

    assert output == project_path / "final" / "final_updated.xlsx"
    assert output.exists()

    book = pd.ExcelFile(output, engine="openpyxl")
    assert "sales" in book.sheet_names
    assert "item_dim" in book.sheet_names

