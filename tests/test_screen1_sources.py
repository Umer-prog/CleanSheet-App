from ui.screen1_sources import (
    find_duplicate_table_names,
    normalize_table_name,
    validate_confirm_requirements,
)


def test_normalize_table_name_basic():
    assert normalize_table_name("Sales Fact Table") == "sales_fact_table"


def test_normalize_table_name_handles_symbols_and_digits():
    assert normalize_table_name(" 2025@Orders ") == "table_2025_orders"


def test_find_duplicate_table_names_detects_existing_collision():
    selected = [{"sheet_name": "Orders", "category": "Transaction"}]
    duplicates = find_duplicate_table_names(selected, existing_table_names={"orders"})
    assert duplicates == {"orders"}


def test_find_duplicate_table_names_detects_internal_collision():
    selected = [
        {"sheet_name": "Orders", "category": "Transaction"},
        {"sheet_name": "Orders!!", "category": "Dimension"},
    ]
    duplicates = find_duplicate_table_names(selected, existing_table_names=set())
    assert duplicates == {"orders"}


def test_validate_confirm_requires_sources():
    assert validate_confirm_requirements([]) == "Add at least one file before continuing."


def test_validate_confirm_requires_transaction_and_dimension():
    sources = [{"file_path": "a.xlsx", "sheets": [{"sheet_name": "S", "category": "Transaction"}]}]
    assert validate_confirm_requirements(sources) == "At least one dimension sheet is required."


def test_validate_confirm_accepts_mixed_categories():
    sources = [
        {"file_path": "a.xlsx", "sheets": [{"sheet_name": "S", "category": "Transaction"}]},
        {"file_path": "b.xlsx", "sheets": [{"sheet_name": "D", "category": "Dimension"}]},
    ]
    assert validate_confirm_requirements(sources) is None

