"""Table-view and inline-entry helpers for OverviewPanel."""

from contextlib import suppress

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import QHeaderView, QTableWidgetItem

from app_gui.error_localizer import localize_error_payload
from app_gui.ui.overview_table_roles import (
    TABLE_ROW_TINT_ROLE,
    TABLE_ROW_KIND_ROLE,
    TABLE_ROW_BOX_ROLE,
    TABLE_ROW_POSITION_ROLE,
    TABLE_COLUMN_NAME_ROLE,
    TABLE_EDITOR_KIND_ROLE,
    TABLE_EDITOR_OPTIONS_ROLE,
    TABLE_EDITOR_REQUIRED_ROLE,
    TABLE_ROW_LOCKED_ROLE,
    TABLE_ROW_CONFIRMED_ROLE,
)
from app_gui.i18n import t, tr
from app_gui.ui.overview_query_state import HISTORY_EVENT_COLUMNS
from app_gui.ui.theme import pick_contrasting_text_color
from app_gui.ui.utils import cell_color
from lib.custom_fields import coerce_value, get_color_key, get_effective_fields
from lib.plan_item_factory import build_add_plan_item
from lib.position_fmt import format_box_position_display
from lib.schema_aliases import get_input_stored_at
from lib.validators import parse_date


_TABLE_CONFIRM_COLUMN = "__confirm__"
_TABLE_CONFIRM_MARK = "√"
_TABLE_DRAFT_MARK = "+"
_TABLE_RECORD_ROLE = Qt.UserRole + 100
_TABLE_ROW_DATA_ROLE = Qt.UserRole + 101


def _confirm_cell_display(slot_state, resolved_row):
    """Return (display_value, raw_value) for the confirm column."""
    if slot_state in ("staged", "staged_locked"):
        return _TABLE_CONFIRM_MARK, True
    if slot_state == "draft":
        return _TABLE_DRAFT_MARK, False
    # "empty" or unknown
    return "", False


_OVERVIEW_TABLE_COLUMN_LABEL_KEYS = {
    "frozen_at": "operations.colFrozenAt",
    "stored_at": "operations.colFrozenAt",
    "thaw_events": "operations.colStorageEvents",
    "storage_events": "operations.colStorageEvents",
}


def _safe_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _table_field_definitions(self):
    field_defs = {}
    meta = getattr(self, "_current_meta", {}) or {}
    inventory = getattr(self, "_current_records", []) or []
    for field_def in get_effective_fields(meta, inventory=inventory):
        if not isinstance(field_def, dict):
            continue
        key = str(field_def.get("key") or "").strip()
        if key:
            field_defs[key] = dict(field_def)
    return field_defs


def _table_column_editor_config(self, column_name):
    field_defs = _table_field_definitions(self)
    if str(column_name or "") in {"stored_at", "frozen_at"}:
        return {"kind": "date", "options": [], "required": True}

    field_def = field_defs.get(str(column_name or ""))
    if not isinstance(field_def, dict):
        return {"kind": "", "options": [], "required": False}

    options = [str(option) for option in list(field_def.get("options") or []) if str(option or "").strip()]
    field_type = str(field_def.get("type") or "str").strip().lower()
    if options:
        kind = "choice"
    elif field_type == "date":
        kind = "date"
    else:
        kind = "text"
    return {
        "kind": kind,
        "options": options,
        "required": bool(field_def.get("required")),
    }


def _table_row_slot_key(row_data):
    box = _safe_int(row_data.get("box"))
    position = _safe_int(row_data.get("position"))
    if box is None or position is None:
        return None
    return (box, position)


def _display_table_columns(self, data_columns):
    columns = _visible_table_data_columns(self, data_columns)
    if not bool(getattr(self, "_table_include_inactive", False)):
        columns.append(_TABLE_CONFIRM_COLUMN)
    return columns


def _visible_table_data_columns(self, data_columns):
    columns = [str(column or "") for column in list(data_columns or [])]
    if bool(getattr(self, "_table_include_inactive", False)):
        return columns
    return [column for column in columns if column not in HISTORY_EVENT_COLUMNS]


def display_table_column_label(column_name):
    if str(column_name or "") == _TABLE_CONFIRM_COLUMN:
        return _TABLE_CONFIRM_MARK
    key = _OVERVIEW_TABLE_COLUMN_LABEL_KEYS.get(str(column_name or "").strip())
    if not key:
        return str(column_name or "")
    return tr(key, default=str(column_name or ""))


