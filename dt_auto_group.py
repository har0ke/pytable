from pytable.models import Image, ImageFlags, FilmRoll
from datetime import datetime, timedelta
import os

def is_raw(image):
    return image.filename.split(".")[-1].lower() not in ["jpeg", "jpg", "png"]

def consume_group_pixel_6(images):
    # print("NEXT: ", images[0])
    i = 1
    for i in range(1, len(images)):
        # print(images[i], images[i].datetime_taken, images[0].datetime_taken, images[i].datetime_taken - images[0].datetime_taken)
        if images[i].datetime_taken - images[0].datetime_taken > timedelta(milliseconds=600):
            break
    else:
        i = len(images)
    # print(i)
    if i == 1:
        # print(images[:1])
        return images[:1], images[1:]

    def priority(image):
        return - (
            image.iso - images[0].iso +
            image.aperture - images[0].aperture +
            image.exposure - images[0].exposure
        )

    sorted_images = sorted(filter(lambda image: is_raw(image) != is_raw(images[0]), images[1:i]), key=priority)

    if len(sorted_images) == 0:
        # print(images[:1])
        return images[:1], images[1:]

    group = [images[0], sorted_images[0]]

    images = images[1:]
    images.remove(sorted_images[0])
    # print(group)
    return group, images


def consume_group_burst(images, delta=None):
    if delta is None:
        delta = timedelta(seconds=1)
    i = -1
    for i in range(len(images)):
        # print(i, images[0], images[0].datetime_taken, images[i], images[i].datetime_taken, (images[i].datetime_taken - images[0].datetime_taken))
        if (images[i].datetime_taken - images[0].datetime_taken) > delta:
            break
    else:
        i += 1

    return images[:i], images[i:]

def consume_group_exposure_bracketing(images):
    seen_exposures = set([])
    seen_raw_exposures = set([])

    def trace_exposure(image):
        bias = int(image.exposure_bias * 100)
        info((image, image.datetime_taken, bias))
        if is_raw(image):
            is_new = bias not in seen_raw_exposures
            if not is_new:
                info(seen_raw_exposures, seen_exposures, bias)
            seen_raw_exposures.add(bias)
        else:
            is_new = bias not in seen_exposures
            if not is_new:
                info(seen_raw_exposures, seen_exposures, bias)
            seen_exposures.add(bias)
        return is_new

    info(images[0])
    trace_exposure(images[0])
    for i in range(1, len(images)):
        if images[i].datetime_taken - images[i - 1].datetime_taken > timedelta(seconds=1):
            info("::: Out of time")
            break

        if not trace_exposure(images[i]):
            info("::: Exposure seen")
            break
        info(images[i])

    else:
        i = len(images)

    return images[:i], images[i:]


def select_leader(images, prefer_raw):

    def leader_preference(image):
        return (
            image.flag(ImageFlags.REJECTED),
            -image.stars,
            -votes[image],
            abs(image.exposure_bias),
            (-int(is_raw(image))) if prefer_raw else int(is_raw(image)),
            image.datetime_taken
        )

    votes = {}
    for image in images:
        if image not in votes:
            votes[image] = 0
        if image.group in images:
            if image.group not in votes:
                votes[image.group] = 0
            votes[image.group] += 1

    leader = min(images, key=leader_preference)

    return leader

def info(*args):
    pass
    # print(*args)

def validate_group(images, prefer_raw):
    will_degrade = False
    has_changes = False

    leader = select_leader(images, prefer_raw)

    for image in images:
        if image.group != leader:
            if image.group == image and not image.flag(ImageFlags.REJECTED):
                # if image was group leader and was not rejected, changing the
                # group leader would degrate image
                will_degrade = True
                print("Below change would degrate dataset: MANUAL ATTENTION NEEDED.")
            print("Change group leader of {}: {} => {}".format(image, image.group, leader))
            image.group = leader
            has_changes = True

    if has_changes:
        stars = max(map(lambda image: image.stars, images))
        rejected = min(map(lambda image: image.flag(ImageFlags.REJECTED), images))
        for image in images:
            if image.flag(ImageFlags.REJECTED) != rejected:
                print("Change rejected status of {}: {} => {}".format(image, image.flag(ImageFlags.REJECTED), rejected))
                image.set_flag(ImageFlags.REJECTED, rejected)
            if image.stars != stars:
                print("Change stars of {}: {} => {}".format(image, image.stars, stars))
                image.stars = stars
        print()
    return has_changes, will_degrade


def main(date_from, force, dry_run):

    images = set([])
    for r in FilmRoll.filter():
        try:
            if datetime.strptime(os.path.split(r.folder)[-1], "%Y%m%d").date() >= date_from:
                # print(r)
                for image in Image.filter(film=r):
                    images.add(image)
            else:
                pass
                # print("not", r)
        except ValueError as e:
            print(e)
            print("Ignoring", r)

    images = sorted(filter(lambda image: image.datetime_taken, images), key=lambda image: (image.datetime_taken, -is_raw(image), image.filename))

    by_model = {}
    for image in images:
        key = (image.maker, image.model)
        if key not in by_model:
            by_model[key] = []
        by_model[key].append(image)

    n = 0
    for model, images in by_model.items():

        images = images[:]
        prefer_raw = True
        while len(images) > 0:
            if model[1].name == "DSC-RX100":
                group, images = consume_group_exposure_bracketing(images)
            elif model[1].name == "ZV-1" or model[1].name == "ILCE-6700":
                original_images = images
                group, images = consume_group_exposure_bracketing(original_images)
                group_burst, images_burst = consume_group_burst(original_images)
                if len(group_burst) > len(group):
                    group, images = group_burst, images_burst
            elif model[1].name == "Pixel 6":
                group, images = consume_group_pixel_6(images)
                prefer_raw = False

            elif (
                model[1].name == "HERO9 Black" or
                model[1].name == "HERO11 Black"
            ):
                group, images = consume_group_burst(images, timedelta(seconds=3))
                prefer_raw = False
            elif (
                model[1].name == "HERO3+ Black Edition" or
                model[1].name == "iPhone 12 mini" or
                model[1].name == "iPhone 15 Pro Max"
            ):
                group, images = images[:1], images[1:]
            else:
                if model[1].name != '':
                    for image in images:
                        print(image)
                    print("Unkown model {} - {}".format(*model))
                break

            has_changes, will_degrade = validate_group(group, prefer_raw)
            if has_changes:
                n += 1

                if not dry_run and (not will_degrade or force):
                    for image in group:
                        print("Saving {}".format(image))
                        image.save()

    print("incorrect", n)

import argparse
if __name__ == '__main__':


    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--from", dest="from_date", default=None)

    options = parser.parse_args()

    if options.from_date is None:
        from_date = datetime.now().date()
    else:
        from_date = datetime.strptime(options.from_date, "%Y%m%d").date()
    main(from_date, options.force, not options.save)
