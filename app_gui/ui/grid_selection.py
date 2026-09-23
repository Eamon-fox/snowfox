"""Grid selection transitions and geometry, independent of Qt and rendering."""

from collections.abc import Callable, Iterable

Slot = tuple[int, int]
SlotPredicate = Callable[[Slot], bool]
EDGES = ("top", "right", "bottom", "left")


def normalize_cell_key(value) -> Slot | None:
    if not isinstance(value, (tuple, list)) or len(value) != 2:
        return None
    try:
        box, position = map(int, value)
    except (TypeError, ValueError, OverflowError):
        return None
    return (box, position) if box > 0 and position > 0 else None


class GridSelection:
    """Own the active slot, empty-slot selection and Shift anchor.

    Mutation methods return potentially changed slots for incremental repaint.
    Availability predicates are supplied by the view, which owns visibility.
    """

    def __init__(self):
        self._active: Slot | None = None
        self._anchor: Slot | None = None
        self._empty_keys: frozenset[Slot] = frozenset()

    @property
    def active(self):
        return self._active

    @property
    def anchor(self):
        return self._anchor

    @property
    def empty_keys(self):
        return self._empty_keys

    def set_active(self, key: Slot | None) -> set[Slot]:
        previous = self._active
        self._active = key
        return {k for k in (previous, key) if k is not None} if previous != key else set()

    def replace_empty(self, keys: Iterable, *, is_empty: SlotPredicate,
                      anchor_key=None, active_key=None) -> set[Slot]:
        previous = set(self._empty_keys) | ({self._active} if self._active else set())
        selected = set()
        box_scope = None
        for value in keys:
            key = normalize_cell_key(value)
            if key is None:
                continue
            if box_scope is None:
                box_scope = key[0]
            if key[0] == box_scope and is_empty(key):
                selected.add(key)

        active = normalize_cell_key(active_key)
        if active not in selected:
            active = self._active if self._active in selected else max(selected, default=None)
        anchor = normalize_cell_key(anchor_key)
        if anchor not in selected:
            anchor = self._anchor if self._anchor in selected else active
        self._empty_keys = frozenset(selected)
        self._active = active
        self._anchor = anchor
        return previous | selected | ({active} if active else set())

    def clear_empty(self, *, clear_anchor=True, clear_active=False) -> set[Slot]:
        changed = set(self._empty_keys)
        self._empty_keys = frozenset()
        if clear_anchor:
            self._anchor = None
        if clear_active:
            changed.update(self.set_active(None))
        return changed

    def reset(self) -> set[Slot]:
        return self.clear_empty(clear_active=True)

    def prune(self, is_empty: SlotPredicate) -> set[Slot]:
        valid = sorted(key for key in self._empty_keys if is_empty(key))
        if valid:
            return self.replace_empty(valid, is_empty=is_empty)
        changed = self.clear_empty() if self._empty_keys else set()
        if self._anchor is not None and not is_empty(self._anchor):
            self._anchor = None
        return changed

    def is_selected(self, key: Slot, *, occupied: bool) -> bool:
        return key in self._empty_keys or (
            key == self._active and (occupied or not self._empty_keys)
        )

    def edge_mask(self, key: Slot, *, rows: int, cols: int, occupied: bool):
        if key not in self._empty_keys:
            return EDGES if self.is_selected(key, occupied=occupied) else ()
        row, col = divmod(key[1] - 1, cols)
        edges = []
        for edge, (dr, dc) in zip(EDGES, ((-1, 0), (0, 1), (1, 0), (0, -1))):
            nr, nc = row + dr, col + dc
            if not (0 <= nr < rows and 0 <= nc < cols) or (key[0], nr * cols + nc + 1) not in self._empty_keys:
                edges.append(edge)
        return tuple(edges)

    def navigation_target(self, direction: str, *, rows: int, cols: int,
                          is_visible: SlotPredicate, first_visible: Callable[[], Slot | None]):
        step = {"left": (0, -1), "right": (0, 1), "up": (-1, 0), "down": (1, 0)}.get(direction)
        if step is None:
            return None
        if self._active is None or not is_visible(self._active):
            return first_visible()
        box, position = self._active
        row, col = divmod(position - 1, cols)
        dr, dc = step
        row, col = row + dr, col + dc
        while 0 <= row < rows and 0 <= col < cols:
            key = (box, row * cols + col + 1)
            if is_visible(key):
                return key
            row, col = row + dr, col + dc
        return self._active
