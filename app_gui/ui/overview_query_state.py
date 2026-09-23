"""Query state shared by Overview's grid/table presenters."""

from dataclasses import dataclass, field

from lib.overview_table_query import get_unique_overview_table_values


HISTORY_EVENT_COLUMNS = frozenset({"thaw_events", "storage_events"})


@dataclass
class OverviewQueryState:
    sort_by: str = "location"
    sort_order: str = "asc"
    column_filters: dict = field(default_factory=dict)
    _unique_values: dict = field(default_factory=dict, init=False, repr=False)

    def reset_sort(self):
        self.sort_by = "location"
        self.sort_order = "asc"

    def reconcile_sort(self, columns):
        if self.sort_by not in columns:
            self.sort_by = "location" if "location" in columns else (columns[0] if columns else "location")
        return self.sort_by

    def invalidate_rows(self):
        self._unique_values.clear()

    def unique_values(self, column, rows):
        if column not in self._unique_values:
            self._unique_values[column] = get_unique_overview_table_values(rows, column)
        return list(self._unique_values[column])

    def active_column_filters(self, *, include_inactive):
        return {
            column: config for column, config in self.column_filters.items()
            if include_inactive or column not in HISTORY_EVENT_COLUMNS
        }
