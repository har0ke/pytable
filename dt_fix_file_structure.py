from pytable.models import Image, ImageFlags, FilmRoll

from datetime import datetime
import peewee as pw
import os
from pprint import pprint
import subprocess

base_path = "/home/oke/Pictures/Darktable"
real_folders = [
    "/home/oke/Pictures/DarktableRemote",
    "/home/oke/Pictures/DarktableLocal",
]

subprocess.check_call(["mountpoint", "/home/oke/Pictures/DarktableRemote"])

query = Image.filter()
pw.prefetch(query, FilmRoll)
dry = True

move_files = []


d_root = "/home/oke/Pictures/Darktable"
d_local = "/home/oke/Pictures/DarktableLocal"
d_remote = "/home/oke/Pictures/DarktableRemote"


def me_and_related_dt(fn, new_folder, new_basename):
    directory, filename = os.path.split(fn)
    basename, ext = os.path.splitext(filename)
    yield fn, os.path.join(new_folder, new_basename + ext)
    yield os.path.join(directory, "." + basename + ".mov"), os.path.join(new_folder, "." + new_basename + ".mov"),
    yield fn + ".xmp", os.path.join(new_folder, new_basename + ext + ".xmp")


def me_and_related_potential(fn, new_folder, new_basename):
    for local_fn, local_fn_related in me_and_related_dt(fn, new_folder, new_basename):
        assert local_fn.startswith(d_root)
        yield local_fn.replace(d_root, d_local), local_fn_related.replace(d_root, d_local)
        yield local_fn.replace(d_root, d_remote), local_fn_related.replace(d_root, d_remote)

def me_and_related(fn, new_folder, new_basename):
    for fn, fn_related in me_and_related_potential(fn, new_folder, new_basename):
        if os.path.exists(fn):
            assert not os.path.exists(fn_related), fn + "=>" + fn_related
            yield fn, fn_related

changes = []

for image in query:
    try:
        n = 0
        dt_fn = datetime.strptime(image.filename[:13],"%Y%m%d_%H%M")
        if image.datetime_taken:
            dt_internal = datetime(image.datetime_taken.year, image.datetime_taken.month, image.datetime_taken.day, image.datetime_taken.hour, image.datetime_taken.minute)
            expected_folder = os.path.join(base_path, dt_internal.strftime("%Y%m%d"))
            if dt_fn != dt_internal:
                d = ((dt_internal - dt_fn).total_seconds() / 3600)
                dt_formatted = image.datetime_taken.strftime("%Y%m%d_%H%M")
                new_film_roll = image.film
                if expected_folder != image.film.folder:
                    new_film_roll = FilmRoll.get(folder=expected_folder)
                    assert new_film_roll

                new_fn = dt_formatted + image.filename[13:]
                new_basename, _ = os.path.splitext(new_fn)

                changes.append((
                    image, new_film_roll, new_fn,
                    list(me_and_related(os.path.join(image.film.folder, image.filename), new_film_roll.folder, new_basename))
                ))

                print("%s: %.2fH" % (image.filename, d))
                for src, dst in changes[-1][-1]:
                    print("\t%s => %s" % (src, dst))
    except Exception as e:
        print("ERROR:", e)



reply = input("Type YES to remove all these files. This is not reversible... : ")

if reply != 'YES':
    print("You did not type 'YES'. Not doing anything!")
    exit(-1)

for image, film_roll, new_fn, move in changes:
    print(image.filename, "=>", new_fn)

    for src, dst in move:
        assert not os.path.exists(dst)

    for src, dst in move:
        print("Moving %s => %s" % (src, dst))
        os.rename(src, dst)
    print("Saving image into sql")
    image.film = film_roll
    image.filename = new_fn
    image.save()
