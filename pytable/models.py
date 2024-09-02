from .database import db_library, db_data
from .fields import DarktableTimestampField, ModuleOrderListField, EnumField
from .types import ImageFlags, v30_jpg_order, v30_order, IOPOrderType, legacy_order, Color
from .modules import DT_MODULES, Module

from typing import List
import peewee as pw

import datetime

class FilmRoll(pw.Model):
    """
    A darktable filmroll.
    """
    access_timestamp: datetime.datetime = DarktableTimestampField() # type: ignore
    folder: str = pw.CharField(1024) # type: ignore

    def __str__(self):
        return self.folder

    class Meta:
        db_table = 'film_rolls'
        database = db_library

class Maker(pw.Model):

    name: str = pw.CharField() # type: ignore

    def __str__(self) -> str:
        return self.name

    class Meta:
        db_table = 'makers'
        database = db_library

class Model(pw.Model):

    name: str = pw.CharField() # type: ignore

    def __str__(self) -> str:
        return self.name

    class Meta:
        db_table = 'models'
        database = db_library

class Lens(pw.Model):

    name: str = pw.CharField() # type: ignore

    def __str__(self) -> str:
        return self.name

    class Meta:
        db_table = 'lens'
        database = db_library

class Camera(pw.Model):

    name: str = pw.CharField() # type: ignore

    class Meta:
        db_table = 'cameras'
        database = db_library

class Image(pw.Model):
    """
    A darktable image.
    """
    id: int = pw.IntegerField(primary_key=True) # type: ignore
    group = pw.ForeignKeyField('self')
    film = pw.ForeignKeyField(FilmRoll)

    # Image width in pixels
    width: int = pw.IntegerField() # type: ignore
    # Image height in pixels
    height: int = pw.IntegerField() # type: ignore

    # The filename of the image
    filename: str = pw.CharField() # type: ignore

    # The maker of the camera used to capture this picture
    maker = pw.ForeignKeyField(Maker)
    # The model of the camera used to capture this picture
    model = pw.ForeignKeyField(Model)
    # The lens used to capture this picture
    lens = pw.ForeignKeyField(Lens)
    # The camera used to capture this picture
    camera = pw.ForeignKeyField(Camera)

    # The exposure used to capture this picture
    exposure = pw.FloatField()
    # The aperture used to capture this picture
    aperture = pw.FloatField()
    # The iso used to capture this picture
    iso = pw.FloatField()
    # The focal length used to capture this picture
    focal_length = pw.FloatField()
    # The focus distance used to capture this picture
    focus_distance = pw.FloatField()

    # The date this picture was taken
    datetime_taken: datetime.datetime = DarktableTimestampField(utc=True, origin=datetime.datetime(1, 1, 1)) # type: ignore

    # The flags attached to this picture. To read individual flags, see 'flag()' function
    flags: int = pw.IntegerField() # type: ignore

    output_width: int = pw.IntegerField() # type: ignore
    output_height: int = pw.IntegerField() # type: ignore
    crop = pw.DoubleField()

    raw_parameters: int = pw.IntegerField() # type: ignore
    # raw_denoise_threshold = pw.DoubleField()
    # raw_auto_bright_threshold = pw.DoubleField()
    raw_black: int = pw.IntegerField() # type: ignore
    raw_maximum: int = pw.IntegerField() # type: ignore

    # license: str = pw.CharField() # type: ignore

    # sha1sum = pw.FixedCharField(40)

    orientation: int = pw.IntegerField() # type: ignore

    # histogram = pw.BlobField()
    # lightmap = pw.BlobField()

    longitude = pw.DoubleField()
    latitude = pw.DoubleField()
    altitude = pw.DoubleField()

    color_matrix = pw.BlobField()

    colorspace: int = pw.IntegerField() # type: ignore
    version: int = pw.IntegerField() # type: ignore
    max_version: int = pw.IntegerField() # type: ignore
    write_timestamp: datetime.datetime = DarktableTimestampField() # type: ignore
    history_end: int = pw.IntegerField() # type: ignore
    position: int = pw.IntegerField() # type: ignore

    aspect_ratio = pw.DoubleField()
    exposure_bias = pw.DoubleField()

    datetime_imported: datetime.datetime = DarktableTimestampField(origin=datetime.datetime(1, 1, 1), column_name="import_timestamp") # type: ignore
    datetime_changed: datetime.datetime = DarktableTimestampField(origin=datetime.datetime(1, 1, 1), column_name="change_timestamp") # type: ignore
    datetime_exported: datetime.datetime = DarktableTimestampField(origin=datetime.datetime(1, 1, 1), column_name="export_timestamp") # type: ignore
    datetime_printed: datetime.datetime = DarktableTimestampField(origin=datetime.datetime(1, 1, 1), column_name="print_timestamp") # type: ignore
    datetime_thumb: datetime.datetime = DarktableTimestampField(origin=datetime.datetime(1, 1, 1), column_name="thumb_timestamp") # type: ignore
    thumb_maxmip: int = pw.IntegerField() # type: ignore

    def flag(self, flag):
        return bool(self.flags & flag.value)

    def set_flag(self, flag, value):
        b = -1
        assert flag
        flag = flag.value
        while flag:
            b += 1
            flag = flag >> 1
        self.flags = (self.flags & ~flag) | (value & flag)



    @property
    def stars(self):
        return self.flags & 0x7

    @stars.setter
    def stars(self, value):
        self.flags = (self.flags & ~0x7) | (value & 0x7)

    def __str__(self):
        return self.filename

    history: pw.BackrefAccessor
    module_order: pw.BackrefAccessor

    def get_ordered_active_modules(self):

        # nextline: type: ignore
        active_history = (self.history
            .order_by(HistoryEntry.num.asc()) # type: ignore
            .where(HistoryEntry.num < self.history_end))

        if len(active_history) == 0:
            return []

        module_orders = self.module_order.select()
        module_order = module_orders[0]
        iop_list = None
        if module_order.version == IOPOrderType.CUSTOM:
            iop_list = module_order.iop_list
        elif module_order.version == IOPOrderType.V30:
            iop_list = [(v, 0) for v in v30_order]
        elif module_order.version == IOPOrderType.V30_JPG:
            iop_list = [(v, 0) for v in v30_jpg_order]
        elif module_order.version == IOPOrderType.LEGACY:
            iop_list = [(v, 0) for v in legacy_order]
        else:
            raise NotImplementedError()

        # Override if iop_list exists for the case that
        # 'module_order.version != CUSTOM'... Is this a bug in dt?
        if module_order.iop_list:
            iop_list = module_order.iop_list

        iop_list = {iop_list[i]: i for i in range(len(iop_list))}

        active_modules = {}
        for he in active_history:
            if he.enabled:
                active_modules[(he.module_name, he.instance)] = he.module
            elif (he.module_name, he.instance) in active_modules:
                del active_modules[(he.module_name, he.instance)]

        active_modules = sorted(active_modules.items(), key=lambda kv: iop_list[kv[0]])
        return list(map(lambda kv: kv[1], active_modules))

    class Meta:
        db_table = 'images'
        database = db_library # This model uses the "people.db" database``

