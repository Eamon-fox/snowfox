"""Check that selecting/focusing a tinted cell does not move its glyphs."""

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter, QPalette, QColor
from PySide6.QtWidgets import QStyle, QStyleOptionViewItem, QTableWidget, QTableWidgetItem

from app_gui.ui.overview_panel_widgets import _OverviewTableTintDelegate
from app_gui.ui.overview_table_roles import TABLE_ROW_TINT_ROLE


@pytest.mark.parametrize("selected", [False, True])
def test_focus_does_not_add_frame_or_change_cell_pixels(qapp, selected):
    table = QTableWidget(1, 1)
    table.setItem(0, 0, QTableWidgetItem("Stable text 123"))
    table.item(0, 0).setData(TABLE_ROW_TINT_ROLE, "#ddeeff")
    delegate = _OverviewTableTintDelegate(table)

    def render(focused):
        option = QStyleOptionViewItem()
        option.initFrom(table)
        option.rect = QRect(0, 0, 220, 36)
        option.widget = table
        option.palette.setColor(QPalette.Text, QColor("#142030"))
        option.state = QStyle.State_Enabled | QStyle.State_Active
        if selected:
            option.state |= QStyle.State_Selected
        if focused:
            option.state |= QStyle.State_HasFocus
        image = QImage(220, 36, QImage.Format_ARGB32)
        image.fill(QColor("white"))
        painter = QPainter(image)
        delegate.paint(painter, option, table.model().index(0, 0))
        painter.end()
        return image

    assert render(False) == render(True)
    table.deleteLater()


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_pending_scrollbar_is_wide_without_horizontal_overflow(qapp, theme):
    from app_gui.ui.plan_table import PlanTable
    from app_gui.ui.theme import apply_dark_theme, apply_light_theme

    old_stylesheet, old_palette, old_font = qapp.styleSheet(), qapp.palette(), qapp.font()
    table = None
    try:
        (apply_light_theme if theme == "light" else apply_dark_theme)(qapp)
        table = PlanTable(40, 5)
        table.verticalHeader().hide()
        table.resize(420, 300)
        table.show()
        qapp.processEvents()
        assert table.verticalScrollBar().isVisible()
        assert table.verticalScrollBar().width() == 10
        assert table.horizontalScrollBar().maximum() == 0
    finally:
        if table is not None:
            table.close()
            table.deleteLater()
        qapp.setStyleSheet(old_stylesheet)
        qapp.setPalette(old_palette)
        qapp.setFont(old_font)
