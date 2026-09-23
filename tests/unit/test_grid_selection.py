"""Selection transitions and geometry without constructing Qt widgets."""

from app_gui.ui.grid_selection import GridSelection


def test_multiselect_keeps_one_box_and_rehomes_removed_active_and_anchor():
    selection = GridSelection()
    empty = {(1, 1), (1, 2), (1, 3), (2, 1)}
    selection.replace_empty(
        [(1, 1), (2, 1), (1, 2), (1, 3), (1, 4)], is_empty=empty.__contains__,
        anchor_key=(1, 1), active_key=(1, 2),
    )
    assert selection.empty_keys == {(1, 1), (1, 2), (1, 3)}
    assert selection.anchor == (1, 1)
    assert selection.active == (1, 2)

    changed = selection.replace_empty([(1, 3)], is_empty=empty.__contains__)
    assert changed == {(1, 1), (1, 2), (1, 3)}
    assert selection.anchor == selection.active == (1, 3)


def test_prune_reconciles_occupied_slots_but_retains_active_when_all_are_removed():
    selection = GridSelection()
    empty = {(1, 1), (1, 2)}
    selection.replace_empty(sorted(empty), is_empty=empty.__contains__, anchor_key=(1, 1))
    empty.remove((1, 1))
    assert selection.prune(empty.__contains__) == {(1, 1), (1, 2)}
    assert selection.anchor == selection.active == (1, 2)
    empty.clear()
    assert selection.prune(empty.__contains__) == {(1, 2)}
    assert not selection.empty_keys
    assert selection.anchor is None
    assert selection.is_selected((1, 2), occupied=True)
    assert selection.reset() == {(1, 2)}
    assert selection.active is None


def test_neighbor_edges_merge_without_joining_across_row_boundaries():
    selection = GridSelection()
    selection.replace_empty([(1, 2), (1, 3), (1, 4)], is_empty=lambda key: True)
    edges = lambda key: selection.edge_mask(key, rows=2, cols=2, occupied=False)
    assert edges((1, 2)) == ("top", "right", "left")
    assert edges((1, 3)) == ("top", "bottom", "left")
    assert edges((1, 4)) == ("right", "bottom")
    assert edges((1, 1)) == ()


def test_keyboard_skips_hidden_slots_and_stops_at_box_boundary():
    selection = GridSelection()
    visible = {(1, 1), (1, 3), (1, 4), (2, 1)}

    def target(direction):
        return selection.navigation_target(
            direction, rows=2, cols=3, is_visible=visible.__contains__,
            first_visible=lambda: min(visible),
        )

    assert target("right") == (1, 1)
    selection.set_active((1, 1))
    assert target("right") == (1, 3)
    assert target("down") == (1, 4)
    selection.set_active((1, 3))
    assert target("right") == (1, 3)
    assert target("down") == (1, 3)
    visible.remove((1, 3))
    assert target("left") == (1, 1)
