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
    """Тест фикса 6: Проверка стандартного поведения Python для True/1 и False/0"""
    items = hl(1, True, 0, False)

    # В каноничном Python list(1, True, 0, False).count(1) равен 2, так как 1 == True
    assert items.count(1) == 2
    assert items.count(True) == 2
    assert items.count(0) == 2
    assert items.count(False) == 2
    
    # Метод index() должен возвращать первое вхождение (для True/1 это индекс 0)
    assert items.index(True) == 0
    assert items.index(1) == 0
    assert items.index(False) == 2
    assert items.index(0) == 2



def test_extreme_numeric_values():
    """Тест фикса 7: Граничные значения числовых типов (Large Ints, Floats, None)"""
    large_int = 2**63 - 1
    negative_large_int = -2**63
    nan_float = float('nan')
    
    items = hl(large_int, negative_large_int, None, nan_float)
    
    assert large_int in items
    assert negative_large_int in items
    assert None in items
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


# =====================================================================
# НOВЫЕ АВТОМАТИЧЕСКИЕ ТЕСТЫ ПРОИЗВОДИТЕЛЬНОСТИ ПО СКРИНШОТАМ СТУДЕНТА
# =====================================================================

def test_student_scale_search_performance():
    """Тест фикса 9: Проверка O(1) поиска существующих и отсутствующих элементов на 20 000 записей"""
    size = 20000
    data = list(range(size))
    random.shuffle(data)
    
    hl_obj = hashlist(data)
    std_list = list(data)
    
    # Выбираем худший случай для списка (элемент в самом конце)
    target_exist = data[-1]
    target_missing = size + 500
    
    # Замер существующего элемента
    t0 = time.perf_counter()
    for _ in range(200): _ = target_exist in hl_obj
    t_hl_exist = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    for _ in range(200): _ = target_exist in std_list
    t_std_exist = time.perf_counter() - t0
    
    assert t_hl_exist < t_std_exist, f"Регрессия поиска! hashlist ({t_hl_exist:.5f}s) медленнее list ({t_std_exist:.5f}s)"

    # Замер отсутствующего элемента
    t0 = time.perf_counter()
    for _ in range(200): _ = target_missing in hl_obj
    t_hl_miss = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    for _ in range(200): _ = target_missing in std_list
    t_std_miss = time.perf_counter() - t0
    
    assert t_hl_miss < t_std_miss, f"Регрессия отсутствия! hashlist ({t_hl_miss:.5f}s) медленнее list ({t_std_miss:.5f}s)"


def test_student_scale_index_performance():
    """Тест фикса 10: Проверка O(1) разрешения индексов через .index() на малом масштабе"""
    size = 20000
    data = list(range(size))
    random.shuffle(data)
    
    hl_obj = hashlist(data)
    std_list = list(data)
    target = data[-1]
    
    t0 = time.perf_counter()
    for _ in range(200): _ = hl_obj.index(target)
    t_hl = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    for _ in range(200): _ = std_list.index(target)
    t_std = time.perf_counter() - t0
    
    assert t_hl < t_std, f"Регрессия метода index! hashlist ({t_hl:.5f}s) медленнее list ({t_std:.5f}s)"


def test_student_scale_count_performance():
    """Тест фикса 11: Проверка константного извлечения количества дубликатов на малом масштабе"""
    size = 20000
    data = [7] * size
    
    hl_obj = hashlist(data)
    std_list = list(data)
    
    t0 = time.perf_counter()
    for _ in range(200): _ = hl_obj.count(7)
    t_hl = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    for _ in range(200): _ = std_list.count(7)
    t_std = time.perf_counter() - t0
    
    assert t_hl < t_std, f"Регрессия метода count! hashlist ({t_hl:.5f}s) медленнее list ({t_std:.5f}s)"


