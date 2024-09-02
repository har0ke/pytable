from pytable.models import Image, ImageFlags, FilmRoll

from datetime import datetime
import peewee as pw
import os
import shutil
from dataclasses import dataclass
from typing import Tuple, Optional, Generic, TypeVar, Iterable

T = TypeVar('T')

Range = Tuple[Optional[T], Optional[T]]

class Filter:


    def __call__(self, image: Image):
        return self.matches(image)

    def matches(self, image: Image) -> bool:
        ...

@dataclass
class LocalRegion(Filter):

    date_range: Range[datetime] = (None, None)
    stars_range: Range[int] = (None, None)

    def matches(self, image: Image) -> bool:

        stars = image.stars if not image.flag(ImageFlags.REJECTED) else -1
        if self.stars_range[0] is not None and stars < self.stars_range[0]:
            return False
        if self.stars_range[1] is not None and stars > self.stars_range[1]:
            return False

        dt = (image.datetime_taken or image.datetime_imported)
        if self.date_range[0] is not None and dt < self.date_range[0]:
            return False
        if self.date_range[1] is not None and dt > self.date_range[1]:
            return False
        return True

@dataclass
class Or(Filter):

    filters: Iterable[Filter]

    def matches(self, image: Image) -> bool:
        return any(f(image) for f in self.filters)

@dataclass
class And(Filter):

    filters: Iterable[Filter]

    def matches(self, image: Image) -> bool:
        return all(f(image) for f in self.filters)


class Config:

    def __init__(self) -> None:
        self.filter = Or([
            LocalRegion((datetime(2024, 6, 14), None), (0, None)),
            LocalRegion((datetime(2024, 6, 22, 14), datetime(2024, 6, 22, 14, 24)))
        ])

        self.d_root = "/home/oke/Pictures/Darktable"
        self.d_local = "/home/oke/Pictures/DarktableLocal"
        self.d_remote = "/home/oke/Pictures/DarktableRemote"


    @staticmethod
    def _is_older_than(image: Image, date: datetime):
        return (image.datetime_taken or image.datetime_imported) < date

    def should_not_be_local(self, image: Image):
        return not self.filter(image)

    def should_be_local(self, image: Image):
        return self.filter(image)

    def image_local_folder(self, image: Image):
        folder = image.film.folder
        if not folder.startswith(self.d_root):
            raise NotImplementedError()
        assert folder.startswith(self.d_root)
        return folder.replace(self.d_root, self.d_local)

    def image_local_image(self, image: Image) -> str:
        return os.path.join(self.image_local_folder(image), image.filename)

    def image_local_image_xmp(self, image: Image) -> str:
        base, ext = os.path.splitext(image.filename)
        version = ("_%02d" % image.version) if image.version != 0 else ""
        xmp_filename = base + version + ext + '.xmp'
        return os.path.join(self.image_local_folder(image), xmp_filename)

    def image_local_iphone_movie(self, image: Image) -> str:
        base, _ = os.path.splitext(image.filename)
        return os.path.join(self.image_local_folder(image), "." + base + ".mov")

    def potential_extras(self, image):
        yield self.image_local_iphone_movie(image)

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum

class SyncReq(Enum):
    EXISTS = 0
    REQUIRED_SOFT = 1
    REQUIRED = 2

    @staticmethod
    def max(a: "SyncReq", b: "SyncReq"):
        if a.value < b.value:
            return b
        return a
    @staticmethod
    def required(v: 'SyncReq'):
        return v == SyncReq.REQUIRED or v == SyncReq.REQUIRED_SOFT

    @staticmethod
    def make(required, optional):
        if required:
            if optional:
                return SyncReq.REQUIRED_SOFT
            return SyncReq.REQUIRED
        return SyncReq.EXISTS

@dataclass
class FileInfo:
    required: bool = False
    optional: bool = False

class SyncManager:

    def __init__(self, config) -> None:
        self._config = config
        self._files: Dict[str, SyncReq] = {}

    def register_file(self, fn: str, requirement: SyncReq):
        if fn in self._files:
            requirement = SyncReq.max(self._files[fn], requirement)
        self._files[fn] = requirement

    def register_image(self, image: Image):
        required = self._config.should_be_local(image)
        self.register_file(
            self._config.image_local_image(image),
            SyncReq.make(required, False)
        )
        self.register_file(
            self._config.image_local_image_xmp(image),
            SyncReq.make(required, False)
        )

        for extra in self._config.potential_extras(image):
            self.register_file(
                extra,
                SyncReq.make(required, True)
            )

    def partition(self):
        result = {k: [] for k in SyncReq}
        for file, req in self._files.items():
            result[req].append(file)
        return result

config = Config()

sync_manager = SyncManager(config)

query = Image.filter()
pw.prefetch(query, FilmRoll)
for image in query:
    sync_manager.register_image(image)


actions = sync_manager.partition()

for key in actions:
    actions[key] = list(sorted(map(
        lambda fn: os.path.relpath(fn, config.d_local) + "\n",
        actions[key]
    )))

with open("required.txt", "w") as f:
    f.writelines(actions[SyncReq.REQUIRED])
import subprocess
user = "oke"
host = "192.168.20.2"

args = [
    "rsync",
    # "--dry-run",
    "--info=progress",
    "--ignore-existing",
    "-av",
    "--files-from",
    "required.txt",
    f"{user}@{host}:lenovo-darktable{config.d_local}",
    os.path.abspath(config.d_local)
]
import shlex
print(shlex.join(args))
subprocess.call(args)

with open("required_optional.txt", "w") as f:
    f.writelines(actions[SyncReq.REQUIRED_SOFT])

with open("remove.txt", "w") as f:
    f.writelines(actions[SyncReq.EXISTS])

exit()
for fn in actions[SyncReq.REQUIRED_SOFT]:
    if not os.path.exists(fn):
        print("FETCH opt: ", fn)

for fn in sync_manager.files_to_fetch_required():
    print("FETCH: ", fn)

for fn in sync_manager.files_to_remove():
    print("RM: ", fn)
n_total = 0
n_not_needed = 0
needs_removal = []
extra_files_to_remove = []
bytes_to_remove = 0

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
