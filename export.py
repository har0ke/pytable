from pytable.models import Color, Image, ImageFlags, FilmRoll, ColorLabel, TaggedImages

from datetime import datetime
import peewee as pw
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Tuple, Optional, Generic, TypeVar, Iterable


export_base = "/home/oke/Nextcloud/Blog/"
query = (
    Image.filter()
    .join(ColorLabel)
    .where(ColorLabel.color == Color.BLUE)
    .where(Image.datetime_taken > datetime(2024, 6, 14, 22))
)
pw.prefetch(query, FilmRoll)

def is_blog(image: Image):
    return (
        (image.group == image or image.group == None) and
        not image.flag(ImageFlags.REJECTED)
    )

images = list(filter(is_blog, query))
for image in sorted(images, key=lambda i: i.datetime_taken or i.datetime_imported):
    assert isinstance(image, Image)
    fn = os.path.join(image.film.folder, image.filename)
    version = "" if image.version == 0 else ("_%02d" % image.version)
    base, ext = os.path.splitext(image.filename)
    xmp = os.path.join(image.film.folder, base + version + ext + ".xmp")
    out_fn = os.path.join(export_base, base + version + ".jpg")

    if os.path.exists(out_fn):
        if not image.datetime_changed or datetime.fromtimestamp(os.stat(out_fn).st_ctime) > image.datetime_changed:
            continue
        os.remove(out_fn)
    subprocess.call([
        'darktable-cli',
        fn,
        xmp,
        '--width', '1920',
        '--out-ext', 'jpg',
        '--upscale', 'false',
        '--hq', 'true',
        out_fn
    ])

print(len(images))