def test_strict_boolean_vs_integer_identity_behavior():
    """Тест системного фикса: проверка эквивалентности True и 1, False и 0 при поиске"""
    from hashlist import hashlist
    
    # Кейс 1: True внутри коллекции, ищем через число 1
    h_true = hashlist([True])
    assert h_true == [1]
    assert 1 in h_true, "Число 1 должно находиться в hashlist([True])"
    assert h_true.count(1) == 1, "Количество единиц в hashlist([True]) должно быть 1"
    assert h_true.index(1) == 0, "Индекс числа 1 в hashlist([True]) должен быть 0"
    
    h_true.remove(1)
    assert len(h_true) == 0, "Удаление 1 должно было очистить коллекцию"

    # Кейс 2: False внутри коллекции, ищем через число 0
    h_false = hashlist([False])
    assert h_false == [0]
    assert 0 in h_false, "Число 0 должно находиться в hashlist([False])"
    assert h_false.count(0) == 1
    assert h_false.index(0) == 0

    h_false.remove(0)
    assert len(h_false) == 0

# =====================================================================
# КОМПЛЕКС ПОЛНОГО ПОКРЫТИЯ: паритет со стандартным list, ленивые токены
# (tokens_ready), GC-циклы, refcount-дисциплина, pickle, протоколы,
# конструкторы, краевые значения
# =====================================================================

import gc
import pickle
import weakref
from collections.abc import MutableSequence


def test_list_parity_random_fuzz():
    """Property-фуззинг: 24 seed'а х ~ 220 случайных операций против зеркального list."""
    for seed in range(24):
        r = random.Random(1700 + seed)
        mirror = []
        h = hashlist()

        for _step in range(220):
            op = r.randrange(11)
            if op == 0:  # append
                v = r.randrange(-50, 50)
                h.append(v); mirror.append(v)
            elif op == 1:  # extend
                it = [r.randrange(-50, 50) for _ in range(r.randrange(3))]
                h.extend(it); mirror.extend(it)
            elif op == 2:  # insert (в т.ч. с зажимом индексов)
                i = r.randrange(-len(mirror) - 3, len(mirror) + 3)
                v = r.randrange(-50, 50)
                h.insert(i, v); mirror.insert(i, v)
            elif op == 3:  # pop() с хвоста
                if mirror:
                    assert h.pop() == mirror.pop()
                else:
                    assert _raise_parity(lambda c: c.pop(), h, mirror) == IndexError
            elif op == 4:  # pop(i) по случайному индексу
                if mirror:
                    i = r.randrange(-len(mirror), len(mirror))
                    assert h.pop(i) == mirror.pop(i)
                else:
                    assert _raise_parity(lambda c: c.pop(0), h, mirror) == IndexError
            elif op == 5:  # remove (может отсутствовать -> ValueError в обоих)
                v = r.randrange(-60, 60)
                try:
                    mirror.remove(v); ok = True
                except ValueError:
                    ok = False
                if ok:
                    h.remove(v)
                else:
                    assert _raise_parity(lambda c: c.remove(v), h, mirror) == ValueError
            elif op == 6:  # setitem
                i = r.randrange(-len(mirror), len(mirror)) if mirror else 0
                v = r.randrange(-50, 50)
                if mirror:
                    h[i] = v; mirror[i] = v
                else:
                    assert _raise_parity(lambda c: c.__setitem__(i, v), h, mirror) == IndexError
            elif op == 7:  # delitem
                i = r.randrange(-len(mirror), len(mirror)) if mirror else 0
                if mirror:
                    del h[i]; del mirror[i]
                else:
                    assert _raise_parity(lambda c: c.__delitem__(i), h, mirror) == IndexError
            elif op == 8:  # reverse
                h.reverse(); mirror.reverse()
            elif op == 9:  # sort
                h.sort(); mirror.sort()
            else:  # пробы in / index / count
                v = r.randrange(-60, 60)
                assert (v in h) == (v in mirror)
                if v in mirror:
                    assert h.index(v) == mirror.index(v)
                assert h.count(v) == mirror.count(v)

            # Полная сверка содержимого после каждой операции
            assert list(h) == mirror
            assert len(h) == len(mirror)


