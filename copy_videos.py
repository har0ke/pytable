import subprocess
import json
import os
import datetime
import glob
from PIL import Image
import shutil
import re
import argparse

class VideoCopyException(Exception):

    def __init__(self, video: str, message: str, *args: object) -> None:
        self.video = video
        self.message = message
        super().__init__(*args)

def video_creation_time(fn):
    try:
        output = subprocess.check_output([
            "ffprobe", "-v", "quiet", fn, "-print_format", "json",
            "-show_entries",
            "stream=index,codec_type:stream_tags=creation_time:format_tags=creation_time"
        ])
    except subprocess.CalledProcessError as e:
        raise VideoCopyException(fn, "'ffprobe' failed to extract creation time") from e
    fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
    data = json.loads(output)
    if "streams" in data:
        for d in data["streams"]:
            if "tags" in d and "creation_time" in d["tags"]:
                return datetime.datetime.strptime(d["tags"]["creation_time"], fmt)
    if "format" in data and "tags" in data["format"] and "creation_time" in data["format"]["tags"]:
        return datetime.datetime.strptime(data["format"]["tags"]["creation_time"], fmt)

    raise VideoCopyException(fn, "Could not find creation time in 'ffprobe' output")
    #import sys
    #import zoneinfo
    #dt = datetime.datetime.fromtimestamp(
    #        os.stat(fn).st_ctime, zoneinfo.ZoneInfo("UTC"))
    #dt = dt.replace(tzinfo=None)
    #return dt
    return ValueError()
def get_time_image(fn):
    fmt = "%Y:%m:%d %H:%M:%S"
    return datetime.datetime.strptime(Image.open(fn)._getexif()[36867], fmt)


FMT_FOLDER = "%Y%m%d"
FMT_BASE = "%Y%m%d_%H%M"

def get_matching_image(video_fn):
    base, ext = os.path.splitext(video_fn)
    ext = ext.lower()
    image_files = list(
            filter(lambda fn: os.path.splitext(fn)[1].lower() in [".jpeg", ".jpg", ".png"],
                    glob.iglob(glob.escape(base) + "*")))
    if len(image_files) >= 2:
        raise VideoCopyException(video_fn, "Too many images found that could belong to video")

    if len(image_files) == 0:
        return None
    return image_files[0]

def match_to_destination_image(video_fn: str, dest_dir: str) -> str | None:
    image_file = get_matching_image(video_fn)
    if image_file is None:
        return None

    image_ext = os.path.splitext(image_file)[-1]
    image_dt = get_time_image(image_file)
    image_size = os.path.getsize(image_file)
    new_base = os.path.join(
        dest_dir,
        image_dt.strftime(FMT_FOLDER),
        image_dt.strftime(FMT_BASE)
    )

    g = glob.escape(new_base) + "_*" + image_ext
    matches = [g for g in glob.glob(g) if image_size == os.path.getsize(g)]
    if len(matches) != 1:
        raise VideoCopyException(
            video_fn,
            "No unique image found at destination that matches the image '%s' "
            "(which belongs to video). Found %d images for glob '%s'"
            % (image_file, len(matches), g)
        )

    _, ext = os.path.splitext(video_fn)
    nfn: str = os.path.splitext(matches[0])[0] + ext
    nfn_parts = list(os.path.split(nfn))
    nfn_parts[-1] = "." + nfn_parts[-1]
    return os.path.join(*nfn_parts)

def get_new_fn(video_fn: str, dest_dir: str) -> str:
    _, ext = os.path.splitext(video_fn)
    ext = ext.lower()

    dest_fn = match_to_destination_image(video_fn, dest_dir)
    if dest_fn:
        return dest_fn

    time = video_creation_time(video_fn)
    new_base = os.path.join(dest_dir, time.strftime(FMT_FOLDER), time.strftime(FMT_BASE))
    g = glob.glob(glob.escape(new_base) + "_*" + ext)
    if len(g) == 0:
        return new_base + "_0000" + ext
    n = 0
    s = os.path.getsize(video_fn)
    for f in g:
        if os.path.getsize(f) == s:
            return f
        p = r".*_(\d+)" + ext
        nn = re.match(p, f)
        n = max(n, int(nn.group(1)))
    return new_base + "_%04d" % (n + 1) + ext

def is_video(fn):
    _, ext = os.path.splitext(fn)
    ext = ext.lower()
    return ext in [".mp4", ".mov", ".mts"]

from dataclasses import dataclass

@dataclass
class DiscoveredVideo:
    video_file: str
    destination_file: str | None
    exits: bool
    error: Exception | None

def discover_new(dest_dir, *directories):
    for directory in directories:
        print("Discovering video files in '%s'" % directory)
        n = 0
        to_copy = 0
        for path, _, files in os.walk(os.path.expanduser(directory)):
            for f in sorted(files):
                fn = os.path.join(path, f)
                if not is_video(fn):
                    continue
                n += 1
                try:
                    nfn = get_new_fn(fn, dest_dir)
                except VideoCopyException as e:
                    yield DiscoveredVideo(fn, None, False, e)
                    print("ERROR: %s: %s" % (e.video, e.message))
                    continue
                if not os.path.exists(nfn):
                    if not os.path.exists(os.path.dirname(nfn)):
                        os.makedirs(os.path.dirname(nfn))
                    to_copy += 1
                    yield DiscoveredVideo(fn, nfn, False, None)
                else:
                    if os.path.getsize(fn) != os.path.getsize(nfn):
                        raise VideoCopyException(fn, "Destination exists but has different size...")
                    yield DiscoveredVideo(fn, nfn, True, None)
        print("Found %d/%d new videos." % (to_copy, n))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", nargs='+')
    parser.add_argument("--destination", default=os.path.expanduser("~/Pictures/Darktable"))
    parser.add_argument("--dry", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    options = parser.parse_args()

    video_files = list(discover_new(options.destination, *options.folder))
    copying = list(filter(lambda r: not r.exits and r.error is None, video_files))

    if options.verbose:
        for c in video_files:
            print("%s => %s%s%s" % (
                c.video_file,
                c.destination_file,
                " (EXISTS)" if c.exits else "",
                " (ERROR)" if c.error else ""
            ))

    print()
    print("Wants to copy %d/%d video files." % (len(copying), len(video_files)))

    if len(copying) == 0:
        exit(0)
    reply = input("Continue? y/n ")
    if reply != 'y':
        print("You did not type 'y'. Not doing anything!")
        exit(1)

    for c in copying:
          assert c.destination_file
          print("Copying %s => %s" % (c.video_file, c.destination_file))
          shutil.copy(c.video_file, c.destination_file)
