import os
from PyQt5 import QtWidgets, QtCore, QtGui
import itertools
from typing import Any, List, Dict
from thumbnails import CachedThumbnailGenerator

from typing import Tuple, Optional
import yaml

BASE_DIR = "/home/oke/Pictures/DarktableLocal/"
CACHE_FOLDER = os.path.expanduser("~/.cache/video_manager")

if not os.path.exists(CACHE_FOLDER):
    os.makedirs(CACHE_FOLDER)

thumbnailer = CachedThumbnailGenerator(CACHE_FOLDER)


class Metadata:

    def __init__(self, rating=0, rejected=False):
        assert type(rating) == int
        self.rating = rating
        self.rejected = rejected

    @classmethod
    def from_file(cls, fn):
        with open(fn) as f:
            data = yaml.load(f, yaml.SafeLoader)
        return Metadata(**data)

    def save(self, fn):
        with open(fn, "w") as f:
            yaml.dump(self.__dict__, f)

class Video:

    def __init__(self, fn: str) -> None:
        self.fn = fn
        self._metadata = None

    def __repr__(self):
        return os.path.basename(self.fn)

    @property
    def metadata(self):
        if not self._metadata:
            if os.path.exists(self.metadata_file()):
                self._metadata = Metadata.from_file(self.metadata_file())
            else:
                self._metadata = Metadata()
        return self._metadata

    def metadata_file(self):
        return self.fn + '.metadata'

    def save_metadata(self):
        self.metadata.save(self.metadata_file())

    def load_thumbnail(self, thumbnailer, callback=None, error_callback=None):
        thumbnailer.create_thumbnail(self.fn, callback, error_callback)

    def __lt__(self, other):
        return self.fn > other.fn

    def __eq__(self, other):
        return self.fn == other.fn

class VideoModel(QtCore.QAbstractListModel):


    def __init__(self):
        super().__init__()
        self._filter_rating = (0, 6)
        self.show_up_to = 10

        self.video_obj_cache = {}
        self.all_files: List[Video] = self.collect_files()
        self.video_files: List[Video] = self.filter_files(self.all_files)


        pixmap = QtGui.QPixmap(256, 256)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.setBrush(QtGui.QColor("red"))
        painter.drawEllipse(pixmap.rect())
        painter.end()
        self.default_icon = QtGui.QIcon(pixmap)

    def collect_files(self, base_dir=BASE_DIR):
        def _():
            for film_roll in os.listdir(base_dir):
                roll_dir = os.path.join(base_dir, film_roll)
                if os.path.isdir(roll_dir):
                    for fn in os.listdir(roll_dir):
                        if fn[0] != '.' and os.path.splitext(fn)[-1].lower() in [".mp4", ".mov", ".avi"]:
                            path = os.path.join(roll_dir, fn)
                            if path not in self.video_obj_cache:
                                self.video_obj_cache[path] = Video(path)
                            yield self.video_obj_cache[path]
        return sorted(_())

    @property
    def filter_rating(self):
        return self._filter_rating

    @filter_rating.setter
    def filter_rating(self, value):
        self._filter_rating = value
        self.update()

    def filter_files(self, videos: List[Video]):
        def flt(video: Video):
            minimum, maximum = self._filter_rating
            rating =  -1 if video.metadata.rejected else video.metadata.rating
            return rating >= minimum and rating < maximum
        return list(filter(flt, videos))[:self.show_up_to]


    def find_video(self, video: Video)-> Tuple[Optional[QtCore.QModelIndex], Video]:
        try:
            index = self.all_files.index(video)
            video = self.all_files[index]
        except ValueError:
            pass

        try:
            index = self.video_files.index(video)
            index = self.index(index, 0)
        except ValueError:
            index = None
        return index, video



    def update(self):
        i = 0
        parent = QtCore.QModelIndex()
        before = list(self.video_files)
        action_list = []
        after = self.filter_files(self.all_files)

        while i < len(after) and i < len(before):
            if before[i] == after[i]:
                i += 1
            elif before[i] < after[i]:
                action_list.append(('r', i))
                before.pop(i)
            else:
                action_list.append(('a', i, after[i]))
                before.insert(i, after[i])

        j = i
        while j < len(before):
            action_list.append(('r', j))
            before.pop(j)

        for j in range(i, len(after)):
                action_list.append(('a', j, after[j]))
                before.insert(j, after[j])
        # assert before == after

        if len(action_list) == 0:
            return
        def work_batch():
            batch = action_list[b:e]
            if batch[0][0] == 'r':
                self.beginRemoveRows(parent, batch[0][1], batch[0][1] + len(batch) - 1)
                del self.video_files[batch[0][1]:batch[0][1] + len(batch)]
                self.endRemoveRows()
            else:
                self.beginInsertRows(parent, batch[0][1], batch[0][1] + len(batch) - 1)
                self.video_files = (
                    self.video_files[0:batch[0][1]] +
                    list(map(lambda a: a[2], batch)) +
                    self.video_files[batch[0][1]:]
                )
                self.endInsertRows()

        b = 0
        e = 1
        for e in range(1, len(action_list)):
            if (
                action_list[e][0] == 'r' and
                action_list[e - 1][0] == 'r' and
                action_list[e][1] == action_list[e - 1][1]
            ):
                continue
            if (
                action_list[e][0] == 'a' and
                action_list[e - 1][0] == 'a' and
                action_list[e][1] == action_list[e - 1][1] + 1
            ):
                continue
            work_batch()
            b = e
        e = len(action_list)
        work_batch()
        assert len(self.video_files) == len(after)
        # assert self.video_files == after

    def reload(self):
        self.all_files = self.collect_files()
        self.update()

    def invalidateFilter(self, index=None, index_to=None):
        self.update()

    def canFetchMore(self, parent: QtCore.QModelIndex) -> bool:
        return self.show_up_to < len(self.all_files)

    def fetchMore(self, parent: QtCore.QModelIndex) -> None:
        self.show_up_to = min(self.show_up_to + 5, len(self.all_files))
        self.update()

    def remove(self, index):
        self.all_files.remove(self.video_files[index.row()])
        self.update()

    def data(self, index: QtCore.QModelIndex, role: int=0) -> Any:
        video = self.video_files[index.row()]
        if role == 0:
            size = 0
            try:
                size = os.stat(video.fn).st_size / 1024. / 1024. / 1024.
            except FileNotFoundError:
                pass
            return '%s %s %.2f' % (
                os.path.basename(video.fn),
                ('★' * video.metadata.rating + '☆' * (5 - video.metadata.rating))
                if not video.metadata.rejected else
                'xxxxx'
                ,
                size
            )
        if role == 1:
            def callback():
                self.dataChanged.emit(index, index)
            return (
                thumbnailer.get_thumbnail(video.fn, callback)
                or self.default_icon
            )


    def rowCount(self, index=None):
        return len(self.video_files)

    def columnCount(self, index):
        return 1


