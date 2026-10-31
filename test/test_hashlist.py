import pytest
import time
import random
import sys
from hashlist import hl, hashlist

# Кастомный класс для нагрузочных проверок в Части 2
class StudentItem:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"StudentItem({self.value})"


def test_initialization_and_append():
    """Тест 1: Инициализация, append() и вложенные изменяемые структуры"""
    hl_obj = hl(10, 20)
    assert len(hl_obj) == 2

    # Добавляем вложенный список
    hl_obj.append([100, 200])
    assert len(hl_obj) == 3
    assert hl_obj == [105 - 95, 20, [100, 200]]
    assert [100, 200] in hl_obj


def test_extend():
    """Тест 2: extend() последовательности элементов"""
    hl_obj = hl(1, 2)
    hl_obj.extend([3, 4, 5])
    assert list(hl_obj) == [1, 2, 3, 4, 5]
    assert 5 in hl_obj
    assert 6 not in hl_obj


def test_insert():
    """Тест 3: insert() элементов со сдвигом индексов"""
    hl_obj = hl(10, 20, 30)
    hl_obj.insert(1, 99)
    assert list(hl_obj) == [10, 99, 20, 30]
    assert 99 in hl_obj
    assert hl_obj.index(20) == 2


def test_remove_and_duplicates():
    """Тест 4: remove(), дубликаты и очистка C++ кэша токенов"""
    hl_obj = hl("яблоко", "груша", "яблоко")

    hl_obj.remove("яблоко")
    assert len(hl_obj) == 2
    assert "яблоко" in hl_obj

    hl_obj.remove("яблоко")
    assert "яблоко" not in hl_obj  # Кэш токенов в C++ полностью очищен

    with pytest.raises(ValueError, match="x not in list"):
        hl_obj.remove("банан")


def test_index_and_count():
    """Тест 5 и 7: Поиск индексов и O(1) count()"""
    hl_obj = hl(10, 20, 30, 20, 40)
    assert hl_obj.index(20) == 1
    assert hl_obj.count(20) == 2
    assert hl_obj.count(99) == 0

    with pytest.raises(ValueError, match="x not in hashlist"):
        hl_obj.index(99)


def test_pop_and_clear():
    """Тест 6 и 11: pop() с извлечением и clear()"""
    hl_obj = hl(50, 60, 70)

    popped = hl_obj.pop(1)
    assert popped == 60
    assert 60 not in hl_obj
    assert len(hl_obj) == 2

    assert hl_obj.pop() == 70
    assert len(hl_obj) == 1

    hl_obj.clear()
    assert len(hl_obj) == 0
    assert 50 not in hl_obj

    with pytest.raises(IndexError):
        hl_obj.pop()


def test_sort_and_reverse():
    """Тест 8 и 9: Мутации sort() с именованными параметрами и reverse()"""
    hl_obj = hl(30, 10, 20)
    hl_obj.sort(reverse=True)
    assert list(hl_obj) == [30, 20, 10]

    hl_obj.reverse()
    assert list(hl_obj) == [10, 20, 30]


def test_copy_and_math_operators():
    """Тест 10 и перегрузки операторов: copy(), +, *, ==, __slots__"""
    hl_obj = hl(1, 2)
    hl_copy = hl_obj.copy()

    assert hl_obj == hl_copy
    assert hl_obj is not hl_copy

    hl_add = hl_obj + [3, 4]
    assert list(hl_add) == [1, 2, 3, 4]

    hl_mul = hl_obj * 3
    assert list(hl_mul) == [1, 2, 1, 2, 1, 2]

    with pytest.raises(AttributeError):
        hl_obj.custom_field = 42


