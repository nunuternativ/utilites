import sys
import os
import tempfile
from collections import defaultdict

from Qt import QtWidgets
from Qt import QtGui
from Qt import QtCore
import cv2

from rf_utils.widget import filmstrip_widget

IMAGE_EXT = ['.png', '.jpeg', '.jpg', '.tiff', '.tif']
_VERSION_ = '1.0'
try:
    MODULEDIR = sys._MEIPASS.replace('\\', '/')
except Exception:
    MODULEDIR = os.path.dirname(sys.modules[__name__].__file__).replace('\\', '/')
LOADINGICON = "{}/icons/gif/loading60.gif".format(MODULEDIR)

def load_images(image_file):
    capture = cv2.imread(image_file, cv2.IMREAD_UNCHANGED)
    frame = cv2.cvtColor(capture, cv2.COLOR_BGR2RGB)
    return frame

class ImageViewer(QtWidgets.QGraphicsView):
    '''
    Image viewer class with pan and zoom
    '''
    scroll_zoom_factor = 1.15
    mouse_zoom_factor = 1.05
    def __init__(self, parent=None):
        super(ImageViewer, self).__init__(parent)
        # viewport vars
        self.clickPos = QtCore.QPoint(0, 0)
        self.clickScenePos = QtCore.QPointF(0.0, 0.0)
        self.viewCenter = QtCore.QPointF(0.0, 0.0)

        # setup
        self.setMouseTracking(True)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        self.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)

        self.h_scroll = self.horizontalScrollBar()
        self.v_scroll = self.verticalScrollBar()
        # toolTip
        self.setToolTip('Frame: F Key\nPan: Middle Mouse\nZoom: Scroll Wheel\n\
            Alt+Middle Mouse\nAdd selection: hold Shift\nSubtract selection: hold Ctrl\nView: Double-Click\nDrag: Ctrl+Middle Mouse')

    def newScene(self):
        scene = QtWidgets.QGraphicsScene()
        self.setScene(scene)
        # actions
        self.frame_action = QtWidgets.QAction(self.scene())
        self.frame_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_F))
        self.addAction(self.frame_action)
        self.frame_action.triggered.connect(self.frameImage)

        return scene

    def mouseDoubleClickEvent(self, event):
        pass

    def getTopLevelItems(self):
        if not self.scene():
            return []
        return [item for item in self.scene().items() if not item.parentItem()]

    def getItemsRect(self):
        allRect = QtCore.QRectF()
        for item in self.getTopLevelItems():
            # unite rect for fit view
            itemRect = item.sceneBoundingRect()
            allRect = allRect.united(itemRect)
        return allRect    

    def frameImage(self):
        allRect = self.getItemsRect()
        # fit all item to center
        self.fitInView(allRect, QtCore.Qt.KeepAspectRatio)

    def getCenter(self):
        rect = self.viewport().rect()
        center = self.mapToScene(rect.center())
        return center

    def viewport_smaller_than_sceneRect(self):
        scene = self.scene()
        if scene:
            sceneRect = scene.sceneRect()
            viewportRect = self.viewport().rect()
            viewportRectScene = self.mapToScene(viewportRect).boundingRect()
            sceneSize = sceneRect.size()
            viewportSize = viewportRectScene.size()
            return sceneSize.width() > viewportSize.width() or sceneSize.height() > viewportSize.height()

    def mousePressEvent(self, event):
        self.clickPos = event.pos()
        self.clickScenePos = self.mapToScene(self.clickPos)
        self.clickGlobalPos = event.globalPos()
        self.viewCenter = self.getCenter()
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        event.accept()

    def mouseMoveEvent(self, event):
        mods = QtWidgets.QApplication.keyboardModifiers()
        buttons = event.buttons()

        if buttons & QtCore.Qt.MiddleButton:
            # middle mouse + alt - zoom
            if mods & QtCore.Qt.AltModifier:
                currPos = event.pos()
                diff = currPos - self.clickPos
                scale_factor = self.mouse_zoom_factor
                allow_scale = True
                consider_diff = diff.x()
                if abs(diff.x()) < abs(diff.y()):
                    consider_diff = diff.y() * -1

                if consider_diff > 0.0:  # zooming in
                    scale_factor = self.mouse_zoom_factor
                else:  # zooming out
                    # only allow zooming out if it's smaller than scene rect
                    if self.viewport_smaller_than_sceneRect(): 
                        scale_factor = 1/self.mouse_zoom_factor
                    else:
                        allow_scale = False
                if allow_scale:
                    self.scale(scale_factor, scale_factor) 
                    self.centerOn(self.viewCenter)
                    self.clickPos = event.pos()

            else:  # middle mouse + alt - pan the frame
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
                currPos = self.mapToScene(event.pos())
                diff = currPos - self.clickScenePos
                self.translate(diff.x(), diff.y())
                
                self.viewCenter = self.getCenter()
                self.clickPos = event.pos()
                self.clickScenePos = self.mapToScene(event.pos())
        QtWidgets.QGraphicsView.mouseMoveEvent(self, event)
        event.accept()

    def wheelEvent(self, event):
        scrollFactor = event.delta()/120.0  # -1.0 or 1.0  - only directions
        # set view center before the scale happen
        self.viewCenter = self.getCenter()

        scale_factor = self.scroll_zoom_factor
        allow_scale = True
        if scrollFactor > 0.0:  # zooming in
            scale_factor = self.scroll_zoom_factor
        else:  # zooming out
            # only allow zooming out if it's smaller than rect
            if self.viewport_smaller_than_sceneRect():  
                scale_factor = 1/self.scroll_zoom_factor
            else:
                allow_scale = False
        if allow_scale:
            oldPos = self.mapToScene(event.pos())
            self.scale(scale_factor, scale_factor)
            newPos = self.mapToScene(event.pos())
            delta = newPos - oldPos
            self.translate(delta.x(), delta.y()) 
        self.clickPos = event.pos()
        event.accept() 

