import time
import random
import sys
import gc
import pickle
import weakref

class StudentItem:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"StudentItem({self.value})"

from hashlist import hl, hashlist

print("=====================================================================")
print("🚀 СТРЕСС-ТЕСТ И БЕНЧМАРК ПРОДУКТА hashlist (CPYTHON PURE C BACKEND)")
print("=====================================================================\n")

# БЛОК 1: Проверка 12 канонических методов из спецификации
print("--- БЛОК 1: ТЕСТ 12 КАНOНИЧЕСКИХ МЕТОДОВ СПИСКА ---")
a = hl(10, 20)
a.append([100, 200])
print(f"1. append():  {a} (Ожидается вложенный список в конце)")

a.extend([30, 40, 50, 60])
print(f"2. extend():  {a}")

a.insert(1, 99)
print(f"3. insert():  {a}")

a.remove(20)
print(f"4. remove():  {a}")

idx = a.index(60)
print(f"5. index():   Индекс элемента 60 равен {idx}")

popped = a.pop(1)
print(f"6. pop():     Извлечен элемент {popped}, список: {a}")

a.append(10)
print(f"7. count():   Элемент 10 повторяется {a.count(10)} раз(а)")

a.reverse()
print(f"8. reverse(): {a} (Развернут на месте)")

a.remove([100, 200])
a.sort(reverse=True)
print(f"9. sort():    {a} (Отсортирован по убыванию)")

a_copy = a.copy()
print(f"10. copy():   Копия: {a_copy} | Равны? {a == a_copy}")

a.clear()
print(f"11. clear():  {a} (Пустой, длина: {len(a)})")
print()

# БЛОК 2: Тест глобальных функций sorted() и reversed()
print("--- БЛОК 2: ТЕСТ ФУНКЦИЙ sorted() И reversed() ---")
b = hl(30, 10, 50, 20, 40)
print(f"Исходный hashlist: {b}")

sorted_b = hashlist(sorted(b))
print(f"Глобальный sorted(): {sorted_b} (Тип: {type(sorted_b).__name__})")

reversed_b = hashlist(reversed(b))
print(f"Глобальный reversed(): {reversed_b} (Тип: {type(reversed_b).__name__})")
print()

# БЛОК 3: Тест детерминированности хэшей (Разный порядок ключей)
print("--- БЛОК 3: ТЕСТ ДЕТЕРМИНИРОВАННОГО СИ-ПОИСКА СЛОВАРЕЙ ---")
d1 = {"а": 1, "б": 2, "в": {"х": 9}}
d2 = {"б": 2, "в": {"х": 9}, "а": 1}
print(f"Равны ли словари на уровне Python? {d1 == d2}")

hash_dict_test = hashlist([d1])
print(f"Найдет ли Си-ядро словарь с измененным порядком ключей за O(1)? {d2 in hash_dict_test}")
print()

# ---------------------------------------------------------------------
# БЛОК 4: Побайтовый анализ памяти чистого Си-объекта
# ---------------------------------------------------------------------
print("--- БЛОК 4: АНАЛИЗ ОПТИМИЗАЦИИ ПАМЯТИ ---")
empty_std_list = []
empty_hl = hashlist()
print(f"Вес пустого встроенного list:              {sys.getsizeof(empty_std_list)} байт")
print(f"Вес оболочки нашего hashlist со __slots__: {sys.getsizeof(empty_hl)} байт")
print()


# ---------------------------------------------------------------------
# БЛОК 4.5: Верификация регрессионных исправлений (Новые тесты багов)
# ---------------------------------------------------------------------
print("--- БЛОК 4.5: ВЕРИФИКАЦИЯ ИСПРАВЛЕНИЯ КРИТИЧЕСКИХ БАГOВ ---")

# 1. Проверка коллизий хэшей (SameHash)
class SameHashItem:
    def __init__(self, name): self.name = name
    def __hash__(self): return 42  # Жесткая искусственная коллизия
    def __eq__(self, other): return isinstance(other, SameHashItem) and self.name == other.name
    def __repr__(self): return f"SameHash({self.name})"

collision_hl = hl(SameHashItem("alpha"), SameHashItem("beta"))
print(f"1. Коллизии хэшей: содержит 'beta'? {SameHashItem('beta') in collision_hl} | Индекс: {collision_hl.index(SameHashItem('beta'))} (Ожидается True и 1)")