def _raise_parity(call, h, mirror):
    """Возвращает тип исключения для hashlist и подтверждает его паритет с list."""
    try:
        call(h); res = None
    except Exception as e:
        res = type(e)
    try:
        call(mirror); ref = None
    except Exception as e:
        ref = type(e)
    assert res == ref, f"Дивергенция ошибок: hashlist={res}, list={ref}"
    return res


def test_tokens_ready_battery():
    """Целевая батарея ленивой политики токенов: точные индексы/counts после каждого вида мутации."""
    data = [i * 7 for i in range(300)]

    # 1. импорт -> append -> поиск
    h, m = hashlist(data), list(data)
    h.append(-1); m.append(-1)
    assert list(h) == m
    assert h.index(-1) == m.index(-1) == len(m) - 1
    assert h.count(data[5]) == m.count(data[5]) == 1

    # 2. импорт -> insert(mid)
    h, m = hashlist(data), list(data)
    h.insert(100, -2); m.insert(100, -2)
    assert h.index(-2) == m.index(-2) == 100
    assert h.index(data[99]) == 99 and h.index(data[100]) == 101
    assert list(h) == m

    # 3. импорт -> insert(0)
    h, m = hashlist(data), list(data)
    h.insert(0, -88); m.insert(0, -88)
    assert h.index(-88) == 0 and h.index(data[0]) == 1
    assert list(h) == m

    # 4. импорт -> insert(len) (вставка в хвост: доливка одного токена)
    h, m = hashlist(data), list(data)
    h.insert(len(m), -9); m.insert(len(m), -9)
    assert h.index(-9) == len(m) - 1 and h.index(data[0]) == 0
    assert list(h) == m

    # 5. импорт -> pop(0)
    h, m = hashlist(data), list(data)
    assert h.pop(0) == m.pop(0) == data[0]
    assert h.index(data[1]) == m.index(data[1]) == 0
    assert data[0] not in h
    assert list(h) == m

    # 6. импорт -> pop() с хвоста (токены остаются живы: позиции не сдвигались)
    h, m = hashlist(data), list(data)
    assert h.pop() == m.pop() == data[-1]
    assert h.index(data[0]) == 0 and h.index(data[-2]) == m.index(data[-2])
    assert list(h) == m

    # 7. импорт -> pop(mid)
    h, m = hashlist(data), list(data)
    assert h.pop(150) == m.pop(150) == data[150]
    assert h.index(data[151]) == m.index(data[151]) == 150
    assert h.count(data[150]) == m.count(data[150]) == 0
    assert list(h) == m

    # 8. импорт -> remove(mid) и remove(хвост)
    h, m = hashlist(data), list(data)
    h.remove(data[10]); m.remove(data[10])
    assert h.index(data[11]) == m.index(data[11]) == 10
    h.remove(data[-1]); m.remove(data[-1])
    assert data[-1] not in h and h.count(data[-1]) == 0
    assert list(h) == m

    # 9. импорт -> del[mid] и del[front]
    h, m = hashlist(data), list(data)
    del h[5]; del m[5]
    assert h.index(data[6]) == m.index(data[6]) == 5
    del h[0]; del m[0]
    assert h.index(data[1]) == m.index(data[1]) == 0
    assert list(h) == m

    # 10. импорт -> setitem(mid) — замена не сдвигает позиции
    h, m = hashlist(data), list(data)
    h[120] = -55; m[120] = -55
    assert h.index(-55) == 120 and h.index(data[121]) == 121
    assert data[120] not in h
    assert list(h) == m

    # 11. импорт -> clear -> append -> поиск (жёсткий переход через пустоту)
    h, m = hashlist(data), list(data)
    h.clear(); m.clear()
    assert list(h) == []
    h.append(11); m.append(11)
    assert 11 in h and h.index(11) == 0 and h.count(11) == 1
    assert list(h) == m

    # 12. импорт -> copy -> поиск в оригинале и в копии
    h, m = hashlist(data), list(data)
    c = h.copy()
    assert c.index(data[42]) == 42 and h.index(data[42]) == 42
    assert list(c) == m

    # 13. импорт -> срез -> поиск в срезе
    h, m = hashlist(data), list(data)
    s = h[10:60]
    assert list(s) == m[10:60]
    assert s.index(data[10]) == 0 and s.index(data[59]) == 49

    # 14. импорт -> тёплый append -> extend(list) -> extend(генератор) -> поиск
    h, m = hashlist(data), list(data)
    h.append(1); m.append(1)                     # токены ещё живы
    h.extend(data[:5]); m.extend(data[:5])
    h.extend(x for x in (-1, -2)); m.extend((-1, -2))
    assert h.index(-1) == m.index(-1) == len(m) - 2
    assert h.count(-2) == 1 and list(h) == m

    # 15. импорт -> sort -> поиск (нативный Timsort-путь)
    shuffled = list(data)
    random.Random(9).shuffle(shuffled)
    h, m = hashlist(shuffled), list(shuffled)
    h.sort(); m.sort()
    assert list(h) == m
    assert h.index(m[0]) == 0 and h.index(m[-1]) == m.index(m[-1])

    # 16. импорт -> reverse -> поиск
    h, m = hashlist(data), list(data)
    h.reverse(); m.reverse()
    assert list(h) == m
    assert h.index(data[0]) == m.index(data[0]) == len(m) - 1

    # 17. каскад сдвигающих мутаций вперемешку + поиск после каждого шага
    h, m = hashlist(data), list(data)
    for k in range(5):
        h.insert(k, -k); m.insert(k, -k)
        assert h.index(-k) == m.index(-k) == k
        assert h.pop(k + 1) == m.pop(k + 1)     # извлечённые значения совпадают
        h.append(k); m.append(k)
        assert h.index(-k) == m.index(-k) == k
        assert h.index(data[250]) == m.index(data[250])
        assert list(h) == m


