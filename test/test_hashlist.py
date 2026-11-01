import pytest
import time
import random
import sys
from hashlist import hl, hashlist

class StudentItem:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"StudentItem({self.value})"


def test_initialization_and_append():
    """Тест 1: Инициализация, append() и вложенные изменяемые структуры"""
    hl_obj = hl(10, 20)
    assert len(hl_obj) == 2

    hl_obj.append([100, 200])
    assert len(hl_obj) == 3
    assert hl_obj == [10, 20, [100, 200]]
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
    """Тест 4: remove(), дубликаты и очистка Си кэша токенов"""
    hl_obj = hl("яблоко", "груша", "яблоко")

    hl_obj.remove("яблоко")
    assert len(hl_obj) == 2
    assert "яблоко" in hl_obj

    hl_obj.remove("яблоко")
    assert "яблоко" not in hl_obj

    with pytest.raises(ValueError, match="x not in list"):
        hl_obj.remove("банан")


def test_advanced_deletions_positions():
    """Тест 4.2: Жёсткая проверка удалений из начала, середины и конца"""
    # Создаем плотный массив
    hl_obj = hl("начало", "а", "б", "середина", "в", "г", "конец")
    
    # 1. Удаляем из самого начала (индекс 0)
    hl_obj.remove("начало")
    assert list(hl_obj) == ["а", "б", "середина", "в", "г", "конец"]
    assert "начало" not in hl_obj
    assert hl_obj.index("середина") == 2 # Проверяем корректность Си-сдвига ярлыков
    
    # 2. Извлекаем из середины через pop
    popped = hl_obj.pop(2) # Удаляем элемент "середина"
    assert popped == "середина"
    assert list(hl_obj) == ["а", "б", "в", "г", "конец"]
    assert "середина" not in hl_obj
    assert hl_obj.index("конец") == 4
    
    # 3. Удаляем с самого конца списка
    hl_obj.remove("конец")
    assert list(hl_obj) == ["а", "б", "в", "г"]
    assert "конец" not in hl_obj


def test_index_and_count():
    """Тест 5 и 7: Поиск индексов и O(1) count()"""
    hl_obj = hl(10, 20, 30, 20, 40)
    assert hl_obj.index(20) == 1
    assert hl_obj.count(20) == 2
    assert hl_obj.count(99) == 0

    with pytest.raises(ValueError):
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
    """Тест 11.2: Детерминированность хэшей словарей с разным порядком ключей на Си-уровне"""
    d1 = {"а": 1, "б": 2, "в": {"х": 9}}
    d2 = {"б": 2, "в": {"х": 9}, "а": 1}

    hl_obj = hashlist([d1])
    assert d2 in hl_obj
    assert hl_obj.count(d2) == 1


def test_stress_massive_append_and_delete():
    """Тест 12: Нагрузочный тест на каскадное добавление и поштучное удаление 100,000 элементов"""
    hl_obj = hashlist()
    items = [f"item_{i}" for i in range(100_000)]

    for item in items:
        hl_obj.append(item)
    assert len(hl_obj) == 100_000

    for _ in range(1000):
        rand_idx = random.randint(0, 99_999)
        assert items[rand_idx] in hl_obj

    # Поштучное каскадное удаление с хвоста — проверка ленивой инвалидации (Lazy Rebuild)
    for i in range(100_000 - 1, -1, -1):
        del hl_obj[i]

    assert len(hl_obj) == 0


def test_stress_hash_collisions_and_unhashables():
    """Тест 13: Стресс-тест на 50,000 нехэшируемых дубликатов и объектов"""
    hl_obj = hashlist()

    nested_list = [1, 2, 3]
    nested_dict = {"key": "val"}

    for _ in range(10_000):
        hl_obj.append(nested_list)
        hl_obj.append(nested_dict)

    assert len(hl_obj) == 20_000
    assert hl_obj.count(nested_list) == 10_000
    assert hl_obj.count(nested_dict) == 10_000


