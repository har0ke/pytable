import peewee as pw
import sys
import os


if sys.platform == "linux":
    db_library = pw.SqliteDatabase(
        os.path.expanduser('~/.config/darktable/library.db'))
    db_data = pw.SqliteDatabase(
        os.path.expanduser('~/.config/darktable/data.db'))
else:
    db = pw.SqliteDatabase(None)
    db_data = pw.SqliteDatabase(None)

def open_sqlite_db(sqlite_fn):
    global db
    db = pw.init(sqlite_fn)
