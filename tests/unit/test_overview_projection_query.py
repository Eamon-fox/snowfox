"""Shared projection queries and local draft overlay, without a Qt window."""

from app_gui.ui.overview_query_state import OverviewQueryState
from app_gui.ui.overview_table_query import query_current_rows
from app_gui.ui.table_entry_row_resolver import resolve_entry_rows
from lib.overview_table_query import (
    build_overview_table_projection,
    query_overview_table,
    query_table_projection,
)


META = {"custom_fields": [{"key": "sample", "type": "str"}], "color_key": "sample"}
LAYOUT = {"rows": 2, "cols": 2, "box_numbers": [1], "box_count": 1}


def test_draft_is_searchable_before_paging_and_preserves_its_state():
    def resolve(rows, columns):
        return resolve_entry_rows(
            rows, draft_map={(1, 3): {"sample": "pending"}}, staged_map={},
            data_columns=columns, color_key="sample", normalize_fn=dict,
        )

    result = query_current_rows(
        records=[], meta=META, layout=LAYOUT, state=OverviewQueryState(),
        resolve_rows=resolve, keyword="pending", limit=1,
    )["result"]
    assert result["total_count"] == result["display_count"] == 1
    assert result["rows"][0]["position"] == 3
    assert result["rows"][0]["slot_state"] == "draft"
    assert result["rows"][0]["row_confirmed"] is False


def test_projection_and_public_query_share_sort_paging_without_leaking_metadata():
    records = [
        {"id": i, "box": 1, "position": i, "sample": name, "stored_at": "2026-01-01"}
        for i, name in enumerate(("beta", "alpha", "gamma"), 1)
    ]
    options = dict(meta=META, sort_by="sample", limit=1, offset=1)
    raw = query_table_projection(build_overview_table_projection(records, meta=META), **options)
    public = query_overview_table(records, **options)
    assert raw["total_count"] == public["total_count"] == 3
    assert raw["rows"][0]["values"] == public["rows"][0]["values"]
    assert public["rows"][0]["values"]["sample"] == "beta"
    assert public["has_more"] is True
    assert "search_text" in raw["rows"][0]
    assert "search_text" not in public["rows"][0]
    assert "record" not in public["rows"][0]


def test_changing_list_filter_uses_current_values():
    records = [
        {"id": i, "box": 1, "position": i, "sample": name}
        for i, name in enumerate(("alpha", "beta"), 1)
    ]
    state = OverviewQueryState(column_filters={"sample": {"type": "list", "values": ["alpha"]}})

    def query():
        return query_current_rows(
            records=records, meta=META, layout=LAYOUT, state=state,
            resolve_rows=lambda rows, columns: rows,
        )["result"]["rows"]

    assert [row["position"] for row in query()] == [1]
    state.column_filters["sample"]["values"] = ["beta"]
    assert [row["position"] for row in query()] == [2]