class ImageSingleViewer(ImageViewer):
    '''
    Single image viewer class with pan and zoom
    '''
    fileDropped = QtCore.Signal(list)
    lostFocus = QtCore.Signal(bool)
    def __init__(self, imageScale=[], parent=None):
        super(ImageSingleViewer, self).__init__(parent)
        self.imageScale = imageScale
        self.pixmapItem = None
        self.setToolTip('Frame: F Key\nPan: Middle Mouse\nZoom: Scroll Wheel')

    def focusOutEvent(self, event):
        self.lostFocus.emit(True)

    def browseSetImage(self):
        imgPath, ext = QtWidgets.QFileDialog.getOpenFileName(parent=self, 
                                                    caption='Set image',
                                                    directory=self.parentUi.app.default_file_dir,
                                                    filter='Images (*.jpg *.png *.tiff)')
        if imgPath:
            self.setImage(path=imgPath)

    def setImage(self, path):
        if not os.path.exists(path): 
            return

        # create new pixmap item with image from the path and scale
        pixmap = QtGui.QPixmap(path)
        if self.imageScale:
            if not pixmap.isNull():
                pixmap = pixmap.scaled(self.imageScale[0], self.imageScale[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)

        # set scene rect to 2 times the image size
        scene = self.newScene()
        scene.setSceneRect(0, 0, pixmap.width()*2, pixmap.height()*2)

        # try to remove the old pixmap item
        if self.pixmapItem:
            try:
                scene.removeItem(self.pixmapItem)
            except:
                pass

        # create new pixmap item and add to the graphic scene
        self.pixmapItem = QtWidgets.QGraphicsPixmapItem()
        scene.addItem(self.pixmapItem)

        # placing background image
        # get the scene center
        self.viewCenter = self.sceneRect().center()
        # move the background image to the center
        self.pixmapItem.setPos(self.viewCenter)
        # the image moving point is at the upper left, have to offset it back up
        self.pixmapItem.setOffset(pixmap.width()*-0.5, pixmap.height()*-0.5)

        # setup pixmap item
        self.pixmapItem.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, False)
        # self.pixmapItem.setZValue(-1.0)
        self.pixmapItem.setPixmap(pixmap)
        
        # frame image to center of the view
        self.frameImage()

    def dragLeaveEvent(self, event):
        event.ignore()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.fileDropped.emit(links)
        else:
            event.ignore()

