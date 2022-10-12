from Qt import QtCore
from Qt import QtWidgets
from Qt import QtGui

from collections import OrderedDict
from functools import partial
import os

from rf_utils.sg import sg_process
from rf_utils import user_info
from rf_utils.widget import entity_browse_widget
from rf_utils.widget import completer
sg = sg_process.sg

class StyleConfig:
    font = 'font-family:Trebuchet MS;'
    fontSize = 'font-size : 9pt;'

    # colors
    black = (0, 0, 0)
    white = (255, 255, 255)
    darkerGray = (35, 35, 35)
    darkGray = (50, 50, 50)
    lightGray = (160, 160, 160)
    midGray = (75, 75, 75)
    brightGray = (235, 235, 235)
    tagBackground = (248, 252, 194)

    # backgrounds
    backgroundTagEdit = 'background-color: rgb{};'.format(brightGray)
    backgroundDark = 'background-color: rgb{};'.format(darkerGray)
    background = 'background-color: rgb{};'.format(darkGray)
    fieldBackground = 'background-color: rgb{};'.format(midGray)

    # tags
    no_border = 'border-width: 0px;'
    border = 'border-width: 2px;'
    tagPadding = 'padding: 2px 2px 2px 2px;'
    backgroundTagHilight = 'background-color: #d1bf84;'
    backgroundTagSelected = 'background-color: #b59957;'
    fontTagHilight = 'color: rgb{};'.format(white)
    fontTagSelected = 'color: rgb{};'.format(white)

class IconPath:
    remove_icon = '%s/core/rf_app/global_library/icons/dialog/remove.png' % os.environ.get('RFSCRIPT')

class TagDisplayWidget(QtWidgets.QListWidget):
    clicked = QtCore.Signal(bool)
    tagChanged = QtCore.Signal(bool)
    # canceled = QtCore.Signal(bool)
    def __init__(self, inLine=True, parent=None):
        super(TagDisplayWidget, self).__init__(parent)
        self.inLine = inLine
        self.setFlow(QtWidgets.QListView.LeftToRight)
        
        self.setSpacing(2)
        self.setViewMode(QtWidgets.QListView.ListMode)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setFrameShape(QtWidgets.QFrame.NoFrame)
        display_styleSheet = '''QListWidget{{ {bg} {fontSize} {font} }}
        QListWidget::item {{ {padding} }}
        QListWidget::item:selected {{ 
            {fontTagSelected} {backgroundTagSelected} {fontSize} {font} {tagBorder} {padding}
        }}
        QListWidget::item:hover {{ 
            {fontTagHilight} {backgroundTagHilight} {fontSize} {font} {tagBorder} {padding}
        }}'''.format(bg=StyleConfig.backgroundDark, 
                    backgroundTagSelected=StyleConfig.backgroundTagSelected, 
                    backgroundTagHilight=StyleConfig.backgroundTagHilight, 
                    fontTagHilight=StyleConfig.fontTagHilight,
                    fontTagSelected=StyleConfig.fontTagSelected,
                    fontSize=StyleConfig.fontSize,
                    tagBorder=StyleConfig.no_border, 
                    padding=StyleConfig.tagPadding,
                    font=StyleConfig.font)
        self.setStyleSheet(display_styleSheet)
        model = self.model()
        if self.inLine:
            self.setFixedWidth(0)
            self.hide()
            self.setWrapping(False)
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
            self.itemChanged.connect(lambda: self.update_width())
            model.rowsInserted.connect(lambda: self.update_width())
            model.rowsRemoved.connect(lambda: self.update_width())
        else:
            self.setWrapping(True)
            self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            self.itemChanged.connect(lambda: self.tag_changed())
            model.rowsInserted.connect(lambda: self.tag_changed())
            model.rowsRemoved.connect(lambda: self.tag_changed())

        self.init_signals()

    def init_signals(self):
        pass

    def clear(self):
        super(TagDisplayWidget, self).clear()
        if self.inLine:
            self.update_width()

    # def keyPressEvent(self, event):
    #     if (event.key() == QtCore.Qt.Key_Escape and
    #         event.modifiers() == QtCore.Qt.NoModifier):
    #         self.selectionModel().clear()
    #         self.canceled.emit(True)
    #     else:
    #         super(TagDisplayWidget, self).keyPressEvent(event)
    
    def resizeEvent(self, event):
        self.setGridSize(self.gridSize())
        super(TagDisplayWidget, self).resizeEvent(event)

    def update_width(self, *args, **kwargs):
        width = 0
        self.show()
        for i in range(self.count()):
            item = self.item(i)
            index = self.indexFromItem(item)
            width += self.rectForIndex(index).width() + 2
        width = width + ((self.count()-1)*self.spacing())
        if width < 0: 
            width = 0
            self.hide()
        self.setFixedWidth(width)
        self.tag_changed()

    def tag_changed(self):
        hasTag = False if not self.count() else True
        self.tagChanged.emit(hasTag)

    def mousePressEvent(self, event):
        if not self.indexAt(event.pos()).isValid():
            self.selectionModel().clear()
        super(TagDisplayWidget, self).mousePressEvent(event)
        self.clicked.emit(True)

