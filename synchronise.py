from pytable.models import Image, ImageFlags, FilmRoll

from datetime import datetime
import peewee as pw
import os
from dataclasses import dataclass
from typing import Tuple, Optional, Generic, TypeVar, Iterable
from vmgr.actions import Trash
import subprocess
import shlex

T = TypeVar('T')
Range = Tuple[Optional[T], Optional[T]]


class Filter:

    def __call__(self, image: Image):
        return self.matches(image)

    def matches(self, image: Image) -> bool:
        return True

    def __str__(self) -> str:
        return 'All'


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

    def __str__(self) -> str:
        return f"LocalRange[({self.date_range[0] and self.date_range[0].strftime("%Y%m%d")}, {self.date_range[1] and self.date_range[1].strftime("%Y%m%d")}), ({self.stars_range[0]}, {self.stars_range[1]})]"

@dataclass
class Or(Filter):

    filters: Iterable[Filter]

    def matches(self, image: Image) -> bool:
        return any(f(image) for f in self.filters)

    def __str__(self) -> str:
        return f"Or([\n\t{"\n\t".join((str(f) + ',' for f in self.filters))}\n])"

@dataclass
class And(Filter):

    filters: Iterable[Filter]

    def matches(self, image: Image) -> bool:
        return all(f(image) for f in self.filters)

    def __str__(self) -> str:
        return f"And([\n\t{"\n\t".join(('<' + str(f) + '>,' for f in self.filters))}\n])"


class Config:

    def __init__(self, d_root: str | None = None, d_local: str | None=None, dry_run=False) -> None:
        self.d_root = d_root or "/home/oke/Pictures/Darktable"
        self.d_local = d_local or "/home/oke/Pictures/DarktableLocal"
        self.dry_run = dry_run

    def image_local_folder(self, image: Image) -> str:
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

    def __init__(self, config: Config, filter: Filter) -> None:
        self._config = config
        self._filter = filter
        self._files: Dict[str, SyncReq] = {}

    def register_file(self, fn: str, requirement: SyncReq):
        if fn in self._files:
            requirement = SyncReq.max(self._files[fn], requirement)
        self._files[fn] = requirement

    def register_image(self, image: Image):
        required = self._filter(image)
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

def write_to(fn, file_list, realtive_to):
    lines = list(sorted(map(
        lambda fn: os.path.relpath(fn, realtive_to) + "\n",
        file_list
    )))
    with open(fn, "w") as f:
        f.writelines(lines)

def synchronize_from_remote(config, required_files):
    write_to("required.txt", required_files, config.d_local)
    user = "oke"
    host = "192.168.20.2"
    args = [
        "rsync",
        "--info=progress",
        "--ignore-existing",
        "-av",
        "--files-from",
        "required.txt",
        f"{user}@{host}:lenovo-darktable{config.d_local}",
        os.path.abspath(config.d_local)
    ]
    if config.dry_run:
        args.append('--dry-run')
    print(shlex.join(args))
    subprocess.call(args)

def remove_unnessecary(config: Config, to_remove):
    remove_list_fn = "sync_remove.txt"
    try:

        reply = input("There are %d files to remove. Want to see them [type: y]? " % len(to_remove))
        if reply == 'y':
            write_to(remove_list_fn, to_remove, config.d_local)
            subprocess.call(['vim', '-R', remove_list_fn])
        if not config.dry_run:
            reply = input("There are %d files to remove. Want to DELETE them [type: YES]? " % len(to_remove))
            if reply == 'YES':
                for f in to_remove:
                    Trash(f).run()
    finally:
        if os.path.exists(remove_list_fn):
            os.remove(remove_list_fn)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action='store_true')
    options, filter_args = parser.parse_known_args()

    filter = None
    while filter_args:
        if filter_args[0] != '--sync':
            print(f"Unexpected arg {filter_args[0]}")
            exit(1)
        try:
            next_sync = filter_args.index('--sync', 1)
            args = filter_args[:next_sync]
            filter_args = filter_args[next_sync:]
        except ValueError:
            args = filter_args
            filter_args = []

        filter_parser = argparse.ArgumentParser()
        filter_parser.add_argument("--from", dest='from_date', type=lambda s: datetime.strptime(s, '%Y%m%d'), default=None)
        filter_parser.add_argument("--to", dest='to_date', type=lambda s: datetime.strptime(s, '%Y%m%d'), default=None)
        filter_parser.add_argument("--min-stars", type=int, default=None)
        filter_parser.add_argument("--max-stars", type=int, default=None)

        filter_options = filter_parser.parse_args(args[1:])
        parsed_filter = LocalRegion((filter_options.from_date, filter_options.to_date), (filter_options.min_stars, filter_options.max_stars))
        if filter:
            filter = Or([
                filter,
                parsed_filter
            ])
        else:
            filter = parsed_filter

    if not filter:
        print("Nothing to be synchronized")
        exit()
    print(filter)
    config = Config(dry_run=options.dry_run)

    sync_manager = SyncManager(config, filter)

    query = Image.filter()
    pw.prefetch(query, FilmRoll)
    for image in query:
        sync_manager.register_image(image)


    actions = sync_manager.partition()

    required_files = actions[SyncReq.REQUIRED]
    synchronize_from_remote(config, required_files)

    to_remove = [l for l in actions[SyncReq.EXISTS] if os.path.exists(l)]
    remove_unnessecary(config, to_remove)

if __name__ == "__main__":
    main()