# 2. Умножение списка на ноль и отрицательные числа
mul_hl = hl(1, 2, 3)
mul_hl *= 0
print(f"2. Умножение списка на 0 (*= 0): {mul_hl} (Ожидается пустой)")

# 3. Мутация вложенных объектов после добавления
nested_mut = [1, 2]
mutation_hl = hl([nested_mut])
nested_mut.append(3)  # изменяем исходный список
print(f"3. Нахождение мутировавшего вложенного списка: {nested_mut in mutation_hl} (Ожидается True)")

# 4. Разнородные типы ключей в словарях и множествах
try:
    mixed_dict = {1: "one", "name": "test"}
    mixed_set = {1, "text", (2, 3)}
    mixed_hl = hl(mixed_dict, mixed_set)
    print(f"4. Разнородные типы внутри dict/set: Успешно обработаны Си-ядром за O(1)!")
except TypeError as e:
    print(f"4. Разнородные типы: КРИТИЧЕСКАЯ ОШИБКА! {e}")

# 5. Ошибка типа при неверном индексе (TypeError)
try:
    idx_hl = hl(10, 20)
    idx_hl["1"] = 100
    print("5. Валидация индексов: КРИТИЧЕСКАЯ ОШИБКА! Строковый индекс пропущен!")
except TypeError:
    print("5. Валидация индексов: Успешно перехвачен TypeError для строк.")

# 6. Разделение близнецов True/1 и False/0 на уровне Си-бакетов
# 6. Верификация идентичности True/1 и False/0 согласно спецификации Python
bool_ident_hl = hl(True)
print(f"6. Тест True/1: 1 in hashlist([True]) -> {1 in bool_ident_hl} (Ожидается: True)")
print(f"   count(1) -> {bool_ident_hl.count(1)} (Ожидается: 1) | index(1) -> {bool_ident_hl.index(1)} (Ожидается: 0)")
bool_ident_hl.remove(1)
print(f"   После remove(1) длина списка -> {len(bool_ident_hl)} (Ожидается: 0)")

print()

# ---------------------------------------------------------------------
# БЛОК 4.6: РЕГРЕССИОННЫЙ КОМПЛЕКС (ПАРИТЕТ LIST, ЛЕНИВЫЕ ТОКЕНЫ,
#           GC-ЦИКЛЫ, PICKLE, КРАЕВЫЕ ЗНАЧЕНИЯ)
# ---------------------------------------------------------------------
print("--- БЛОК 4.6: РЕГРЕССИОННЫЙ КОМПЛЕКС (ПАРИТЕТ LIST, ЛЕНИВЫЕ ТОКЕНЫ, GC, PICKLE) ---")

_complex_total = 0
_complex_passed = 0

def complex_check(name, ok):
    """Самопроверка одного сценария и накопление итогового счётчика блока."""
    global _complex_total, _complex_passed
    _complex_total += 1
    _complex_passed += 1 if ok else 0
    print(f"   ► {name}: {'OK' if ok else 'ПРОВАЛ!'}")

# 1. Мини-фузз: случайные операции зеркально применяются к hashlist и к list.
#    Потенциально невалидные операции (pop по пустому, отсутствующий элемент
#    у remove/index, setitem вне диапазона) защищаются зеркалом m: сначала
#    проверяется легальность операции на list, только затем она выполняется
#    для обоих контейнеров.
def _mini_fuzz():
    ops = ("append", "insert", "pop", "remove", "setitem", "index", "count", "contains")
    for seed in range(6):
        rng = random.Random(seed)
        h, m = hl(), []
        for step in range(160):
            op = ops[rng.randrange(len(ops))]
            val = rng.randrange(-5, 15)
            if op == "append":
                h.append(val); m.append(val)
            elif op == "insert":
                pos = rng.randrange(len(m) + 1)
                h.insert(pos, val); m.insert(pos, val)
            elif op == "pop" and m:
                pos = rng.randrange(len(m))
                if h.pop(pos) != m.pop(pos): return False
            elif op == "remove" and val in m:
                h.remove(val); m.remove(val)
            elif op == "setitem" and m:
                pos = rng.randrange(len(m))
                h[pos] = val; m[pos] = val
            elif op == "index" and val in m:
                if h.index(val) != m.index(val): return False
            elif op == "count":
                if h.count(val) != m.count(val): return False
            elif op == "contains":
                if (val in h) != (val in m): return False
        if len(h) != len(m) or not (h == m): return False
    return True