def _resolve_table_header_labels(self, columns):
    field_labels = {}
    for field_def in _table_field_definitions(self).values():
        key = str(field_def.get("key") or "").strip()
        if key:
            field_labels[key] = str(field_def.get("label") or key)

    return {
        str(column or ""): field_labels.get(str(column or ""), display_table_column_label(column))
        for column in list(columns or [])
    }


def _set_table_columns(self, headers, *, header_labels=None):
    raw_columns = [str(header or "") for header in list(headers or [])]
    resolved_labels = dict(header_labels or _resolve_table_header_labels(self, raw_columns))

    self.ov_table.setRowCount(0)
    self.ov_table.setColumnCount(len(raw_columns))
    self._table_row_signatures = []
    self._table_render_shape_key = None
    self._table_header_labels = dict(resolved_labels)
    for idx, col_name in enumerate(raw_columns):
        header_item = QTableWidgetItem(str(resolved_labels.get(col_name, col_name)))
        header_item.setData(Qt.UserRole, col_name)
        self.ov_table.setHorizontalHeaderItem(idx, header_item)
    header = self.ov_table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.Interactive)
    header.setSectionsMovable(False)
    header.setSectionsClickable(True)
    self.ov_table.setSortingEnabled(False)

    default_widths = {
        "id": 60,
        "location": 220,
        "frozen_at": 100,
        "stored_at": 100,
        "thaw_events": 200,
        "storage_events": 200,
        "cell_line": 100,
        "note": 180,
        "short_name": 150,
        _TABLE_CONFIRM_COLUMN: 34,
    }
    for idx, col_name in enumerate(raw_columns):
        if col_name in default_widths:
            self.ov_table.setColumnWidth(idx, default_widths[col_name])
        else:
            self.ov_table.setColumnWidth(idx, 120)


def _format_location_value(self, row_data, fallback_value):
    box = _safe_int(row_data.get("box"))
    position = _safe_int(row_data.get("position"))
    if box is None or position is None:
        return str(fallback_value or "")

    return format_box_position_display(
        box,
        position,
        layout=getattr(self, "_current_layout", {}) or {},
        box_label=tr("operations.box", default="Box"),
        position_label=tr("operations.position", default="Position"),
    )


def _sync_table_sort_indicator(self):
    header = getattr(self, "ov_table_header", None)
    columns = list(getattr(self, "_table_columns", []) or [])
    if header is None or not columns:
        return

    sort_by = self._query_state.reconcile_sort(columns)

    sort_order = str(self._query_state.sort_order or "asc").lower()
    qt_order = Qt.DescendingOrder if sort_order == "desc" else Qt.AscendingOrder
    section_index = columns.index(sort_by)

    self._ignore_table_sort_change = True
    try:
        header.setSortIndicatorShown(True)
        header.setSortIndicator(section_index, qt_order)
    finally:
        self._ignore_table_sort_change = False


def _on_table_sort_changed(self, logical_index, order):
    if bool(getattr(self, "_ignore_table_sort_change", False)):
        return
    columns = list(getattr(self, "_table_columns", []) or [])
    if logical_index < 0 or logical_index >= len(columns):
        return

    column_name = str(columns[logical_index] or "location")
    if column_name == _TABLE_CONFIRM_COLUMN:
        self._sync_table_sort_indicator()
        return
    self._query_state.sort_by = column_name
    self._query_state.sort_order = "desc" if order == Qt.DescendingOrder else "asc"
    self._apply_filters()


def _table_cell_is_editable(self, row_data, column_name):
    if bool(getattr(self, "_table_include_inactive", False)):
        return False
    if str(row_data.get("row_kind") or "") != "empty_slot":
        return False
    if bool(row_data.get("row_locked")):
        return False
    return str(column_name or "") in self._draft_store.entry_columns()


def _row_text_brush(color_value):
    tint_hex = cell_color(color_value or None)
    return tint_hex, QBrush(QColor(pick_contrasting_text_color(tint_hex)))


def _row_identity_key(row_data):
    slot_key = _table_row_slot_key(row_data)
    if slot_key is not None:
        return ("slot", slot_key[0], slot_key[1])

    record_id = _safe_int(row_data.get("record_id"))
    if record_id is not None:
        return ("record", record_id)
    return ("kind", str(row_data.get("row_kind") or ""))


def _table_first_row_item(self, row):
    if row < 0 or row >= self.ov_table.rowCount():
        return None
    for column in range(self.ov_table.columnCount()):
        item = self.ov_table.item(row, column)
        if item is not None:
            return item
    return None


