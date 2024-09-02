import os
import multiprocessing
import hashlib
import subprocess
from PyQt5 import QtGui
import multiprocessing.pool
from typing import Dict, Optional

class CachedThumbnailGenerator:

    def __init__(self, cache_folder) -> None:
        self.cache_folder = cache_folder
        self.memory_cache: Dict[str, Optional[QtGui.QIcon]] = {}
        self.pool = multiprocessing.pool.ThreadPool(1)

    def create_thumbnail(self, video_file, callback=None, error_callback=None):
        self.pool.apply_async(
            self._get_thumbnail_file, (video_file,),
            callback=callback, error_callback=error_callback)

    def get_thumbnail(self, video_file, callback=None, error_callback=None):
        cache_key = video_file

        if cache_key not in self.memory_cache:
            self.memory_cache[cache_key] = None

            def inner_callback(thumbnail_file):
                if not thumbnail_file:
                    return
                image = QtGui.QImage(thumbnail_file)
                pixmap = QtGui.QPixmap.fromImage(image)
                self.memory_cache[cache_key] = QtGui.QIcon(pixmap)
                if callback:
                    callback()

            self.create_thumbnail(
                video_file, inner_callback, error_callback)

        if cache_key in self.memory_cache and self.memory_cache[cache_key]:
            return self.memory_cache[cache_key]
        return None

    def _cache_file(self, video_file):
        abs_path = os.path.abspath(os.path.expanduser(video_file)) #  + str(sec)
        digest = hashlib.md5(abs_path.encode()).hexdigest()
        return os.path.join(self.cache_folder, digest[:1], digest[1:2], digest + ".jpg")

    def _load_cache(self, video_file):
        pass

    @staticmethod
    def _generate_thumbnail(video_fn, thumbnail_fn):
        subprocess.check_call([
            'ffmpeg', '-i',
            video_fn,
            "-threads", "1",
            '-ss', '00:00:00.000',
            '-c:v', 'mjpeg',
            '-vframes', '1',
            '-frames:v', '1',
            '-filter:v', 'scale=300:300:force_original_aspect_ratio=increase,crop=300:300',
            # '-f', 'image2pipe',
            # '-'
            thumbnail_fn
        ])

    def _get_thumbnail_file(self, video_file):
        cache_file = self._cache_file(video_file)
        if not os.path.exists(cache_file):
            if not os.path.exists(os.path.dirname(cache_file)):
                os.makedirs(os.path.dirname(cache_file))
            self._generate_thumbnail(video_file, cache_file)
            assert os.path.exists(cache_file)
        return cache_file
