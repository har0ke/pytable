from pytable.models import Image, ImageFlags, FilmRoll

from datetime import datetime
import peewee as pw
import os
import shutil

remove_three_stars_before = datetime(2024, 4, 1)
remove_secondary_before = datetime(2024, 6, 15)
remove_rejected_before = datetime(2024, 6, 15)

query = Image.filter()
pw.prefetch(query, FilmRoll)

def is_older_than(image, cmp):
   return (image.datetime_taken or image.datetime_imported) < cmp

def should_remove(image):
    return (
        (is_older_than(image, remove_three_stars_before) and image.stars < 3) or
        (image.flag(ImageFlags.REJECTED) and is_older_than(image, remove_rejected_before)) or
        (image.group_id != image.id and is_older_than(image, remove_secondary_before))
    )

file_usages = {}
for x in query:
    path = os.path.join(x.film.folder, x.filename)
    if path not in file_usages:
        file_usages[path] = 0
    if not should_remove(x):
        file_usages[path] += 1

n_total = 0
n_not_needed = 0
needs_removal = []
extra_files_to_remove = []
bytes_to_remove = 0

d_root = "/home/oke/Pictures/Darktable"
d_local = "/home/oke/Pictures/DarktableLocal"
d_remote = "/home/oke/Pictures/DarktableRemote"

def potential_extras(fn):
    directory, filename = os.path.split(fn)
    basename, _ = os.path.splitext(filename)

    iphone_movie = os.path.join(directory, "." + basename + ".mov")
    yield iphone_movie

needs_fetching = []

for file, usages in file_usages.items():
    if not file.startswith(d_root):
        print("SKIPPNG", file)
        continue
    assert file.startswith(d_root)
    remote_file = file.replace(d_root, d_remote)
    local_file = file.replace(d_root, d_local)

    if usages > 0:
        if not os.path.exists(local_file):
            needs_fetching.append((remote_file, local_file))
    else:
        n_not_needed += 1
        if os.path.exists(local_file):
            needs_removal.append(local_file)
            bytes_to_remove += os.stat(local_file).st_size

        for extra_fn in potential_extras(local_file):
            if os.path.exists(extra_fn):
                extra_files_to_remove.append(extra_fn)
                bytes_to_remove += os.stat(extra_fn).st_size

files_to_remove = list(sorted(needs_removal + extra_files_to_remove))

needs_fetching = sorted(needs_fetching)
import pprint
print("Files to fetch: ")
pprint.pprint(needs_fetching)
print("Extra files to remove:")
pprint.pprint(extra_files_to_remove)
print("First files to remove:")
pprint.pprint(needs_removal[:10])
print("Last files to remove:")
pprint.pprint(needs_removal[-10:])

with open("remove.txt", "w") as f:
    pprint.pprint(sorted(set(needs_removal).union(extra_files_to_remove)), f)

print("Not needed:            %6d / %6d (%3d%%)" % (n_not_needed, len(file_usages), 100 * n_not_needed / len(file_usages)))
print()
print("Not yet deleted:       %6d / %6d (%3d%%)" % (len(needs_removal), n_not_needed, 100 * len(needs_removal) / n_not_needed))
print("Bytes to free:         %5.2fGB" % (bytes_to_remove / 1024. / 1024 / 1024))
print("Total files to remove: %d" % len(files_to_remove))
print()
print("Total files to fetch: %3d" % len(needs_fetching))
print()

reply = input("Type YES to remove all these files. This is not reversible... : ")

if reply == 'YES':

    for fn in files_to_remove:
        assert fn.startswith(d_local)
        os.remove(fn)

    for f, t in needs_fetching:
        assert os.path.exists(f), "Backup corruped, file not found: " + f
        assert not os.path.exists(t)
        print(f, t)
        shutil.copy(f, t)

else:
    print("You did not type 'YES'. Not doing anything!")