class ColorLabel(pw.Model):

    image: Image = pw.ForeignKeyField(Image, column_name='imgid') # type: ignore
    color: Color = EnumField(Color) # type: ignore

    class Meta:
        primary_key = False
        db_table = 'color_labels'
        database = db_library

class HistoryEntry(pw.Model):
    """
    A darktable filmroll.
    """
    image: Image = pw.ForeignKeyField(Image, column_name="imgid", backref="history") # type: ignore
    num: int = pw.IntegerField() # type: ignore

    module_name: str = pw.CharField(256, column_name="operation") # type: ignore
    version: int = pw.IntegerField(column_name="module") # type: ignore
    params: bytes = pw.BlobField(column_name="op_params") # type: ignore

    enabled: bool = pw.BooleanField() # type: ignore

    blendop_version: int = pw.IntegerField() # type: ignore
    blendop_params: bytes = pw.BlobField() # type: ignore

    instance: int = pw.IntegerField(column_name="multi_priority") # type: ignore
    name: str = pw.CharField(256, column_name="multi_name") # type: ignore
    name_hand_edited: int = pw.IntegerField(column_name="multi_name_hand_edited") # type: ignore

    @property
    def module(self):
        for cls in DT_MODULES:
            if cls.NAME == self.module_name and cls.VERSION == self.version:
                return cls(self.instance, self.params)
        return Module(self.instance, self.params, module_name=self.module_name)

    def __str__(self):
        return "%3d - %sv%d-%s" % (
            self.num, self.module_name, self.version, self.instance)

    class Meta:
        primary_key = False
        db_table = 'history'
        database = db_library


class ModuleOrderEntry(pw.Model):
    """
    A darktable filmroll.
    """
    image: Image = pw.ForeignKeyField(Image, column_name="imgid", backref="module_order") # type: ignore
    version: IOPOrderType = EnumField(IOPOrderType) # type: ignore
    iop_list = ModuleOrderListField()

    def __str__(self):
        return str((self.version, self.iop_list))

    class Meta:
        primary_key = False
        db_table = 'module_order'
        database = db_library

class Tag(pw.Model):

    name: str = pw.CharField() # type: ignore
    synonyms: str = pw.CharField() # type: ignore
    flags: int = pw.IntegerField() # type: ignore

    class Meta:
        db_table = 'tags'
        database = db_data

class TaggedImages(pw.Model):

    image: Image = pw.ForeignKeyField(Image, backref='tags', column_name='imgid') # type: ignore
    tag: Tag = pw.ForeignKeyField(Tag, backref='images', column_name='tagid') # type: ignore

    class Meta:
        primary_key = False
        db_table = 'tagged_images'
        database = db_library
