import subprocess
import json
import os
import datetime
import glob
from PIL import Image
import shutil
import re

def get_time(fn):
        try:
                output = subprocess.check_output([
                        "ffprobe", "-v", "quiet", fn, "-print_format", "json",
                        "-show_entries",
                        "stream=index,codec_type:stream_tags=creation_time:format_tags=creation_time"
                ])
        except subprocess.CalledProcessError as e:
                print("FFPROBE failed for ", fn)
                return ValueError()
        fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
        data = json.loads(output)
        if "streams" in data:
                for d in data["streams"]:
                        if "tags" in d and "creation_time" in d["tags"]:
                                return datetime.datetime.strptime(d["tags"]["creation_time"], fmt)
        if "format" in data and "tags" in data["format"] and "creation_time" in data["format"]["tags"]:
                        return datetime.datetime.strptime(data["format"]["tags"]["creation_time"], fmt)
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

def get_new_fn(fn):
        base, ext = os.path.splitext(fn)
        directory, base_fn = os.path.split(base)
        ext = ext.lower()

        image_files = list(
                filter(lambda fn: os.path.splitext(fn)[1].lower() in [".jpeg", ".jpg", ".png"],
                       glob.iglob(glob.escape(base) + "*")))
        assert len(image_files) < 2
        fmt_folder = "%Y%m%d"
        fmt_base = "%Y%m%d_%H%M"
        if image_files:
                f = image_files[0]
                image_ext = os.path.splitext(f)[-1]
                image_dt = get_time_image(f)
                image_size = os.path.getsize(f)
                new_base = os.path.join(os.path.expanduser("~/Pictures/Darktable"), image_dt.strftime(fmt_folder), image_dt.strftime(fmt_base))

                g = glob.escape(new_base) + "_*" + image_ext
                matches = [g for g in glob.glob(g) if image_size == os.path.getsize(g)]
                if len(matches) != 1:
                        print()
                        print("NO MATCH")
                        print(image_files)
                        print(matches)
                        print(g)
                        print(image_dt)

                        return None
                assert len(matches) == 1, fn
                nfn = os.path.splitext(matches[0])[0] + ext
                nfn = list(os.path.split(nfn))
                nfn[-1] = "." + nfn[-1]
                return os.path.join(*nfn)

        time = get_time(fn)
        if isinstance(time, ValueError):
                print("NO TIME")
                return None
        new_base = os.path.join(os.path.expanduser("~/Pictures/Darktable"), time.strftime(fmt_folder), time.strftime(fmt_base))
        g = glob.glob(glob.escape(new_base) + "_*" + ext)
        if len(g) == 0:
                return new_base + "_0000" + ext
        n = 0
        s = os.path.getsize(fn)
        for f in g:
                if os.path.getsize(f) == s:
                        return f
                p = r".*_(\d+)" + ext
                nn = re.match(p, f)
                n = max(n, int(nn.group(1)))
        n = new_base + "_%04d" % (n + 1) + ext
        return n

def main(dir, dry):
        print(dir)
        for p, folders, files in os.walk(os.path.expanduser(dir)):
                for f in sorted(files):
                        base, ext = os.path.splitext(f)

                        ext = ext.lower()
                        if ext not in [".mp4", ".mov", ".mts"]:
                                if ext not in [".jpg", ".jpeg", ".png"]:
                                        pass # print("Not handled: ", os.path.join(p, f))
                                continue
                        fn = os.path.join(p, f)
                        nfn = get_new_fn(fn)
                        if not nfn:
                                print("SKIP: ", fn)
                                continue
                        assert nfn

                        if not os.path.exists(nfn):
                                if not os.path.exists(os.path.dirname(nfn)):
                                        os.makedirs(os.path.dirname(nfn))
                                print(fn, nfn)
                                if not dry:
                                        shutil.copy(fn, nfn)
                        else:
                                print(fn, nfn, "EXIST")




import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--dry", action="store_true")
options = parser.parse_args()
main("/run/media/oke/3634-3063", options.dry)
main("/run/media/oke/3138-3162", options.dry)
main("/run/media/oke/01D5-9878/DCIM/", options.dry)
main("/run/media/oke/E5B5-DBF0/DCIM", options.dry)
main("/run/media/oke/disk/", options.dry)
main("~/Nextcloud/InstantUpload", options.dry)
main("/home/oke/Desktop/360/", options.dry)