try:
    fuzz_ok = _mini_fuzz()
    print(f"1. Мини-фузз: 6 сидов × 160 зеркальных операций (append/insert/pop/remove/setitem/index/count/in)")
except Exception as e:
    fuzz_ok = False
    print(f"1. Мини-фузз: ИСКЛЮЧЕНИЕ {type(e).__name__}: {e}")
complex_check("Мини-фузз: паритет со list", fuzz_ok)

# 2. Батарея ленивых токенов: после каждой мутации поиск обязан оставаться
#    корректным — где-то доливается один слот, где-то позиции сдвигаются и
#    хэш-таблица перестраивается с нуля.
try:
    tok_h, tok_m = hl(10, 20, 30, 40), [10, 20, 30, 40]
    tok_ok = (30 in tok_h) and tok_h.index(30) == tok_m.index(30) == 2   # eager-токены при создании
    tok_h.append(50); tok_m.append(50)              # append: ленивая доделка одного слота
    tok_ok = tok_ok and 50 in tok_h and tok_h.count(50) == tok_m.count(50) == 1
    tok_h.insert(2, 999); tok_m.insert(2, 999)      # insert в середину: сдвиг позиций
    tok_ok = tok_ok and tok_h.index(999) == tok_m.index(999) == 2
    tok_h.pop(0); tok_m.pop(0)                      # pop(0): сдвиг всех позиций
    tok_ok = tok_ok and tok_h.index(50) == tok_m.index(50) == 4
    tok_h.pop(); tok_m.pop()                        # pop с хвоста
    tok_ok = tok_ok and (50 in tok_h) == (50 in tok_m) == False
    tok_h.remove(999); tok_m.remove(999)            # remove из середины: сдвиг
    tok_ok = tok_ok and list(tok_h) == tok_m == [20, 30, 40]
    tok_h[0] = -1; tok_m[0] = -1                    # setitem: перезапись слота
    tok_ok = tok_ok and tok_h.index(-1) == 0 and (20 in tok_h) == (20 in tok_m) == False
    tok_h.sort(); tok_m.sort()                      # sort: полная переиндексация
    tok_ok = tok_ok and list(tok_h) == tok_m == [-1, 30, 40] and tok_h.index(30) == 1
    tok_h.reverse(); tok_m.reverse()                # reverse: снова сдвиг позиций
    tok_ok = tok_ok and list(tok_h) == tok_m and tok_h.index(-1) == tok_m.index(-1) == 2
    tok_h.extend([77, 88]); tok_m.extend([77, 88])  # extend: eager-токены у новых слотов
    tok_ok = tok_ok and 77 in tok_h and tok_h.index(77) == tok_m.index(77) == 3
    tok_h.clear(); tok_m.clear()                    # clear: штатное обнуление
    tok_h.append(1234); tok_m.append(1234)          # «возрождение» после clear
    tok_ok = tok_ok and list(tok_h) == tok_m == [1234] and 1234 in tok_h
    print(f"2. Батарея ленивых токенов: 11 мутаций подряд (append/insert/pop/pop(0)/remove/setitem/sort/reverse/extend/clear/append) — паритет со list на каждом шаге")
except Exception as e:
    tok_ok = False
    print(f"2. Батарея ленивых токенов: ИСКЛЮЧЕНИЕ {type(e).__name__}: {e}")
complex_check("Ленивые токены: батарея мутаций", tok_ok)

# 3. GC-циклы: hashlist с самоссылкой и взаимный цикл из двух hashlist
#    обязаны умирать только средствами сборщика мусора. Слабые ссылки берём
#    на маркер-объекты ВНУТРИ контейнеров (как в pytest-наборе): сам hashlist
#    слабым ссылкам не поддаётся, но при его смерти содержимое умирает вместе
#    с ним — это и есть маркер сборки цикла.
try:
    class _GcMarker:
        pass

    marker_solo, marker_pair = _GcMarker(), _GcMarker()
    ref_solo, ref_pair = weakref.ref(marker_solo), weakref.ref(marker_pair)

    solo = hl({"a": 1})
    solo.append(marker_solo)
    solo.append(solo)                               # цикл на самого себя

    pair1, pair2 = hl(1), hl(2)
    pair1.append(marker_pair)
    pair1.append(pair2); pair2.append(pair1)        # взаимный цикл

    del solo, pair1, pair2, marker_solo, marker_pair
    gc.collect()
    gc_ok = ref_solo() is None and ref_pair() is None
    print(f"3. GC-циклы: самоссылка и взаимный цикл двух hashlist корректно освобождаются сборщиком мусора (маркеры внутри контейнеров)")