class ImageSlideViewer(QtWidgets.QWidget):
    '''
    Multiple image viewer class with pan and zoom
    '''
    imageDropped = QtCore.Signal(list)
    imagePasted = QtCore.Signal(QtGui.QPixmap)
    def __init__(self, imageScale=[], parent=None):
        super(ImageSlideViewer, self).__init__(parent)
        self._allow_image_drop = False
        self._drop_add_image = False
        self._paste_add_image = False
        self._show_last_image = True

        # main layout
        self.allLayout = QtWidgets.QHBoxLayout()
        self.allLayout.setSpacing(0)
        self.allLayout.setContentsMargins(0, 0, 0, 0)

        self.viewSplitter = QtWidgets.QSplitter()
        self.viewSplitter.setOrientation(QtCore.Qt.Horizontal)
        self.viewSplitWidget = QtWidgets.QWidget(self.viewSplitter)
        self.listSplitWidget = QtWidgets.QWidget(self.viewSplitter)
        self.viewSplitter.setSizes([300, 30])
        self.allLayout.addWidget(self.viewSplitter)

        # add viewer
        self.view_layout = QtWidgets.QVBoxLayout(self.viewSplitWidget)
        self.view_layout.setSpacing(0)
        self.view_layout.setContentsMargins(0, 0, 0, 0)

        self.viewer = ImageSingleViewer()
        self.viewer.setToolTip('Frame: F Key\nPan: Middle Mouse\nZoom: Scroll Wheel\nNext: Arrow Down\nPrevious: Arrow Up')
        self.view_layout.addWidget(self.viewer)

        # film strip
        self.list_layout = QtWidgets.QVBoxLayout(self.listSplitWidget)
        self.list_layout.setSpacing(0)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.reelWidget = filmstrip_widget.DisplayReel()
        self.reelWidget.allow_paste = False
        
        self.reelWidget.displayListWidget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        # self.reelWidget.setMinimumWidth(100)
        self.list_layout.addWidget(self.reelWidget)

        self.setLayout(self.allLayout)
        self.allLayout.setStretch(0, 8)
        self.allLayout.setStretch(1, 1)

        self.viewer.installEventFilter(self)
        self.reelWidget.displayListWidget.installEventFilter(self)
        self.init_signals()

    def eventFilter(self, source, event):
        if source in (self.viewer, self.reelWidget.displayListWidget) and event.type() == QtCore.QEvent.KeyPress and event == QtGui.QKeySequence.Paste:
            pixmap = QtWidgets.QApplication.clipboard().pixmap()
            if pixmap:
                self.imagePasted.emit(pixmap)
                if self._paste_add_image:
                    fh, temp = tempfile.mkstemp(suffix='.png')
                    os.close(fh)
                    pixmap.save(temp, "PNG")
                    self.image_dropped([temp])
                return True
        return super(ImageSlideViewer, self).eventFilter(source, event)

    @property
    def allow_image_drop(self):
        return self._allow_image_drop

    @allow_image_drop.setter
    def allow_image_drop(self, value):
        self._allow_image_drop = value
        self.viewer.setAcceptDrops(value)

    @property
    def show_last_image(self):
        return self._show_last_image

    @show_last_image.setter
    def show_last_image(self, value):
        self._show_last_image = value

    @property
    def drop_add_image(self):
        return self._drop_add_image

    @drop_add_image.setter
    def drop_add_image(self, value):
        self._drop_add_image = value

    @property
    def paste_add_image(self):
        return self._paste_add_image

    @paste_add_image.setter
    def paste_add_image(self, value):
        self._paste_add_image = value

    def init_signals(self): 
        self.reelWidget.clicked.connect(self.reel_selected)
        self.reelWidget.fileDropped.connect(self.image_dropped)
        self.viewer.fileDropped.connect(self.image_dropped)

    def image_dropped(self, links):
        supported_formats = ['.'+str(f) for f in QtGui.QImageReader.supportedImageFormats()]
        links = [l for l in links if len(os.path.splitext(l)) > 1 and os.path.splitext(l)[-1].lower() in supported_formats]
        if links:
            self.imageDropped.emit(links)
            if self._drop_add_image:
                self.add_images(links)

    def clear(self):
        self.reelWidget.clear()
        self.viewer.newScene()

    def add_images(self, paths):
        display_paths = []
        for p in paths:
            path = None
            data = None
            if isinstance(p, (list, tuple)):
                if len(p) > 1:
                    path = p[0]
                    data = p[1]
            elif isinstance(p, dict):
                path = p.get('filepath')
                data = p
            else:
                path = p
            if path:
                self.reelWidget.add_item(path=path, data=data)
                display_paths.append(path)

        # set image after add
        if self._show_last_image == True:
            self.reelWidget.displayListWidget.setCurrentRow(self.reelWidget.displayListWidget.count()-1)
            self.viewer.setImage(display_paths[-1])
        else:
            self.reelWidget.displayListWidget.setCurrentRow(0)
            self.viewer.setImage(display_paths[0])

    def reel_selected(self, path):
        if isinstance(path, (list, tuple)):
            if len(p) > 1:
                path = path[0]
                data = path[1]
        elif isinstance(path, dict):
            path = path.get('filepath')

        if not path or not os.path.exists(path):
            self.viewer.newScene()
        else:
            self.viewer.setImage(path)

    def current_image_path(self):
        return self.reelWidget.get_current_item()

    def selected_items(self):
        return self.reelWidget.displayListWidget.selectedItems()