def test_performance_benchmark_minimum_speedup():
    """Тест 14: Индустриальный бенчмарк производительности на 1,000,000 элементов."""
    size = 1_000_000
    data = list(range(size))
    random.shuffle(data)

    hl_obj = hashlist(data)
    std_list = list(data)
    target = data[-1]

    start = time.perf_counter()
    res_cpp = target in hl_obj
    t_cpp = time.perf_counter() - start

    start = time.perf_counter()
    res_std = target in std_list
    t_std = time.perf_counter() - start

    assert res_cpp is True
    assert res_std is True

    speedup = t_std / t_cpp
    print(f"\n[Pytest Бенчмарк] Ускорение Си ядра: {speedup:,.1f}x")
    assert speedup > 1.0


# =====================================================================
# НOВЫЕ СВЕРХЖЕСТКИЕ ТЕСТЫ ДЛЯ ИСКЛЮЧЕНИЯ ЛЮБЫХ РЕГРЕССИЙ НА PYPI
# =====================================================================

class MockSameHash:
    def __init__(self, val): self.val = val
    def __hash__(self): return 101
    def __eq__(self, other): return isinstance(other, MockSameHash) and self.val == other.val


def test_fix_hash_collisions():
    """Тест фикса 1: Работа Си-ядра при жестких искусственных коллизиях хэшей"""
    o1 = MockSameHash("alpha")
    o2 = MockSameHash("beta")
    items = hl(o1, o2)
    
    assert o2 in items
    assert items.index(o2) == 1
    assert items.count(o2) == 1
    
    items.remove(o2)
    assert o2 not in items
    assert o1 in items


def test_fix_multiplication_edge_cases():
    """Тест фикса 2: Умножение и инкрементное умножение на 0 и отрицательные числа"""
    items = hl(10, 20, 30)
    
    assert len(items * 0) == 0
    assert len(items * -5) == 0
    
    items *= 0
    assert len(items) == 0


def test_fix_mutable_nested_objects():
    """Тест фикса 3: Системный перехват мутировавших «на лету» вложенных коллекций"""
    nested = [1, 2]
    items = hl(nested)
    
    nested.append(9)
    assert nested in items
    assert items.count(nested) == 1


def test_fix_mixed_types_in_collections():
    """Тест фикса 4: Разнородные, несравнимые типы ключей (str, int) внутри dict и set"""
    mixed_dict = {1: "int", "key": "str"}
    mixed_set = {100, "text", (5, 6)}
    
    items = hl(mixed_dict, mixed_set)
    assert mixed_dict in items
    assert mixed_set in items


def test_fix_invalid_index_type_errors():
    """Тест фикса 5: Строгая валидация типов индексов (TypeError на строки)"""
    items = hl(10, 20)
    
    with pytest.raises(TypeError):
        _ = items["0"]
        
    with pytest.raises(TypeError):
        items["1"] = 99
        
    with pytest.raises(TypeError):
        del items["0"]


def test_boolean_vs_integer_identity():
    """Тест фикса 6: Проверка, что Си-ядро отличает True от 1, а False от 0 в хэш-таблице"""
    items = hl(1, True, 0, False)
    
    assert items.count(1) == 1
    assert items.count(True) == 1
    assert items.count(0) == 1
    assert items.count(False) == 1
    
    assert items.index(True) == 1
    assert items.index(False) == 3


def test_extreme_numeric_values():
    """Тест фикса 7: Граничные значения числовых типов (Large Ints, Floats, None)"""
    large_int = 2**63 - 1
    negative_large_int = -2**63
    nan_float = float('nan')
    
    items = hl(large_int, negative_large_int, None, nan_float)
    
    assert large_int in items
    assert negative_large_int in items
    assert None in items
    # Для NaN проверяем идентичность объекта (в Си-ядре s_ptr == i_ptr спасет)
    assert nan_float in items


def test_cascade_mutations_and_lazy_rebuild():
    """Тест фикса 8: Смешанный каскад вставок и удалений из разных позиций списка"""
    hl_obj = hashlist()
    
    # Плотное заполнение
    for i in range(1000):
        hl_obj.append(i)
        
    # Смешанное удаление (из середины и конца)
    for _ in range(200):
        hl_obj.pop(500) # Из середины
        hl_obj.pop()    # С конца
        
    # Мгновенная вставка новых элементов
    hl_obj.extend(["new1", "new2"])
    
    assert "new1" in hl_obj
    assert "new2" in hl_obj
    assert hl_obj.index("new1") == len(hl_obj) - 2
    assert hl_obj.count("new1") == 1
