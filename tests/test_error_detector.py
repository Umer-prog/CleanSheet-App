"""
Tests for Section 3: error_detector.py
Run with: python -m pytest tests/test_error_detector.py -v
"""
import pandas as pd
import pytest

from core.project_manager import create_project
from core.mapping_manager import add_mapping
from core.dim_manager import save_dim_dataframe
from core.data_loader import save_as_csv
from core.error_detector import (
    check_against_dim_values,
    detect_all_errors,
    detect_errors,
    run_checks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project(tmp_path):
    """Return a fresh project path."""
    return create_project("ErrTest", "Corp", tmp_path)


@pytest.fixture
def seeded_project(project):
    """Project with a dim table, a transaction table, and one mapping."""
    dim_df = pd.DataFrame({"item_name": ["Widget", "Gadget", "Sprocket"]})
    save_dim_dataframe(project, "item_dim", dim_df)

    t_df = pd.DataFrame({"item": ["Widget", "Gadget", "Typo", "widget"]})
    save_as_csv(t_df, project / "metadata" / "data" / "transactions" / "sales.csv")

    mapping = {
        "transaction_table": "sales",
        "transaction_column": "item",
        "dim_table": "item_dim",
        "dim_column": "item_name",
    }
    add_mapping(project, mapping)
    return project


# ---------------------------------------------------------------------------
# check_against_dim_values
# ---------------------------------------------------------------------------

class TestCheckAgainstDimValues:
    def test_valid_value_returns_none(self):
        assert check_against_dim_values("Widget", {"Widget", "Gadget"}) is None

    def test_invalid_value_returns_dict(self):
        result = check_against_dim_values("Typo", {"Widget", "Gadget"})
        assert result is not None
        assert result["type"] == "value_not_in_dim"
        assert result["value"] == "Typo"

    def test_blank_value_is_error(self):
        assert check_against_dim_values("", {"Widget"}) is not None

    def test_whitespace_only_is_error(self):
        assert check_against_dim_values("   ", {"Widget"}) is not None

    def test_strips_whitespace_before_check(self):
        # "Widget" with surrounding spaces should match "Widget" in the set
        assert check_against_dim_values("  Widget  ", {"Widget"}) is None

    def test_case_sensitive(self):
        # "widget" (lowercase) should NOT match "Widget"
        result = check_against_dim_values("widget", {"Widget", "Gadget"})
        assert result is not None

    def test_error_dict_has_message(self):
        result = check_against_dim_values("Bad", {"Good"})
        assert "message" in result


# ---------------------------------------------------------------------------
# run_checks
# ---------------------------------------------------------------------------

class TestRunChecks:
    def test_no_errors_returns_empty(self):
        assert run_checks("Widget", {"Widget"}) == []

    def test_error_returns_list(self):
        results = run_checks("Typo", {"Widget"})
        assert len(results) == 1
        assert results[0]["type"] == "value_not_in_dim"

    def test_multiple_checks_all_run(self):
        # With only one check registered, one result at most
        results = run_checks("Bad", {"Good"})
        assert isinstance(results, list)


# ---------------------------------------------------------------------------
# detect_errors
# ---------------------------------------------------------------------------

class TestDetectErrors:
    def test_returns_errors_for_bad_values(self, seeded_project):
        from core.mapping_manager import get_mappings
        mapping = get_mappings(seeded_project)[0]
        errors, _ = detect_errors(seeded_project, mapping)
        bad_values = [e["bad_value"] for e in errors]
        assert "Typo" in bad_values
        assert "widget" in bad_values  # case-sensitive mismatch

    def test_no_errors_for_valid_values(self, seeded_project):
        from core.mapping_manager import get_mappings
        mapping = get_mappings(seeded_project)[0]
        errors, _ = detect_errors(seeded_project, mapping)
        bad_values = [e["bad_value"] for e in errors]
        assert "Widget" not in bad_values
        assert "Gadget" not in bad_values

    def test_error_dict_structure(self, seeded_project):
        from core.mapping_manager import get_mappings
        mapping = get_mappings(seeded_project)[0]
        errors, _ = detect_errors(seeded_project, mapping)
        assert len(errors) > 0
        e = errors[0]
        for key in ("row_index", "transaction_table", "transaction_column",
                    "bad_value", "dim_table", "dim_column", "error_type"):
            assert key in e

    def test_row_index_is_int(self, seeded_project):
        from core.mapping_manager import get_mappings
        mapping = get_mappings(seeded_project)[0]
        errors, _ = detect_errors(seeded_project, mapping)
        for e in errors:
            assert isinstance(e["row_index"], int)

    def test_missing_transaction_table_raises(self, project):
        mapping = {
            "transaction_table": "missing",
            "transaction_column": "col",
            "dim_table": "item_dim",
            "dim_column": "item_name",
        }
        with pytest.raises(FileNotFoundError):
            detect_errors(project, mapping)

    def test_missing_column_raises(self, seeded_project):
        mapping = {
            "transaction_table": "sales",
            "transaction_column": "nonexistent_col",
            "dim_table": "item_dim",
            "dim_column": "item_name",
        }
        with pytest.raises(ValueError):
            detect_errors(seeded_project, mapping)

    def test_all_valid_returns_empty(self, project):
        dim_df = pd.DataFrame({"name": ["A", "B"]})
        save_dim_dataframe(project, "d", dim_df)
        t_df = pd.DataFrame({"col": ["A", "B"]})
        save_as_csv(t_df, project / "metadata" / "data" / "transactions" / "t.csv")
        mapping = {
            "transaction_table": "t",
            "transaction_column": "col",
            "dim_table": "d",
            "dim_column": "name",
        }
        errors, _ = detect_errors(project, mapping)
        assert errors == []


# ---------------------------------------------------------------------------
# detect_all_errors
# ---------------------------------------------------------------------------

class TestDetectAllErrors:
    def test_returns_dict_keyed_by_mapping_id(self, seeded_project):
        from core.mapping_manager import get_mappings
        mappings = get_mappings(seeded_project)
        results = detect_all_errors(seeded_project, mappings)
        assert "map_001" in results
        assert isinstance(results["map_001"], list)

    def test_missing_file_returns_empty_list(self, project):
        mappings = [{
            "id": "map_001",
            "transaction_table": "missing",
            "transaction_column": "col",
            "dim_table": "missing_dim",
            "dim_column": "col",
        }]
        results = detect_all_errors(project, mappings)
        assert results["map_001"] == []

    def test_multiple_mappings(self, project):
        dim1 = pd.DataFrame({"item": ["A", "B"]})
        dim2 = pd.DataFrame({"region": ["North", "South"]})
        save_dim_dataframe(project, "item_dim", dim1)
        save_dim_dataframe(project, "region_dim", dim2)

        t_df = pd.DataFrame({"item_col": ["A", "WRONG"], "region_col": ["North", "BAD"]})
        save_as_csv(t_df, project / "metadata" / "data" / "transactions" / "sales.csv")

        mid1 = add_mapping(project, {
            "transaction_table": "sales", "transaction_column": "item_col",
            "dim_table": "item_dim", "dim_column": "item",
        })
        mid2 = add_mapping(project, {
            "transaction_table": "sales", "transaction_column": "region_col",
            "dim_table": "region_dim", "dim_column": "region",
        })

        from core.mapping_manager import get_mappings
        results = detect_all_errors(project, get_mappings(project))
        assert len(results[mid1]) == 1
        assert len(results[mid2]) == 1