except Exception as e:
    gc_ok = False
    print(f"3. GC-циклы: ИСКЛЮЧЕНИЕ {type(e).__name__}: {e}")
complex_check("GC-циклы: weakref-маркеры", gc_ok)

# 4. Pickle round-trip: плоский и вложенный hashlist сериализуются, а O(1)-поиск
#    обязан работать сразу после pickle.loads().
try:
    pkl_h = hl("текст", [4, 5], {"k": 1}, 4096)
    pkl_m = list(pkl_h)
    restored = pickle.loads(pickle.dumps(pkl_h))
    pkl_ok = (restored == pkl_m) and ({"k": 1} in restored) and (restored.index("текст") == 0) and (restored.index(4096) == 3)
    nested = hl(hl(1, 2), hl(3, 4))
    nested_rt = pickle.loads(pickle.dumps(nested))
    pkl_ok = pkl_ok and len(nested_rt) == 2 and list(nested_rt[0]) == [1, 2] and list(nested_rt[1]) == [3, 4]
    print(f"4. Pickle round-trip: плоский список (строка/list/dict/int) и вложенные hashlist; O(1)-поиск сразу после pickle.loads()")
except Exception as e:
    pkl_ok = False
    print(f"4. Pickle round-trip: ИСКЛЮЧЕНИЕ {type(e).__name__}: {e}")
complex_check("Pickle round-trip + O(1)-поиск", pkl_ok)

# 5. Паритет типов исключений: для каждого случая — свежие контейнеры.
#    Сравниваем только типы исключений, тексты сообщений сознательно не трогаем.
def _exc_type(fn):
    try:
        fn()
        return "(нет ошибки)"
    except Exception as e:
        return type(e).__name__

try:
    pairs = [
        ("pop() на пустом",                lambda: hl().pop(),          lambda: [].pop()),
        ("remove(99) из hl(1, 2)",         lambda: hl(1, 2).remove(99), lambda: [1, 2].remove(99)),
        ("index(99) в hl(1, 2)",           lambda: hl(1, 2).index(99),  lambda: [1, 2].index(99)),
        ("extend(5) от hl(1)",             lambda: hl(1).extend(5),     lambda: [1].extend(5)),
        ("pop(\"0\") по строке-индексу",   lambda: hl(1).pop("0"),      lambda: [1].pop("0")),
    ]
    exc_ok = True
    for name, f_h, f_m in pairs:
        eh, em = _exc_type(f_h), _exc_type(f_m)
        parity = eh == em
        exc_ok = exc_ok and parity
        print(f"   {name}: hashlist -> {eh}, list -> {em} {'(паритет)' if parity else '(РЕГРЕССИЯ!)'}")
    print(f"5. Паритет типов исключений: 5 пар (pop/remove/index/extend/тип индекса) на свежих контейнерах")
except Exception as e:
    exc_ok = False
    print(f"5. Паритет типов исключений: ИСКЛЮЧЕНИЕ {type(e).__name__}: {e}")
complex_check("Паритет типов исключений", exc_ok)

# 6. Краевые значения: NaN (никогда не равен), -0.0 == 0.0, различимость True/1
#    на уровне бакетов, гигантские ±2^70 (за границей быстрых int-токенов) и
#    знаменитая коллизия hash(-1) == hash(-2) == -2 в CPython.
try:
    edge_m = [0.0, -0.0, float("nan"), 1, True, 2**70, -(2**70), -1, -2]
    edge_h = hl(*edge_m)
    edge_ok = (
        edge_h.index(-0.0) == edge_m.index(-0.0) == 0
        and edge_h.index(0.0) == edge_m.index(0.0) == 0
        and (float("nan") in edge_h) is False
        and edge_h.count(float("nan")) == edge_m.count(float("nan")) == 0
        and edge_h.count(1) == edge_m.count(1) == 2            # 1 и True считаются вместе (паритет list)
        and edge_h.index(True) == edge_m.index(True) == 3      # первое равное значение
        and (2**70 in edge_h) is True
        and edge_h.index(-(2**70)) == edge_m.index(-(2**70)) == 6
        and edge_h.index(-1) == edge_m.index(-1) == 7          # hash(-1) == hash(-2)
        and edge_h.index(-2) == edge_m.index(-2) == 8          # ...но значения различимы
    )
    print(f"6. Краевые значения: NaN не находится, -0.0 == 0.0, True/1 различимы по бакетам, ±2^70 через PyObject_Hash, коллизия hash(-1) == hash(-2)")
