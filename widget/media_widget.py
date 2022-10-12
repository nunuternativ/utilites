# coding=utf-8
import os
import re
import subprocess
import sys
import time
from collections import OrderedDict
import gc
import numpy as np
import cv2
from threading import Thread
from PIL import Image
from Qt import QtWidgets, QtCore, QtGui

# import rf_config as config
# from rf_utils import icon

VIDEO_EXT = ['.mov', '.mp4']
IMAGE_EXT = ['.png', '.jpeg', '.jpg', '.tiff', '.tif']
EXR_EXT = '.exr'
PLAYABLE_MEDIA = VIDEO_EXT + IMAGE_EXT + [EXR_EXT]
_VERSION_ = '2.5'
# RV_PATH = config.Software.rv
try:
    MODULEDIR = sys._MEIPASS.replace('\\', '/')
except Exception:
    MODULEDIR = os.path.dirname(sys.modules[__name__].__file__).replace('\\', '/')
LOADINGICON = "{}/icons/gif/loading60.gif".format(MODULEDIR)
PLAYICON = "{}/icons/etc/play_button.png".format(MODULEDIR)


def convert_to_list(inputs, path=True):
    """

    Args:
        input (str,list):
        path (bool):

    Returns:

    """
    # Check sequence sign
    # detect and expand "filename.[100-200].ext" to list of filepath
    pattern = ("(\[[0-9]{1,}-[0-9]{1,}\])")

    if type(inputs) == type(str()):
        inputs = [inputs]

    if not path:
        return inputs
    else:
        result = []
        for input_i in inputs:
            if not input_i:
                continue
            r = re.findall(pattern, input_i)
            if r:
                framenum = r[0][1:-1].split('-')
                start = int(framenum[0])
                end = int(framenum[1])
                result += [input_i.replace(r[0], str("%04d" % i)) for i in range(start, end + 1)]
            else:
                result += [input_i]

    return result

def load_videos(video_file):
    capture = cv2.VideoCapture(video_file)

    read_flag, frame = capture.read()
    vid_frames = []
    i = 1

    while (read_flag):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        vid_frames.append(frame)
        read_flag, frame = capture.read()
        i += 1
    vid_frames = np.asarray(vid_frames, dtype='uint8')[:-1]

    capture.release()
    del capture
    gc.collect()
    return vid_frames

def load_images(image_file):
    capture = cv2.imread(image_file, cv2.IMREAD_UNCHANGED)
    # height, width, channels = capture.shape
    frame = cv2.cvtColor(capture, cv2.COLOR_BGR2RGB)

    return frame

# def load_EXR(image_file):
#     import OpenEXR
#     import Imath
#     def adjust_gamma(image, gamma=1.0):
#         # build a lookup table mapping the pixel values [0, 255] to
#         # their adjusted gamma values
#         invGamma = 1.0 / gamma
#         table = np.array([((i / 255.0) ** invGamma) * 255
#                           for i in np.arange(0, 256)]).astype(np.uint8)

#         # apply gamma correction using the lookup table
#         return cv2.LUT(image, table)

#     channels = {}

#     pt = Imath.PixelType(Imath.PixelType.FLOAT)
#     exr = OpenEXR.InputFile(image_file)
#     dw = exr.header()['dataWindow']
#     size = ((dw.max.x - dw.min.x + 1), (dw.max.y - dw.min.y + 1))

#     # # RED
#     # redstr = exr.channel('R', pt)
#     # red = np.fromstring(redstr, dtype=np.float32)
#     # red.shape = (size[1], size[0])  # Numpy arrays are (row, col)

#     # # Green
#     # greenstr = exr.channel('G', pt)
#     # green = np.fromstring(greenstr, dtype=np.float32)
#     # green.shape = (size[1], size[0])  # Numpy arrays are (row, col)

#     # # RED
#     # bluestr = exr.channel('B', pt)
#     # blue = np.fromstring(bluestr, dtype=np.float32)
#     # blue.shape = (size[1], size[0])  # Numpy arrays are (row, col)

#     (redstr, greenstr, bluestr) = exr.channels("RGB", pt)
#     red = np.fromstring(redstr, dtype=np.float32)
#     red.shape = (size[1], size[0])

#     green = np.fromstring(greenstr, dtype=np.float32)
#     green.shape = (size[1], size[0])

#     blue = np.fromstring(bluestr, dtype=np.float32)
#     blue.shape = (size[1], size[0])

#     data = np.dstack((red, green, blue)) * 255.0  # Use 255.9 instead of 256 because of hot pixel in image
#     data = data.astype(np.uint8)
#     data = adjust_gamma(data, 2.2)
#     return (data, channels)

