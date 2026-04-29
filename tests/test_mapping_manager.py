"""
Tests for Section 3: mapping_manager.py and dim_manager.py
Run with: python -m pytest tests/test_mapping_manager.py -v
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from core.project_manager import create_project
from core.mapping_manager import (
    add_mapping,
    delete_mapping,
    delete_mappings_for_table,
    get_mapping_by_id,
    get_mappings,
)
from core.dim_manager import (
    append_dim_row,
    dim_exists,
    get_dim_columns,
    get_dim_dataframe,
    save_dim_dataframe,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project(tmp_path):
    """Return a fresh project path."""
    return create_project("MapTest", "Corp", tmp_path)


def sample_mapping(t_table="sales", t_col="item", d_table="item_dim", d_col="item_name"):
    return {
        "transaction_table": t_table,
        "transaction_column": t_col,
        "dim_table": d_table,
        "dim_column": d_col,
    }


# ---------------------------------------------------------------------------
# mapping_manager — add_mapping
# ---------------------------------------------------------------------------

class TestAddMapping:
    def test_returns_mapping_id(self, project):
        mid = add_mapping(project, sample_mapping())
        assert mid == "map_001"

    def test_sequential_ids(self, project):
        mid1 = add_mapping(project, sample_mapping())
        mid2 = add_mapping(project, sample_mapping("orders", "customer", "cust_dim", "name"))
        assert mid1 == "map_001"
        assert mid2 == "map_002"

    def test_persists_to_store(self, project):
        add_mapping(project, sample_mapping())
        store = json.loads((project / "metadata" / "mappings" / "mapping_store.json").read_text())
        assert len(store["mappings"]) == 1
        m = store["mappings"][0]
        assert m["transaction_table"] == "sales"
        assert m["transaction_column"] == "item"
        assert m["dim_table"] == "item_dim"
        assert m["dim_column"] == "item_name"

    def test_id_assigned_not_caller_supplied(self, project):
        data = {**sample_mapping(), "id": "ignored"}
        mid = add_mapping(project, data)
        assert mid == "map_001"
        m = get_mapping_by_id(project, mid)
        assert m["id"] == "map_001"


# ---------------------------------------------------------------------------
# mapping_manager — get_mappings / get_mapping_by_id
# ---------------------------------------------------------------------------

class TestGetMappings:
    def test_empty_project_returns_empty(self, project):
        assert get_mappings(project) == []

    def test_returns_all_mappings(self, project):
        add_mapping(project, sample_mapping())
        add_mapping(project, sample_mapping("orders", "cust", "cust_dim", "name"))
        assert len(get_mappings(project)) == 2

    def test_get_by_id_found(self, project):
        mid = add_mapping(project, sample_mapping())
        m = get_mapping_by_id(project, mid)
        assert m is not None
        assert m["id"] == mid

    def test_get_by_id_not_found_returns_none(self, project):
        assert get_mapping_by_id(project, "map_999") is None


# ---------------------------------------------------------------------------
# mapping_manager — delete_mapping
# ---------------------------------------------------------------------------

class TestDeleteMapping:
    def test_removes_mapping(self, project):
        mid = add_mapping(project, sample_mapping())
        delete_mapping(project, mid)
        assert get_mappings(project) == []

    def test_only_removes_target(self, project):
        mid1 = add_mapping(project, sample_mapping())
        mid2 = add_mapping(project, sample_mapping("orders", "c", "cd", "n"))
        delete_mapping(project, mid1)
        remaining = get_mappings(project)
        assert len(remaining) == 1
        assert remaining[0]["id"] == mid2

    def test_unknown_id_is_silent(self, project):
        add_mapping(project, sample_mapping())
        delete_mapping(project, "map_999")  # should not raise
        assert len(get_mappings(project)) == 1


# ---------------------------------------------------------------------------
# mapping_manager — delete_mappings_for_table
# ---------------------------------------------------------------------------

class TestDeleteMappingsForTable:
    def test_deletes_transaction_side(self, project):
        add_mapping(project, sample_mapping("sales", "item", "item_dim", "name"))
        add_mapping(project, sample_mapping("orders", "cust", "cust_dim", "name"))
        deleted = delete_mappings_for_table(project, "sales")
        assert deleted == 1
        assert len(get_mappings(project)) == 1

    def test_deletes_dim_side(self, project):
        add_mapping(project, sample_mapping("sales", "item", "item_dim", "name"))
        add_mapping(project, sample_mapping("orders", "cust", "cust_dim", "name"))
        deleted = delete_mappings_for_table(project, "item_dim")
        assert deleted == 1

    def test_returns_count(self, project):
        add_mapping(project, sample_mapping("sales", "item", "item_dim", "name"))
        add_mapping(project, sample_mapping("sales", "region", "region_dim", "region"))
        deleted = delete_mappings_for_table(project, "sales")
        assert deleted == 2

    def test_no_match_returns_zero(self, project):
        add_mapping(project, sample_mapping())
        assert delete_mappings_for_table(project, "nonexistent") == 0


# ---------------------------------------------------------------------------
# dim_manager — save and load
# ---------------------------------------------------------------------------

class TestDimManager:
    def _make_dim(self, project):
        df = pd.DataFrame({"item_name": ["Widget", "Gadget"], "code": ["W1", "G2"]})
        save_dim_dataframe(project, "item_dim", df)
        return df

    def test_dim_exists_false_before_save(self, project):
        assert not dim_exists(project, "item_dim")

    def test_dim_exists_true_after_save(self, project):
        self._make_dim(project)
        assert dim_exists(project, "item_dim")

    def test_save_creates_dim_file(self, project):
        self._make_dim(project)
        dim_dir = project / "metadata" / "data" / "dim"
        assert any(f.stem == "item_dim" for f in dim_dir.iterdir())

    def test_load_roundtrip(self, project):
        self._make_dim(project)
        df = get_dim_dataframe(project, "item_dim")
        assert list(df.columns) == ["item_name", "code"]
        assert df["item_name"].tolist() == ["Widget", "Gadget"]

    def test_save_duplicate_raises(self, project):
        self._make_dim(project)
        with pytest.raises(FileExistsError):
            self._make_dim(project)

    def test_get_dim_columns(self, project):
        self._make_dim(project)
        cols = get_dim_columns(project, "item_dim")
        assert cols == ["item_name", "code"]

    def test_get_dim_missing_raises(self, project):
        with pytest.raises(FileNotFoundError):
            get_dim_dataframe(project, "missing_dim")


# ---------------------------------------------------------------------------
# dim_manager — append_dim_row
# ---------------------------------------------------------------------------

class TestAppendDimRow:
    def test_appends_row(self, project):
        df = pd.DataFrame({"item_name": ["Widget"], "code": ["W1"]})
        save_dim_dataframe(project, "item_dim", df)

        append_dim_row(project, "item_dim", {"item_name": "Sprocket", "code": "S9"})

        loaded = get_dim_dataframe(project, "item_dim")
        assert len(loaded) == 2
        assert loaded.iloc[-1]["item_name"] == "Sprocket"

    def test_values_stored_as_strings(self, project):
        df = pd.DataFrame({"name": ["A"], "qty": ["1"]})
        save_dim_dataframe(project, "d", df)
        append_dim_row(project, "d", {"name": "B", "qty": 42})

        loaded = get_dim_dataframe(project, "d")
        assert loaded.iloc[-1]["qty"] == "42"

    def test_append_to_missing_dim_raises(self, project):
        with pytest.raises(FileNotFoundError):
            append_dim_row(project, "missing_dim", {"col": "val"})

    def test_multiple_appends(self, project):
        df = pd.DataFrame({"val": ["a"]})
        save_dim_dataframe(project, "d", df)
        append_dim_row(project, "d", {"val": "b"})
        append_dim_row(project, "d", {"val": "c"})
        loaded = get_dim_dataframe(project, "d")
        assert loaded["val"].tolist() == ["a", "b", "c"]