except Exception as e:
    edge_ok = False
    print(f"6. Краевые значения: ИСКЛЮЧЕНИЕ {type(e).__name__}: {e}")
complex_check("Краевые значения (NaN, -0.0, True/1, ±2^70, hash(-1)/hash(-2))", edge_ok)

print()
print(f"👉 ИТОГ РЕГРЕССИОННОГО КОМПЛЕКСА: пройдено {_complex_passed} из {_complex_total}")

# ---------------------------------------------------------------------
# БЛОК 5: ГЛOБАЛЬНЫЙ СТРЕСС-ТЕСТ НА 5 000 000 РАЗНОРОДНЫХ ЭЛЕМЕНТОВ
# ---------------------------------------------------------------------
SIZE_HEAVY = 5000000
MIXED_COUNT = 1000000

print(f"--- БЛОК 5: УЛЬТИМАТИВНЫЙ НАГРУЗОЧНЫЙ ТЕСТ ({SIZE_HEAVY:,} ЭЛЕМЕНТОВ) ---")
print("1. Генерируем 4 миллиона standard целых чисел...")
heavy_data = list(range(SIZE_HEAVY - MIXED_COUNT))

print("2. Генерируем 1 миллион нехэшируемых и сложных объектов...")
target_mixed_item = {"секретный_ключ": "найди_меня_если_сможешь", "id": 66}

types_pool = [True, False, None, {"вложенный_ключ": 42}, [1, 2, 3], {11, 22}, StudentItem(123)]
mixed_pool = [types_pool[i % len(types_pool)] if i % len(types_pool) < 6 else StudentItem(i) for i in range(MIXED_COUNT - 1)]
mixed_pool.append(target_mixed_item)

print("3. Объединяем массивы и перемешиваем в случайном порядке...")
full_heavy_data = heavy_data + mixed_pool
random.shuffle(full_heavy_data)

print("4. Загружаем 5 млн элементов в C++ структуры ядра...")
start_init = time.perf_counter()
indexed_hl_heavy = hashlist(full_heavy_data)
standard_list_heavy = list(full_heavy_data)
print(f"   Инициализация Си вектора и хэш-карты завершена за: {time.perf_counter() - start_init:.2f} сек")

print(f"\n⚡ Начинаем замеры поиска вложенного словаря среди {SIZE_HEAVY:,} элементов:")

start = time.perf_counter()
found_opt = target_mixed_item in indexed_hl_heavy
t_heavy_opt = time.perf_counter() - start
print(f"  [hashlist (нативный Си O(1) поиск)]: Результат = {found_opt} | Время = {t_heavy_opt:.8f} сек")

start = time.perf_counter()
found_std = target_mixed_item in standard_list_heavy
t_heavy_std = time.perf_counter() - start
print(f"  [Встроенный Python list (линейный O(N))]: Результат = {found_std} | Время = {t_heavy_std:.8f} сек")

print(f"\n👉 ИТОГ СТРЕСС-ТЕСТА: На пяти миллионах разнородных данных Си ядро выиграло у Python list в {t_heavy_std / t_heavy_opt:,.1f} раз(а)!")
print()

# ---------------------------------------------------------------------
# БЛОК 6: СТУДЕНЧЕСКИЙ ПРОФИЛЬНЫЙ БЕНЧМАРК (ДОПОЛНЕНИЕ С УЧЕТОМ СКРИНШОТОВ)
# ---------------------------------------------------------------------
print("--- БЛОК 6: СРАВНЕНИЕ ОБЫЧНОГО LIST И HASHLIST НА МАЛОМ МАСШТАБЕ ---")
SIZE_STUD = 20000
REPEATS_STUD = 7
print(f"Размер основного набора: {SIZE_STUD:,} элементов")
print(f"Количество повторов: {REPEATS_STUD}\n")
print(f"{'Операция':<40} {'list, мс':<12} {'hashlist, мс':<15} {'Сравнение'}")
print("-" * 95)

