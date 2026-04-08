"""
Tests for Section 1: project_manager.py and data_loader.py
Run with: python -m pytest tests/test_project_manager.py -v
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from core.project_manager import (
    create_project,
    list_projects,
    open_project,
    save_project_json,
    save_settings_json,
)
from core.data_loader import (
    get_sheet_as_dataframe,
    load_csv,
    load_dim_json,
    load_excel_sheets,
    save_as_csv,
    save_as_json,
)


# ---------------------------------------------------------------------------
# project_manager tests
# ---------------------------------------------------------------------------

class TestCreateProject:
    def test_creates_folder_structure(self, tmp_path):
        project_path = create_project("TestProject", "Acme", tmp_path)

        assert project_path.exists()
        assert (project_path / "data" / "transactions").exists()
        assert (project_path / "data" / "dim").exists()
        assert (project_path / "history").exists()
        assert (project_path / "mappings").exists()

    def test_writes_project_json(self, tmp_path):
        project_path = create_project("MyProject", "Corp", tmp_path)
        pj = json.loads((project_path / "project.json").read_text())

        assert pj["project_name"] == "MyProject"
        assert pj["company"] == "Corp"
        assert pj["transaction_tables"] == []
        assert pj["dim_tables"] == []

    def test_writes_settings_json(self, tmp_path):
        project_path = create_project("P", "C", tmp_path)
        sj = json.loads((project_path / "settings.json").read_text())

        assert sj["history_enabled"] is True
        assert sj["current_manifest"] is None
        assert "project_path" in sj

    def test_writes_empty_mapping_store(self, tmp_path):
        project_path = create_project("P", "C", tmp_path)
        ms = json.loads((project_path / "mappings" / "mapping_store.json").read_text())

        assert ms == {"mappings": []}

    def test_returns_project_path(self, tmp_path):
        project_path = create_project("Alpha", "Beta", tmp_path)
        assert project_path == tmp_path / "Alpha"

    def test_name_used_as_folder_name(self, tmp_path):
        project_path = create_project("SalesModule", "X", tmp_path)
        assert project_path.name == "SalesModule"


class TestOpenProject:
    def test_returns_merged_data(self, tmp_path):
        project_path = create_project("TestOpen", "OpenCo", tmp_path)
        state = open_project(project_path)

        assert state["project_name"] == "TestOpen"
        assert state["company"] == "OpenCo"
        assert "settings" in state
        assert state["settings"]["history_enabled"] is True

    def test_missing_project_json_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            open_project(tmp_path / "nonexistent")

    def test_project_path_in_result(self, tmp_path):
        project_path = create_project("P", "C", tmp_path)
        state = open_project(project_path)
        assert "project_path" in state


class TestListProjects:
    def test_finds_existing_projects(self, tmp_path):
        create_project("Alpha", "A", tmp_path)
        create_project("Beta", "B", tmp_path)

        projects = list_projects(tmp_path)
        names = [p["project_name"] for p in projects]

        assert "Alpha" in names
        assert "Beta" in names

    def test_ignores_non_project_folders(self, tmp_path):
        (tmp_path / "not_a_project").mkdir()
        create_project("Real", "R", tmp_path)

        projects = list_projects(tmp_path)
        assert len(projects) == 1

    def test_empty_root_returns_empty_list(self, tmp_path):
        assert list_projects(tmp_path) == []

    def test_nonexistent_root_returns_empty_list(self, tmp_path):
        assert list_projects(tmp_path / "does_not_exist") == []

    def test_project_has_required_keys(self, tmp_path):
        create_project("P", "C", tmp_path)
        projects = list_projects(tmp_path)
        assert len(projects) == 1
        p = projects[0]
        for key in ("project_name", "company", "created_at", "last_modified", "project_path"):
            assert key in p


class TestSaveHelpers:
    def test_save_project_json(self, tmp_path):
        project_path = create_project("P", "C", tmp_path)
        state = open_project(project_path)

        state["company"] = "Updated"
        save_project_json(project_path, {k: v for k, v in state.items() if k != "settings"})

        reloaded = json.loads((project_path / "project.json").read_text())
        assert reloaded["company"] == "Updated"

    def test_save_settings_json(self, tmp_path):
        project_path = create_project("P", "C", tmp_path)
        save_settings_json(project_path, {"history_enabled": False, "current_manifest": "m001"})

        reloaded = json.loads((project_path / "settings.json").read_text())
        assert reloaded["history_enabled"] is False
        assert reloaded["current_manifest"] == "m001"


# ---------------------------------------------------------------------------
# data_loader tests (file-based, no Excel dependency for most)
# ---------------------------------------------------------------------------

class TestSaveAndLoadCsv:
    def test_roundtrip(self, tmp_path):
        df = pd.DataFrame({"name": ["Alice", "Bob"], "age": ["30", "25"]})
        dest = tmp_path / "test.csv"
        save_as_csv(df, dest)

        loaded = load_csv(dest)
        assert list(loaded.columns) == ["name", "age"]
        assert loaded["name"].tolist() == ["Alice", "Bob"]

    def test_creates_parent_dirs(self, tmp_path):
        df = pd.DataFrame({"x": ["1"]})
        dest = tmp_path / "sub" / "dir" / "file.csv"
        save_as_csv(df, dest)
        assert dest.exists()

    def test_load_missing_csv_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_csv(tmp_path / "missing.csv")


class TestSaveAndLoadJson:
    def test_roundtrip(self, tmp_path):
        df = pd.DataFrame({"item": ["Widget", "Gadget"], "code": ["W1", "G2"]})
        dest = tmp_path / "dim.json"
        save_as_json(df, dest)

        loaded = load_dim_json(dest)
        assert list(loaded.columns) == ["item", "code"]
        assert loaded["item"].tolist() == ["Widget", "Gadget"]

    def test_creates_parent_dirs(self, tmp_path):
        df = pd.DataFrame({"x": ["1"]})
        dest = tmp_path / "nested" / "dim.json"
        save_as_json(df, dest)
        assert dest.exists()

    def test_load_missing_json_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_dim_json(tmp_path / "missing.json")


class TestExcelLoader:
    """
    These tests require an actual Excel file. They create one in-memory using openpyxl
    via pandas so no fixture file is needed.
    """

    def _make_excel(self, tmp_path) -> Path:
        path = tmp_path / "sample.xlsx"
        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            pd.DataFrame({"col_a": ["x", "y"], "col_b": ["1", "2"]}).to_excel(
                writer, sheet_name="Sheet1", index=False
            )
            pd.DataFrame({"name": ["Alice"], "dept": ["Sales"]}).to_excel(
                writer, sheet_name="Employees", index=False
            )
        return path

    def test_load_excel_sheets_returns_names(self, tmp_path):
        path = self._make_excel(tmp_path)
        sheets = load_excel_sheets(path)
        assert "Sheet1" in sheets
        assert "Employees" in sheets

    def test_get_sheet_as_dataframe(self, tmp_path):
        path = self._make_excel(tmp_path)
        df = get_sheet_as_dataframe(path, "Sheet1")
        assert list(df.columns) == ["col_a", "col_b"]
        assert df.shape == (2, 2)

    def test_get_sheet_values_as_strings(self, tmp_path):
        path = self._make_excel(tmp_path)
        df = get_sheet_as_dataframe(path, "Sheet1")
        # pandas 2.x may use StringDtype; confirm values are string-like regardless
        assert df["col_b"].map(type).eq(str).all()

    def test_missing_excel_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_excel_sheets(tmp_path / "missing.xlsx")

    def test_missing_excel_get_sheet_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            get_sheet_as_dataframe(tmp_path / "missing.xlsx", "Sheet1")
