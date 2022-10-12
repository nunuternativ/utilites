from Qt import QtWidgets
from Qt import QtGui
from Qt import QtCore

class TextEditWithPlaceHolder(QtWidgets.QPlainTextEdit):
    """QPlainTextEdit with placeholder text option.
    Reimplemented from the C++ code used in Qt5.
    """
    editorLostFocus = QtCore.Signal(bool)
    def __init__(self, *args, **kwargs):
        super(TextEditWithPlaceHolder, self).__init__(*args, **kwargs)

        self._placeholderText = ''
        self._placeholderVisible = False
        self.textChanged.connect(self.placeholderVisible)

    def focusOutEvent(self, event):
        self.editorLostFocus.emit(True)

    def placeholderVisible(self):
        """Return if the placeholder text is visible, and force update if required."""
        placeholderCurrentlyVisible = self._placeholderVisible
        self._placeholderVisible = self._placeholderText and self.document().isEmpty() and not self.hasFocus()
        if self._placeholderVisible != placeholderCurrentlyVisible:
            self.viewport().update()
        return self._placeholderVisible

    def placeholderText(self):
        """Return text used as a placeholder."""
        return self._placeholderText

    def setPlaceholderText(self, text):
        """Set text to use as a placeholder."""
        self._placeholderText = text
        if self.document().isEmpty():
            self.viewport().update()

    def paintEvent(self, event):
        """Override the paint event to add the placeholder text."""
        if self.placeholderVisible():
            painter = QtGui.QPainter(self.viewport())
            colour = self.palette().text().color()
            colour.setAlpha(128)
            painter.setPen(colour)
            painter.setClipRect(self.rect())
            margin = self.document().documentMargin()
            textRect = self.viewport().rect().adjusted(margin, margin, 0, 0)
            painter.drawText(textRect, QtCore.Qt.AlignTop | QtCore.Qt.TextWordWrap, self.placeholderText())
        super(TextEditWithPlaceHolder, self).paintEvent(event)