class TagLineEdit(QtWidgets.QLineEdit):
    clicked = QtCore.Signal(bool)
    def __init__(self, parent=None):
        super(TagLineEdit, self).__init__(parent)
        self._placeholderText = ''
        self.setStyleSheet(StyleConfig.fieldBackground)

    def setPlaceholderText(self, text):
        self._placeholderText = text
        super(TagLineEdit, self).setPlaceholderText(text)

    def hidePlaceHolderText(self):
        super(TagLineEdit, self).setPlaceholderText('')

    def showPlaceHolderText(self):
        super(TagLineEdit, self).setPlaceholderText(self._placeholderText)

    def focusInEvent(self, event):
        super(TagLineEdit, self).focusInEvent(event)
        self.clicked.emit(True)

class TagWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal(bool)
    edited = QtCore.Signal(QtWidgets.QWidget)
    def __init__(self, inLine=True, parent=None) :
        super(TagWidget, self).__init__(parent)
        self.use_hash = True
        self.inLine = inLine
        self.allow_creation = True
        self.allow_duplicate = False
        self.allow_rename = True
        self.allow_delete = True

        self.allLayout = QtWidgets.QHBoxLayout() if self.inLine else QtWidgets.QVBoxLayout()
        self.tag_list = OrderedDict()
        self.completer = completer.CustomQCompleter()
        self.del_action = None

        self.setup_ui()
        self.init_signal()

    def set_data(self, data, displayKey):
        self.tag_list = OrderedDict([(i[displayKey], i) for i in data])
        self.completer.setModel(QtCore.QStringListModel(self.tag_list.keys()))
        self.completer.setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.completer.highlighted.connect(self.selecting_completion)
        self.completer.activated.connect(self.completion_finished)
        self.line_edit.setCompleter(self.completer)

    def clear(self):
        self.line_edit.clear()
        self.display.clear()

    def selecting_completion(self):
        try: self.line_edit.returnPressed.disconnect()
        except: pass

    def completion_finished(self):
        self.line_edit.returnPressed.connect(self.set_hashtag)

    def setup_ui(self):
        # label
        self.label = QtWidgets.QLabel('')

        # display listWidget
        self.display = TagDisplayWidget(inLine=self.inLine)
        self.display.setFocusPolicy(QtCore.Qt.ClickFocus)

        # lineEdit
        self.line_edit = TagLineEdit()
        model = QtGui.QStandardItemModel()
        self.line_edit.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        if self.inLine:
            self.allLayout.addWidget(self.label)
            self.allLayout.addWidget(self.display)
            self.allLayout.addWidget(self.line_edit)
            self.allLayout.setSpacing(3)
            self.line_layout = self.allLayout
        else:
            self.line_layout = QtWidgets.QHBoxLayout()
            self.line_layout.setContentsMargins(0, 0, 0, 0)
            self.line_layout.setSpacing(3)
            self.line_layout.addWidget(self.label)
            self.line_layout.addWidget(self.line_edit)

            self.allLayout.addLayout(self.line_layout)
            self.allLayout.addWidget(self.display)
            self.allLayout.setSpacing(3)

        self.allLayout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.allLayout)

    def init_signal(self):
        self.line_edit.returnPressed.connect(self.set_hashtag)
        self.line_edit.clicked.connect(self.activated)

        self.display.itemDoubleClicked.connect(self.add_rename)
        self.display.clicked.connect(self.activated)
        self.display.tagChanged.connect(self.toggle_placeholdertext)

        # action
        self.del_action = QtWidgets.QAction(self.display)
        self.del_action.setShortcutContext(QtCore.Qt.WidgetWithChildrenShortcut)
        self.del_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Delete))
        self.display.addAction(self.del_action)
        self.del_action.triggered.connect(self.remove_selected_item)

    def activated(self):
        self.clicked.emit(True)

    def toggle_placeholdertext(self, hasTag):
        if hasTag:
            self.line_edit.hidePlaceHolderText()
        else:
            self.line_edit.showPlaceHolderText()

    def set_all_hashtag(self,projectEntity,assetName):
        tagEntity = find_asset_tags(projectEntity,assetName)
        for tag in tagEntity['tags']:
            self.add_item(tag['name'])

    def set_hashtag(self):
        text = self.line_edit.text()
        if text:
            self.add_item(text)
            self.line_edit.clear()

    def add_item(self, text, data=None, check=True):
        items = [self.display.item(i) for i in range(self.display.count())]
        # check for duplicates
        if not data:
            data = self.tag_list.get(text, text)
        # overrides checking of duplication and creation when adding item programatically
        if check:
            if data in [item.data(QtCore.Qt.UserRole) for item in items] and not self.allow_duplicate:
                return
            # check if allow creation
            if not self.allow_creation and text not in self.tag_list.keys():
                return

        item = QtWidgets.QListWidgetItem(self.display)
        item.setForeground(QtGui.QColor(StyleConfig.black[0], StyleConfig.black[1], StyleConfig.black[2]))
        item.setBackground(QtGui.QColor(StyleConfig.tagBackground[0], StyleConfig.tagBackground[1], StyleConfig.tagBackground[2]))

        display_text = text
        if self.use_hash:
            display_text = '#' + text

        item.setText(display_text)
        item.setData(QtCore.Qt.UserRole, data)
        self.display.setCurrentItem(item)
        item.setSelected(False)
        self.edited.emit(self)

    def add_items(self, itemData, check=True):
        for text, data in itemData:
            self.add_item(text=text, data=data, check=check)

    def remove(self,item):
        self.display.removeItemWidget(item)
        self.display.takeItem(self.display.row(item))

    def remove_selected_item(self):
        if not self.allow_delete:
            return
        sels = self.display.selectedItems()
        if sels:
            for item in sels:
                self.remove(item=item)
            self.edited.emit(self)

    def add_rename(self,item):
        if not self.allow_rename:
            return
        # create lineEdit
        lineEdit = QtWidgets.QLineEdit()
        styleSheet = '''
        QLineEdit{{ {font} {fontSize} {editBg} color:rgb{black}; border:none;}}
        '''.format(font=StyleConfig.font, 
                fontSize=StyleConfig.fontSize, 
                editBg=StyleConfig.backgroundTagEdit, 
                black=StyleConfig.black)
        lineEdit.setStyleSheet(styleSheet)
        model = QtGui.QStandardItemModel()
        lineEdit.setFocusPolicy(QtCore.Qt.StrongFocus)
        lineEdit.setCompleter(self.completer)
        lineEdit.setFixedHeight(15)
        self.display.setItemWidget(item,lineEdit)

        # connect rename signals
        lineEdit.textChanged.connect(partial(self.rename_text_changed, lineEdit, item))
        lineEdit.returnPressed.connect(partial(self.rename, item, lineEdit))
        lineEdit.editingFinished.connect(partial(self.cancel_rename, item, lineEdit))
        self.display.itemDoubleClicked.disconnect(self.add_rename)

    def rename_text_changed(self, lineEdit, item, *args, **kwargs):
        text = lineEdit.text()
        completer = lineEdit.completer()
        i = 0
        fm = QtGui.QFontMetrics(lineEdit.font())
        max_width = fm.width(text) 
        completion_text = text
        while completer.setCurrentRow(i):
            curr_completion = completer.currentCompletion()
            pixelsWide = fm.width(curr_completion)
            if pixelsWide > max_width:
                max_width = pixelsWide
                completion_text = curr_completion
            i += 1
        
        lineEdit.setFixedWidth(max_width+13)
        lineEdit.adjustSize()
        item.setSizeHint(QtCore.QSize(max_width+17, lineEdit.sizeHint().height()))
        
    def rename(self,item,lineEdit):
        item_last = item.text()
        text = lineEdit.text()

        # check for duplicates
        items = [self.display.item(i) for i in range(self.display.count())]
        if text in [item.data(QtCore.Qt.UserRole) for item in items] and not self.allow_duplicate:
            self.cancel_rename(item, lineEdit)
            return
        # check if allow creation
        if not self.allow_creation and text not in self.tag_list.keys():
            self.cancel_rename(item, lineEdit)
            return

        if text:
            display_text = text
            if self.use_hash:
                display_text = '#' + text
            item.setText(display_text)
            item.setData(QtCore.Qt.UserRole, text)
        else:
            item.setText(item_last)
        
        self.adjust_item_to_text(lineEdit, item)
        self.display.removeItemWidget(item)  # remove line edit
        self.display.itemDoubleClicked.connect(self.add_rename)
        self.edited.emit(self)
        item.setSelected(False)

    def adjust_item_to_text(self, lineEdit, item):
        fm = QtGui.QFontMetrics(lineEdit.font())
        max_width = fm.width(item.text()) 
        item.setSizeHint(QtCore.QSize(max_width+10, lineEdit.sizeHint().height()))

    def cancel_rename(self, item, lineEdit):
        item.setText(item.text())
        self.adjust_item_to_text(lineEdit, item)
        self.display.removeItemWidget(item)  # remove line edit
        self.display.itemDoubleClicked.connect(self.add_rename)
        item.setSelected(False)

    def get_all_item(self):
        return [self.display.item(a).data(QtCore.Qt.UserRole) for a in range(self.display.count())]

    def get_all_item_data(self):
        return [(self.display.item(a).text().replace('#', ''), self.display.item(a).data(QtCore.Qt.UserRole)) for a in range(self.display.count())]

    def get_all_tags(self):
        textList = [self.display.item(a).data(QtCore.Qt.UserRole) for a in range(self.display.count())]
        tagEntity = [find_one_tag(text) for text in textList]
        return tagEntity

    def publish_hashtag(self,projectEntity,assetName):
        add_tags = []
        tagList  = self.get_all_item()
        for tag in tagList:
            findTag = find_one_tag(tag)
            if not findTag == None:
                add_tags.append(findTag)
            else:
                createTag = ''
                createTag = create_hashtag(tag)
                add_tags.append(createTag)

        update_hashtag(projectEntity,assetName,add_tags)

