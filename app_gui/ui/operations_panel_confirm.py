"""Confirmation and rollback-detail helpers for OperationsPanel."""

import os
from datetime import datetime

from PySide6.QtWidgets import QMessageBox

from app_gui.i18n import tr
from app_gui.ui.dialogs.common import ask_yes_no



def _confirm_warning_dialog(self, *, title, text, informative_text, detailed_text=None):
    return ask_yes_no(
        self,
        title=title,
        text=text,
        informative_text=informative_text,
        detailed_text=detailed_text,
        icon=QMessageBox.Warning,
        default_button=QMessageBox.No,
    )


def _confirm_execute(self, title, details):
    return _confirm_warning_dialog(
        self,
        title=title,
        text=tr("operations.confirmModify"),
        informative_text=details,
    )


def _format_size_bytes(size_bytes):
    try:
        value = float(size_bytes)
    except (TypeError, ValueError):
        return "-"
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024.0 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    if idx == 0:
        return f"{int(value)} {units[idx]}"
    return f"{value:.1f} {units[idx]}"


def _build_rollback_confirmation_lines(
    self,
    *,
    backup_path,
    yaml_path,
    source_event=None,
    include_action_prefix=True,
):
    yaml_abs = os.path.abspath(str(yaml_path or ""))
    raw_backup = str(backup_path or "").strip()
    backup_abs = os.path.abspath(raw_backup) if raw_backup else ""
    backup_label = os.path.basename(backup_abs) if backup_abs else tr("operations.planRollbackLatest")

    lines = []
    restore_line = tr("operations.planRollbackRestore", backup=backup_label)
    if include_action_prefix:
        restore_line = f"{tr('operations.rollback')}: {restore_line}"
    lines.append(restore_line)
    lines.append(tr("operations.planRollbackYamlPath", path=yaml_abs or "-"))

    if backup_abs:
        lines.append(tr("operations.planRollbackBackupPath", path=backup_abs))
        try:
            stat = os.stat(backup_abs)
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size = _format_size_bytes(stat.st_size)
            lines.append(tr("operations.planRollbackBackupMeta", mtime=mtime, size=size))
        except Exception:
            lines.append(tr("operations.planRollbackBackupMissing", path=backup_abs))

    if isinstance(source_event, dict) and source_event:
        timestamp = str(source_event.get("timestamp") or "-")
        action = str(source_event.get("action") or "-")
        trace_id = str(source_event.get("trace_id") or "-")
        lines.append(
            tr(
                "operations.planRollbackSourceEvent",
                timestamp=timestamp,
                action=action,
                trace_id=trace_id,
            )
        )
    return lines
