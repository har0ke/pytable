from pytable.models import Image, ImageFlags, FilmRoll

import peewee as pw
import os
import subprocess

base_path = "/home/oke/Pictures/Darktable"

subprocess.check_call(["mountpoint", "/home/oke/Pictures/DarktableRemote"])
real_folders = [
    "/home/oke/Pictures/DarktableLocal",
    "/home/oke/Pictures/DarktableRemote",
]

query: list[Image] = Image.filter()
pw.prefetch(query, FilmRoll)
images = list(query)
import itertools


required_files = list(itertools.chain(*[
    [os.path.join(image.film.folder, image.filename),
     os.path.join(image.film.folder,
                    os.path.splitext(image.filename)[0] +
                    (("_%02d" % image.version) if image.version != 0 else "") +
                    os.path.splitext(image.filename)[1]) + ".xmp"
    ]
    for image in images]))

allowed_files = list(itertools.chain(*[
    [os.path.join(image.film.folder, "." + os.path.splitext(image.filename)[0] + ".mov")]
    for image in images])) + required_files



for fn in allowed_files:
    assert fn.startswith(base_path)

for folder in real_folders:
    real_files = set([os.path.join(path, file) for path, folders, files in os.walk(folder) for file in files if file[-3:] not in ["mov", "mp4", "mts", "ata"]])
    mapped_allowed = [fn.replace(base_path, folder) for fn in allowed_files]

    print(":::: Files to remove:")
    for fn in sorted(real_files.difference(set(mapped_allowed))):
        print(fn)

    if folder == "/home/oke/Pictures/DarktableRemote":
        print(":::: Missing files:")
        mapped_required = [fn.replace(base_path, folder) for fn in required_files]
        for fn in sorted(set(mapped_required).difference(set(real_files))):
            print(fn)