class SGTagWidget(TagWidget):
    def __init__(self, inLine=True, parent=None) :
        super(SGTagWidget, self).__init__(inLine, parent)
        sg_hashtag = find_tag()
        self.set_data(data=sg_hashtag, displayKey='name')

class SGUserWidget(TagWidget):
    def __init__(self, users=[], inLine=True, parent=None) :
        super(SGUserWidget, self).__init__(inLine, parent)
        if not users:
            users = user_info.SGUser().userEntities
        self.set_data(data=users, displayKey='name')

class SGEpTagWidget(TagWidget):
    def __init__(self, project, episodes=[], inLine=True, parent=None):
        super(SGEpTagWidget, self).__init__(inLine, parent)
        self.project = project
        if not episodes:
            episodes = sg_process.get_episodes(self.project['name'])
        self.set_data(data=episodes, displayKey='code')
        self.setup_button()

    def setup_button(self):
        self.spec_shot_button = QtWidgets.QPushButton('...')
        button_styleSheet = '''QPushButton {{ {bg} {border1} }}
        QPushButton:hover {{ {bg} {border2} border-color: rgb{lightGray};}}
        QPushButton:pressed {{ {bgPressed} {border2} border-color: rgb{brightGray};}}
        '''.format(bg=StyleConfig.fieldBackground, 
                border1=StyleConfig.no_border,
                border2=StyleConfig.border,
                bgPressed=StyleConfig.backgroundDark, 
                lightGray=StyleConfig.lightGray,
                brightGray=StyleConfig.brightGray)
        self.spec_shot_button.setStyleSheet(button_styleSheet)
        self.spec_shot_button.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.spec_shot_button.clicked.connect(self.browse_shot)
        self.line_layout.addWidget(self.spec_shot_button)

    def browse_shot(self):
        dialog = BrowseShotDialog(project=self.project, parent=self)
        dialog.completed.connect(self.add_shot)
        dialog.exec_()
        self.clicked.emit(True)
        
    def add_shot(self, result):
        if result:
            allow_creation = self.allow_creation
            self.allow_creation = True
            self.add_item(text=result['code'], data=result)
            self.allow_creation = allow_creation

