import peewee as pw

import datetime
import itertools

class DarktableTimestampField(pw.TimestampField):
    """
    Darktable not always stores timestamps as UNIX timestamps with origin of
    1970-01-01, but sometimes 0001-01-01. This timestamp field lets the user
    specifiy what origin to use for the timestamp.
    """

    def __init__(self, *args, origin=datetime.datetime(1970, 1, 1), **kwargs) -> None:
        kwargs['resolution'] = 10**6
        self.epoch_diff = (datetime.datetime(1970, 1, 1) - origin).total_seconds()
        super().__init__(*args, **kwargs)

    def python_value(self, value):
        if value is None or value == -1:
            return None
        return super().python_value(value - self.epoch_diff * self.resolution)

    def db_value(self, value):
        if value is None or value == -1:
            return -1

        if isinstance(value, datetime.datetime):
            pass
        elif isinstance(value, datetime.date):
            value = datetime.datetime(value.year, value.month, value.day)
        else:
            raise ValueError()

        return super().db_value(value) + self.epoch_diff * self.resolution

class ModuleOrderListField(pw.CharField):

    def db_value(self, value):
        print("db_value")
        value = super().db_value(value)
        if hasattr(value, "__item__"):
            new_value = ",".join([str(v) for v in itertools.chain(*value)])
            print(value, new_value)
            return new_value
        print(value)
        return value

    def python_value(self, value):
        value = super().python_value(value)
        if isinstance(value, str):
            values = value.split(",")
            assert len(values) % 2 == 0
            new_value = [
                (values[i * 2], int(values[i * 2 + 1]))
                for i in range(int(len(values) / 2))]
            return new_value
        return value

class EnumField(pw.IntegerField):

    def __init__(self, enum_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.enum_type = enum_type

    def db_value(self, value):
        return value.value

    def python_value(self, value):
        return self.enum_type(super().python_value(value))