def _table_row_data_from_item(item):
    if item is None:
        return {}
    row_data = item.data(_TABLE_ROW_DATA_ROLE)
    if isinstance(row_data, dict):
        return dict(row_data)

    record = item.data(_TABLE_RECORD_ROLE)
    return {
        "row_kind": item.data(TABLE_ROW_KIND_ROLE),
        "box": item.data(TABLE_ROW_BOX_ROLE),
        "position": item.data(TABLE_ROW_POSITION_ROLE),
        "record": record if isinstance(record, dict) else None,
        "row_locked": bool(item.data(TABLE_ROW_LOCKED_ROLE)),
        "row_confirmed": bool(item.data(TABLE_ROW_CONFIRMED_ROLE)),
    }


def _table_row_data(self, row):
    return _table_row_data_from_item(_table_first_row_item(self, row))


def _set_cached_row_data(self, row_data):
    target_key = _row_identity_key(row_data)
    rows = list(getattr(self, "_table_rows", []) or [])
    for idx, cached_row in enumerate(rows):
        if _row_identity_key(cached_row) != target_key:
            continue
        rows[idx] = dict(row_data)
        self._table_rows = rows
        return


def _table_column_index(self, column_name):
    try:
        return list(getattr(self, "_table_columns", []) or []).index(str(column_name or ""))
    except ValueError:
        return -1


def _table_row_item(self, row, column_name):
    column_index = _table_column_index(self, column_name)
    if column_index < 0:
        return None
    return self.ov_table.item(row, column_index)


def _snapshot_table_entry_values(self, row, *, row_data=None):
    base_row = dict(row_data or _table_row_data(self, row) or {})
    snapshot = self._draft_store.normalize_entry_values((base_row.get("values") or {}))
    for column_name in snapshot:
        item = _table_row_item(self, row, column_name)
        if item is None:
            continue
        snapshot[column_name] = str(item.text() or "").strip()
        if column_name in {"stored_at", "frozen_at"}:
            snapshot["stored_at"] = snapshot["frozen_at"] = snapshot[column_name]
    return snapshot


def _row_with_entry_values(self, row_data, entry_values):
    row = dict(row_data)
    row["values"] = {**row.get("values", {}), **self._draft_store.normalize_entry_values(entry_values)}
    return self._draft_store.resolve_rows([row], self._table_data_columns)[0]


def _render_table_row(self, row_index, row_data):
    resolved_row = dict(row_data or {})
    values = dict(resolved_row.get("values") or {})
    row_tint, row_text_brush = _row_text_brush(resolved_row.get("color_value"))
    record = resolved_row.get("record")
    if not isinstance(record, dict):
        record_id = _safe_int(resolved_row.get("record_id"))
        if record_id is not None:
            record = self.overview_records_by_id.get(record_id)
            resolved_row["record"] = record
    self._table_row_records[row_index] = record

    slot_state = str(resolved_row.get("slot_state") or "empty")
    for col_index, column in enumerate(list(getattr(self, "_table_columns", []) or [])):
        if column == _TABLE_CONFIRM_COLUMN:
            display_value, raw_value = _confirm_cell_display(slot_state, resolved_row)
            raw_value = bool(raw_value)
        else:
            raw_value = values.get(column, "")
            display_value = _format_location_value(self, resolved_row, raw_value) if column == "location" else raw_value

        item = QTableWidgetItem(str(display_value))
        item.setData(TABLE_ROW_TINT_ROLE, row_tint)
        item.setData(TABLE_ROW_KIND_ROLE, str(resolved_row.get("row_kind") or ""))
        item.setData(TABLE_ROW_BOX_ROLE, _safe_int(resolved_row.get("box")))
        item.setData(TABLE_ROW_POSITION_ROLE, _safe_int(resolved_row.get("position")))
        item.setData(TABLE_COLUMN_NAME_ROLE, column)
        item.setData(TABLE_ROW_LOCKED_ROLE, bool(resolved_row.get("row_locked")))
        item.setData(TABLE_ROW_CONFIRMED_ROLE, bool(resolved_row.get("row_confirmed")))
        item.setData(_TABLE_RECORD_ROLE, record if isinstance(record, dict) else None)
        item.setData(_TABLE_ROW_DATA_ROLE, dict(resolved_row))
        item.setForeground(row_text_brush)

        editable = _table_cell_is_editable(self, resolved_row, column)
        editor_config = _table_column_editor_config(self, column) if editable else {"kind": "", "options": [], "required": False}
        item.setData(TABLE_EDITOR_KIND_ROLE, editor_config.get("kind", ""))
        item.setData(TABLE_EDITOR_OPTIONS_ROLE, list(editor_config.get("options") or []))
        item.setData(TABLE_EDITOR_REQUIRED_ROLE, bool(editor_config.get("required")))

        flags = item.flags() | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        if editable:
            flags |= Qt.ItemIsEditable
        else:
            flags &= ~Qt.ItemIsEditable
        item.setFlags(flags)

        if column == _TABLE_CONFIRM_COLUMN:
            item.setTextAlignment(Qt.AlignCenter)
            if slot_state in ("staged", "staged_locked"):
                item.setForeground(QBrush(QColor("#2e7d32")))  # green for confirmed
            elif slot_state == "draft":
                item.setForeground(QBrush(QColor("#9e9e9e")))  # gray for pending draft
        elif column == "id":
            with suppress(ValueError, TypeError):
                item.setData(Qt.UserRole, int(raw_value))
        elif column == "location":
            box = _safe_int(resolved_row.get("box"))
            position = _safe_int(resolved_row.get("position"))
            if box is not None and position is not None:
                item.setData(Qt.UserRole, box * 1000 + position)

        self.ov_table.setItem(row_index, col_index, item)


