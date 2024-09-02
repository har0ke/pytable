from pytable.models import Image, ImageFlags, FilmRoll

from datetime import datetime
import peewee as pw
import os
import shutil


query = Image.filter()

output_folder = "output"
for image in query:
    assert isinstance(image, Image)
    if image.stars >= 3 and (not image.group or image.group == image):

        print(image)

        image_path = os.path.join(image.film.folder, image.filename)

        output_path = os.path.join(output_folder, os.path.splitext(image.filename)[0] + ".jpg")


        if os.path.exists(output_path):
            continue
        command = [
            'darktable-cli',
            '--width', '1920',
            '--hq', 'true',
            image_path,
            output_path
        ]

        import subprocess
        subprocess.call(command)
