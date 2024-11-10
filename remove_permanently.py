from pytable.models import Image, ImageFlags, FilmRoll
import os
import sys


import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--execute", action='store_true')

options = parser.parse_args()


n_rejected = 0
n_less_than_three = 0
n_total = 0
n_total_leaders = 0
n_less_than_three_leaders = 0
n_rejected_leaders = 0

def is_leader(image):
    return not image.group_id or image.group_id == image.id

def should_remove(image):
    is_rejected = image.flag(ImageFlags.REJECTED)
    return is_rejected or (image.stars < 3 and not is_leader(image))

query: list[Image] = Image.filter().prefetch(FilmRoll)
images = query
images_to_remove = filter(should_remove, images)

d_root = "/home/oke/Pictures/Darktable"
d_local = "/home/oke/Pictures/DarktableLocal"
d_remote = "/home/oke/Pictures/DarktableRemote"

from datetime import datetime

ids_to_remove = []

for i in images_to_remove:
    fn = os.path.join(i.film.folder, i.filename)
    assert fn.startswith(d_root)
    print(fn.replace(d_root + '/', ''))

    remote_file = fn.replace(d_root, d_remote)
    local_file = fn.replace(d_root, d_local)
    ids_to_remove.append(i.id)




if ids_to_remove and options.execute:
    print(len(ids_to_remove))
    query = Image.delete().where(Image.id.in_(ids_to_remove))
    query.execute()