def test_mixed_interleave_search():
    """Реалистичный смешанный паттерн: 1000 пар (append -> O(1) поиск -> точный index)."""
    h = hashlist()
    for i in range(1000):
        h.append(i)
        assert i in h
        assert h.index(i) == i
    assert list(h) == list(range(1000))
    assert h.count(777) == 1
    assert 2000 not in h


def test_errors_parity():
    """Попарная сверка типов исключений с нативным list."""
    def raise_type_of(call, container):
        try:
            call(container)
            return None
        except Exception as e:
            return type(e)

    h, l = hl(1, 2, 3), [1, 2, 3]
    cases = [
        lambda c: c.pop(),
        lambda c: c.pop(100),
        lambda c: c.pop(-100),
        lambda c: c.remove(77),
        lambda c: c.index(77),
        lambda c: c.index(slice(1, 2)),
        lambda c: c.index(2, 1),
        lambda c: c.pop("0"),
        lambda c: c.insert("0", 9),
        lambda c: c.insert(None, 4),
        lambda c: c.extend(77),
        lambda c: c.extend(None),
        lambda c: c.__delitem__(100),
        lambda c: c.__delitem__(-100),
        lambda c: c.__delitem__("0"),
        lambda c: c.__getitem__("0"),
    ]
    for fn in cases:
        assert raise_type_of(fn, h) == raise_type_of(fn, l), \
            f"Дивергенция исключений: hashlist={raise_type_of(fn, h)}, list={raise_type_of(fn, l)}"

    # Зажим индексов insert() по краям — паритет с list
    hi, li = hl(1, 2), [1, 2]
    hi.insert(50, 9); li.insert(50, 9)
    hi.insert(-50, 8); li.insert(-50, 8)
    assert list(hi) == li == [8, 1, 2, 9]


class _KeyRec:
    __slots__ = ("k",)

    def __init__(self, k): self.k = k


