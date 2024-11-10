
import os
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("-u", action='store_true')
parser.add_argument("-a", action='store_true')
parser.add_argument("-n", "--dry-run", action='store_true')
parser.add_argument("base")
parser.add_argument("trash")
parser.add_argument("file_list")

options = parser.parse_args()


def me_and_extras(fn):
    directory, filename = os.path.split(fn)
    basename, ext = os.path.splitext(filename)
    yield fn
    iphone_movie = os.path.join(directory, "." + basename + ".mov")
    yield iphone_movie
    yield fn + ".xmp"
    for i in range(1, 10):
        xmp = os.path.join(directory, f"{basename}_{i:02d}.{ext}.xmp")
        if os.path.exists(xmp):
            yield xmp
        else:
            break

base = os.path.abspath(options.base)
trash = os.path.abspath(options.trash)
if options.u:
    if options.a:
        print("Restoring all!")
        for path, dirs, files in os.walk(trash):
            for file in files:
                src = os.path.join(path, file)
                dst = os.path.join(base, os.path.relpath(src, trash))

                print("Moving:")
                print(src)
                print(dst)
                if not options.dry_run:
                    os.rename(src, dst)
    else:
        print("Restoring list!")
        with open(options.file_list, 'r') as f:
            for base_fn in f.readlines():
                full_fn = os.path.join(trash, base_fn.strip())
                for src in me_and_extras(full_fn):
                    dst = os.path.join(base, os.path.relpath(src, trash))
                    if os.path.exists(src):
                        print("Moving:")
                        print(src)
                        print(dst)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        if not options.dry_run:
                            os.rename(src, dst)
                    else:
                        print("Does not exit:", src)
else:
    print("Trashing list!")
    with open(options.file_list, 'r') as f:
        for base_fn in f.readlines():
            full_fn = os.path.join(base, base_fn.strip())
            for src in me_and_extras(full_fn):
                dst = os.path.join(trash, os.path.relpath(src, base))
                if os.path.exists(src):
                    print("Moving:")
                    print(src)
                    print(dst)
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    if not options.dry_run:
                        os.rename(src, dst)