def _row_render_signature(row_data, columns):
    values = row_data.get("values") or {}
    record = row_data.get("record")
    record_id = record.get("id") if isinstance(record, dict) else row_data.get("record_id")
    return (
        str(row_data.get("row_kind") or ""),
        _safe_int(row_data.get("box")),
        _safe_int(row_data.get("position")),
        _safe_int(record_id),
        str(row_data.get("color_value") or ""),
        bool(row_data.get("row_confirmed")),
        bool(row_data.get("row_locked")),
        tuple(("" if values.get(col) is None else str(values.get(col))) for col in columns),
    )


def _render_table_rows(self, rows):
    rows_list = list(rows or [])
    columns = list(getattr(self, "_table_columns", []) or [])
    column_type_map = self._table_column_types
    shape_key = (tuple(columns), tuple(sorted(column_type_map.items())))
    prev_shape_key = getattr(self, "_table_render_shape_key", None)
    prev_signatures = list(getattr(self, "_table_row_signatures", []) or [])
    new_signatures = [_row_render_signature(row, columns) for row in rows_list]

    need_full_rebuild = (
        prev_shape_key != shape_key
        or self.ov_table.rowCount() != len(rows_list)
        or len(prev_signatures) != len(rows_list)
    )

    self.ov_table.setSortingEnabled(False)
    updates_enabled = bool(self.ov_table.updatesEnabled())
    self.ov_table.setUpdatesEnabled(False)
    self._ignore_table_item_change = True

    try:
        if need_full_rebuild:
            self.ov_table.setRowCount(len(rows_list))
            self._table_row_records = [None] * len(rows_list)
            for row_index, row_data in enumerate(rows_list):
                _render_table_row(self, row_index, row_data)
        else:
            if len(self._table_row_records) < len(rows_list):
                self._table_row_records.extend(
                    [None] * (len(rows_list) - len(self._table_row_records))
                )
            for row_index, (sig, row_data) in enumerate(zip(new_signatures, rows_list)):
                if prev_signatures[row_index] == sig:
                    continue
                _render_table_row(self, row_index, row_data)
    finally:
        self._ignore_table_item_change = False
        self.ov_table.setUpdatesEnabled(updates_enabled)

    self._table_row_signatures = new_signatures
    self._table_render_shape_key = shape_key


def _refresh_table_entry_row_visual(self, row, *, row_data=None):
    if row < 0 or row >= self.ov_table.rowCount():
        return
    current_row = dict(row_data or _table_row_data(self, row) or {})
    current_item = self.ov_table.currentItem()
    selected_row = current_item.row() if current_item is not None else row
    current_column = current_item.column() if current_item is not None else 0

    self.ov_table.setSortingEnabled(False)
    self._ignore_table_item_change = True
    try:
        _render_table_row(self, row, current_row)
    finally:
        self._ignore_table_item_change = False

    signatures = list(getattr(self, "_table_row_signatures", []) or [])
    if 0 <= row < len(signatures):
        columns = list(getattr(self, "_table_columns", []) or [])
        signatures[row] = _row_render_signature(current_row, columns)
        self._table_row_signatures = signatures

    if 0 <= selected_row < self.ov_table.rowCount():
        target = self.ov_table.item(selected_row, current_column) or _table_first_row_item(self, selected_row)
        if target is not None:
            self.ov_table.setCurrentItem(target)


