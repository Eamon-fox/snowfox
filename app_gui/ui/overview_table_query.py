"""Current-inventory table queries, independent of Qt widgets and windows."""

from lib.overview_table_query import build_overview_table_projection, query_table_projection
from app_gui.ui.overview_query_state import HISTORY_EVENT_COLUMNS

TABLE_ROW_LIMIT = 500


def query_current_rows(*, records, meta, layout, state, resolve_rows,
                       keyword="", box=None, color_value=None, limit=TABLE_ROW_LIMIT):
    """Overlay local drafts before using the shared inventory query pipeline."""
    projection = build_overview_table_projection(
        records, meta=meta, layout=layout, include_empty_slots=True,
    )
    columns = [c for c in projection["columns"] if c not in HISTORY_EVENT_COLUMNS]
    projection["columns"] = columns
    projection["rows"] = resolve_rows(projection["rows"], columns)
    result = query_table_projection(
        projection, meta=meta, keyword=keyword, box=box, color_value=color_value,
        column_filters=state.active_column_filters(include_inactive=False),
        sort_by=state.reconcile_sort(columns), sort_order=state.sort_order, limit=limit,
    )
    return {"ok": True, "result": result}
