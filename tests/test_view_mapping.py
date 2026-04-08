from pathlib import Path

import pandas as pd

from core.data_loader import load_csv, save_as_csv
from core.dim_manager import save_dim_dataframe
from core.project_manager import create_project
from ui.views.view_mapping import (
    format_dataframe_preview,
    get_valid_dim_values,
    replace_transaction_value,
)


def test_format_dataframe_preview_for_empty_df():
    assert format_dataframe_preview(pd.DataFrame()) == "(No rows)"


def test_get_valid_dim_values_returns_sorted_unique(tmp_path):
    project = create_project("P", "C", tmp_path)
    save_dim_dataframe(
        project,
        "item_dim",
        pd.DataFrame({"name": ["Widget", "  Widget ", "Gadget", ""]}),
    )
    values = get_valid_dim_values(project, "item_dim", "name")
    assert values == ["Gadget", "Widget"]


def test_replace_transaction_value_updates_target_row(tmp_path):
    project = create_project("P", "C", tmp_path)
    csv_path = Path(project) / "data" / "transactions" / "sales.csv"
    save_as_csv(pd.DataFrame({"item": ["Bad", "Good"]}), csv_path)

    mapping = {
        "transaction_table": "sales",
        "transaction_column": "item",
        "dim_table": "item_dim",
        "dim_column": "name",
    }
    replace_transaction_value(project, mapping, row_index=0, new_value="Widget")

    reloaded = load_csv(csv_path)
    assert reloaded.iloc[0]["item"] == "Widget"
    assert reloaded.iloc[1]["item"] == "Good"

