"""
Tests for Section 2: snapshot_manager.py
Run with: python -m pytest tests/test_snapshot_manager.py -v
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from core.project_manager import create_project
from core.snapshot_manager import (
    create_snapshot,
    get_manifest,
    hash_dataframe,
    list_manifests,
    revert_to_manifest,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project(tmp_path):
    """Create a fresh project and return its path."""
    return create_project("SnapTest", "Acme", tmp_path)


def make_df(data=None):
    if data is None:
        data = {"name": ["Alice", "Bob"], "dept": ["Sales", "IT"]}
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# hash_dataframe
# ---------------------------------------------------------------------------

class TestHashDataframe:
    def test_returns_8_chars(self):
        assert len(hash_dataframe(make_df())) == 8

    def test_same_content_same_hash(self):
        df1 = make_df()
        df2 = make_df()
        assert hash_dataframe(df1) == hash_dataframe(df2)

    def test_different_content_different_hash(self):
        df1 = make_df({"a": ["x"]})
        df2 = make_df({"a": ["y"]})
        assert hash_dataframe(df1) != hash_dataframe(df2)

    def test_hash_is_hex_string(self):
        h = hash_dataframe(make_df())
        int(h, 16)  # raises ValueError if not valid hex


# ---------------------------------------------------------------------------
# create_snapshot — history ON
# ---------------------------------------------------------------------------

class TestCreateSnapshotHistoryOn:
    def test_returns_manifest_id(self, project):
        mid = create_snapshot(project, {"sales": make_df()})
        assert mid == "manifest_001"

    def test_creates_manifest_folder(self, project):
        mid = create_snapshot(project, {"sales": make_df()})
        assert (project / "history" / mid).is_dir()

    def test_creates_manifest_json(self, project):
        mid = create_snapshot(project, {"sales": make_df()}, label="First upload")
        manifest_file = project / "history" / mid / "manifest.json"
        assert manifest_file.exists()
        data = json.loads(manifest_file.read_text())
        assert data["manifest_id"] == mid
        assert data["label"] == "First upload"
        assert "sales" in data["tables"]
        assert "created_at" in data

    def test_hashed_csv_written_to_manifest_folder(self, project):
        df = make_df()
        mid = create_snapshot(project, {"sales": df})
        manifest = get_manifest(project, mid)
        hashed_file = project / "history" / mid / manifest["tables"]["sales"]
        assert hashed_file.exists()

    def test_hashed_filename_contains_hash(self, project):
        df = make_df()
        mid = create_snapshot(project, {"sales": df})
        manifest = get_manifest(project, mid)
        filename = manifest["tables"]["sales"]
        assert hash_dataframe(df) in filename

    def test_updates_data_transactions(self, project):
        create_snapshot(project, {"sales": make_df()})
        assert (project / "data" / "transactions" / "sales.csv").exists()

    def test_updates_settings_current_manifest(self, project):
        mid = create_snapshot(project, {"sales": make_df()})
        settings = json.loads((project / "settings.json").read_text())
        assert settings["current_manifest"] == mid

    def test_sequential_manifest_ids(self, project):
        mid1 = create_snapshot(project, {"t1": make_df()})
        mid2 = create_snapshot(project, {"t1": make_df({"a": ["x"]})})
        assert mid1 == "manifest_001"
        assert mid2 == "manifest_002"

    def test_multiple_tables_in_one_snapshot(self, project):
        tables = {
            "sales": make_df({"item": ["A"]}),
            "orders": make_df({"order": ["1"]}),
        }
        mid = create_snapshot(project, tables)
        manifest = get_manifest(project, mid)
        assert "sales" in manifest["tables"]
        assert "orders" in manifest["tables"]

    def test_deduplication_same_content_not_rewritten(self, project):
        df = make_df()
        mid = create_snapshot(project, {"sales": df})
        manifest = get_manifest(project, mid)
        hashed_file = project / "history" / mid / manifest["tables"]["sales"]
        mtime_before = hashed_file.stat().st_mtime

        # Second snapshot with identical content — file should not be overwritten
        mid2 = create_snapshot(project, {"sales": df})
        manifest2 = get_manifest(project, mid2)
        hashed_file2 = project / "history" / mid2 / manifest2["tables"]["sales"]
        # New manifest folder has its own copy (different folder), this is fine
        assert hashed_file2.exists()
        # Original file in manifest_001 untouched
        assert hashed_file.stat().st_mtime == mtime_before


# ---------------------------------------------------------------------------
# create_snapshot — history OFF
# ---------------------------------------------------------------------------

class TestCreateSnapshotHistoryOff:
    def test_returns_none(self, project):
        settings = json.loads((project / "settings.json").read_text())
        settings["history_enabled"] = False
        (project / "settings.json").write_text(json.dumps(settings))

        result = create_snapshot(project, {"sales": make_df()})
        assert result is None

    def test_still_updates_data_transactions(self, project):
        settings = json.loads((project / "settings.json").read_text())
        settings["history_enabled"] = False
        (project / "settings.json").write_text(json.dumps(settings))

        create_snapshot(project, {"sales": make_df()})
        assert (project / "data" / "transactions" / "sales.csv").exists()

    def test_no_history_folder_created(self, project):
        settings = json.loads((project / "settings.json").read_text())
        settings["history_enabled"] = False
        (project / "settings.json").write_text(json.dumps(settings))

        create_snapshot(project, {"sales": make_df()})
        history_path = project / "history"
        # Either doesn't exist or has no manifest subfolders
        if history_path.exists():
            manifest_folders = [d for d in history_path.iterdir() if d.name.startswith("manifest_")]
            assert manifest_folders == []


# ---------------------------------------------------------------------------
# get_manifest
# ---------------------------------------------------------------------------

class TestGetManifest:
    def test_returns_manifest_data(self, project):
        mid = create_snapshot(project, {"t": make_df()}, label="test")
        data = get_manifest(project, mid)
        assert data["manifest_id"] == mid
        assert data["label"] == "test"

    def test_missing_manifest_raises(self, project):
        with pytest.raises(FileNotFoundError):
            get_manifest(project, "manifest_999")


# ---------------------------------------------------------------------------
# list_manifests
# ---------------------------------------------------------------------------

class TestListManifests:
    def test_empty_history_returns_empty(self, project):
        assert list_manifests(project) == []

    def test_returns_in_order(self, project):
        create_snapshot(project, {"t": make_df()}, label="first")
        create_snapshot(project, {"t": make_df({"a": ["x"]})}, label="second")
        manifests = list_manifests(project)
        assert len(manifests) == 2
        assert manifests[0]["manifest_id"] == "manifest_001"
        assert manifests[1]["manifest_id"] == "manifest_002"

    def test_returns_all_manifests(self, project):
        for i in range(3):
            create_snapshot(project, {"t": make_df({"a": [str(i)]})})
        assert len(list_manifests(project)) == 3

    def test_no_history_folder_returns_empty(self, tmp_path):
        p = create_project("NoHist", "Co", tmp_path)
        assert list_manifests(p) == []


# ---------------------------------------------------------------------------
# revert_to_manifest
# ---------------------------------------------------------------------------

class TestRevertToManifest:
    def test_restores_files_to_transactions(self, project):
        original_df = make_df({"val": ["original"]})
        mid = create_snapshot(project, {"sales": original_df})

        # Overwrite with new data
        create_snapshot(project, {"sales": make_df({"val": ["updated"]})})

        # Revert to first
        revert_to_manifest(project, mid)
        restored = pd.read_csv(project / "data" / "transactions" / "sales.csv")
        assert restored["val"].tolist() == ["original"]

    def test_updates_settings_current_manifest(self, project):
        mid1 = create_snapshot(project, {"t": make_df()})
        create_snapshot(project, {"t": make_df({"a": ["x"]})})

        revert_to_manifest(project, mid1)
        settings = json.loads((project / "settings.json").read_text())
        assert settings["current_manifest"] == mid1

    def test_does_not_delete_newer_manifests(self, project):
        mid1 = create_snapshot(project, {"t": make_df()})
        mid2 = create_snapshot(project, {"t": make_df({"a": ["x"]})})

        revert_to_manifest(project, mid1)
        assert (project / "history" / mid2).exists()

    def test_missing_manifest_raises(self, project):
        with pytest.raises(FileNotFoundError):
            revert_to_manifest(project, "manifest_999")

    def test_multiple_table_revert(self, project):
        tables_v1 = {
            "sales": make_df({"item": ["A"]}),
            "orders": make_df({"order": ["1"]}),
        }
        tables_v2 = {
            "sales": make_df({"item": ["B"]}),
            "orders": make_df({"order": ["2"]}),
        }
        mid1 = create_snapshot(project, tables_v1)
        create_snapshot(project, tables_v2)

        revert_to_manifest(project, mid1)

        sales = pd.read_csv(project / "data" / "transactions" / "sales.csv", dtype=str)
        orders = pd.read_csv(project / "data" / "transactions" / "orders.csv", dtype=str)
        assert sales["item"].tolist() == ["A"]
        assert orders["order"].tolist() == ["1"]
