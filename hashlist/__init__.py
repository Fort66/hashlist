# ruff: noqa: I001
import os
import sys

if sys.platform == "win32":
    libs_dir = os.path.join(os.path.dirname(__file__), ".libs")
    if os.path.isdir(libs_dir):
        os.add_dll_directory(libs_dir)
    elif os.path.isdir(r"C:\msys64\ucrt64\bin"):
        os.add_dll_directory(r"C:\msys64\ucrt64\bin")

from collections.abc import MutableSequence
from .hashlist_backend import HashListCpp

class hashlist(MutableSequence):
    __slots__ = ('_backend',)

    def __init__(self, iterable=None):
        self._backend = HashListCpp(iterable)

    def append(self, item):
        self._backend.append(item)

    def extend(self, iterable):
        self._backend.extend(iterable)

    def insert(self, index, item):
        items = [self[i] for i in range(len(self))]
        items.insert(index, item)
        self._backend.clear()
        self._backend.extend(items)

    def remove(self, item):
        self._backend.remove(item)

    def clear(self):
        self._backend.clear()

    def index(self, item, *args):
        if args:
            items_list = [self[i] for i in range(len(self))]
            return items_list.index(item, *args)
        return self._backend.index_of(item)
    def pop(self, *args):
        # Распаковываем кортеж аргументов напрямую в C API парсер
        return self._backend.pop(*args)

    def count(self, item):
        return self._backend.count(item)

    def sort(self, *args, **kwargs):
        items = [self[i] for i in range(len(self))]
        items.sort(*args, **kwargs)
        self._backend.clear()
        self._backend.extend(items)

    def reverse(self):
        self._backend.reverse()

    def copy(self):
        return hashlist(self)

    def __reversed__(self):
        for i in range(len(self) - 1, -1, -1):
            yield self[i]

    def __len__(self):
        return self._backend.__len__()

    def __getitem__(self, index):
        if isinstance(index, slice):
            items = [self[i] for i in range(len(self))]
            return hashlist(items[index])
        if not isinstance(index, int):
            raise TypeError("hashlist indices must be integers or slices")
        return self._backend[index]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            items = [self[i] for i in range(len(self))]
            items[index] = value
            self._backend.clear()
            self._backend.extend(items)
            return
        if not isinstance(index, int):
            raise TypeError("hashlist indices must be integers or slices")
        items = [self[i] for i in range(len(self))]
        items[index] = value
        self._backend.clear()
        self._backend.extend(items)

    def __delitem__(self, index):
        if isinstance(index, slice):
            items = [self[i] for i in range(len(self))]
            del items[index]
            self._backend.clear()
            self._backend.extend(items)
            return
        if not isinstance(index, int):
            raise TypeError("hashlist indices must be integers or slices")
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError("hashlist deletion index out of range")
        self._backend.pop(index)

    def __contains__(self, item):
        return self._backend.contains(item)

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __add__(self, other):
        if not hasattr(other, '__iter__'): return NotImplemented
        result = self.copy()
        result.extend(other)
        return result

    def __iadd__(self, other):
        if not hasattr(other, '__iter__'): return NotImplemented
        self.extend(other)
        return self

    def __mul__(self, value):
        if not isinstance(value, int): return NotImplemented
        result = hashlist()
        if value <= 0: return result
        for _ in range(value):
            result.extend(self)
        return result

    def __imul__(self, value):
        if not isinstance(value, int): return NotImplemented
        if value <= 0:
            self.clear()
            return self
        old_items = list(self)
        for _ in range(value - 1):
            self.extend(old_items)
        return self

    def __eq__(self, other):
        if isinstance(other, hashlist):
            if len(self) != len(other): return False
            return list(self) == list(other)
        if isinstance(other, list):
            return list(self) == other
        return False

    def __repr__(self):
        return f"hashlist({list(self)})"

def hl(*args):
    return hashlist(args)
