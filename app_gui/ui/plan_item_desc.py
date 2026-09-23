"""GUI-facing helpers for compact plan-item descriptions."""

from __future__ import annotations

from app_gui.i18n import tr
from lib.plan_item_desc import build_plan_item_desc


_ACTION_I18N_KEY = {
    "takeout": "overview.takeout",
    "move": "operations.move",
    "add": "operations.add",
    "edit": "operations.edit",
    "rollback": "operations.rollback",
}


def localized_action(action: str) -> str:
    """Return localized display text for a canonical action name."""
    key = _ACTION_I18N_KEY.get(action.lower())
    return tr(key) if key else action.capitalize()


def _item_desc_msg(key, default, **kwargs):
    full_key = f"agentToolRunner.{key}"
    text = tr(full_key, default=default, **kwargs)
    if kwargs:
        try:
            return str(text).format(**kwargs)
        except Exception:
            return str(text)
    return str(text)


def build_localized_plan_item_desc(panel, item):
    action = str((item or {}).get("action") or "")
    action_norm = action.lower()
    action_label = localized_action(action or action_norm) if (action or action_norm) else "?"
    return build_plan_item_desc(
        item,
        layout=getattr(panel, "_current_layout", None),
        action_label=action_label,
        msg_func=_item_desc_msg,
    )