def _canonical_choice_value(value, options):
    text = str(value or "").strip()
    if not text:
        return ""
    for option in list(options or []):
        if option == text:
            return option
    lowered = text.casefold()
    for option in list(options or []):
        if str(option).casefold() == lowered:
            return option
    return None


def _normalize_table_entry_payload(self, row_data, *, snapshot):
    normalized = self._draft_store.normalize_entry_values(snapshot)
    stored_at = str(get_input_stored_at(normalized, default="") or "").strip()
    if not stored_at:
        header_labels = dict(getattr(self, "_table_header_labels", {}) or {})
        field_label = header_labels.get("stored_at") or header_labels.get("frozen_at") or "stored_at"
        return None, tr(
            "errors.userFacing.missingRequiredField",
            default="Missing required field: {field}",
            field=field_label,
        )
    if parse_date(stored_at) is None:
        return None, localize_error_payload({"error_code": "invalid_date"})

    field_defs = _table_field_definitions(self)
    fields = {}
    for key, field_def in field_defs.items():
        raw_text = str(normalized.get(key, "") or "").strip()
        field_label = str(field_def.get("label") or key)
        required = bool(field_def.get("required"))
        options = [str(option) for option in list(field_def.get("options") or []) if str(option or "").strip()]

        if not raw_text:
            if required:
                return None, tr(
                    "errors.userFacing.missingRequiredField",
                    default="Missing required field: {field}",
                    field=field_label,
                )
            continue

        if options:
            canonical = _canonical_choice_value(raw_text, options)
            if canonical is None:
                return None, localize_error_payload({"error_code": "invalid_field_options"})
            raw_text = canonical

        try:
            coerced = coerce_value(raw_text, field_def.get("type", "str"))
        except Exception as exc:
            if str(field_def.get("type") or "").strip().lower() == "date":
                return None, localize_error_payload({"error_code": "invalid_date"})
            return None, str(exc)

        if coerced is not None:
            fields[key] = coerced

    box = _safe_int(row_data.get("box"))
    position = _safe_int(row_data.get("position"))
    if box is None or position is None:
        return None, localize_error_payload({"error_code": "invalid_position"})

    return {
        "box": box,
        "positions": [position],
        "stored_at": stored_at,
        "fields": fields,
    }, ""


def _current_table_filter_args(self):
    return {
        "keyword": self.ov_filter_keyword.text().strip().lower(),
        "selected_box": self.ov_filter_box.currentData(),
        "selected_cell": self.ov_filter_cell.currentData(),
    }


def _refresh_current_table_view(self):
    if getattr(self, "_overview_view_mode", "grid") != "table":
        return
    self._apply_filters_table(**_current_table_filter_args(self))


def _confirm_table_entry_row(self, row):
    row_data = _table_row_data(self, row)
    if str(row_data.get("row_kind") or "") != "empty_slot":
        return False
    if bool(getattr(self, "_table_include_inactive", False)):
        return False
    if bool(row_data.get("row_locked")) and bool(row_data.get("row_confirmed")):
        return False

    slot_key = _table_row_slot_key(row_data)
    if slot_key is None:
        return False

    snapshot = _snapshot_table_entry_values(self, row, row_data=row_data)
    payload, error_text = _normalize_table_entry_payload(self, row_data, snapshot=snapshot)
    if payload is None:
        if error_text:
            self.status_message.emit(error_text, 4000)
        return True

    item = build_add_plan_item(
        box=payload["box"],
        positions=payload["positions"],
        stored_at=payload["stored_at"],
        fields=payload["fields"],
        source="overview_table",
    )
    self.plan_items_requested.emit([item])

    if self._draft_store.is_staged(slot_key):
        self._draft_store.clear_draft(slot_key)
    else:
        self._draft_store.set_draft(slot_key, snapshot)

    _refresh_current_table_view(self)
    return True


def _unconfirm_table_entry_row(self, row):
    """Remove a staged single-slot add item when the user clicks the confirm column again."""
    row_data = _table_row_data(self, row)
    if str(row_data.get("row_kind") or "") != "empty_slot":
        return False
    if not row_data.get("row_confirmed"):
        return False

    slot_key = _table_row_slot_key(row_data)
    if slot_key is None:
        return False

    staged = self._draft_store.staged_slot_map().get(slot_key)
    if staged is None or not staged.get("editable"):
        return False  # only single-slot (editable) items can be unconfirmed from table

    box, position = slot_key
    self.plan_item_removal_requested.emit([{
        "action": "add",
        "box": box,
        "position": position,
    }])

    self._draft_store.clear_draft(slot_key)

    return True


