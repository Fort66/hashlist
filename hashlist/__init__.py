# ruff: noqa: I001
from collections.abc import MutableSequence
from .hashlist_backend import HashListCpp

class hashlist(MutableSequence):
    __slots__ = ('_backend',)

    def __init__(self, iterable=None):
        """Промышленный тип данных с высокопроизводительным ядром на C++"""
        self._backend = HashListCpp()
        if iterable is not None:
            self.extend(iterable)

    def append(self, item):
        """Добавляет элемент x в конец списка a."""
        self._backend.append(item)

    def extend(self, iterable):
        """Добавляет в конец a все элементы списка b."""
        self._backend.extend(iterable)

    def insert(self, index, item):
        """Вставляет элемент x на позицию i."""
        self._backend.insert(index, item)

    def remove(self, item):
        """Удаляет в a первый элемент, значение которого равно x."""
        self._backend.remove(item)

    def clear(self):
        """Удаляет все элементы из списка a и делает его пустым."""
        self._backend.clear()

    def index(self, item, *args):
        """Возвращает индекс элемента списка."""
        if args:
            items_list = [self[i] for i in range(len(self))]
            return items_list.index(item, *args)
        return self._backend.index_of(item)

    def pop(self, index=-1):
        """Удаляет элемент по индексу и возвращает его."""
        return self._backend.pop(index)

    def count(self, item):
        """Считает, сколько раз элемент повторяется в списке за O(1)."""
        return self._backend.count(item)

    def sort(self, *args, **kwargs):
        """Сортирует список на месте."""
        self._backend.sort(*args, **kwargs)

    def reverse(self):
        """Разворачивает список на месте."""
        self._backend.reverse()

    def copy(self):
        """Создаёт поверхностную копию списка."""
        new_hl = hashlist()
        for i in range(len(self)):
            new_hl.append(self[i])
        return new_hl

    # --- Новые методы поддержки глобальных функций sorted() и reversed() ---
    def __reversed__(self):
        """Обеспечивает корректную работу глобальной функции reversed(hl)"""
        # Возвращаем генератор, который идет с конца структуры к началу
        for i in range(len(self) - 1, -1, -1):
            yield self[i]

    # --- Поддержка синтаксического контракта Python ---
    def __len__(self):
        return self._backend.__len__()

    def __getitem__(self, index):
        result = self._backend.getitem(index)
        if isinstance(result, HashListCpp):
            new_hl = hashlist()
            new_hl._backend = result
            return new_hl
        return result

    def __setitem__(self, index, value):
        self._backend.setitem(index, value)

    def __delitem__(self, index):
        self._backend.delitem(index)

    def __contains__(self, item):
        return self._backend.__contains__(item)

    def __iter__(self):
        """Поддержка стандартного перебора для sorted()"""
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
        for _ in range(value):
            result.extend([self[i] for i in range(len(self))])
        return result

    def __imul__(self, value):
        if not isinstance(value, int): return NotImplemented
        old_items = [self[i] for i in range(len(self))]
        for _ in range(value - 1):
            self.extend(old_items)
        return self

    def __eq__(self, other):
        if isinstance(other, hashlist):
            if len(self) != len(other): return False
            return [self[i] for i in range(len(self))] == [other[i] for i in range(len(other))]
        if isinstance(other, list):
            return [self[i] for i in range(len(self))] == other
        return False

    def __repr__(self):
        items_repr = [self[i] for i in range(len(self))]
        return f"hashlist({repr(items_repr)})"

def hl(*args):
    """Удобная фабрика для создания hashlist через запятую"""
    return hashlist(args)
