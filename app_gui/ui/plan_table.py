"""Pending-plan table that fits the panel instead of expanding to long values."""

from PySide6.QtWidgets import QHeaderView, QTableWidget


class PlanTable(QTableWidget):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_columns()

    def fit_columns(self):
        if self.columnCount() != 5:
            return
        width = self.viewport().width()
        scale = min(1.0, width / 560)
        action, target, date, status = (
            max(minimum, round(preferred * scale))
            for preferred, minimum in ((88, 52), (108, 64), (100, 98), (80, 52))
        )
        summary = max(48, width - action - target - date - status)
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setMinimumSectionSize(36)
        for column, size in enumerate((action, target, date, summary, status)):
            self.setColumnWidth(column, size)