def _prefill_table_record_row(self, row_data):
    normalized_row = dict(row_data or {})
    row_kind = str(normalized_row.get("row_kind") or "")
    slot_key = _table_row_slot_key(normalized_row)

    if row_kind == "empty_slot" and slot_key is not None:
        staged = self._draft_store.staged_slot_map().get(slot_key)
        if staged and len(tuple(staged.get("positions") or ())) > 1:
            self._interactions.emit_add_prefill(
                slot_key[0],
                slot_key[1],
                positions=tuple(staged.get("positions") or ()),
            )
            return True

        self._interactions.emit_add_prefill(slot_key[0], slot_key[1])
        return True

    record = normalized_row.get("record")
    if not isinstance(record, dict):
        record_id = _safe_int(normalized_row.get("record_id"))
        if record_id is not None:
            record = self.overview_records_by_id.get(record_id)
            normalized_row["record"] = record

    if not isinstance(record, dict):
        return False

    box_num = _safe_int(record.get("box", normalized_row.get("box")))
    position = _safe_int(record.get("position", normalized_row.get("position")))
    record_id = _safe_int(record.get("id", normalized_row.get("record_id")))
    if box_num is None or position is None or record_id is None:
        return False

    self._interactions.emit_takeout_prefill(box_num, position, record_id)
    return True


def on_table_cell_clicked(self, row, column):
    item = self.ov_table.item(row, column) or _table_first_row_item(self, row)
    if item is None:
        return

    row_data = _table_row_data_from_item(item)
    column_name = str(item.data(TABLE_COLUMN_NAME_ROLE) or "")
    if column_name == _TABLE_CONFIRM_COLUMN:
        # Staged + editable (single-slot) → toggle off (unconfirm)
        if (
            row_data.get("row_confirmed")
            and not row_data.get("row_locked")
            and str(row_data.get("row_kind") or "") == "empty_slot"
        ):
            if _unconfirm_table_entry_row(self, row):
                return
        # Otherwise try to confirm (draft → staged)
        if _confirm_table_entry_row(self, row):
            return

    _prefill_table_record_row(self, row_data)


def on_table_row_double_clicked(self, row, column):
    on_table_cell_clicked(self, row, column)


def _on_table_item_changed(self, item):
    if bool(getattr(self, "_ignore_table_item_change", False)):
        return
    if item is None:
        return

    column_name = str(item.data(TABLE_COLUMN_NAME_ROLE) or "")
    if column_name not in self._draft_store.entry_columns():
        return

    row_data = _table_row_data_from_item(item)
    if not _table_cell_is_editable(self, row_data, column_name):
        return

    row = int(item.row())
    slot_key = _table_row_slot_key(row_data)
    if slot_key is None:
        return

    snapshot = _snapshot_table_entry_values(self, row, row_data=row_data)
    self._draft_store.set_draft(slot_key, snapshot)

    next_row = _row_with_entry_values(self, row_data, snapshot)
    _set_cached_row_data(self, next_row)
    _refresh_table_entry_row_visual(self, row, row_data=next_row)


def _on_plan_store_changed(self):
    if getattr(self, "_overview_view_mode", "grid") != "table":
        return
    if bool(getattr(self, "_table_include_inactive", False)):
        return
    self._draft_store.reconcile_with_staged()
    _refresh_current_table_view(self)


def _on_table_context_menu(self, pos):
    """Show context menu for table rows with draft-discard option."""
    from PySide6.QtWidgets import QMenu

    item = self.ov_table.itemAt(pos)
    if item is None:
        return

    row_data = _table_row_data_from_item(item)
    if str(row_data.get("row_kind") or "") != "empty_slot":
        return

    slot_key = _table_row_slot_key(row_data)
    if slot_key is None or not self._draft_store.has_draft(slot_key):
        return

    menu = QMenu(self)
    discard_action = menu.addAction(t("overview.discardDraft", default="Discard changes"))
    chosen = menu.exec_(self.ov_table.viewport().mapToGlobal(pos))
    if chosen is discard_action:
        self._draft_store.clear_draft(slot_key)
        _refresh_current_table_view(self)
