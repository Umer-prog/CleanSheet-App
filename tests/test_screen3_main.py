from ui.screen3_main import build_nav_items, mapping_nav_label


def test_mapping_nav_label_builds_expected_text():
    mapping = {
        "transaction_table": "posted_fact_table",
        "dim_table": "item_dim",
    }
    assert mapping_nav_label(mapping) == "posted_fact_table -> item_dim"


def test_build_nav_items_includes_mapping_then_static_views():
    mappings = [
        {
            "id": "map_001",
            "transaction_table": "sales",
            "transaction_column": "item",
            "dim_table": "item_dim",
            "dim_column": "name",
        }
    ]
    items = build_nav_items(mappings)
    assert items[0]["kind"] == "mapping"
    assert items[0]["key"] == "map_001"
    assert any(i.get("key") == "t_sources" for i in items)
    assert any(i.get("key") == "d_sources" for i in items)
    assert any(i.get("key") == "history" for i in items)
    assert any(i.get("key") == "settings" for i in items)