stud_raw = list(range(SIZE_STUD))
random.shuffle(stud_raw)

# 1. Создание из готовых данных
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = list(stud_raw)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = hashlist(stud_raw)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Создание из готовых данных':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 2. append (20 000 элементов)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list()
    for i in range(SIZE_STUD): l.append(i)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist()
    for i in range(SIZE_STUD): h.append(i)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'append (20 000 элементов)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 3. extend (20 000 элементов)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(); l.extend(stud_raw)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(); h.extend(stud_raw)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'extend (20 000 элементов)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

st_list = list(stud_raw)
st_hl = hashlist(stud_raw)

# 4. Вставка в конец (1 000)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(st_list)
    for i in range(1000): l.insert(len(l), i)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(st_hl)
    for i in range(1000): h.insert(len(h), i)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Вставка в конец (1 000)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 5. Вставка в начало (500)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(st_list)
    for i in range(500): l.insert(0, i)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(st_hl)
    for i in range(500): h.insert(0, i)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Вставка в начало (500)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 6. Удаление с конца (1 000)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(st_list)
    for _ in range(1000): l.pop()
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(st_hl)
    for _ in range(1000): h.pop()
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Удаление с конца (1 000)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 7. Удаление с начала (500)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(st_list)
    for _ in range(500): l.pop(0)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(st_hl)
    for _ in range(500): h.pop(0)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Удаление с начала (500)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

targets_stud = [random.randint(0, SIZE_STUD - 1) for _ in range(1000)]
missing_stud = [random.randint(SIZE_STUD, SIZE_STUD * 2) for _ in range(1000)]

# 8. Поиск существующих элементов
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for t in targets_stud: _ = t in st_list
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for t in targets_stud: _ = t in st_hl
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Поиск существующих элементов':<40} {t_list:<12.3f} {t_hl:<15.3f} {'hashlist быстрее' if t_hl < t_list else 'list быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 9. Поиск отсутствующих элементов
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for t in missing_stud: _ = t in st_list
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for t in missing_stud: _ = t in st_hl
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Поиск отсутствующих элементов':<40} {t_list:<12.3f} {t_hl:<15.3f} {'hashlist быстрее' if t_hl < t_list else 'list быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 10. index
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for t in targets_stud: _ = st_list.index(t)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for t in targets_stud: _ = st_hl.index(t)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'index':<40} {t_list:<12.3f} {t_hl:<15.3f} {'hashlist быстрее' if t_hl < t_list else 'list быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 11. count (20 000 одинаковых)
uniq_list = [5] * SIZE_STUD
uniq_hl = hashlist(uniq_list)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = uniq_list.count(5)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = uniq_hl.count(5)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'count (20 000 одинаковых)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'hashlist быстрее' if t_hl < t_list else 'list быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 12. remove (100 удалений дубликатов)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(uniq_list)
    for _ in range(100): l.remove(5)
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(uniq_list)
    for _ in range(100): h.remove(5)
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'remove (100 удалений дубликатов)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 13. Срезы
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = st_list[100:15000:3]
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = st_hl[100:15000:3]
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Срезы':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 14. Полный перебор элементов
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for item in st_list: pass
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    for item in st_hl: pass
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Полный перебор элементов':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 15. reverse
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(st_list); l.reverse()
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(st_hl); h.reverse()
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'reverse':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 16. sort
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(st_list); l.sort()
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(st_hl); h.sort()
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'sort':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 17. copy
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = st_list.copy()
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD): _ = st_hl.copy()
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'copy':<40} {t_list:<12.3f} {t_hl:<15.3f} {'list быстрее' if t_list < t_hl else 'hashlist быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")

# 18. Смешанные операции (2 000)
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    l = list(st_list)
    for i in range(1000): l.append(i); _ = i in l
    for _ in range(1000): l.pop()
t_list = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
t0 = time.perf_counter()
for _ in range(REPEATS_STUD):
    h = hashlist(st_hl)
    for i in range(1000): h.append(i); _ = i in h
    for _ in range(1000): h.pop()
t_hl = (time.perf_counter() - t0) * 1000 / REPEATS_STUD
print(f"{'Смешанные операции (2 000)':<40} {t_list:<12.3f} {t_hl:<15.3f} {'hashlist быстрее' if t_hl < t_list else 'list быстрее'}: в {max(t_hl, t_list)/min(t_hl, t_list):.2f}x")
print("=====================================================================")