def test_sort_stability_and_parity():
    """sort(): нативный Timsort-путь, key/reverse-пути — стабильность и паритет с sorted()."""
    r = random.Random(4242)
    for _trial in range(20):
        data = [_KeyRec(r.randrange(8)) for _ in range(r.randrange(0, 60))]
        h = hashlist(data)
        h.sort(key=lambda rec: rec.k)
        expected = sorted(data, key=lambda rec: rec.k)
        # Стабильность: равные ключи сохраняют исходный порядок объектов
        assert all(a is b for a, b in zip(h, expected))

    # reverse=True через key-путь
    data = [_KeyRec(r.randrange(8)) for _ in range(40)]
    h = hashlist(data)
    h.sort(key=lambda rec: rec.k, reverse=True)
    expected = sorted(data, key=lambda rec: rec.k, reverse=True)
    assert all(a is b for a, b in zip(h, expected))

    # Нативный путь (без key): стабильность на равных значениях разных типов (list-parity)
    vals = [2, 1.0, 1, True, 0, False, 2.0, 3]
    hv, lv = hashlist(vals), list(vals)
    hv.sort(); lv.sort()
    assert all(a is b for a, b in zip(hv, lv))

    # Пустой и одноэлементный сортировки — все пути безопасны
    for base in ([], [1], [2, 1]):
        hx = hashlist(base)
        hx.sort()
        assert list(hx) == sorted(base)
        hx.sort(reverse=True)
        assert list(hx) == sorted(base, reverse=True)


def test_refcount_discipline():
    """Рефкаунт-дисциплина: каждая операция обязана сохранять точные количества ссылок."""
    x, y = object(), object()
    base_x, base_y = sys.getrefcount(x), sys.getrefcount(y)

    h = hashlist()
    h.append(x)
    assert sys.getrefcount(x) == base_x + 1
    h.append(x)
    assert sys.getrefcount(x) == base_x + 2

    h.pop()  # хвостовой pop отдаёт ссылку владельца и не оставляет хвоста
    assert sys.getrefcount(x) == base_x + 1

    h.remove(x)
    assert sys.getrefcount(x) == base_x

    h.append(x)
    del h[0]
    assert sys.getrefcount(x) == base_x

    h.append(x)
    h[0] = y
    assert sys.getrefcount(x) == base_x and sys.getrefcount(y) == base_y + 1
    h.clear()
    assert sys.getrefcount(y) == base_y

    h.append(x)
    c = h.copy()
    assert sys.getrefcount(x) == base_x + 2
    del c
    assert sys.getrefcount(x) == base_x + 1

    s = h[0:1]
    assert sys.getrefcount(x) == base_x + 2
    del s
    assert sys.getrefcount(x) == base_x + 1

    h.append(y)
    h.reverse()   # перестановка указателей не меняет количества ссылок
    assert sys.getrefcount(x) == base_x + 1 and sys.getrefcount(y) == base_y + 1

    h.clear()
    assert sys.getrefcount(x) == base_x and sys.getrefcount(y) == base_y


def test_gc_cycles_collect():
    """Цикл hashlist -> hashlist обязан собираться сборщиком мусора."""
    gc.collect()

    class _Marker:
        pass

    m = _Marker()
    ref = weakref.ref(m)
    h = hashlist()
    h.append(m)      # маркер живёт ровно в контейнере
    h.append(h)      # самоссылочный цикл
    del h, m
    gc.collect()
    assert ref() is None, "самоссылочный hashlist не был собран GC"