class ImageGridItem(QtWidgets.QGraphicsPixmapItem):
    def __init__(self, *args, **kwargs):
        super(ImageGridItem, self).__init__(*args, **kwargs) 
        self.painter = QtGui.QPainter()
        self.orig_pixmap = None
        self.border_pixmap = None
        self.pen = None

        self.texts = defaultdict(list)
        self.overlays = defaultdict(list)

    def setOverlay(self, path, scale, position='topLeft', border=0):
        fn, ext = os.path.splitext(path)
        if ext in ['.gif']:
            # create item
            item = QtWidgets.QGraphicsProxyWidget(parent=self)
            
            # create label
            label = QtWidgets.QLabel()
            label.setAttribute(QtCore.Qt.WA_NoSystemBackground)
            label.setScaledContents(True)

            # create movie
            movie = QtGui.QMovie(path)
            label.setMovie(movie)

            # scale movie
            movRect = movie.frameRect()
            size = QtCore.QSize(movRect.width(), movRect.height())
            size.scale(scale[0], scale[1], QtCore.Qt.KeepAspectRatio)
            movie.setScaledSize(size)
            movie.start()

            # add label to item
            item.setWidget(label)
        else:
            item = QtWidgets.QGraphicsPixmapItem(parent=self)
            pixmap = QtGui.QPixmap(path)
            pixmap = pixmap.scaled(scale[0], scale[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
            item.setPixmap(pixmap)

        item.setVisible(True)
        item.setZValue(1.0)
        self.positionOverlayObject(item, position, border)
        self.overlays[position].append(item)

    def hideOverlays(self):
        for pos, items in self.overlays.items():
            for item in items:
                item.setVisible(False)

    def showOverlays(self):
        for pos, items in self.overlays.items():
            for item in items:
                item.setVisible(True)

    def removeAllOverlays(self):
        for pos, items in self.overlays.items():
            for item in items:
                self.scene().removeItem(item)
        self.overlays = defaultdict(list)

    def removeOverlay(self, position):
        if position in self.overlays:
            for item in self.overlays[position]:
                self.scene().removeItem(item)
            self.overlays[position] = []

    def setText(self, text, position='bottomCenter', border=0, font=QtGui.QFont('Calibri', 16), color=QtGui.QColor('yellow')):
        textItem = QtWidgets.QGraphicsTextItem(parent=self)
        textItem.setVisible(True)
        textItem.setZValue(1.0)

        # set the text
        textItem.setPlainText(text)
        textItem.setFont(font)
        textItem.setDefaultTextColor(color)
        self.positionOverlayObject(textItem, position, border)
        self.texts[position].append(textItem)

    def positionOverlayObject(self, item, position, border):
        imgRect = self.boundingRect()
        itemRect = item.boundingRect()
        if position == 'topLeft':
            item.setTransform(QtGui.QTransform.fromTranslate(border, border))
        elif position == 'topCenter':
            item.setTransform(QtGui.QTransform.fromTranslate((imgRect.width()*0.5) - (itemRect.width()*0.5), border))
        elif position == 'topRight':
            item.setTransform(QtGui.QTransform.fromTranslate(imgRect.width() - itemRect.width() - border, border))
        elif position == 'midLeft':
            item.setTransform(QtGui.QTransform.fromTranslate(border, (imgRect.height()*0.5) - (itemRect.height()*0.5)))
        elif position == 'center':
            item.setTransform(QtGui.QTransform.fromTranslate((imgRect.width()*0.5) - (itemRect.width()*0.5), (imgRect.height()*0.5) - (itemRect.height()*0.5)))
        elif position == 'midRight':
            item.setTransform(QtGui.QTransform.fromTranslate(imgRect.width() - itemRect.width() - border, (imgRect.height()*0.5) - (itemRect.height()*0.5)))
        elif position == 'bottomLeft':
            item.setTransform(QtGui.QTransform.fromTranslate(border, (imgRect.height() - itemRect.height() - border)))
        elif position == 'bottomCenter':
            item.setTransform(QtGui.QTransform.fromTranslate((imgRect.width()*0.5) - (itemRect.width()*0.5), (imgRect.height() - itemRect.height() - border)))
        elif position == 'bottomRight':
            item.setTransform(QtGui.QTransform.fromTranslate(imgRect.width() - itemRect.width() - border, (imgRect.height() - itemRect.height() - border)))

    def hideTexts(self):
        for position, texts in self.texts.items():
            for text in texts:
                text.setVisible(False)

    def showTexts(self):
        for position, texts in self.texts.items():
            for text in texts:
                text.setVisible(True)

    def removeAllTexts(self):
        if self.scene():
            for pos, items in self.texts.items():
                for item in items:
                    self.scene().removeItem(item)
        self.texts = defaultdict(list)

    def removeText(self, index):
        if position in self.texts:
            for item in self.texts[position]:
                self.scene().removeItem(item)
            self.texts[position] = []

    def getOrigPixmap(self):
        if not self.orig_pixmap:
            self.orig_pixmap = self.pixmap()

    def setBorder(self, color, width=24):
        self.getOrigPixmap()
        if self.orig_pixmap and not self.orig_pixmap.isNull():
            self.border_pixmap = self.orig_pixmap.copy()
            self.painter.begin(self.border_pixmap)
            if self.painter.isActive():
                self.pen = QtGui.QPen(color, width)
                self.painter.setPen(self.pen)
                self.painter.drawRect(self.boundingRect())
                self.painter.end()
                self.setPixmap(self.border_pixmap)

    def hideBorder(self):
        self.getOrigPixmap()
        self.setPixmap(self.orig_pixmap)

    def showBorder(self):
        if self.border_pixmap:
            self.setPixmap(self.border_pixmap)

class ImageLoadThread(QtCore.QThread):
    loadFinished = QtCore.Signal(list)
    frameLoaded = QtCore.Signal(list)
    percentLoaded = QtCore.Signal(float)
    __stop = False

    def __init__(self, filenames=[], parent=None):
        super(ImageLoadThread, self).__init__(parent=parent)
        self.filenames = filenames
        self.images = []
        self._stop = False

    # def __del__(self):
    #     self.wait()
    #     return 0

    def stop(self):
        self._stop = True
        return 0

    def run(self):
        if not self.filenames:
            return 0

        num_files = len(self.filenames)
        for i, each in enumerate(self.filenames):
            each_name, each_ext = os.path.splitext(each)
            basename = os.path.basename(each)
            loaded = False
            if each_ext.lower() in IMAGE_EXT:
                # image = QtGui.QPixmap(each)
                # CANNOT use QPixmap directly here outside of GUI thread, use cv2 instead
                image = load_images(each)
                self.images.append(image)
                loaded = True

            if self._stop:
                # print("Threading interrupted.\n")
                break
            if loaded:
                self.frameLoaded.emit([i, image])
                percent = round((float(i+1)/num_files) * 100.0, 2)
                self.percentLoaded.emit(percent)

        if self._stop:
            self.images = []
            self._stop = False
        self.loadFinished.emit(self.images)

        return 0

class ImageGridViewer(ImageViewer):
    '''
    Grid style multiple image viewer with pan and zoom
    '''
    itemDoubleClicked = QtCore.Signal(dict)
    itemSelected = QtCore.Signal(dict)
    loadFinished = QtCore.Signal(list)

    def __init__(self, imagePerRow=4, 
                    rowSpacing=10, 
                    columnSpacing=10, 
                    gridScale=(2048, 1024), 
                    borderWidth=10, 
                    useFullSize=False, 
                    fullSizeMultiplier=0.5,
                    parent=None):
        super(ImageGridViewer, self).__init__(parent)

        self.loadThread = None
        self.items = []

        self.imagePerRow = imagePerRow
        self.rowSpacing = rowSpacing
        self.columnSpacing = columnSpacing
        self.gridScale = gridScale

        self.borderWidth = borderWidth
        self.useFullSize = useFullSize
        self.fullSizeMultiplier = fullSizeMultiplier

        self.x = 0.0
        self.y = 0.0
        self.ri = 0
        self.num_images = 0
        self.lastItem = None
        self._item_is_selectable = True
        
        self.rubberband = QtWidgets.QRubberBand(QtWidgets.QRubberBand.Rectangle, self)
        self.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)

    def showBorders(self):
        for item in self.getTopLevelItems():
            item.showBorder()

    def hideBorders(self):
        for item in self.getTopLevelItems():
            item.hideBorder()

    def hideOverlays(self):
        for item in self.getTopLevelItems():
            item.hideOverlays()

    def showOverlays(self):
        for item in self.getTopLevelItems():
            item.showOverlays()

    def hideTexts(self):
        for item in self.getTopLevelItems():
            item.hideTexts()

    def showTexts(self):
        for item in self.getTopLevelItems():
            item.showTexts()

    def setLoading(self, loading):
        if loading:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
            # self.loadMovie.start()
            # self.scene().addItem(self.loadItem)
        else:
            # self.loadMovie.stop()
            # self.scene().removeItem(self.loadItem)
            QtWidgets.QApplication.restoreOverrideCursor()

    def mouseDoubleClickEvent(self, event):
        selItems = self.scene().selectedItems()
        if selItems:
            item = selItems[0]
            self.itemDoubleClicked.emit(item.data(QtCore.Qt.UserRole))
        event.accept()

    def mousePressEvent(self, event):
        super(ImageGridViewer, self).mousePressEvent(event)
        buttons = event.buttons()
        mods = QtWidgets.QApplication.keyboardModifiers()
        if buttons == QtCore.Qt.LeftButton:
            # left clicked
            self.rubberband.setGeometry(QtCore.QRect(event.pos(), QtCore.QSize()))
            self.rubberband.show()
        elif buttons == QtCore.Qt.MiddleButton:
            if mods == QtCore.Qt.ControlModifier:
                self.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        event.accept()

    def mouseMoveEvent(self, event):
        super(ImageGridViewer, self).mouseMoveEvent(event)
        buttons = event.buttons()
        mods = QtWidgets.QApplication.keyboardModifiers()
        if buttons & QtCore.Qt.LeftButton:
            if self.rubberband.isVisible():
                self.rubberband.setGeometry(QtCore.QRect(self.clickPos, event.pos()).normalized())
        elif buttons & QtCore.Qt.MiddleButton:
            if mods & QtCore.Qt.ControlModifier:
                curr_scene = self.scene()
                selItems = curr_scene.selectedItems()
                itemUnder = curr_scene.itemAt(self.clickScenePos, QtGui.QTransform())
                items = [i for i in selItems + [itemUnder] if i and not i.parentItem()]
                if items:
                    mimedata = QtCore.QMimeData()
                    urls = []
                    for item in items:
                        data = item.data(QtCore.Qt.UserRole)
                        if 'filepath' in data:
                            url = QtCore.QUrl.fromLocalFile(data['filepath'])
                            urls.append(url)
                    mimedata.setUrls(urls)

                    # init drag
                    drag = QtGui.QDrag(self)
                    # set mime data
                    drag.setMimeData(mimedata) 
                    # set pixmap
                    pixmap = QtGui.QPixmap(item.pixmap()).scaled(64, 64, QtCore.Qt.KeepAspectRatio)
                    drag.setPixmap(pixmap)
                    # set cursor
                    cursor = QtGui.QCursor(QtCore.Qt.ClosedHandCursor)
                    drag.setDragCursor(cursor.pixmap(), QtCore.Qt.MoveAction)
                    # set hot spot
                    drag.setHotSpot(event.pos() - self.clickPos)
                    # start dragging
                    drag.start(QtCore.Qt.MoveAction)
        event.accept()

    def mouseReleaseEvent(self, event):
        super(ImageGridViewer, self).mouseReleaseEvent(event)
        if self.rubberband.isVisible():
            self.rubberband.hide()

        curr_scene = self.scene()
        if curr_scene:
            buttons = event.button()
            mods = QtWidgets.QApplication.keyboardModifiers()
            # selection
            if buttons == QtCore.Qt.LeftButton:
                # it's a single click
                if self.clickPos == event.pos():
                    item = self.itemAt(self.clickPos)
                    sel_value = True
                    # add
                    if mods == QtCore.Qt.ShiftModifier:
                        sel_value = True
                    elif mods == QtCore.Qt.ControlModifier:  # subtract
                        sel_value = False
                    elif mods == QtCore.Qt.AltModifier:
                        sel_value = not(item.isSelected())
                    else:
                        curr_scene.clearSelection()

                    if item:
                        parentItem = item.parentItem()
                        if parentItem:
                            item = parentItem
                        item.setSelected(sel_value)
                        self.itemSelected.emit(item.data(QtCore.Qt.UserRole))
                    # else:
                    #     self.itemSelected.emit(None)
                else:  # its a rubber band drag
                    croppedItems = [i for i in curr_scene.items(self.mapToScene(self.rubberband.geometry())) if not i.parentItem()]
                    painterPath = QtGui.QPainterPath()
                    rect = self.mapToScene(self.rubberband.geometry())
                    if croppedItems:
                        if mods & QtCore.Qt.ControlModifier:  # if user pressed ctrl, subtract selection
                            painterPath = QtGui.QPainterPath()
                            oldPainterPath = QtGui.QPainterPath()

                            selButtons = curr_scene.selectedItems()
                            if selButtons:
                                for button in selButtons:
                                    rect = button.sceneBoundingRect()
                                    oldPainterPath.addRect(rect)
                            else:
                                oldPainterPath.addRect(self.sceneRect())

                            for button in croppedItems:
                                rect = button.sceneBoundingRect()
                                painterPath.addRect(rect)
                            painterPath = oldPainterPath.subtracted(painterPath)

                        elif mods & QtCore.Qt.ShiftModifier:  # if user pressed shift, add selection
                            selButtons = curr_scene.selectedItems()
                            croppedItems.extend(selButtons)
                            for button in croppedItems:
                                rect = button.sceneBoundingRect()
                                painterPath.addRect(rect)
                        elif not mods:  # no modifier key pressed
                            painterPath.addRect(rect.boundingRect())
                        curr_scene.setSelectionArea(painterPath)
                    else:
                        curr_scene.clearSelection()
        event.accept()

    def dropEvent(self, event):
        super(ImageGridViewer, self).dropEvent(event)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        event.accept()

    def dragLeaveEvent(self, event):
        super(ImageGridViewer, self).dragLeaveEvent(event)
        self.setDragMode(QtWidgets.QGraphicsView.NoDrag)
        event.accept()

    def frameImage(self):
        '''
        function called when 'f' is pressed to frame select/all items
        '''
        selItems = self.scene().selectedItems()
        if selItems:
            allRect = QtCore.QRectF()
            for item in selItems:
                itemRect = item.sceneBoundingRect()
                allRect = allRect.united(itemRect)
            self.fitInView(allRect, QtCore.Qt.KeepAspectRatio)
        else:
            super(ImageGridViewer, self).frameImage()

    def clear(self):
        scene = self.newScene()
        # reset arrangment vars
        self.x = 0.0
        self.y = 0.0
        self.ri = 0
        self.num_images = 0
        self.lastItem = None
        self.items = []

    def add_ui_items(self, item_datas):
        # clear current scene
        scene = self.newScene()

        # create items
        self.items = []
        paths =[]
        for data in item_datas:
            if isinstance(data, (list, tuple)):
                path = data[0]
                userdata = data[1]
            elif isinstance(data, (str, unicode)):
                path = data
                userdata = data

            item = ImageGridItem()
            item.setZValue(0.0)
            item.setFlag(QtWidgets.QGraphicsItem.ItemIsSelectable, self._item_is_selectable)
            item.setData(QtCore.Qt.UserRole, userdata)  # set user data

            paths.append(path)
            self.items.append(item)

        # reset arrangment vars
        self.x = 0.0
        self.y = 0.0
        self.ri = 0
        self.num_images = len(paths)
        self.lastItem = None

        return paths

    def showImages(self, images):
        '''
        images = [path, path, ...] or [(path, data), ...]
        * data can be a dict with special key for display
            - '__toolTip' is for item's toolTip
            - '__border_color' is for item's border color
        '''
        # stop old thread, if any
        if self.loadThread != None:
            self.loadThread.stop()
            self.loadThread.exit()
            self.loadThread.wait()
        
        # add item to the UI
        paths = self.add_ui_items(item_datas=images)
        if paths:
            # start new thread
            self.loadThread = ImageLoadThread(paths)
            self.loadThread.frameLoaded.connect(self.onFrameLoaded)
            self.loadThread.loadFinished.connect(self.onLoadFinished)

            self.loadThread.start()

            self.setLoading(loading=True)

    def onFrameLoaded(self, loadData):
        # number of the image
        i = loadData[0]
        # convert cv image to QPixmap
        if not isinstance(loadData[1], QtGui.QPixmap):
            cvImg = loadData[1]
            height, width, channel  = cvImg.shape
            bytesPerLine = 3 * width
            img = QtGui.QImage(cvImg.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)
            pixmap = QtGui.QPixmap(img)
        else:
            pixmap = loadData[1]

        # QPixmapGraphicsItem 
        if self.items and i <= len(self.items)-1:
            item = self.items[i]

            # if set to use full size, just use the image original size * self.fullSizeMultiplier
            if self.useFullSize:
                if self.fullSizeMultiplier != 1.0 and not pixmap.isNull():
                    pixmap = pixmap.scaled(pixmap.width()*self.fullSizeMultiplier, pixmap.height()*self.fullSizeMultiplier, QtCore.Qt.KeepAspectRatio)
                item.setPixmap(pixmap)
            else:
                # fill blackground with black to make sure every item has same size
                if not pixmap.isNull():
                    pixmap = pixmap.scaled(self.gridScale[0], self.gridScale[1], QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                canvas = QtGui.QPixmap(self.gridScale[0], self.gridScale[1])
                painter = QtGui.QPainter()
                painter.begin(canvas)
                painter.drawPixmap((canvas.width() - pixmap.width())*0.5, (canvas.height()-pixmap.height())*0.5, pixmap)
                painter.end()
                item.setPixmap(canvas)

            # add item
            self.scene().addItem(item)
            self.arrangeImages(items=[(i, item)])

    def arrangeImages(self, items=[]):
        if not items:
            items = list(enumerate(self.items))
            self.x = 0.0
            self.y = 0.0
            self.ri = 0
            self.num_images = len(self.items)
            self.lastItem = None

            # reset all positions to 0 0
            for i, item in items:
                item.setPos(0, 0)

        for i, item in items:
            # set position
            item.setPos(self.x, self.y)
            self.lastItem = item
            self.ri += 1

            # if it's not the last item, calcualte position for next item
            allRect = self.getItemsRect()
            if i < self.num_images - 1:
                # new row
                if self.ri > self.imagePerRow - 1:
                    self.x = 0.0
                    self.y = allRect.height() + self.rowSpacing
                    self.ri = 0
                else:  # old row
                    self.x = self.lastItem.sceneBoundingRect().topRight().x() + self.columnSpacing

            # keep framing each item loaded so the frame expands while each image loads
            # set scene rect to 2 times of all the time size for easy zoom/pan
            allRect_w = allRect.width()
            allRect_h = allRect.height()
            self.scene().setSceneRect(allRect_w*-0.5, allRect_h*-0.5, allRect_w*2, allRect_h*2)
            super(ImageGridViewer, self).frameImage()

    def onLoadFinished(self):
        # setting item appearance from data attach to the class
        self.set_item_decorations()

        self.loadFinished.emit(self.items)
        self.setLoading(loading=False)

        if self.loadThread:
            self.loadThread.stop()
            self.loadThread.exit()
            self.loadThread.wait()
        self.loadThread = None

    def set_item_decorations(self):
        for item in self.items:
            item.removeAllTexts()
            item.removeAllOverlays()

            itemData = item.data(QtCore.Qt.UserRole)
            if itemData:
                if '__toolTip' in itemData:
                    item.setToolTip(itemData['__toolTip'])
                if '__border_color' in itemData:
                    item.setBorder(itemData['__border_color'], self.borderWidth)
                if '__text' in itemData:
                    fontDatas = itemData['__text']
                    for fontData in fontDatas:
                        item.setText(text=fontData[0], position=fontData[1], border=fontData[2], font=fontData[3], color=fontData[4])
                if '__pixmap' in itemData:
                    pixmapDatas = itemData['__pixmap']
                    for pixmapData in pixmapDatas:
                        item.setOverlay(path=pixmapData[0], scale=pixmapData[1], position=pixmapData[2], border=pixmapData[3])

    def browseSaveImage(self, renderSize=(1920, 1080), verticalBorder=1.0, horizontalBorder=1.0, writeToTemp=False):
        dialog = QtWidgets.QFileDialog()
        dialog.setWindowTitle('Export color script')
        dialog.setNameFilters(["JPEG (*.jpg *.JPG)", "PNG (*.png *.PNG)", "TIFF (*.tiff *.TIFF)"])
        dialog.setDefaultSuffix('jpg')
        dialog.setLabelText (QtWidgets.QFileDialog.Accept, "Export")
        dialog.setFileMode(QtWidgets.QFileDialog.AnyFile)
        dialog.setAcceptMode(QtWidgets.QFileDialog.AcceptSave) 
        dialog.setDirectory(os.path.expanduser("~"))
        dialog.setOption(QtWidgets.QFileDialog.DontUseNativeDialog)
        
        chosen_path = None
        save_path = None
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            chosen_path = dialog.selectedFiles()[0]

            self.setLoading(loading=True)
            save_path = chosen_path
            if writeToTemp:
                fn, ext = os.path.splitext(chosen_path)
                out_fh, save_path = tempfile.mkstemp(suffix=ext)
                save_path = save_path.replace('\\', '/')
                os.close(out_fh)
            self.saveImage(path=save_path, 
                        renderSize=renderSize, 
                        verticalBorder=verticalBorder, 
                        horizontalBorder=horizontalBorder)
            self.setLoading(loading=False)

        return chosen_path, save_path

    def saveImage(self, path, renderSize=(1920, 1080), verticalBorder=1.0, horizontalBorder=1.0):
        fn, ext = os.path.splitext(path)
        if ext.lower() not in IMAGE_EXT:
            print('Invalid save format: {}'.format(ext))
            return

        area = self.getItemsRect()
        size = area.size().toSize()

        # Create a QImage to render to and fix up a QPainter for it.
        image = QtGui.QImage(size.width(), size.height(), QtGui.QImage.Format_ARGB32_Premultiplied)
        painter = QtGui.QPainter(image)

        # Render the region of interest to the QImage.
        self.scene().render(painter, image.rect(), area)
        painter.end()

        # resize to render size
        pixmap = QtGui.QPixmap()
        pixmap = pixmap.fromImage(image.scaled(renderSize[0]*verticalBorder, renderSize[1]*horizontalBorder, 
                                                QtCore.Qt.KeepAspectRatio, 
                                                QtCore.Qt.SmoothTransformation))
        canvas = QtGui.QPixmap(renderSize[0], renderSize[1])
        painter = QtGui.QPainter()
        painter.begin(canvas)
        painter.drawPixmap((canvas.width() - pixmap.width())*0.5, (canvas.height()-pixmap.height())*0.5, pixmap)
        painter.end()

        # Save the image to a file.
        canvas.save(path, ext, 100)

        return path

class ImageDialog(QtWidgets.QDialog):
    ''' Frameless popup image view dialog with pan and zoom '''
    leftClicked = QtCore.Signal()
    rightClicked = QtCore.Signal()
    def __init__(self, path, all_paths=[], view_size=(1540, 860), 
                animated=False, animation_size_mult=0.75, animation_duration=220, 
                parent=None):
        super(ImageDialog, self).__init__(parent)
        self.path = path
        self.all_paths = all_paths  # image paths for next, previous arrow
        self.view_size = view_size
        self.animated = animated
        self.animation_size_mult = animation_size_mult
        self.animation_duration = animation_duration

        self.setup_ui()
        self.init_signals()

    def init_signals(self):
        self.close_button.clicked.connect(self.close)
        self.left_arrow.clicked.connect(self.previous_image)
        self.right_arrow.clicked.connect(self.next_image)

        # key actions
        # left
        self.right_action = QtWidgets.QAction(self)
        self.right_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Left))
        self.addAction(self.right_action)
        self.right_action.triggered.connect(self.previous_image)
        # right
        self.right_action = QtWidgets.QAction(self)
        self.right_action.setShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Right))
        self.addAction(self.right_action)
        self.right_action.triggered.connect(self.next_image)

    def setup_ui(self):
        # setup viewer window
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.Popup)

        # setup view widget
        self.all_layout = QtWidgets.QVBoxLayout(self)
        self.all_layout.setSpacing(0)
        self.all_layout.setContentsMargins(0, 0, 0, 0)

        self.top_layout = QtWidgets.QHBoxLayout()
        self.top_layout.setContentsMargins(12, 12, 12, 12)
        self.all_layout.addLayout(self.top_layout)

        self.spacer1 = QtWidgets.QSpacerItem(16, 16, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.top_layout.addItem(self.spacer1)

        # close button
        self.close_button = QtWidgets.QPushButton('  X Close  ')
        self.top_layout.addWidget(self.close_button)

        # view widget
        self.view_layout = QtWidgets.QHBoxLayout()
        self.all_layout.addLayout(self.view_layout)

        # <<
        self.left_arrow = QtWidgets.QPushButton('<')
        self.left_arrow.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding))
        self.left_arrow.setFixedWidth(50)
        self.view_layout.addWidget(self.left_arrow)

        # viewer
        self.view_widget = ImageSingleViewer()
        self.view_widget.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view_widget.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.view_widget.setToolTip('Frame: F Key\nPan: Middle Mouse\nZoom: Scroll Wheel\nClose: Esc')
        self.view_layout.addWidget(self.view_widget)

        # >>
        self.right_arrow = QtWidgets.QPushButton('>')
        self.right_arrow.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding))
        self.right_arrow.setFixedWidth(50)
        self.view_layout.addWidget(self.right_arrow)

        # bottom layout
        self.bottom_layout = QtWidgets.QHBoxLayout()
        self.bottom_layout.setContentsMargins(12, 12, 12, 12)
        self.all_layout.addLayout(self.bottom_layout)

        self.spacer2 = QtWidgets.QSpacerItem(16, 16, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.bottom_layout.addItem(self.spacer2)

        self.file_label = QtWidgets.QLabel()
        self.bottom_layout.addWidget(self.file_label)

        self.spacer3 = QtWidgets.QSpacerItem(16, 16, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.bottom_layout.addItem(self.spacer3)

    def exec_(self):
        # set size
        screen_size = QtWidgets.QDesktopWidget().screenGeometry(-1)
        max_x = (screen_size.width() - self.view_size[0]) / 2
        max_y = (screen_size.height() - self.view_size[1]) / 2
        if not self.animated:
            end_size = QtCore.QSize(int(self.view_size[0]), int(self.view_size[1]))
            self.resize(end_size)
            self.move(max_x, max_y)
            self.show()
            self.setImage()
        else:
            min_x = (screen_size.width() - (self.view_size[0]*self.animation_size_mult)) / 2 
            min_y = (screen_size.height() - (self.view_size[1]*self.animation_size_mult)) / 2 
            start_top_left = QtCore.QPoint(min_x, min_y)
            start_rect = QtCore.QRect(start_top_left, QtCore.QSize((self.view_size[0]*self.animation_size_mult), (self.view_size[1]*self.animation_size_mult)))
            end_top_left = QtCore.QPoint(max_x, max_y)
            end_rect = QtCore.QRect(end_top_left, QtCore.QSize(self.view_size[0], self.view_size[1]))
            
            animation = QtCore.QPropertyAnimation(self, b"geometry")
            animation.setDuration(self.animation_duration) 
            animation.setEasingCurve(QtCore.QEasingCurve.OutCubic)
            animation.setStartValue(start_rect)
            animation.setEndValue(end_rect)
            animation.valueChanged.connect(lambda :self.setImage())
            self.show()
            animation.start()
        super(ImageDialog, self).exec_()

    def previous_image(self):
        if self.all_paths and self.path not in self.all_paths:
            return
        all_paths = list(self.all_paths.keys())
        prev_index = all_paths.index(self.path) - 1
        if prev_index < 0:
            prev_index = len(all_paths) - 1
        self.path = all_paths[prev_index]
        self.setImage()

    def next_image(self):
        if self.all_paths and self.path not in self.all_paths:
            return
        all_paths = list(self.all_paths.keys())
        next_index = all_paths.index(self.path) + 1
        if next_index > len(all_paths) -1:
            next_index = 0
        self.path = all_paths[next_index]
        self.setImage()

    def setImage(self):
        if self.all_paths and self.path in self.all_paths:
            text = self.all_paths[self.path]
        else:
            text = os.path.basename(self.path)

        self.file_label.setText(text)
        self.view_widget.setImage(self.path)