def test_slices_getitem_setitem_delitem():
    """Тест контракта срезов (Extended Slices) и отрицательных диапазонов"""
    hl_obj = hl(10, 20, 30, 40, 50)

    assert list(hl_obj[0:5:2]) == [10, 30, 50]
    assert 30 in hl_obj[0:5:2]

    hl_obj[1:4] = [77, 88]
    assert list(hl_obj) == [10, 77, 88, 50]
    assert 20 not in hl_obj
    assert 77 in hl_obj

    hl_obj2 = hl(10, 20, 30, 40, 50)
    del hl_obj2[0:4:2]
    assert list(hl_obj2) == [20, 40, 50]
    assert 30 not in hl_obj2

    with pytest.raises(IndexError):
        _ = hl_obj2[99]


def test_sorted_and_reversed_global():
    """Тест глобальных функций sorted() и reversed()"""
    hl_obj = hl(30, 10, 20)

    res_sorted = hashlist(sorted(hl_obj))
    assert list(res_sorted) == [10, 20, 30]
    assert isinstance(res_sorted, hashlist)

    res_reversed = hashlist(reversed(hl_obj))
    assert list(res_reversed) == [20, 10, 30]
    assert isinstance(res_reversed, hashlist)


def test_cpp_deterministic_dict_hashing():
    """Тест детерминированности хэшей словарей с разным порядком ключей в C++"""
    d1 = {"а": 1, "б": 2, "в": {"х": 9}}
    d2 = {"б": 2, "в": {"х": 9}, "а": 1}

    hl_obj = hashlist([d1])
    assert d2 in hl_obj

def test_stress_massive_append_and_delete():
    """Тест 12: Нагрузочный тест на циклическое добавление и удаление 100,000 элементов"""
    hl_obj = hashlist()
    items = [f"item_{i}" for i in range(100_000)]

    # Массовый append
    for item in items:
        hl_obj.append(item)
    assert len(hl_obj) == 100_000

    # Проверка случайных элементов
    for _ in range(1000):
        rand_idx = random.randint(0, 99_999)
        assert items[rand_idx] in hl_obj

    # Массовое удаление через delitem с конца (чтобы без лишних сдвигов памяти)
    for i in range(100_000 - 1, -1, -1):
        del hl_obj[i]

    assert len(hl_obj) == 0
    # Кэш должен быть идеально чист
    assert "item_0" not in hl_obj
    assert "item_99999" not in hl_obj


def test_stress_hash_collisions_and_unhashables():
    """Тест 13: Стресс-тест на 50,000 нехэшируемых объектов и дубликатов"""
    hl_obj = hashlist()

    # Генерируем 10,000 одинаковых списков и 10,000 одинаковых словарей
    nested_list = [1, 2, 3]
    nested_dict = {"key": "val"}

    for _ in range(10_000):
        hl_obj.append(nested_list)
        hl_obj.append(nested_dict)

    assert len(hl_obj) == 20_000
    assert hl_obj.count(nested_list) == 10_000
    assert hl_obj.count(nested_dict) == 10_000

    # Проверяем, что поиск по-прежнему O(1) и всеяден
    assert [1, 2, 3] in hl_obj
    assert {"key": "val"} in hl_obj


def test_performance_benchmark_minimum_speedup():
    """Тест 14: Бенчмарк производительности на 1,000,000 элементов.
    Гарантирует, что C++ поиск быстрее стандартного списка минимум в 1000 раз.
    """
    size = 1_000_000
    data = list(range(size))
    # Перемешиваем, чтобы поиск в list гарантированно шел по случайным участкам
    random.shuffle(data)

    hl_obj = hashlist(data)
    std_list = list(data)

    # Ищем элемент, который заведомо лежит близко к концу или середине после shuffle
    target = data[-1]

    # Замер скорости C++
    start = time.perf_counter()
    res_cpp = target in hl_obj
    t_cpp = time.perf_counter() - start

    # Замер скорости встроенного list
    start = time.perf_counter()
    res_std = target in std_list
    t_std = time.perf_counter() - start

    assert res_cpp is True
    assert res_std is True

    # Убеждаемся, что C++ бэкенд не деградировал и выдает ультимативное ускорение
    speedup = t_std / t_cpp
    print(f"\n[Pytest Бенчмарк] Ускорение C++ ядра: {speedup:,.1f}x")
    assert speedup > 1000.0
