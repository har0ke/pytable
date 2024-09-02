import subprocess
from dataclasses import dataclass
from typing import List, Callable, Any, Optional
import functools
import inspect
import sys
import os
import datetime
import traceback

from video import VideoModel, Video, BASE_DIR
from typing import Tuple


TRASH_DT_FORMAT = "%Y-%m-%dT%H:%M:%S"
TRASH = "/home/oke/.local/share/Trash"
TRASH_INFO = os.path.join(TRASH, "info")
TRASH_FILES = os.path.join(TRASH, "files")

import json
from typing import Generic, TypeVar

T = TypeVar('T')
V = TypeVar('V')

class ActionException(Exception):

    def __init__(self, message, *args: object) -> None:
        self.message = message
        super().__init__(*args)

    def __repr__(self) -> str:
        return f"<Exception: '{self.message}'>"

class ActionFailed(ActionException):
    ...

class ActionIncomplete(ActionException):
    ...

import uuid
class UndoableAction(Generic[T]):

    ID = "OverrideMe"

    def __init__(self, args: T, group_leader=None, uid=None):
        self.args: T = args
        self.uuid = uid
        if self.uuid is None:
            self.uuid = group_leader.uuid if group_leader else uuid.uuid4().hex

    def undo_action(self) -> "UndoableAction[Any]": ...

    def run(self, model: VideoModel) -> Optional[bool]: ...


class RestoreFromTrash(UndoableAction[str]):

    def undo_action(self) -> UndoableAction[Any]:
        return Trash(self.args)

    def __str__(self) -> str:
        return f"Restoring {self.args}"

    @staticmethod
    def trashed_files():
        for fn in os.listdir(TRASH_INFO):
            if fn.endswith('.trashinfo'):
                with open(os.path.join(TRASH_INFO, fn), 'r') as f:
                    lines_iter = iter(f)
                    if next(lines_iter) != '[Trash Info]\n':
                        print("Invalid trashinfo file: ", fn)
                        continue
                    path = None
                    date = None
                    for line in f:
                        line = line.strip()
                        if path is None and line.startswith('Path='):
                            path = line[5:]
                        if date is None and line.startswith('DeletionDate='):
                            date = datetime.datetime.strptime(line[13:], TRASH_DT_FORMAT)
                    if path is None or date is None:
                        print("Invalid trashinfo file: ", fn)
                        continue
                    trash_file = os.path.join(TRASH_FILES, fn[:-10])
                    if not os.path.exists(trash_file):
                        print("Trashed file does not exist: ", trash_file)
                        continue
                    yield (date, trash_file, path)


    def run(self, model):
        file = self.args
        matches = sorted(((date, trash_file) for (date, trash_file, path) in self.trashed_files() if path == self.args), reverse=True)
        if len(matches) == 0:
            raise ActionFailed("Could not find trashed file")
        try:
            os.rename(matches[0][1], file)
        except Exception as e:
            traceback.print_exception(e)
            raise ActionFailed("Could not move file to original destination...")
        try:
            os.remove(os.path.join(TRASH_INFO, os.path.basename(file) + ".trashinfo"))
        except Exception as e:
            traceback.print_exception(e)

        return True



class Trash(UndoableAction[str]):

    def undo_action(self) -> UndoableAction[Any]:
        return RestoreFromTrash(self.args)

    def __str__(self) -> str:
        return f"Trashing {self.args}"

    def run(self, model: VideoModel):
        file = os.path.abspath(os.path.expanduser(self.args))
        i = 0
        suffix = ""
        while True:
            info_fn = os.path.join(TRASH_INFO, os.path.basename(file) + suffix + ".trashinfo")
            try:
                with open(info_fn, 'x') as f:
                    f.write(
                        "[Trash Info]\n"
                        f"Path={file}\n"
                        f"DeletionDate={datetime.datetime.now().strftime(TRASH_DT_FORMAT)}\n"
                    )
            except FileExistsError:
                i += 1
                suffix = f"_{i}"
                continue

            trash_fn = os.path.join(TRASH_FILES, os.path.basename(file) + suffix)
            if os.path.exists(trash_fn):
                os.remove(info_fn)
                i += 1
                suffix = f"_{i}"
                continue
            os.rename(file, trash_fn)
            index, video = model.find_video(Video(self.args))
            if index:
                model.remove(index)
            break

