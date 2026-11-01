import time
import random
import sys

# Кастомный класс для проверки объектов в Блоке 5
class StudentItem:
    def __init__(self, value):
        self.value = value
    def __repr__(self):
        return f"StudentItem({self.value})"


from hashlist import hl, hashlist

print("=====================================================================")
print("🚀 СТРЕСС-ТЕСТ И БЕНЧМАРК ПРОДУКТА hashlist (CPYTHON PURE C BACKEND)")
print("=====================================================================\n")

# ---------------------------------------------------------------------
# БЛОК 1: Проверка 12 канонических методов из спецификации
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# БЛОК 2: Тест глобальных функций sorted() и reversed()
# ---------------------------------------------------------------------
print("--- БЛОК 2: ТЕСТ ФУНКЦИЙ sorted() И reversed() ---")
b = hl(30, 10, 50, 20, 40)
print(f"Исходный hashlist: {b}")

sorted_b = hashlist(sorted(b))
print(f"Глобальный sorted(): {sorted_b} (Тип: {type(sorted_b).__name__})")

reversed_b = hashlist(reversed(b))
print(f"Глобальный reversed(): {reversed_b} (Тип: {type(reversed_b).__name__})")
print()


# ---------------------------------------------------------------------
# БЛОК 3: Тест детерминированности хэшей (Разный порядок ключей)
# ---------------------------------------------------------------------
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
mutation_hl = hl(nested_mut)
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
bool_ident_hl = hl(1, True, 0, False)
print(f"6. Разделение типов: count(1) -> {bool_ident_hl.count(1)} (Ожидается 1) | count(True) -> {bool_ident_hl.count(True)} (Ожидается 1)")
print(f"   Индекс True: {bool_ident_hl.index(True)} (Ожидается 1) | Индекс False: {bool_ident_hl.index(False)} (Ожидается 3)")
print()

# ---------------------------------------------------------------------
# БЛОК 5: ГЛOБАЛЬНЫЙ СТРЕСС-ТЕСТ НА 5 000 000 РАЗНОРОДНЫХ ЭЛЕМЕНТОВ
# ---------------------------------------------------------------------
SIZE_HEAVY = 5_000_000
MIXED_COUNT = 1_000_000

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
found_std = standard_list_heavy.count(target_mixed_item) > 0 if False else (target_mixed_item in standard_list_heavy)
t_heavy_std = time.perf_counter() - start
print(f"  [Встроенный Python list (линейный O(N))]: Результат = {found_std} | Время = {t_heavy_std:.8f} сек")

print(f"\n👉 ИТОГ СТРЕСС-ТЕСТА: На пяти миллионах разнородных данных Си ядро выиграло у Python list в {t_heavy_std / t_heavy_opt:,.1f} раз(а)!")
print("=====================================================================")
