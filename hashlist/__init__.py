# ruff: noqa: I001
import os
import sys

if sys.platform == "win32":
    libs_dir = os.path.join(os.path.dirname(__file__), ".libs")
    if os.path.isdir(libs_dir):
        os.add_dll_directory(libs_dir)

from collections.abc import MutableSequence
from .hashlist_backend import HashListCpp as _HashListCpp


class hashlist(_HashListCpp, MutableSequence):
    """Высокопроизводительная замена list с O(1) поиском на нативном C-ядре.

    Горячие методы (append/extend/insert/remove/pop/clear/count/sort/reverse/
    copy/len/getitem/setitem(срезы через C?):int/contains/iter) наследуются
    непосредственно от C-класса HashListCpp: вызов h.append(x) — прямой
    C-вызов уровня list.append, без Python-кадра.

    Python-слой добавляет только редкие протокольные добивки (арифметика,
    сортировка с key/reverse, index со start/stop, срезовые setitem/delitem).
    """

    __slots__ = ()

    def index(self, item, *args):
        if args:
            return list(self).index(item, *args)
        return _HashListCpp.index_of(self, item)

    def sort(self, *args, **kwargs):
        if not args and not kwargs:
            # Нативный Timsort CPython поверх ленты указателей
            _HashListCpp.sort(self)
            return
        items = list(self)
        items.sort(*args, **kwargs)
        self.clear()
        self.extend(items)

    def __reversed__(self):
        for i in range(len(self) - 1, -1, -1):
            yield self[i]

    def __setitem__(self, index, value):
        if isinstance(index, slice):
            items = list(self)
            items[index] = value
            self.clear()
            self.extend(items)
            return
        self.setitem_c(index, value)

    def __delitem__(self, index):
        if isinstance(index, slice):
            items = list(self)
            del items[index]
            self.clear()
            self.extend(items)
            return
        self.delitem_c(index)

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
        if isinstance(other, hashlist):
            return list(self) == list(other)
        if isinstance(other, list):
            return list(self) == other
        return False

    def __reduce__(self):
        # Pickle-поддержка: пересобираем через публичный конструктор.
        # Самоссылочные контейнеры (h.append(h)) не сериализуются.
        return (hashlist, (list(self),))

    def __repr__(self):
        return f"hashlist({list(self)})"


def hl(*args):
    return hashlist(args)