class SGShotTagWidget(TagWidget):
    def __init__(self, project, shots=[], inLine=True, parent=None):
        super(SGShotTagWidget, self).__init__(inLine, parent)
        self.project = project
        if not shots:
            shots = sg_process.get_all_shots(self.project['name'])
        self.set_data(data=shots, displayKey='code')

class SGAssetTagWidget(TagWidget):
    def __init__(self, project, assets=[], filters=[], inLine=True, parent=None) :
        super(SGAssetTagWidget, self).__init__(inLine, parent)
        self.project = project
        if not assets:
            assets = sg_process.get_assets(project=self.project['name'], filters=filters)
        self.set_data(data=assets, displayKey='code')

class BrowseShotDialog(QtWidgets.QDialog):
    ''' Dialog for selecting shot '''
    completed = QtCore.Signal(dict)
    def __init__(self, project, parent=None):
        super(BrowseShotDialog, self).__init__(parent)
        self.project = project
        self.w = 225
        self.h = 180
        self.init_ui()
        self.init_signals()
        self.set_default()

    def init_ui(self):
        self.setWindowTitle('Select Seq/Shot')
        self.setStyleSheet(StyleConfig.background)
        self.resize(self.w, self.h)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.MSWindowsFixedSizeDialogHint)

        self.allLayout = QtWidgets.QVBoxLayout()
        self.setLayout(self.allLayout)

        self.sg_nav_widget = entity_browse_widget.SGSceneNavigation2(sg=sg, shotFilter=True)
        # self.sg_nav_widget.shotExtraFilter = ['sg_shot_type', 'is', 'Shot']
        self.sg_nav_widget.shotExtraField = ['sg_sequence']
        self.sg_nav_widget.shotWidget.displayAttr = 'code'
        self.sg_nav_widget.layout.setSpacing(5)
        self.sg_nav_widget.shotWidget.set_searchable(False)
        self.allLayout.addWidget(self.sg_nav_widget)

        self.button_layout = QtWidgets.QHBoxLayout()
        self.allLayout.addLayout(self.button_layout)
        spacerItem = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.button_layout.addItem(spacerItem)
        # button
        self.select_button = QtWidgets.QPushButton('Select')
        self.select_button.setMinimumSize(QtCore.QSize(75, 25))
        button_styleSheet = '''QPushButton {{ {bg} {no_border} }}
        QPushButton:hover {{ {bg} {border} border-color: rgb{lightGray};}}
        QPushButton:pressed {{ {bgPressed} {border} border-color: rgb{brightGray};}}
        '''.format(bg=StyleConfig.fieldBackground, 
                no_border=StyleConfig.no_border,
                border=StyleConfig.border,
                lightGray=StyleConfig.lightGray,
                brightGray=StyleConfig.brightGray,
                bgPressed=StyleConfig.backgroundDark)
        self.select_button.setStyleSheet(button_styleSheet)
        self.button_layout.addWidget(self.select_button)

    def init_signals(self):
        self.select_button.clicked.connect(self.select)

    def set_default(self):
        self.sg_nav_widget.list_episodes(projectEntity=self.project)

    def select(self):
        result = self.sg_nav_widget.shotWidget.current_item()
        self.completed.emit(result)
        self.close()