def test_edge_values_parity():
    """Краевые значения на паритет с list: NaN, -0.0, True/1, ≥2^59, hash(-1/-2), подклассы."""
    nan1 = float("nan")
    nan2 = float("nan")
    assert nan1 in hashlist([nan1]) and nan1 in [nan1]          # тот же объект
    assert nan2 not in hashlist([nan1]) and nan2 not in [nan1]  # другой NaN

    hz, lz = hashlist([0.0, -0.0]), [0.0, -0.0]
    assert 0 in hz and 0 in lz
    assert -0.0 in hz and -0.0 in lz
    # list-parity ".index": первое РАВНОЕ значение — -0.0 == 0.0, поэтому обе стороны вернут 0
    assert hz.index(-0.0) == lz.index(-0.0) == 0
    assert hz.count(0.0) == lz.count(0.0) == 2

    hb, lb = hashlist([True, 1, 0, False, 0]), [True, 1, 0, False, 0]
    for probe in (True, False, 1, 0, 2):
        assert hb.count(probe) == lb.count(probe)
        if probe in lb:
            assert hb.index(probe) == lb.index(probe)

    # Большие целые за границей быстрого токена (±2^59)
    hbig = hashlist([2**59 - 1, 2**70, -(2**70), 2**63 - 1, -2**63])
    assert hbig.index(2**70) == 1 and hbig.index(-(2**70)) == 2
    assert hbig.count(2**59 - 1) == 1 and hbig.count(2**70) == 1

    # Хэш-магия CPython: hash(-1) == hash(-2) == -2, но значения различны
    hm, lm = hashlist([-1, -2]), [-1, -2]
    assert hm.index(-1) == lm.index(-1) == 0
    assert hm.index(-2) == lm.index(-2) == 1
    assert (-3 not in hm) and (-3 not in lm)

    # Подклассы str/int: ищутся как обычные значения (паритет list)
    class _MyStr(str):
        pass

    class _MyInt(int):
        pass

    hs, ls = hashlist([_MyStr("x")]), [_MyStr("x")]
    assert "x" in hs and "x" in ls
    assert _MyStr("x") in hs and _MyStr("x") in ls
    hi, li = hashlist([_MyInt(5)]), [_MyInt(5)]
    assert 5 in hi and 5 in li
    assert hi.index(5) == li.index(5) == 0

    # b"a" vs "a" — байты не равны строке (паритет)
    assert b"a" not in hashlist(["a"]) and b"a" not in ["a"]

    # Объект с падающим __hash__: токен переходит в структурный, поиск по идентичности (паритет)
    class _BadHash:
        def __init__(self, v): self.v = v
        def __hash__(self): raise RuntimeError("no hash for you")
        def __eq__(self, o): return isinstance(o, _BadHash) and self.v == o.v

    bh = _BadHash("q")
    hbad, lbad = hashlist([bh]), [bh]
    assert bh in hbad and bh in lbad
    assert hbad.index(bh) == lbad.index(bh) == 0
    assert hbad.count(bh) == lbad.count(bh) == 1
    assert _BadHash("zzz") not in hbad and _BadHash("zzz") not in lbad


def test_protocol_parity():
    """Протоколы: len/repr/eq/арифметика/reversed/sorted/срезы/pickle/bool/MutableSequence."""
    h = hashlist([3, 1, 2])
    l = [3, 1, 2]

    assert len(h) == 3 and len(l) == 3
    assert bool(h) and not bool(hashlist())
    assert repr(h) == "hashlist([3, 1, 2])"
    assert h == l and l == h
    assert h == hashlist([3, 1, 2])
    assert h != [4]

    assert list(h + [4]) == [3, 1, 2, 4]
    assert isinstance(h + [4], hashlist)
    h += [4]
    assert list(h) == [3, 1, 2, 4]

    assert isinstance(h * 2, hashlist)
    assert list(h * 2) == [3, 1, 2, 4, 3, 1, 2, 4]
    h *= 2
    assert list(h) == [3, 1, 2, 4] * 2
    h *= 0
    assert list(h) == []

    with pytest.raises(TypeError):
        _ = h + 5
    with pytest.raises(TypeError):
        _ = h * "x"

    h2 = hashlist([3, 1, 2])
    assert list(reversed(h2)) == [2, 1, 3]
    assert sorted(h2) == [1, 2, 3]
    assert list(iter(h2)) == [3, 1, 2]

    s = h2[1:]
    assert isinstance(s, hashlist) and list(s) == [1, 2]
    del h2[0]              # [1, 2]
    h2[0] = 9              # [9, 2]
    h2[0:1] = [7, 7]       # [7, 7, 2]
    del h2[0:2]            # [2]
    h2 += [5]              # [2, 5] через __iadd__
    assert list(h2) == [2, 5]

    assert isinstance(h2, MutableSequence)
    with pytest.raises(AttributeError):
        h2.arbitrary = 1

    assert type(h2.copy()) is hashlist

    # pickle: ациклический контейнер + вложенный hashlist
    restored = pickle.loads(pickle.dumps(hashlist([1, "two", [3, 4], {"k": 5}, True, None])))
    assert type(restored) is hashlist
    assert list(restored) == [1, "two", [3, 4], {"k": 5}, True, None]
    assert restored.index("two") == 1 and {"k": 5} in restored

    nested = hashlist([hashlist([1, 2]), 3])
    r2 = pickle.loads(pickle.dumps(nested))
    assert isinstance(r2, hashlist) and isinstance(r2[0], hashlist)
    assert r2 == [[1, 2], 3]


