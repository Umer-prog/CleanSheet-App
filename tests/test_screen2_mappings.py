from ui.screen2_mappings import (
    find_unmapped_tables,
    mapping_key,
    validate_mapping_selection,
)


def test_validate_mapping_selection_requires_table_and_columns():
    assert (
        validate_mapping_selection(
            transaction_table=None,
            dim_table="item_dim",
            transaction_column="item",
            dim_column="name",
        )
        == "Select a transaction table."
    )


def test_validate_mapping_selection_accepts_valid_input():
    assert (
        validate_mapping_selection(
            transaction_table="sales",
            dim_table="item_dim",
            transaction_column="item",
            dim_column="name",
        )
        is None
    )


def test_find_unmapped_tables_returns_missing_both_sides():
    mappings = [
        {
            "transaction_table": "sales",
            "transaction_column": "item",
            "dim_table": "item_dim",
            "dim_column": "name",
        }
    ]
    missing_tx, missing_dim = find_unmapped_tables(
        transaction_tables=["sales", "orders"],
        dim_tables=["item_dim", "customer_dim"],
        mappings=mappings,
    )
    assert missing_tx == ["orders"]
    assert missing_dim == ["customer_dim"]


def test_mapping_key_normalizes_tuple_shape():
    m = {
        "transaction_table": "sales",
        "transaction_column": "item",
        "dim_table": "item_dim",
        "dim_column": "name",
    }
    assert mapping_key(m) == ("sales", "item", "item_dim", "name")

