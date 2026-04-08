import json

import pandas as pd

from core.project_manager import create_project
from core.snapshot_manager import create_snapshot, get_manifest, update_manifest_label
from ui.views.view_history import manifest_tables_text, manifest_title
from ui.views.view_settings import merged_project_payload, merged_settings_payload


def test_update_manifest_label_changes_manifest_json(tmp_path):
    project = create_project("P", "C", tmp_path)
    create_snapshot(project, {"sales": pd.DataFrame({"item": ["A"]})}, label="old")
    update_manifest_label(project, "manifest_001", "new label")
    manifest = get_manifest(project, "manifest_001")
    assert manifest["label"] == "new label"


def test_manifest_title_and_tables_helpers():
    manifest = {
        "manifest_id": "manifest_001",
        "created_at": "2026-01-01 10:30",
        "tables": {"sales": "sales_a1b2.csv"},
    }
    assert manifest_title(manifest) == "manifest_001 | 2026-01-01 10:30"
    assert "sales -> sales_a1b2.csv" in manifest_tables_text(manifest)


def test_merged_settings_payload_preserves_existing_keys():
    project = {
        "project_path": "x:/p",
        "settings": {"current_manifest": "manifest_002", "history_enabled": True},
    }
    payload = merged_settings_payload(project, history_enabled=False)
    assert payload["history_enabled"] is False
    assert payload["current_manifest"] == "manifest_002"
    assert payload["project_path"] == "x:/p"


def test_merged_project_payload_updates_identity_fields_only():
    project = {
        "created_at": "2026-01-01",
        "transaction_tables": ["sales"],
        "dim_tables": ["item_dim"],
    }
    payload = merged_project_payload(project, project_name="New", company="NewCo")
    assert payload["project_name"] == "New"
    assert payload["company"] == "NewCo"
    assert payload["transaction_tables"] == ["sales"]
    assert payload["dim_tables"] == ["item_dim"]

