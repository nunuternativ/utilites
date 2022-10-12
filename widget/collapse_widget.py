from Qt import QtCore, QtGui, QtWidgets


class CollapsibleBox(QtWidgets.QWidget):
    stateChanged = QtCore.Signal(bool)

    def __init__(self, title="", parent=None, collapse=True):
        super(CollapsibleBox, self).__init__(parent)
        self.collapse = collapse
        self.toggle_button = QtWidgets.QToolButton(text=title, checkable=True)
        self.toggle_button.setChecked(collapse)
        self.toggle_button.setStyleSheet("QToolButton { border: none; }")
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.toggled.connect(self.collapse_toggled)

        self.toggle_animation = QtCore.QParallelAnimationGroup(self)

        self.content_area = QtWidgets.QScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        self.content_area.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.content_area.setFrameShadow(QtWidgets.QFrame.Raised)

        self.main_layout = QtWidgets.QVBoxLayout()
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.addWidget(self.toggle_button)
        self.main_layout.addWidget(self.content_area)

        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self, b"minimumHeight"))
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self, b"maximumHeight"))
        self.toggle_animation.addAnimation(QtCore.QPropertyAnimation(self.content_area, b"maximumHeight"))

    @QtCore.Slot()
    def collapse_toggled(self):
        checked = self.toggle_button.isChecked()
        self.toggle_button.setArrowType(QtCore.Qt.DownArrow if not checked else QtCore.Qt.RightArrow)
        self.toggle_animation.setDirection(QtCore.QAbstractAnimation.Forward if not checked else QtCore.QAbstractAnimation.Backward)
        self.toggle_animation.start()

        self.stateChanged.emit(checked)

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def setContentLayout(self, layout):
        self.clearLayout(self.content_area.layout())
        self.content_area.setLayout(layout)
        self.setLayout(self.main_layout)
        
        collapsed_height = (self.sizeHint().height() - self.content_area.maximumHeight())
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount()):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(200)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(self.toggle_animation.animationCount() - 1)
        content_animation.setDuration(200)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)

        if self.collapse:
            self.setMinimumHeight(0)
            self.setMaximumHeight(collapsed_height)

# example usage
# from rf_utils.widget import collapse_widget as cw
# reload(cw)
# import random
# from Qt import QtCore, QtWidgets, QtGui
# dir(QtCore)

# w = QtWidgets.QMainWindow()
# w.setCentralWidget(QtWidgets.QWidget())
# dock = QtWidgets.QDockWidget("Collapsible Demo")
# w.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock)
# scroll = QtWidgets.QScrollArea()
# dock.setWidget(scroll)
# content = QtWidgets.QWidget()
# scroll.setWidget(content)
# scroll.setWidgetResizable(True)
# vlay = QtWidgets.QVBoxLayout(content)
# for i in range(10):
#     box = cw.CollapsibleBox("Collapsible Box Header-{}".format(i))
#     vlay.addWidget(box)
#     lay = QtWidgets.QVBoxLayout()
#     for j in range(8):
#         label = QtWidgets.QLabel("{}".format(j))
#         color = QtGui.QColor(*[random.randint(0, 255) for _ in range(3)])
#         label.setStyleSheet(
#             "background-color: {}; color : white;".format(color.name())
#         )
#         label.setAlignment(QtCore.Qt.AlignCenter)
#         lay.addWidget(label)

#     box.setContentLayout(lay)
# vlay.addStretch()
# w.resize(640, 480)
# w.show()
