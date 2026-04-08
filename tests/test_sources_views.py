from ui.views.view_d_sources import has_dim_name_conflict
from ui.views.view_t_sources import count_mappings_for_table, has_table_name_conflict


def test_count_mappings_for_table_counts_both_sides():
    mappings = [
        {"transaction_table": "sales", "dim_table": "item_dim"},
        {"transaction_table": "orders", "dim_table": "region_dim"},
        {"transaction_table": "sales", "dim_table": "customer_dim"},
    ]
    assert count_mappings_for_table(mappings, "sales") == 2
    assert count_mappings_for_table(mappings, "item_dim") == 1


def test_has_table_name_conflict_checks_transaction_and_dim():
    project = {"transaction_tables": ["sales"], "dim_tables": ["item_dim"]}
    assert has_table_name_conflict(project, "sales") is True
    assert has_table_name_conflict(project, "item_dim") is True
    assert has_table_name_conflict(project, "orders") is False


def test_has_dim_name_conflict_checks_both_lists():
    project = {"transaction_tables": ["sales"], "dim_tables": ["item_dim"]}
    assert has_dim_name_conflict(project, "item_dim") is True
    assert has_dim_name_conflict(project, "sales") is True
    assert has_dim_name_conflict(project, "region_dim") is False