class SetVideoStars(UndoableAction[Tuple[str, bool, int, bool, int]]):

    def run(self, model: VideoModel):
        file, old_reject, old_rating, new_reject, new_rating = self.args
        index, video = model.find_video(Video(file))
        video.metadata.rejected = new_reject
        video.metadata.rating = new_rating
        video.save_metadata()
        if index:
            model.dataChanged.emit(index, index)

    def undo_action(self) -> UndoableAction[Any]:
        file, old_reject, old_rating, new_reject, new_rating = self.args
        return SetVideoStars((file, new_reject, new_rating, old_reject, old_rating))

    def __str__(self):
        file, old_reject, old_rating, new_reject, new_rating = self.args
        return f"{file}: rejected status ({old_reject} -> {new_reject}) and rating ({old_rating} -> {new_rating})"

class UndoableActionList:

    def __init__(self, fn: str) -> None:
        self._data: List[UndoableAction] = []
        self._fn: str = fn
        self._load()

    def _load(self):
        with open(self._fn, "a") as f:
            pass

        self.f = open(self._fn, 'r+')

        for line in self.f:
            ID, uuid, args = json.loads(line.strip())

            revert_fns = [obj for name, obj in inspect.getmembers(sys.modules[__name__])
                          if inspect.isclass(obj) and name == ID]
            assert len(revert_fns) == 1
            self._data.append(revert_fns[0](args, uid=uuid))
        self.f.seek(0, os.SEEK_END)

    def append(self, action: UndoableAction):
        json.dump((action.__class__.__name__, action.uuid, action.args), self.f)
        self.f.write("\n")
        self.f.flush()
        self._data.append(action)

    def pop(self, uuid=None):
        if not self._data:
            return None
        if uuid and self._data[-1].uuid != uuid:
            return None
        action = self._data.pop()
        self._remove_line()
        return action

    def clear(self):
        self._data = []
        self.f.seek(0, os.SEEK_SET)
        self.f.truncate()
        self.f.flush()

    def _remove_line(self):
        pos = self.f.tell() - 1

        if pos == -1:
            return

        while pos > 0 and self.f.read(1) != "\n":
            pos -= 1
            self.f.seek(pos, os.SEEK_SET)
        if pos != 0:
            pos += 1
        self.f.seek(pos, os.SEEK_SET)
        self.f.truncate()
        self.f.flush()

class HistoryManager:

    def __init__(self) -> None:
        self.history = UndoableActionList(os.path.join(BASE_DIR, "vmgr.history"))
        self.future = UndoableActionList(os.path.join(BASE_DIR, "vmgr.redo"))

    def apply(self, model, *actions: UndoableAction):
        should_reload = False
        self.future.clear()
        for action in actions:
            print(action)
            should_reload = action.run(model) or should_reload
            self.history.append(action)
        if should_reload:
            model.reload()
        else:
            model.update()

    @staticmethod
    def move(stack_1: UndoableActionList, stack_2, model, undo):
        action: Optional[UndoableAction] = stack_1.pop()
        should_reload = False
        while action is not None:
            try:
                if undo:
                    print(action.undo_action())
                    should_reload = action.undo_action().run(model) or should_reload
                else:
                    print(action)
                    should_reload = action.run(model) or should_reload
            except:
                stack_1.append(action)
                raise
            stack_2.append(action)
            action = stack_1.pop(action and action.uuid)
        return should_reload

    def undo(self, model):
        should_reload = self.move(self.history, self.future, model, True)
        if should_reload:
            model.reload()
        else:
            model.update()

    def redo(self, model: VideoModel):
        should_reload = self.move(self.future, self.history, model, False)
        if should_reload:
            model.reload()
        else:
            model.update()



