# ruff: noqa: I001
import os
import sys

if sys.platform == "win32":
    libs_dir = os.path.join(os.path.dirname(__file__), ".libs")
    if os.path.isdir(libs_dir):
        os.add_dll_directory(libs_dir)

from collections.abc import MutableSequence
from .hashlist_backend import HashListCpp

class hashlist(MutableSequence):
    __slots__ = ('_backend',)

    def __init__(self, iterable=None, /):
        # Если передали Си-объект напрямую (из срезов/копий) — привязываем его
        if isinstance(iterable, HashListCpp):
            self._backend = iterable
        elif isinstance(iterable, hashlist):
            self._backend = iterable._backend.copy()
        else:
            self._backend = HashListCpp(iterable)

    def append(self, item):
        self._backend.append(item)

    def extend(self, iterable):
        self._backend.extend(iterable)

    def insert(self, index, item):
        if not isinstance(index, int):
            raise TypeError("hashlist indices must be integers")
        self._backend.insert(index, item)

    def remove(self, item):
        self._backend.remove(item)

    def clear(self):
        self._backend.clear()

    def index(self, item, *args):
        if args:
            return list(self).index(item, *args)
        return self._backend.index_of(item)

    def pop(self, *args):
        return self._backend.pop(*args)

    def count(self, item):
        return self._backend.count(item)


    def sort(self, *args, **kwargs):
        items = list(self)
        items.sort(*args, **kwargs)
        self._backend.clear()
        self._backend.extend(items)

    def reverse(self):
        self._backend.reverse()

    def copy(self):
        # НАДЁЖНЫЙ ФИКС: Вызываем нативный Си-слепок памяти
        return hashlist(self._backend.copy())

    def __reversed__(self):
        for i in range(len(self) - 1, -1, -1):
            yield self[i]

    def __len__(self):
        return self._backend.__len__()

    def __getitem__(self, index):
        if isinstance(index, slice):
            # НАДЁЖНЫЙ ФИКС: Вызываем нативный Си-срез
            return hashlist(self._backend[index])
        if not isinstance(index, int):
            raise TypeError("hashlist indices must be integers or slices")
        return self._backend[index]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            items = list(self)
            items[index] = value
            self._backend.clear()
            self._backend.extend(items)
            return
        if not isinstance(index, int):
            raise TypeError("hashlist indices must be integers or slices")
        self._backend.setitem_c(index, value)

    def __delitem__(self, index):
        if isinstance(index, slice):
            items = list(self)
            del items[index]
            self._backend.clear()
            self._backend.extend(items)
            return
        if not isinstance(index, int):
            raise TypeError("hashlist indices must be integers or slices")
        self._backend.delitem_c(index)

    def __contains__(self, item):
        return self._backend.contains(item)

    def __iter__(self):
        # НАДЁЖНЫЙ ФИКС: Прямой сквозной проход по Си-итератору ядра
        return self._backend.__iter__()

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
        for _ in range(value): result.extend(self)
        return result

    def __imul__(self, value):
        if not isinstance(value, int): return NotImplemented
        if value <= 0:
            self.clear()
            return self
        old_items = list(self)
        for _ in range(value - 1): self.extend(old_items)
        return self

    def __eq__(self, other):
        if isinstance(other, hashlist): return list(self) == list(other)
        if isinstance(other, list): return list(self) == other
        return False

    def __repr__(self):
        return f"hashlist({list(self)})"

def hl(*args):
    return hashlist(args)