def test_constructor_paths():
    """Все пути конструктора + мгновенный поиск сразу после создания."""
    assert list(hashlist()) == []
    assert list(hashlist(None)) == []

    assert hashlist([1, 2, 3]).index(2) == 1      # list — быстрый путь
    assert hashlist((1, 2, 3)).index(3) == 2      # tuple — быстрый путь
    assert hashlist(x * 2 for x in range(10)).index(18) == 9   # генератор
    assert list(hashlist("hap")) == list("hap")   # строка
    assert list(hashlist(b"ab")) == list(b"ab")   # байты
    assert list(hashlist({"k": 1, "m": 2})) == list({"k": 1, "m": 2})  # dict -> ключи

    hs = hashlist({5, "5"})
    for probe in (5, "5"):
        assert probe in hs and hs.count(probe) == 1

    # hashlist из hashlist: чистого и грязного (кэш токенов в dirty-состоянии)
    a = hashlist([1, 2, 3])
    b = hashlist(a)
    assert list(b) == list(a) == [1, 2, 3] and b.index(3) == 2

    dirty = hashlist([1, 2, 3])
    dirty.append(4)
    dirty.insert(0, 0)      # позиции сдвинуты: кэш токенов помечен dirty
    d2 = hashlist(dirty)
    assert list(d2) == list(dirty) == [0, 1, 2, 3, 4]
    assert d2.index(4) == 4 and d2.index(0) == 0 and d2.count(2) == 1

    assert list(hashlist(hashlist())) == []          # из пустого

    # Вложенные структуры найдены сразу после конструкции
    nested = hashlist([[1], {"x": 2}, {3}])
    assert [1] in nested and {"x": 2} in nested and {3} in nested
    assert nested.index({"x": 2}) == 1


def test_search_speedup_soft_guard():
    """Мягкий перф-порог (с щедрым запасом): поиск не регрессирует на 200K."""
    size = 200_000
    data = list(range(size))
    random.shuffle(data)
    h, mirror = hashlist(data), list(data)

    _ = data[0] in h          # прогрев: ленивая раскладка бакетов вне замера
    missing = size + 777
    reps = 300

    t0 = time.perf_counter()
    for _ in range(reps):
        _ = missing in h
    t_hl = time.perf_counter() - t0

    t0 = time.perf_counter()
    for _ in range(reps):
        _ = missing in mirror
    t_std = time.perf_counter() - t0

    speedup = t_std / t_hl
    print(f"\n[Soft guard @200K, отсутствующий] {t_std / reps * 1e3:.2f} мс vs "
          f"{t_hl / reps * 1e6:.1f} мкс -> {speedup:,.0f}x")
    assert speedup > 50, f"Деградация поиска на 200K: всего {speedup:.1f}x"