def generateGrid(w, h, sq):
    color1 = (0xFF, 0xFF, 0xFF)
    color2 = (0x95, 0x95, 0x95)
    img = np.zeros((w, h, 3), dtype=np.uint8)
    c = np.fromfunction(lambda x, y: ((x // sq) + (y // sq)) % 2, (w, h))
    img[c == 0] = color1
    img[c == 1] = color2
    return img

def findCenter(img):
    # gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # th, threshed = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    #
    # _, cnts, hierarchy = cv2.findContours(threshed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # M = cv2.moments(cnts[0])
    #
    # cX = int(M["m10"] / M["m00"])
    # cY = int(M["m01"] / M["m00"])
    cX = img.shape[0] / 2
    cY = img.shape[1] / 2

    #  =========================

    return (cX, cY)

def generateThumbnailImage(image):
    """

    Args:
        image (object): numpy image object

    Returns: numpy image object

    """

    class point_2D(object):

        def __init__(self, x=0.0, y=0.0):
            self.x = x
            self.y = y

        @property
        def coor(self):
            return (self.x, self.y)

        @property
        def rcoor(self):
            return (int(round(self.x)), int(round(self.y)))

        def __str__(self):
            return str([self.x, self.y])

    def rotatepoint(cx, cy, angle, point):
        # cos(r)(px-cx) + (py-cy) sin(r)+cx
        # -sin(r)(a-m) + cos(r)(b-n)+n

        result = point_2D()
        r = ((0 - angle) * (22.0 / 7.0)) / 180.0
        s = np.sin(r)
        c = np.cos(r)

        # Translate to origin
        result.x = point.x - cx
        result.y = point.y - cy

        # rotate point
        xnew = (c * result.x) - (result.y * s)
        ynew = (-s * result.x) + (result.y * c)

        # Translate back
        result.x = xnew + cx
        result.y = ynew + cy

        return result

    image = image.copy()

    origin = findCenter(image)

    height, width = image.shape[:2]
    circleRadius = int((np.minimum(height, width) / 2) * 0.7)
    triangleRadius = circleRadius * 0.8

    # Create circle
    # a = point_2D()
    # b = point_2D()

    # cv2.circle(img=image, center=o.rcoor, radius=10, color=(0, 0, 0), thickness=-1)
    # cv2.circle(img=image, center=a.rcoor, radius=10, color=(255, 0, 0), thickness=-1)
    # cv2.circle(img=image, center=b.rcoor, radius=10, color=(255, 255, 0), thickness=-1)
    # cv2.circle(img=image, center=c.rcoor, radius=10, color=(0, 150, 255), thickness=-1)

    button_image = np.zeros((circleRadius * 2, circleRadius * 2, 4), dtype=np.uint8)
    triangle_image = button_image.copy()

    _org = findCenter(button_image)
    o = point_2D()
    o.x = _org[0]
    o.y = _org[1]

    c = point_2D()
    c.x = round(o.x + triangleRadius)
    c.y = round(o.y)

    a = rotatepoint(o.x, o.y, 120, c)
    b = rotatepoint(o.x, o.y, 240, c)

    triangle_cnt = np.array([a.rcoor, b.rcoor, c.rcoor])
    cv2.circle(img=button_image, center=findCenter(button_image), radius=circleRadius, color=(255, 255, 255),
               thickness=-1)
    cv2.drawContours(triangle_image, [triangle_cnt], 0, (255, 255, 255), -1)

    button_image = button_image - triangle_image

    offset_x = origin[1] - (button_image.shape[1] / 2)
    offset_y = origin[0] - (button_image.shape[0] / 2)
    image[offset_x:offset_x + button_image.shape[0], offset_y:offset_y + button_image.shape[1], :3] -= button_image[:,
                                                                                                       :, :3]
    cv2.imshow(';', image)
    cv2.waitKey()

    return image
    
class ClickableLabel(QtWidgets.QLabel):
    playStopMedia = QtCore.Signal()

    def __init__(self, parent=None):
        super(ClickableLabel, self).__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)

    # def mouseDoubleClickEvent(self, *args, **kwargs):
    #     if os.path.splitext(self.currentMedia.path)[-1] in PLAYABLE_MEDIA:
    #         subprocess.Popen([RV_PATH, self.currentMedia.path])

    def mousePressEvent(self, event):
        if event.buttons() == QtCore.Qt.RightButton:
            pass
        elif event.buttons() == QtCore.Qt.LeftButton:
            self.playStopMedia.emit()

    @property
    def currentMedia(self):
        return self.parentWidget().currentMedia

    @property
    def videoFile(self):
        return self.parentWidget().videoFile

class MediaModel(object):

    def __init__(self,
                 name='Null',
                 path='',
                 type='Null',
                 images=[],
                 layers={},
                 width=0,
                 height=0):
        super(MediaModel, self).__init__()

        self.name = name
        self.path = path
        self.type = type
        self.width = width
        self.height = height

        self.ext = os.path.splitext(path)[-1] if path else ''
        images = convert_to_list(images, path=False)
        self.images = images
        self.layers = layers
        self.length = len(images)

    def loadlayers(self, layername):
        return self.layers[layername] if len(self.layers[layername]) else self.images[0]

    def resize(self, factor):
        resized_images = []
        curr_width = self.images[0].shape[1]
        curr_height = self.images[0].shape[0]
        target_size = (int(curr_width*factor), int(curr_height*factor))
        for img in self.images:
            result = cv2.resize(img, dsize=target_size, interpolation=cv2.INTER_CUBIC)
            resized_images.append(result)
        self.images = np.asarray(resized_images, dtype='uint8')
        self.width = self.images[0].shape[1]
        self.height = self.images[0].shape[0]

    def __getitem__(self, item):
        return self.images[item]

    def __len__(self):
        return self.length

    def __eq__(self, other):
        if hasattr(other, 'path'):
            if other.path == self.path:
                return True
        return False

class MediaPlayThread(QtCore.QThread):
    CONTINUE = QtCore.Signal()
    LOOP = QtCore.Signal()

    def __init__(self, length, startframe=0, fps=24, parent=None):
        super(MediaPlayThread, self).__init__(parent=parent)
        self.fps = float(fps)
        self.startframe = int(startframe)
        self.length = int(length)
        self.threadParent = self.parent()
        self._stop = False

    # def __del__(self):
    #     self.wait()

    def stop(self):
        self._stop = True

    def run(self):
        while self.startframe <= self.length and self.threadParent.isVisible():
            if self._stop:
                break
            # print(self.startframe)
            time.sleep(1 / self.fps)
            self.CONTINUE.emit()
            self.startframe += 1

            if self.startframe >= self.length:
                self.startframe = 0
                self.LOOP.emit()

        self.exit()
        return 0

class MediaThread(QtCore.QThread):
    loadFinished = QtCore.Signal(list)
    frameLoaded = QtCore.Signal(list)
    percentLoaded = QtCore.Signal(float)
    __stop = False

    def __init__(self, filenames=[], metadata=[], single_video_frame_at=None, vide_quality=1.0, parent=None):
        super(MediaThread, self).__init__(parent=parent)
        self.filenames = filenames
        self.metadata = metadata if metadata and len(metadata)==len(self.filenames) else [None]*len(self.filenames)  # attached data
        self.images = []
        self.capture = None
        self._stop = False
        self.single_video_frame_at = single_video_frame_at  # value between 0.0 - 1.0 is the range from start to end of the video
        self.vide_quality = vide_quality
        self._fullVideoLoaded = False

    # def __del__(self):
    #     del self.images
    #     gc.collect()
    #     # self.wait()
    #     return 0

    def stop(self):
        self._stop = True
        # self.capture.release()
        return 0

    def load_videos(self, video_file):
        self.capture = cv2.VideoCapture(video_file)
        read_flag, frame = self.capture.read()
        vid_frames = []
        i = 0

        if self.single_video_frame_at == None:
            while read_flag:
                if self._stop:
                    # print('Video loading interrupted.\n')
                    break
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                vid_frames.append(frame)
                read_flag, frame = self.capture.read()
                i += 1
            self._fullVideoLoaded = True
        else:  # load specific frame
            try:
                total = int(self.capture.get(cv2.CAP_PROP_FRAME_COUNT))
                poster_index = int(total * self.single_video_frame_at)
                for f in range(total):
                    if self._stop:
                        # print('Video loading interrupted.\n')
                        break
                    success = self.capture.grab()
                    if not success:
                        break
                    if f == poster_index:# 
                        read_flag, frame = self.capture.retrieve()
                        break
            except Exception as e:
                print('faild to get poster frame, using 0.')

            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            vid_frames.append(frame)
            self._fullVideoLoaded = False
                
        if self._stop:
            vid_frames = np.asarray([], dtype='uint8')
        else:
            # rescale to quality
            if self.vide_quality < 1.0:
                resized_images = []
                curr_width = vid_frames[0].shape[1]
                curr_height = vid_frames[0].shape[0]
                target_size = (int(curr_width*self.vide_quality), int(curr_height*self.vide_quality))
                for img in vid_frames:
                    result = cv2.resize(img, dsize=target_size, interpolation=cv2.INTER_CUBIC)
                    resized_images.append(result)
                vid_frames = resized_images
            vid_frames = np.asarray(vid_frames, dtype='uint8')

        self.capture.release()
        gc.collect()

        return vid_frames

    def run(self):
        if not self.filenames:
            return 0

        num_files = len(self.filenames)
        for i, each in enumerate(self.filenames):
            # print('load thread running')
            each_name, each_ext = os.path.splitext(each)
            basename = os.path.basename(each)

            if not os.path.exists(each):
                print("Missing file : {}\n".format(each))
                continue

            if each_ext.lower() in VIDEO_EXT:
                data = self.load_videos(each)
                if not data.any():
                    continue
                # print(len(data))
                image = MediaModel(name=basename,
                                   path=each,
                                   type='video',
                                   images=data,
                                   width=data[0].shape[1],
                                   height=data[0].shape[0])
                self.images.append(image)

            elif each_ext.lower() in IMAGE_EXT:
                data = load_images(each)
                image = MediaModel(name=basename,
                                   path=each,
                                   type='image',
                                   images=[data],
                                   width=data.shape[1],
                                   height=data.shape[0])

                self.images.append(image)

            # elif each_ext.lower() == EXR_EXT:
            #     data, channels = load_EXR(each)
            #     image = MediaModel(name=basename,
            #                        path=each,
            #                        type='exr',
            #                        images=[data],
            #                        layers=channels,
            #                        width=data.shape[1],
            #                        height=data.shape[0])
            #     self.images.append(image)

            else:
                print("Load Error : {}\n".format(each_ext))
                return 0

            if self._stop:
                # print("Threading interrupted.\n")
                break
            else:
                # emit current image
                self.frameLoaded.emit([image, self.metadata[i]])
                # emit percentage
                percent = round((float(i+1)/num_files) * 100.0, 2)
                self.percentLoaded.emit(percent)

        if self._stop:
            self.images = []
            # self._stop = False
        self.loadFinished.emit([self.images, self.metadata])
        # print('load thread finished')
        self.exit()
        return 0

class PreviewMedia(QtWidgets.QWidget):
    _currentMedia = []
    currentMediaStart = 0
    currentMediaFrame = -1
    currentMedialength = 0
    currentFrameData = None
    globalFrameRange = 0
    layer = 'overall'
    imap = QtGui.QImage()
    images = []
    displayImages = []
    loadMediaFinished = True
    currentGlobalFrame = -1
    currentFrameIndex = 0
    nomedia_text = "No active media."
    pause_text = "Click on the image to PLAY."
    play_text = "Playing media, click to PAUSE."

    _playThread = None
    playing = False

    mediaLoading = QtCore.Signal()
    mediaLoadFinished = QtCore.Signal()

    def __init__(self, parent=None, fps=24):
        super(PreviewMedia, self).__init__(parent)

        self.pos = self.pos()
        self.fps = fps
        self.previousLayer = self.layer
        self.ipixmap = QtGui.QPixmap()
        self.currentMedia = MediaModel()
        self.mediaThread = None
        self.movie = None

        # set to value between 0-1 to load single frame at first load, user have to hit Play to load the rest
        self.poster_frame_weight = None  
        self.continue_load_media = None  # store unfinished load path

        mainLayout = QtWidgets.QVBoxLayout()
        mediaLayout = QtWidgets.QHBoxLayout()
        self.layerListWidget = QtWidgets.QListWidget(self)
        self.mediaplayer = ClickableLabel(self)
        self.informationText = QtWidgets.QLabel(self)
        controller_layout = QtWidgets.QHBoxLayout()
        self.controller_play = QtWidgets.QLabel(self)
        self.information2Text = QtWidgets.QLabel(self)

        mediaLayout.addWidget(self.mediaplayer)
        mediaLayout.addWidget(self.layerListWidget)
        mainLayout.addLayout(mediaLayout)
        mainLayout.addWidget(self.informationText)
        mainLayout.addLayout(controller_layout)
        controller_layout.addWidget(self.controller_play)
        mainLayout.addWidget(self.information2Text)

        self.setLayout(mainLayout)

        self.mediaplayer.setMouseTracking(True)
        self.setMouseTracking(True)
        self.layerListWidget.setMouseTracking(True)

        # Decoration
        mediaLayout.setStretch(0, 1)
        self.mediaplayer.setAlignment(QtCore.Qt.AlignCenter)
        self.mediaplayer.setAlignment(QtCore.Qt.AlignHCenter)
        self.layerListWidget.setVisible(False)
        self.informationText.setText("Frame: N/A")
        self.informationText.setVisible(True)
        mainLayout.setStretch(0, 1)

        self.informationText.setAlignment(QtCore.Qt.AlignCenter)
        self.informationText.setAlignment(QtCore.Qt.AlignHCenter)

        controller_layout.setAlignment(QtCore.Qt.AlignCenter)
        controller_layout.setAlignment(QtCore.Qt.AlignHCenter)

        self.information2Text.setText("FPS: {} | Resolution : {} x {}".format(self.fps, 0, 0))
        self.information2Text.setAlignment(QtCore.Qt.AlignCenter)
        self.information2Text.setAlignment(QtCore.Qt.AlignHCenter)

        self.controller_play.setVisible(True)
        self.controller_play.setText(self.nomedia_text)

        self.layerListWidget.clicked.connect(self.layerDropdown_onChanged)
        self.mediaplayer.playStopMedia.connect(self.play_onCLicked)

    def loadMedia(self, mediapaths):
        if self.mediaThread != None and self.mediaThread.isRunning():
            self.mediaThread.stop()
            self.mediaThread.exit()
            self.mediaThread.wait()

        # Not load any media when this widget is closed.
        if not self.isVisible():
            return False

        # Stop playing when load new media
        if self.playing:
            self.stop_playMedia()

        # If path not List
        mediapaths = convert_to_list(mediapaths)
        # Check if media already loaded.
        if sorted(self._currentMedia) != sorted(mediapaths):
            self.layerListWidget.setVisible(False)
            self._loadMedia(mediapaths)
        else:
            self.controller_play.setVisible(True)
            return 0

    def _loadMedia(self, filenames):
        self.loadMediaFinished = False
        self._currentMedia = filenames

        self.controller_play.setText("Loading media, please wait...")
        self.mediaLoading.emit()
        self.informationText.setText("Frame: N/A")
        self.setLoading(True)

        filenames = convert_to_list(filenames)

        # Reset list every time when load new media.
        self.images = []
        self.layer = 'overall'
        self.startAnim = False
        self.globalFrameRange = 0

        self.mediaThread = MediaThread(filenames, single_video_frame_at=self.poster_frame_weight)
        self.mediaThread.start()

        self.mediaThread.frameLoaded.connect(self.mediaThread_onLoadFrameFinished)
        self.mediaThread.percentLoaded.connect(self.mediaThread_updateLoadProgress)
        self.mediaThread.loadFinished.connect(self.mediaThread_onLoadMediaFinished)

        self.controller_play.setVisible(True)

        if self.poster_frame_weight != None:
            self.continue_load_media = filenames

        return 0

    def _continueLoadMedia(self):
        self.loadMediaFinished = False
        self._currentMedia = self.continue_load_media

        self.controller_play.setText("Loading media, please wait...")
        self.mediaLoading.emit()
        self.informationText.setText("Frame: N/A")
        self.setLoading(True)

        self.continue_load_media = convert_to_list(self.continue_load_media)

        # Reset list every time when load new media.
        self.images = []
        self.layer = 'overall'
        self.startAnim = False
        self.globalFrameRange = 0

        self.mediaThread = MediaThread(self.continue_load_media, single_video_frame_at=None)
        self.mediaThread.start()

        self.mediaThread.frameLoaded.connect(self.mediaThread_onLoadFrameFinished)
        self.mediaThread.percentLoaded.connect(self.mediaThread_updateLoadProgress)
        self.mediaThread.loadFinished.connect(self.mediaThread_onContinueLoadMediaFinished)

        self.controller_play.setVisible(True)
        self.continue_load_media = None

        return 0

    def mediaThread_onLoadFrameFinished(self, medialist):
        image, data = medialist
        self.images += [image]
        for each in self.images:
            # print("Add : " + str(len(each.images)))
            self.globalFrameRange += len(each.images)

        if len(self.images) == 1:
            self.loadFrame(0)
            self.updateInfo()

    def mediaThread_updateLoadProgress(self, percent):
        self.controller_play.setText("Loading {}%...".format(percent))

    def mediaThread_onLoadMediaFinished(self, medialist):
        if medialist:
            # self.mediaThread = None
            self.images = medialist[0]
            self.globalFrameRange = 0
            for each in self.images:
                self.globalFrameRange += len(each.images)

            if self.currentMedia.ext.lower() in PLAYABLE_MEDIA:
                self.controller_play.setVisible(True)
            else:
                self.controller_play.setVisible(False)

            self.controller_play.setText(self.pause_text)
            self.loadMediaFinished = True
            self.loadFrame(0)
            self.updateInfo()
            self.mediaLoadFinished.emit()

    def mediaThread_onContinueLoadMediaFinished(self, medialist):
        if medialist:
            self.mediaThread_onLoadMediaFinished(medialist)
            self.mediaThread._fullVideoLoaded = True
            self.play_onCLicked()
            self.mediaLoadFinished.emit()

    def clear_view(self):
        # self.mediaThread = None
        self.images = []
        self._currentMedia = []
        self.globalFrameRange = 0
        self.controller_play.setText(self.nomedia_text)
        self.loadMediaFinished = True
        self.currentMedia = MediaModel()
        self.informationText.setText("Frame: N/A")
        # self.updateInfo()

    def setLoading(self, start): 
        self.mediaplayer.setText('Loading...')
        if not self.movie:
            self.movie = QtGui.QMovie(LOADINGICON)
        self.mediaplayer.setMovie(self.movie)
        self.movie.start()

    def loadFrame(self, percent=None, nextframe=False, firstframe=False):
        """

        Args:
            percent (float): value between 0.0 - 1.0

        Returns (None): 0 if Fail, Otherwise return None

        """

        if percent == None and not nextframe and not firstframe:
            return 0

        # Calculate frame
        perframe = 1.0 / self.globalFrameRange if self.globalFrameRange else 0
        current_percent = self.currentGlobalFrame * perframe
        if nextframe:
            # Generate next frame's percent
            percent = current_percent + perframe

        elif firstframe:
            # Generate next frame's percent
            percent = 0

        # == Which media will play ==
        selectedMedia = int((percent * len(self.images)))
        self.currentFrameIndex = selectedMedia
        # print(self.globalFrameRange, percent)
        self.currentGlobalFrame = round(self.globalFrameRange * percent)  # From whole frame
        # == Which frame of media will play ==
        try:
            self.currentMedialength = float(self.images[selectedMedia].length)
        except IndexError:
            return 0

        # Media area from the whole length, represent in float (0.0-1.0)
        currentMediaArea = float(1.0 / len(self.images))
        self.currentMediaStart = (currentMediaArea * selectedMedia) * self.globalFrameRange
        currentMedialength2 = currentMediaArea * self.globalFrameRange
        mediaCurrentFrame = int(
            (int(self.currentGlobalFrame - self.currentMediaStart) / currentMedialength2) * self.currentMedialength)
        currentMedia = self.images[selectedMedia]
        if currentMedia == self.currentMedia and mediaCurrentFrame == self.currentMediaFrame and self.previousLayer == self.layer:
            return 0
        else:
            self.currentMediaFrame = mediaCurrentFrame
            self.currentMedia = currentMedia

        if self.currentMediaFrame >= self.currentMedialength:
            self.currentMediaFrame = 0

        try:
            # Set currentMedia
            if self.layer != 'overall':
                if self.previousLayer == self.layer:
                    return 0
                self.currentFrameData = self.currentMedia.loadlayers(layername=self.layer)
                self.previousLayer = self.layer
            else:

                self.currentFrameData = self.currentMedia[self.currentMediaFrame]
                self.previousLayer = self.layer

            height, width, channel = self.currentFrameData.shape

            # Load media from path instead, if media is normal image
            if self.currentMedia.ext.lower() in IMAGE_EXT:
                self.imap = self.currentMedia.path
            else:
                self.imap = QtGui.QImage(self.currentFrameData.data, width, height, width * 3, QtGui.QImage.Format_RGB888)

            self.ipixmap = QtGui.QPixmap(self.imap).scaled(self.mediaplayer.size(), QtCore.Qt.KeepAspectRatio)
            self.mediaplayer.setPixmap(self.ipixmap)
            self.updateInfo()
        except IndexError as e:
            print("Could not load frame : {}".format(self.currentMediaFrame))

    def updateInfo(self):
        if os.path.splitext(self.currentMedia.path)[-1].lower() in VIDEO_EXT:
            if self.currentMedia.length >= 2:
                self.informationText.setText("Frame: {}/{}".format(self.currentMediaFrame + 1, self.currentMedia.length))
            else:
                self.informationText.setText("Frame: N/A")
        else:
            frame = self.currentFrameIndex+1
            all_frame = int(self.globalFrameRange)
            if self.loadMediaFinished:
                self.informationText.setText("Frame: {}/{}".format(frame, all_frame))
            else:
                self.informationText.setText("Frame: N/A")

        self.information2Text.setText(
            "FPS : {} | Resolution : {} x {}".format(self.fps, self.currentMedia.width, self.currentMedia.height))

    def layerDropdown_onChanged(self):
        layername = self.layerListWidget.currentItem().text()
        self.showLayer(layername)
        self.loadFrame(0)

    def play_onCLicked(self):
        if self.mediaThread:
            # if it's a video and not all the frames are loaded, continue load
            if not self.mediaThread._fullVideoLoaded and self.currentMedia.ext.lower() in VIDEO_EXT:
                self._continueLoadMedia()
            else: # else, play
                if self.loadMediaFinished and self.playing == False and self.currentMedia.ext.lower() in PLAYABLE_MEDIA:
                    self.start_playMedia()
                else:
                    self.stop_playMedia()

    def start_playMedia(self):
        self.playing = True
        self.controller_play.setText(self.play_text)

        if os.path.splitext(self.currentMedia.path)[-1].lower() in VIDEO_EXT:
            startframe = self.currentMediaFrame
        else:
            startframe = self.currentFrameIndex

        self._playThread = MediaPlayThread(startframe=startframe, fps=self.fps, length=self.globalFrameRange+1, parent=self)
        self._playThread.CONTINUE.connect(lambda: self.loadFrame(nextframe=True))
        self._playThread.LOOP.connect(lambda: self.loadFrame(firstframe=True))
        self._playThread.start()

    def stop_playMedia(self):
        if hasattr(self._playThread, 'finished'):
            self._playThread.terminate()
            self._playThread = None
            self.playing = False
            self.controller_play.setText(self.pause_text)

    def resizeEvent(self, event):
        self.layerListWidget.setMaximumWidth(0.2 * self.width())
        if self.ipixmap.isNull():
            return 0

        try:
            self.ipixmap = QtGui.QPixmap(self.imap).scaled(self.mediaplayer.size(), QtCore.Qt.KeepAspectRatio)
        except Exception as e:
            pass

        self.mediaplayer.setPixmap(self.ipixmap)

        self.setMinimumSize(QtCore.QSize(100, 100))
        # super(PreviewMedia, self).resizeEvent(event)

    def mouseMoveEvent(self, *args, **kwargs):
        if not self.playing and self.loadMediaFinished and self.images and self.mediaThread and self.mediaThread._fullVideoLoaded: 
            # Mouse pos[x]
            mouse_x = self.cursor().pos().x()
            start_x = self.mapToGlobal(self.rect().topLeft()).x()
            end_x = self.width()
            playPercent = ((mouse_x - start_x) / float(end_x))
            self.loadFrame(playPercent)

    def showLayerListWidget(self):
        # Show LayerListWidget
        self.layerListWidget.clear()
        if self.currentMedia.layers:
            self.layerListWidget.setVisible(True)
            self.layerListWidget.addItems(self.currentMedia.layers.keys())
        else:
            self.layerListWidget.setVisible(False)

    def enterEvent(self, *args, **kwargs):
        self.startAnim = True

    def leaveEvent(self, *args, **kwargs):
        self.startAnim = False

    def __newimagesize(self, w, h):
        new_w = self.width() - (self.width() * 0.2)
        new_h = (h * new_w) / w

        if h > self.mediaplayer.height() * 0.3:
            new_h = self.mediaplayer.height() - (self.mediaplayer.height() * 0.3)
            new_w = (w * new_h) / h

        return ((new_w, new_h))

    def showLayer(self, layername):
        self.layer = layername

class PipelinePreviewMedia(PreviewMedia): 
    def __init__(self, parent=None):
        super(PipelinePreviewMedia, self).__init__(parent)

    def view(self, project, entityName, step, process): 
        from rf_utils.context import context_info 
        context = context_info.Context()
        context.update(project=project, entityType='scene', entity=entityName, step=step, process=process)
        scene = context_info.ContextPathInfo(context=context)
        output = scene.path.name().abs_path()
        mov = self.find_latest_playblast(output)
        if mov: 
            print('Playing "{}" ...'.format(mov[0]))
            self.mediaplayer.clear()
            self.loadMedia([mov[0]])

    def find_latest_playblast(self, path, latest=True): 
        from rf_utils import file_utils
        movExts = ['.mov']
        latests = []
        steps = file_utils.list_folder(path)

        for step in steps: 
            stepPath = '{}/{}'.format(path, step)
            processes = file_utils.list_folder(stepPath)

            for process in processes: 
                mediaPath = '{}/{}/output'.format(stepPath, process)
                if os.path.exists(mediaPath): 
                    files = file_utils.list_file(mediaPath)

                    if files: 
                        if any(os.path.splitext(a)[-1] in movExts for a in files): 
                            if latest: 
                                versions = [re.findall(r'v\d{3}', a)[0] for a in files if re.findall(r'v\d{3}', a)]
                                highest = sorted(versions)[-1]
                                pickFiles = [a for a in files if highest in a]
                                pickFile = pickFiles[0] if pickFiles else files[-1]
                                mov = '{}/{}'.format(mediaPath, pickFile)
                                latests.append(mov)
                            else: 
                                latests += ['{}/{}'.format(mediaPath, a) for a in files if os.path.splitext(a)[-1] in movExts]

        return latests

class testWindow(QtWidgets.QMainWindow):

    def __init__(self, parent=None):
        super(testWindow, self).__init__(parent)

        self.setGeometry(300, 300, 250, 300)

        self.initUI()
        self.initConnect()

    def initUI(self):
        self.setCentralWidget(QtWidgets.QWidget())
        self.mainLayout = QtWidgets.QVBoxLayout()

        self.thumbnail = PreviewMedia(self.centralWidget())
        # self.thumbnail.poster_frame_weight = 0.2
        self.buttonLayout = QtWidgets.QHBoxLayout()
        self.loadMOVButton = QtWidgets.QPushButton()
        self.loadMOVButton.setText("Load MOV")
        self.loadJpegButton = QtWidgets.QPushButton()
        self.loadJpegButton.setText("Load JPEG")
        self.loadPngButton = QtWidgets.QPushButton()
        self.loadPngButton.setText("Load PNG")
        self.loadTiffButton = QtWidgets.QPushButton()
        self.loadTiffButton.setText("Load TIFF")
        self.loadExrButton = QtWidgets.QPushButton()
        self.loadExrButton.setText("Load EXR")
        self.buttonLayout.addWidget(self.loadMOVButton)
        self.buttonLayout.addWidget(self.loadJpegButton)
        self.buttonLayout.addWidget(self.loadPngButton)
        self.buttonLayout.addWidget(self.loadTiffButton)
        self.buttonLayout.addWidget(self.loadExrButton)

        self.buttonLayout.setStretch(0, 1)
        self.buttonLayout.setStretch(1, 1)
        self.buttonLayout.setStretch(2, 1)
        self.buttonLayout.setStretch(3, 1)
        self.buttonLayout.setStretch(4, 1)

        self.mainLayout.addWidget(self.thumbnail)
        self.mainLayout.addLayout(self.buttonLayout)

        self.centralWidget().setLayout(self.mainLayout)

    def initConnect(self):
        self.loadMOVButton.clicked.connect(self.loadMOVButton_onClicked)
        self.loadJpegButton.clicked.connect(self.loadJpegButton_onClicked)
        self.loadPngButton.clicked.connect(self.loadPngButton_onClicked)
        self.loadTiffButton.clicked.connect(self.loadTIFFButton_onClicked)
        self.loadExrButton.clicked.connect(self.loadExrButton_onClicked)

    def loadMOVButton_onClicked(self):
        self.thumbnail.loadMedia("P:/Hanuman/scene/publ/act1/hnm_act1_q0030a_s0010/edit/animatic/hero/outputMedia/hnm_act1_q0030a_s0010_edit_animatic.hero.mov")

    def loadJpegButton_onClicked(self):
        self.thumbnail.loadMedia('P:/DarkHorse/Daily/texture/2020_07_16/bedroom_mtl_main_md.v000_001.[0001-0006].jpg')

    def loadPngButton_onClicked(self):
        self.thumbnail.loadMedia('P:/DarkHorse/Daily/texture/2019_07_09/berserkerLeader_mtl_main_md.v003.[0001-0005].png')

    def loadTIFFButton_onClicked(self):
        self.thumbnail.loadMedia('P:/DarkHorse/Daily/sim/2020_01_22/Nook.q0010_s0030.jaxBerserker_sim_clothWRP_md.0001/jaxBerserker_001.[1001-1046].tif')

    def loadExrButton_onClicked(self):
        self.thumbnail.loadMedia('P:/DarkHorse/scene/publ/t1/dkh_t1_q0010_s0115/comp/main/hero/output/exr/dkh_t1_q0010_s0115_comp_main.hero.[1001-1010].exr')

class MediaGridItem(QtWidgets.QListWidgetItem):
    def __init__(self, images=[], overlay_images=[], overlay_texts=[], parent=None):
        super(MediaGridItem, self).__init__(parent)
        self._isLoaded = False
        self._isLoading = False

        self.pixmaps = []
        self.overlay_pixmaps = self.cache_overlays(overlay_images)
        self.overlay_texts = overlay_texts
        self.stillPixmap = None
        self.current_frame = 0

        self.loadMovie = QtGui.QMovie(LOADINGICON)
        self.playpixmap = QtGui.QPixmap(PLAYICON)

        self.type = None
        self.len = None
        self.path = None

        self.cache_images(images=images)

    def cache_overlays(self, overlay_images):
        overlay_pixmaps = []
        for path, alignment, size_multiplier in overlay_images:
            pixmap = QtGui.QPixmap(path)
            overlay_pixmaps.append((pixmap, alignment, size_multiplier))
        return overlay_pixmaps

    def cache_images(self, images):
        self.clear_pixmaps()
        if images:
            pixmaps = []
            # set image frame
            parent_size = self.listWidget().item_size
            blank_img = QtGui.QImage(parent_size.width(), parent_size.height(), QtGui.QImage.Format_RGB888) 
            blank_img.fill(QtGui.qRgb(0, 0, 0))
            painter = QtGui.QPainter()
            for i in range(images.length):
                qimg = QtGui.QImage(images.images[i].data, images.width, images.height, images.width*3, QtGui.QImage.Format_RGB888)
                
                pixmap = QtGui.QPixmap.fromImage(qimg).scaled(parent_size, QtCore.Qt.KeepAspectRatio)
                canvas_pixmap = QtGui.QPixmap.fromImage(blank_img)
                painter.begin(canvas_pixmap)
                painter.drawPixmap((canvas_pixmap.width() - pixmap.width())*0.5, (canvas_pixmap.height()-pixmap.height())*0.5, pixmap)
                painter.end()

                # overlay images
                if self.overlay_pixmaps:
                    for overlay_pixmap, alignment, size_multiplier in self.overlay_pixmaps:
                        canvas_pixmap = self.draw_overlay_pixmap(canvas_pixmap=canvas_pixmap, 
                                                                overlay_pixmap=overlay_pixmap, 
                                                                alignment=alignment,
                                                                size_multiplier=size_multiplier)
                if self.overlay_texts:
                    for kwargs in self.overlay_texts:
                        kwargs['canvas_pixmap'] = canvas_pixmap
                        canvas_pixmap = self.draw_overlay_text(**kwargs)
                pixmaps.append(canvas_pixmap)

            # type
            self.type = str(images.type)
            self.len = len(images.images) - 1
            self.path = str(images.path)
            self.pixmaps = pixmaps

    def clear_pixmaps(self):
        del self.pixmaps
        # gc.collect()
        self.pixmaps = []
        self._isLoaded = False

    def load_frame(self, frame_num):
        # keep a try block in case the item has been deleted while listWidget is reloading
        try:
            self.set_image(self.pixmaps[frame_num])
            self.current_frame = frame_num
        except (IndexError, RuntimeError) as e:
            # print(e)
            return

    def refresh(self):
        self.load_frame(frame_num=self.current_frame)

    def percent_frame(self, percent):
        frame_at_percent = int(percent * self.len)
        # print(frame_at_percent)
        self.load_frame(frame_num=frame_at_percent)

    def next_frame(self):
        next_frame_index = self.current_frame + 1
        self.load_frame(frame_num=next_frame_index)

    def set_image(self, pixmap):
        icon = QtGui.QIcon()
        icon.addPixmap(pixmap, QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.setIcon(icon)

    def draw_overlay_pixmap(self, canvas_pixmap, overlay_pixmap, alignment='center', size_multiplier=1.0):
        canvas = canvas_pixmap.copy()
        iconSize = canvas.size()

        # resize fg pixmap
        overlay_pixmap = overlay_pixmap.scaled(iconSize*size_multiplier, QtCore.Qt.KeepAspectRatio)
        painter = QtGui.QPainter()
        painter.begin(canvas)
        pos = self.get_overlay_positions(canvas_pixmap=canvas, overlay=overlay_pixmap, alignment=alignment)
        painter.drawPixmap(pos[0], pos[1], overlay_pixmap)
        painter.end()
        return canvas

    def draw_overlay_text(self, canvas_pixmap, text, alignment='topCenter', font='Arial', size=16, color=(255, 255, 255), **kwargs):
        canvas = canvas_pixmap.copy()
        painter = QtGui.QPainter()
        painter.begin(canvas)
        if not isinstance(color, QtGui.QColor):
            color = QtGui.QColor(color[0], color[1], color[2])
        painter.setPen(color)
        painter.setFont(QtGui.QFont(font, size))
        # get text sizes
        text_matrics = QtGui.QFontMetrics(painter.font()).size(QtCore.Qt.TextSingleLine, text)
        text_size = (text_matrics.width(), text_matrics.height()*0.5)
        pos = self.get_overlay_positions(canvas_pixmap=canvas, overlay=text_size, alignment=alignment)
        painter.drawText(QtCore.QPoint(pos[0], pos[1]+text_size[1]), text)
        painter.end()
        return canvas

    def get_overlay_positions(self, canvas_pixmap, overlay, alignment='center', gap=15):
        if isinstance(overlay, QtGui.QPixmap):
            overlay_width = overlay.width()
            overlay_height = overlay.height()
        else:
            overlay_width, overlay_height = overlay

        if alignment == 'center':
            return (canvas_pixmap.width() - overlay_width)*0.5, (canvas_pixmap.height() - overlay_height)*0.5
        elif alignment == 'topLeft':
            return (gap, gap)
        elif alignment == 'topCenter':
            return ((canvas_pixmap.width() - overlay_width)*0.5, gap)
        elif alignment == 'topRight':
            return ((canvas_pixmap.width() - overlay_width)-gap, gap)
        elif alignment == 'bottomLeft':
            return (gap, (canvas_pixmap.height() - overlay_height)-gap)
        elif alignment == 'bottomCenter':
            return ((canvas_pixmap.width() - overlay_width)*0.5, (canvas_pixmap.height() - overlay_height)-gap)
        elif alignment == 'bottomRight':
            return ((canvas_pixmap.width() - overlay_width)-gap, (canvas_pixmap.height() - overlay_height)-gap)
        else:
            return (0, 0)

    def show_play_button(self):
        if self.current_frame < len(self.pixmaps):
            overlay_result = self.draw_overlay_pixmap(self.pixmaps[self.current_frame], self.playpixmap)
            self.set_image(pixmap=overlay_result)

    def hide_play_button(self):
        if self.current_frame < len(self.pixmaps):
            self.set_image(pixmap=self.pixmaps[self.current_frame])

    def overlay_movie_pixmap(self, pixmap, movie):
        movie_pixmap = movie.currentPixmap()
        canvas = pixmap.copy()
        painter = QtGui.QPainter()
        painter.begin(canvas)
        pos = self.get_overlay_positions(canvas_pixmap=canvas, overlay=movie_pixmap, alignment='center')
        painter.drawPixmap(pos[0], pos[1], movie_pixmap)
        painter.end()
        self.set_image(pixmap=canvas)

    def show_loading(self):
        # save the pixmap currently display at the time item starts loading
        self.stillPixmap = self.icon().pixmap(self.listWidget().iconSize())
        self.loadMovie.frameChanged.connect(lambda: self.overlay_movie_pixmap(self.stillPixmap, self.loadMovie))
        self.loadMovie.start()
        self._isLoading = True

    def hide_loading(self):
        if self._isLoading:
             # stop movie
            self.loadMovie.stop()

            # display the still pixmap saved before loading with current list widget icon size
            parent_size = self.listWidget().item_size
            self.stillPixmap = self.stillPixmap.scaled(parent_size, QtCore.Qt.KeepAspectRatio)
            self.set_image(pixmap=self.stillPixmap)

            self._isLoading = False

class MediaGridViewer(QtWidgets.QListWidget):
    '''
    Grid style media viewer for displaying video or image
    '''
    itemClickedUser = QtCore.Signal(dict)
    itemDoubleClicked = QtCore.Signal(MediaGridItem)
    itemExited = QtCore.Signal()
    itemCreated = QtCore.Signal(MediaGridItem)

    def __init__(self, fps=24, quality=0.20, parent=None): 
        super(MediaGridViewer, self).__init__(parent)
        # init vars
        self.fps = fps
        self.quality = quality
        self.autoplay_delay_time = 250  # delay time for autoplay after mouse hover
        self.fullload_delay_time = 750  # delay time before full load starts after mouse hover
        self.poster_frame_weight = 0.2  # weight for first frame to display

        # internal vars
        self.clickPos = QtCore.QPoint(0, 0)
        self.previewLoadThreads = []
        self.fullLoadThreads = []
        self.playThreads = []
        self.last_index = None  # the last index mouse visited
        self.scrub_item = None  # play item when middle mouse clicked
        self.delay_timer = None  # QTimer stopwatch for delay time
        # self.item_border_color = (83, 133, 166)

        # private_vars
        self._item_size = QtCore.QSize(256, 256)
        self._auto_play = False
        self._show_play_button = False
        self._clear_cache_on_hide = True

        # UI setup
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setViewMode(QtWidgets.QListView.IconMode)
        self.setMovement(QtWidgets.QListView.Static)
        self.setMouseTracking(False)
        self.viewport().installEventFilter(self)

        self.set_useage_tooltip()
        self.init_signals()

    def selectedItems(self):
        indexes = self.selectionModel().selectedIndexes()
        indexes.sort(key=lambda i: i.row())
        items = [self.itemFromIndex(index) for index in indexes]
        return items

    def stretch_items(self, mode, offset=9):
        if mode == 'horizontal':
            width = self.width() - offset
            self.setIconSize(QtCore.QSize(width, width))
        elif mode == 'vertical':
            height = self.height() - offset
            self.setIconSize(QtCore.QSize(height, height))

    def clear(self):
        self.stop_all_plays()
        self.stop_full_load()
        self.stop_preview_load()

        # need to clear all the pixmaps out of memory or the memory won't be released
        self.clear_all_pixmaps()
        super(MediaGridViewer, self).clear()

    def clear_all_pixmaps(self):
        for i in range(self.count()):
            item = self.item(i)
            item.clear_pixmaps()

    @property
    def item_size(self):
        return self._item_size

    @item_size.setter
    def item_size(self, value):
        self._item_size = QtCore.QSize(value[0], value[1])

    @property
    def auto_play(self):
        return self._auto_play

    @auto_play.setter 
    def auto_play(self, value):
        if value == True:
            self._auto_play = True
            self.setMouseTracking(True)
        else:
            self._auto_play = False
            self.setMouseTracking(False)

    @property
    def clear_cache_on_hide(self):
        return self._clear_cache_on_hide

    @clear_cache_on_hide.setter 
    def clear_cache_on_hide(self, value):
        self._clear_cache_on_hide = value

    @property
    def show_play_button(self):
        return self._show_play_button

    @show_play_button.setter
    def show_play_button(self, value):
        self._show_play_button = value

    def resizeEvent(self, event):
        self.setGridSize(self.gridSize())
        super(MediaGridViewer, self).resizeEvent(event)

    def mouseDoubleClickEvent(self, event):
        item = self.itemAt(event.pos())
        if item:
            self.itemDoubleClicked.emit(item)

    def mousePressEvent(self, event):
        buttons = event.buttons()
        mods = QtWidgets.QApplication.keyboardModifiers()
        self.clickPos = event.pos()
        item = self.itemAt(event.pos())
        if not mods:
            if buttons == QtCore.Qt.MiddleButton:
                if item:
                    if not self.auto_play:
                        is_video = item.type == 'video'
                        if self.show_play_button and is_video:
                            item.hide_play_button()
                        if is_video:
                            self.scrub_item = item
                            playPercent = self.getPlayPercent(item=item)
                            item.percent_frame(percent=playPercent)
            elif buttons == QtCore.Qt.LeftButton:
                if item:
                    if self.show_play_button:
                        self.toggle_play(item=item)
                    else:
                        super(MediaGridViewer, self).mousePressEvent(event)
                else:
                    super(MediaGridViewer, self).mousePressEvent(event)
            else:
                super(MediaGridViewer, self).mousePressEvent(event)
        elif mods == QtCore.Qt.ControlModifier:
            if item:
                if not self.show_play_button:
                    self.toggle_play(item=item)
        else:
            super(MediaGridViewer, self).mousePressEvent(event)
        event.accept()

    def toggle_play(self, item):
        self.stop_all_plays()
        self.auto_play = not(self.auto_play)
        if self.auto_play:
            self.mouse_enter(item=item)
        else:
            if self.show_play_button and item.type == 'video':
                item.show_play_button()
        self.set_useage_tooltip()

    def set_useage_tooltip(self):
        base_tooltip = 'Play: Double-Click\nScrub Frame: Middle Mouse (pause first)\nDrag: Ctrl+Middle Mouse'
        if not self.show_play_button:
            self.setToolTip(base_tooltip + '\nPlay/Pause: Ctrl+Left Mouse')
        else:
            self.setToolTip(base_tooltip + '\nPlay/Pause: Left Mouse')

    def mouseMoveEvent(self, event):
        buttons = event.buttons()
        mods = QtWidgets.QApplication.keyboardModifiers()
        if buttons & QtCore.Qt.MiddleButton and mods & QtCore.Qt.ControlModifier:
            selItems = self.selectedItems()
            itemUnder = self.itemAt(self.clickPos)
            if [i for i in selItems if i is itemUnder]:
                items = selItems
            else:
                items = selItems + [itemUnder] 
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
                pixmap = QtGui.QPixmap(item.pixmaps[item.current_frame]).scaled(64, 64, QtCore.Qt.KeepAspectRatio)
                drag.setPixmap(pixmap)
                # set cursor
                cursor = QtGui.QCursor(QtCore.Qt.ClosedHandCursor)
                drag.setDragCursor(cursor.pixmap(), QtCore.Qt.MoveAction)
                # set hot spot
                drag.setHotSpot(event.pos() - self.clickPos)
                # start dragging
                drag.start(QtCore.Qt.MoveAction)

        else:
            super(MediaGridViewer, self).mouseMoveEvent(event)
        event.accept()

    def init_signals(self):
        self.itemClicked.connect(self.on_item_clicked)
        self.itemEntered.connect(self.mouse_enter)
        self.itemExited.connect(self.mouse_leave)

    def eventFilter(self, widget, event):
        # only if the event is happening within the viewport
        mods = QtWidgets.QApplication.keyboardModifiers()
        if widget is self.viewport() and mods != QtCore.Qt.ControlModifier:
            if self.auto_play:
                if event.type() in (QtCore.QEvent.MouseMove, QtCore.QEvent.Wheel):
                    # --- track mouse leaving item
                    item = self.itemAt(event.pos())
                    if item: # mouse is on an item
                        # get current item index
                        index = self.indexFromItem(item)
                        if index != self.last_index and self.last_index != None:
                            leave_item = self.itemFromIndex(self.last_index)
                            self.itemExited.emit()
                        self.last_index = index
                    else:  # mouse leave to empitiness
                        if self.last_index != None:
                            self.itemExited.emit()
                            self.last_index = None
            else:
                self.last_index = None
                
                # middle mouse drag
                if event.type() in (QtCore.QEvent.MouseMove, QtCore.QEvent.Wheel):
                    buttons = event.buttons()
                    if buttons & QtCore.Qt.MiddleButton and self.scrub_item:
                        # --- track mid mouse drag
                        if self.scrub_item._isLoaded:
                            playPercent = self.getPlayPercent(item=self.scrub_item)
                            self.scrub_item.percent_frame(percent=playPercent)
                        else:
                            if not self.scrub_item._isLoading:
                                self.continue_load(item=self.scrub_item)
                elif event.type() in (QtCore.QEvent.MouseButtonRelease, QtCore.QEvent.Wheel):
                    if self.scrub_item:
                        if self.show_play_button and self.scrub_item.type == 'video':
                            self.scrub_item.show_play_button()

        return QtWidgets.QListWidget.eventFilter(self, widget, event)

    def leaveEvent(self, event):
        self.itemExited.emit()
        self.last_index = None
        super(MediaGridViewer, self).leaveEvent(event)

    def hideEvent(self, event):
        ''' called when user switch tab/hide the widget, this will release loaded memory '''
        self.stop_full_load()
        self.stop_preview_load()
        if self.clear_cache_on_hide:
            self.clear_all_pixmaps()
        super(MediaGridViewer, self).hideEvent(event)

    def getPlayPercent(self, item):
        mouse_x = self.cursor().pos().x()
        item_rect = self.visualItemRect(item)
        start_x = self.mapToGlobal(item_rect.topLeft()).x()
        end_x = self.mapToGlobal(item_rect.topRight()).x()
        playPercent = 1.0 - ((end_x - mouse_x) / float(end_x - start_x))
        if playPercent < 0:
            playPercent = 0
        elif playPercent > 1:
            playPercent = 1
        return playPercent

    def on_item_clicked(self, item):
        # emit user data
        data = item.data(QtCore.Qt.UserRole)
        self.itemClickedUser.emit(data)

    def mouse_enter(self, item):
        if self.auto_play and item.type == 'video':
            if item._isLoaded:
                self.delay_timer = QtCore.QTimer()
                self.delay_timer.setSingleShot(True)
                self.delay_timer.timeout.connect(lambda: self.play_delay_trigger(item=item))
                self.delay_timer.start(self.autoplay_delay_time)
            else:
                # don't spawn another thread if the item is already loading
                if item._isLoading:
                    return
                # Start a timer. if mouse still on the object, continue loading the rest of the media
                self.delay_timer = QtCore.QTimer()
                self.delay_timer.setSingleShot(True)
                self.delay_timer.timeout.connect(lambda: self.load_delay_trigger(item=item))
                self.delay_timer.start(self.fullload_delay_time)

    def load_delay_trigger(self, item):
        local_mouse_pos = self.mapFromGlobal(self.cursor().pos())
        if self.itemAt(local_mouse_pos) is item:
            self.continue_load(item)

    def play_delay_trigger(self, item):
        local_mouse_pos = self.mapFromGlobal(self.cursor().pos())
        if self.itemAt(local_mouse_pos) is item:
            self.play_media(item=item)

    def play_media(self, item):
        self.stop_all_plays()
        self.stop_full_load()

        playThread = MediaPlayThread(startframe=item.current_frame, fps=self.fps, length=item.len, parent=self)
        playThread.CONTINUE.connect(lambda: item.next_frame())
        playThread.LOOP.connect(lambda: item.load_frame(0))
        playThread.start()
        self.playThreads.append(playThread)

    def mouse_leave(self):
        self.stop_full_load()
        self.stop_all_plays()
        for i in range(self.count()):
            item = self.item(i)
            if self.show_play_button and item.type == 'video':
                item.show_play_button()

    def stop_all_plays(self):
        for i in range(self.count()):
            item = self.item(i)
            item.hide_loading()
            
        # stop all playthreads
        for thread in self.playThreads:
            if thread.isRunning():
                thread.stop()
                thread.exit()
                thread.wait()
                thread.setParent(None)  # set thread parent to None so it gets gabage collect
        self.playThreads = []

    def stop_full_load(self):
        #print('stop full loads')
        for thread in self.fullLoadThreads:
            if thread and thread.isRunning():
                thread.stop()
                thread.exit()
                thread.wait()
        self.fullLoadThreads = []

    def stop_preview_load(self):
        #print('stop preview loads')
        for thread in self.previewLoadThreads:
            if thread and thread.isRunning():
                thread.stop()
                thread.exit()
                thread.wait()
        self.previewLoadThreads = []

    def load_first_frame(self, paths, metadata):
        self.stop_all_plays()
        self.stop_full_load()
        self.stop_preview_load()

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        previewLoadThread = MediaThread(filenames=paths, metadata=metadata, single_video_frame_at=self.poster_frame_weight, vide_quality=self.quality)
        previewLoadThread.frameLoaded.connect(self.preview_loaded)
        previewLoadThread.loadFinished.connect(self.preview_load_finished)
        previewLoadThread.start()

        self.previewLoadThreads.append(previewLoadThread)

    def continue_load(self, item):
        #print('continue load')
        self.stop_full_load()
        self.stop_all_plays()

        index = QtCore.QPersistentModelIndex(self.indexFromItem(item))
        metadata = [{'index': index, 'text':item.text(), 'user_data': item.data(QtCore.Qt.UserRole)}]

        item.hide_play_button()
        item.show_loading()  # show loading GIF
        
        # start new thread
        fullLoadThread = MediaThread(filenames=[item.path], metadata=metadata, single_video_frame_at=None, vide_quality=self.quality)
        fullLoadThread.loadFinished.connect(self.fullframe_load_finished)
        fullLoadThread.start()
        self.fullLoadThreads.append(fullLoadThread)
        # print('continue load done')
    
    def preview_loaded(self, item_data):
        '''
        Once a media is loaded, add a UI item to widget
        item_data = tuple( MediaModel, (text, user data) )
        '''
        images, metadata = item_data
        user_data = None
        if 'user_data' in metadata:
            user_data = metadata['user_data']
        
        # get overlay image
        overlay_images = []
        if user_data and '__overlay_images' in user_data:
            overlay_images = user_data['__overlay_images']
        # get overlay texts
        overlay_texts = []
        if user_data and '__overlay_texts' in user_data:
            overlay_texts = user_data['__overlay_texts']

        if 'index' in metadata:
            index = metadata['index']
            item = self.item(index.row())
            item.cache_images(images=images)
            item._isLoaded = False
        else:
            item = MediaGridItem(images=images, overlay_images=overlay_images, overlay_texts=overlay_texts, parent=self)

        # set image to frame 0 
        # in case load_first_frame this will be the poster frame
        # in case continue load this will roll to start of the clip
        item.load_frame(frame_num=0)
        if self.show_play_button and item.type == 'video':
            item.show_play_button()

        # set text
        text = ''
        if 'text' in metadata:
            text = metadata['text']
        item.setText(text)

        # set user data
        item.setData(QtCore.Qt.UserRole, user_data)

        # special user data
        if user_data and '__toolTip' in user_data:
            item.setToolTip(user_data['__toolTip'])
        if user_data and '__backgroundColor' in user_data:
            col = user_data['__backgroundColor']
            item.setBackground(QtGui.QBrush(QtGui.QColor(col[0], col[1], col[2])))

        # emit item created signal
        self.itemCreated.emit(item)
        return item

    def preview_load_finished(self):
        # manually trigger resize event to make sure images are aligned in grid
        self.resizeEvent(QtGui.QResizeEvent(self.size(), QtCore.QSize()))
        QtWidgets.QApplication.restoreOverrideCursor()

    def fullframe_load_finished(self, finish_data):
        # coming from mouse pointing on unloaded item
        images, metadata = finish_data

        item = None
        if 'index' in metadata[0]:
            index = metadata[0]['index']
            item = self.item(index.row())
            if item:
                # needs to check if there's image return from fullLoadThread
                # if interrupted, will return []
                item.hide_loading()
                if images:
                    item.cache_images(images=images[0])
                    item._isLoaded = True
                    # continue playing if mouse is still on the item
                    if self.auto_play:
                        local_mouse_pos = self.mapFromGlobal(self.cursor().pos())
                        if self.itemAt(local_mouse_pos) is item:
                            self.play_media(item=item)

    def add_items(self, media_info):
        ''' 
            media_info = [path1, path2, ...] or [(path1, text2, data1), (path2, text2, data2), ...]
        '''
        paths = []
        metadatas = [] 
        for media in media_info:
            if isinstance(media, (list, tuple)):
                path = media[0]
                text = media[1]
                data = media[2]
            elif isinstance(media, (str, unicode)):
                path = media
                text = ''
                data = media  # data is path if not specified

            fn, ext = os.path.splitext(path)
            if ext.lower() in IMAGE_EXT + VIDEO_EXT:
                paths.append(path)
                metadatas.append({'text': text, 'user_data':data})
            else:
                print('Unsupported file type: {}'.format(path))

        if paths:
            # load first frame
            self.load_first_frame(paths=paths, metadata=metadatas)

    def update_items(self, update_data):
        '''
        update_data = [ (QListWidgetItem, {filepath: 'filepath', text: 'text', user data: {data}), ... ]
        '''
        paths = []
        metadatas = []
        for item, data in update_data:
            index = QtCore.QPersistentModelIndex(self.indexFromItem(item))
            metadata = {'index': index}
            if 'filepath' in data:
                paths.append(data['filepath'])
            if 'text' in data:
                metadata['text'] = data['text']
            if 'user_data' in data:
                metadata['user_data'] = data['user_data']
            metadatas.append(metadata)

        if paths:
            # load first frame
            self.load_first_frame(paths=paths, metadata=metadatas)

    def refresh_items(self):
        for i in range(self.count()):
            item = self.item(i)
            item.refresh()
            if self.show_play_button and item.type == 'video':
                item.show_play_button()


if __name__ == '__main__':
    app = QApplication(sys.argv[0])
    # form = testWindow()
    # form.show()
    app.exec_()

'''
# image = generateGrid(1080,1920,10)
# image = cv2.imread("C:/Users/nook/Pictures/lego friends.jpeg")
# generateThumbnailImage(image)

# ----------- TEST IN MAYA
from rftool.utils.ui import maya_win
from rf_utils.widget import media_widget
reload(media_widget)

form = media_widget.testWindow(parent=maya_win.getMayaWindow())
form.show()

'''