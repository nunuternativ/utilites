import os
import sys

from Qt import QtWidgets
from Qt import QtGui
from Qt import QtCore

class BlinkButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super(BlinkButton, self).__init__(*args, **kwargs)
        self.default_color = self.getColor()

        self.clicked.connect(self.stop_blink)

    def getColor(self):
        return self.palette().color(QtGui.QPalette.Button)

    def setColor(self, value):
        if value == self.getColor():
            return
        palette = self.palette()
        palette.setColor(self.backgroundRole(), value)
        self.setAutoFillBackground(True)
        self.setPalette(palette)

    color = QtCore.Property(QtGui.QColor, getColor, setColor)

    def start_blink(self, color=QtGui.QColor(200, 200, 200), duration=1000, loopCount=100):
        self.animation = QtCore.QPropertyAnimation(self, "color")
        self.animation.setDuration(duration)
        self.animation.setLoopCount(loopCount)
        self.animation.setStartValue(self.default_color)
        self.animation.setEndValue(self.default_color)
        self.animation.setKeyValueAt(0.1, color)
        self.animation.start()

    def stop_blink(self):
        if self.animation:
            self.animation.stop()
        self.setColor(self.default_color) 

class TestWidget(QtWidgets.QWidget):

    def __init__(self):
        super(TestWidget, self).__init__()
        self.resize(300,200)
        layout = QtWidgets.QVBoxLayout(self)

        self.button_stop = BlinkButton("Stop")
        layout.addWidget(self.button_stop)


# w = TestWidget()
# w.show()

