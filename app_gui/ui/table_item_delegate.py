"""Stable text geometry and a single selection treatment for tinted tables."""

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPalette, QTextLayout, QTextOption
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem, QStyledItemDelegate


class TintedTableDelegate(QStyledItemDelegate):
    def __init__(self, tint_role, parent=None, *, wrap=False):
        super().__init__(parent)
        self._tint_role = tint_role
        self._wrap = wrap

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        selected = bool(opt.state & QStyle.State_Selected)
        opt.state &= ~QStyle.State_HasFocus
        text = opt.text
        opt.text = ""
        opt.features &= ~QStyleOptionViewItem.HasDisplay
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        painter.save()
        painter.setClipRect(opt.rect)
        tint = QColor(str(index.data(self._tint_role) or ""))
        if tint.isValid() and not selected:
            tint.setAlpha(90 if opt.palette.color(QPalette.Window).lightnessF() > 0.5 else 128)
            painter.fillRect(opt.rect, tint)
        painter.setFont(opt.font)
        painter.setPen((option.palette if selected else opt.palette).color(QPalette.Text))
        text_rect = opt.rect.adjusted(8, 4, -8, -4)
        flags = int(opt.displayAlignment)
        if self._wrap:
            self._paint_wrapped_text(painter, text_rect, text, opt)
        else:
            flags |= int(Qt.TextSingleLine)
            text = opt.fontMetrics.elidedText(text, Qt.ElideRight, max(0, text_rect.width()))
            painter.drawText(text_rect, flags, text)
        painter.restore()

    @staticmethod
    def _paint_wrapped_text(painter, rect, text, option):
        metrics = option.fontMetrics
        line_height = metrics.lineSpacing()
        limit = max(1, rect.height() // line_height)
        layout = QTextLayout(text, option.font)
        text_option = QTextOption()
        text_option.setWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        layout.setTextOption(text_option)
        lines = []
        layout.beginLayout()
        while len(lines) < limit:
            line = layout.createLine()
            if not line.isValid():
                break
            line.setLineWidth(max(1, rect.width()))
            start, length = line.textStart(), line.textLength()
            if len(lines) == limit - 1:
                lines.append(metrics.elidedText(text[start:], Qt.ElideRight, max(0, rect.width())))
            else:
                lines.append(text[start:start + length].strip())
        layout.endLayout()
        y = rect.top() + max(0, (rect.height() - len(lines) * line_height) // 2)
        for line_text in lines:
            painter.drawText(QRect(rect.left(), y, rect.width(), line_height), Qt.AlignLeft | Qt.AlignVCenter, line_text)
            y += line_height