def find_project(project):
    return sg.find_one('Project', [['name', 'is', project]], ['id', 'name'])

def find_tag():
    return sg.find('Tag',[],['name'])

def find_one_tag(tagName):
    return sg.find_one('Tag',[['name', 'is', tagName]],['name'])

def find_asset_tags(projectEntity,assetName):
    return sg.find_one('Asset', [['project', 'is', projectEntity],['code','is',assetName]], ['tags'])

def create_hashtag(tagName):
    data = {'name':tagName}
    return sg.create('Tag', data)

def update_hashtag(projectEntity,assetName,tagList):
    filters = [['code','is',assetName],['project', 'is', projectEntity]]
    assetEntity = sg.find_one('Asset',filters, ['name'])
    data = {'tags': tagList}
    return sg.update('Asset', assetEntity['id'], data)

if __name__ == '__main__':
    app = HashtagWidget()
    app.show()

#from rf_app.global_library import hashtags_widget
#reload(hashtags_widget)
#app = hashtags_widget.hashtagWidget()
#app.show()

#projectEntity = hashtags_widget.find_project('Global library')
#app.set_all_hashtag(projectEntity,'TESTPROP')
#app.publish_hashtag(projectEntity,'TESTPROP')
#app.get_all_item()
#app.get_all_tags()