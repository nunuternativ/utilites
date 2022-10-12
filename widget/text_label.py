import sys
import os
import re
import itertools
from copy import copy

from Qt import QtCore
from Qt import QtWidgets
from Qt import QtGui

is_python2 = True if sys.version_info[0] < 3 else False

class HtmlLabel(QtWidgets.QLabel):
    ''' QLabel that supports non-latin characters, url and local path '''
    def __init__(self, parent=None):
        super(HtmlLabel, self).__init__(parent)
        self.custom_links = {}  # {link: (function, args, ...)}

        self.setScaledContents(True)
        # self.setMinimumWidth(100)
        self.setTextFormat(QtCore.Qt.RichText)
        self.setCursor(QtCore.Qt.IBeamCursor)
        self.setTextInteractionFlags(QtCore.Qt.LinksAccessibleByMouse | QtCore.Qt.TextSelectableByMouse)
        # self.setOpenExternalLinks(True)
        self.linkActivated.connect(self.link_clicked)

    def link_clicked(self, link):
        if link in self.custom_links:
            func = self.custom_links[link][0]
            args = self.custom_links[link][1:] if len(self.custom_links[link]) > 1 else None
            func(*args)
        else:
            # holding Shift key for open file directory
            if os.path.exists(os.path.dirname(link)):
                mods = QtWidgets.QApplication.keyboardModifiers()
                if mods & QtCore.Qt.ShiftModifier:
                    link = QtCore.QUrl.fromLocalFile(os.path.dirname(link))
            QtGui.QDesktopServices.openUrl(link)

    def setText(self, text, custom_links=[]):
        self.custom_links = {}
        if custom_links:
            self.custom_links = custom_links

        convert_result = self.convert(text)
        super(HtmlLabel, self).setText(convert_result)

        # size_hint = self.sizeHint()
        # print(size_hint)
        # self.setMinimumHeight(size_hint.height())

    def convert(self, input_text):
        if not input_text:
            return input_text

        # clean text from unwanted chars
        cleaned_texts = []
        for line in input_text.split('\n'):
            new_lines = []
            for text in line.split(' '):
                path = copy(text)
                # replace backslashes with forwardslashes
                path = path.replace('\\', '/')
                new_lines.append(path)
            cleaned_texts.append(' '.join(new_lines))
        input_text = '\n'.join(cleaned_texts)
        # print(input_text)
        # find urls
        urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', input_text)
        hyperlink_dict = {}
        for url in urls:
            html_url = "<a href='{url}'>{url}</a>".format(url=url)
            hyperlink_dict[url] = html_url

        # find local path
        for line in input_text.split('\n'):
            quote_texts = re.findall(r'(".+?")', line)
            if quote_texts:
                plain_texts = re.split('|'.join(quote_texts), line)
                for qt in quote_texts:
                    local_path = self.find_local_link(qt[1:-1])
                    if local_path:
                        hyperlink_dict[qt] = local_path
            else:
                plain_texts = line.split(' ')
            for path in plain_texts:
                local_path = self.find_local_link(path)
                if local_path:
                    hyperlink_dict[path] = local_path
        if self.custom_links:
            hyperlink_dict.update(dict((k, "<a href='{k}'>{k}</a>".format(k=k)) for k, v in self.custom_links.items()))

        if hyperlink_dict:
            # add plain text syntax
            for line in input_text.split('\n'):
                plain_texts = re.split('|'.join(hyperlink_dict.keys()), line)

                new_plain_texts = []
                for txt in plain_texts:
                    if txt:
                        html_line = '<pr>' + txt + '</pr>'
                        input_text = input_text.replace(txt, html_line) 
            input_text = input_text.replace('\n', '<br>')

            # replace hyperlinks
            hyperlink_dict = dict((re.escape(k), v) for k, v in hyperlink_dict.items()) 
            pattern = re.compile("|".join(hyperlink_dict.keys()))
            input_text = pattern.sub(lambda m: hyperlink_dict[re.escape(m.group(0))], input_text)
        else:
            new_lines = []
            for line in input_text.split('\n'):
                new_lines.append('<pr>' + line + '</pr>')
            input_text = '<br>'.join(new_lines)

        # decode Thai - Python2 only
        if is_python2:
            input_text = input_text.decode(encoding='UTF-8', errors='ignore')
        return input_text

    def find_local_link(self, path):
        if '/' not in path:
            return 

        # match drive and slashes
        match_drive = re.match('^[A-Z]:', path)
        sep_splits = path.split('/')
        if match_drive and len(sep_splits)>1 and sep_splits[0]==match_drive.group():
            path_escape = path.replace(' ', '%20')
            html_path = '<a href="{path_escape}">{path}</a>'.format(path_escape=path_escape, path=path)
            return html_path 

class BlinkLabel(QtWidgets.QLabel):
    def __init__(self, text='', pattern=[], interval=300, parent=None):
        super(BlinkLabel, self).__init__(parent)

        self.blink_text = text
        self.blink_pattern = pattern
       
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(interval)
        self.timer.timeout.connect(self.blink)

    @property
    def blink_pattern(self):
        return self._blink_pattern

    @blink_pattern.setter
    def blink_pattern(self, pattern):
        self._blink_pattern = itertools.cycle(pattern)

    @property
    def blink_text(self):
        return self._text

    @blink_text.setter
    def blink_text(self, text):
        self._text = text

    def blink(self):
        pattern = next(self.blink_pattern)

        try:
            self.setText(self.blink_text[pattern[0]: pattern[1]])
        except IndexError:
            print('Invalid pattern: {} {}'.format(self.blink_text, self.blink_pattern))

    def start(self):
        self.timer.start()

    def stop(self):
        self.timer.stop()

    def set_interval(self, interval):
        self.timer.setInterval(interval)