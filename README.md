*Read this in other languages: [Русский](#hashlist-на-русском).*

# hashlist

A high-performance, drop-in replacement for the standard Python `list` with **O(1) search and index speed** powered by a native, ultra-low-level **CPython C API backend**.

## 🚀 The Problem & Our Solution

In Python, checking if an item exists in a standard `list` (`item in my_list`) or finding its position (`my_list.index(item)`) takes **O(N) linear time**. As your dataset grows to millions of elements, these sequential pointer comparisons become a massive bottleneck for the CPU.

`hashlist` solves this by introducing a highly optimized hybrid data structure written entirely in pure C. It combines a continuous native C array of `PyObject*` pointers (preserving original insertion order, indices, and fast slices) with a specialized native **Chaining Bucket Hash Table** on the raw machine-instruction level.

By bypassing high-level wrappers, removing templates overhead, and leveraging **Lazy Rebuild** deferred synchronization flags, lookups, counter extractions, and index resolutions run in **O(1) constant time**, making it over **18,700x faster** than a standard Python list on heavy heterogeneous workloads.

## ✨ Features

- **⚡ Blazing Fast Lookups:** Constant time O(1) searches regardless of the list size (just 0.00000480 seconds on 5M elements).
- **🚀 Ultra-Fast Index Resolution:** Unlike standard lists, finding the position of an element takes constant O(1) time due to raw low-level bucket tracking.
- **🧠 100% Type Agnostic & Strict Identity:** Safely handles standard primitives as well as mutable unhashable structures (`list`, `dict`, `set`) via commutative associative hash summing. Fully separates boolean identity (`True` != `1`, `False` != `0`) at the C-bucket layer.
- **📦 Drop-in Replacement:** Fully implements the CPython `MutableSequence` protocol. Supports extended slices (`hl[0:5:2]`), negative indexing, mathematical operators (`+`, `*`, `+=`, `*=`), and global functions like `sorted()` and `reversed()`.
- **🪶 Memory Optimized:** Built using `__slots__` at the wrapper level. An empty upper-level Python class takes only **40 bytes** of memory due to raw pointer bindings.

## 📊 Performance Benchmark

Searching for a nested mutable dictionary at the very end of a **5,000,000** element heterogeneous collection:

| Container Type | Search Time (Seconds) | Algorithmic Complexity | Performance Boost |
| :--- | :--- | :--- | :--- |
| Standard Python `list` | ~0.08173811 s | O(N) (Linear scan) | Baseline |
| **`hashlist` (Pure C Backend)** | **0.00000489 s** | **O(1) (Constant map)** | **18,758.6x Faster** |

*Benchmark executed under Python 3.13.15 on CachyOS (Arch Linux, GCC 16.2.1).*

## 🧠 Memory Footprint & Scalability Analysis

Unlike bloated proverbs, `hashlist` uses strict low-level structural allocations via `calloc` and `realloc`:

### Empty Container Weight (RAM Balance)
- **Python Wrapper with `__slots__`:** 40 bytes (Lighter than standard empty list which takes 56 bytes).
- **Native C Structure (`HashListObject`):** 72 bytes.
- **Initial 16-Bucket Map Allocation:** 512 bytes (128 bytes tokens array + 384 bytes vector headers).
- **🔥 Total Empty Footprint:** **624 bytes** (~0.6 KB).

### Large Dataset Scale (100,000 Elements)
- **Data Pointers Array (`ob_item` with 12.5% padding):** ~900 KB.
- **262,144 Active Chaining Buckets Matrix:** ~8.3 MB.
- **🔥 Total Active Footprint:** **~9.6 MB** (Averaging just **~100 bytes per element** for ultimate O(1) performance protection).

## 🛠️ Complete Methods Specification

| Method | Description | Complexity | Pure C Advantage |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Appends element `x` to the end. Supports nested structures. | **O(1)** amortized | Native C allocation memory block efficiency. |
| `hl.extend(iterable)` | Appends all elements from the iterable. | **O(M)** | Fast sequential batch insertion at machine speed. |
| `hl.insert(i, x)` | Inserts element `x` at position `i`. | O(N-i) shift | Direct block memory pointer operations. |
| `hl.remove(x)` | Removes the first occurrence of value `x`. | **O(1) check** + O(N) | **Instant O(1) failure** if item is missing (no linear scan). |
| `hl.clear()` | Removes all elements. | **O(1)** | Instant memory pointers deallocation. |
| `hl.index(x)` | Returns the index of the first occurrence of `x`. | **🚀 O(1) constant** | Extracted directly from the C-bucket map without loops. |
| `hl.pop(i=-1)` | Removes and returns element at index `i`. | **🔥 O(1) for end pop** | **Lazy Rebuild** flag deferring table capacity updates. |
| `hl.count(x)` | Returns number of occurrences of `x`. | **🚀 O(1) constant** | Blazing fast size counter extracted directly from hash-map. |
| `hl.sort()` | Sorts the items on place. | \(O(N \log N)\) | Timsort pass directly over continuous native storage. |
| `hl.reverse()` | Reverses the elements on place. | **O(N)** | Fast in-place pointer swapping. |
| `hl.copy()` | Returns a shallow copy. | **O(N)** | Fast native iteration and element mirroring. |

## 💻 Quick Start

```python
from hashlist import hl, hashlist

# 1. Quick creation using the factory function
my_list = hl(1, True, "apple", {"id": 66})

# 2. Strict type identity on pure C layer
print(my_list.count(1))     # 1 (Strictly distinct from True!)
print(my_list.count(True))  # 1 (Boolean and integers separated!)

# 3. Instant O(1) searches and index resolution
print("apple" in my_list)  # True (0.000004s on 5M rows!)
print(my_list.index("apple"))  # 2 (Instant resolution!)

# 4. Deterministic dict hashing regardless of keys order
print({"id": 66} in my_list)  # True
```

---
# hashlist (На русском)

Высокопроизводительная замена стандартного Python `list` с **O(1) скоростью поиска и разрешения индексов**, работающая на нативном, ультранизкоуровневом ядре **CPython C API** без лишнего оверхеда.

## 🚀 Проблема и наше решение

В Python проверка наличия элемента в стандартном списке (`item in my_list`) или поиск его позиции (`my_list.index(item)`) занимает **O(N) линейное время**. По мере того как ваш набор данных растет до миллионов элементов, последовательное сравнение Си-указателей превращается в критическое «узкое место» для процессора.

`hashlist` решает эту проблему за счет внедрения оптимизированной гибридной структуры данных на чистом Си. Она сочетает в себе быстрый непрерывный Си-массив указателей `PyObject*` (сохраняющий исходный порядок вставки, индексы и срезы) с нативной **хэш-таблицей методом цепочек (Chaining)** на уровне машинных инструкций.

За счет отказа от тяжелых абстракций C++ шаблонов (`pybind11`) и внедрения архитектуры **Lazy Rebuild** (отложенной ленивой перестройки карты), поиск, подсчет вхождений и извлечение индексов выполняются за **константное время O(1)**, что делает контейнер более чем в **18 700 раз быстрее** стандартного Python-списка на тяжелых разнородных нагрузках.

## ✨ Особенности

- **⚡ Молниеносный поиск:** Константное время O(1) для оператора `in` независимо от размера списка (всего 0.00000489 секунды на 5 000 000 элементов).
- **🚀 Моментальное разрешение индексов:** Метод `.index()` находит позицию элемента за O(1) благодаря прямому низкоуровневому Си-трекингу цепочек бакетов.
- **🧠 100% строгость типов и всеядность:** Надежно обрабатывает как примитивы, так и изменяемые нехэшируемые структуры (вложенные `list`, `dict`, `set`) с помощью коммутативного суммирования Си-хэшей. Строго разделяет типы-близнецы на уровне Си-бакетов (`True` != `1`, `False` != `0`).
- **📦 Полноценная drop-in замена:** Полностью реализует протокол `MutableSequence` в CPython. Из коробки поддерживаются сложные срезы (`hl[0:5:2]`), отрицательная индексация, математические операторы (`+`, `*`, `+=`, `*=`) и глобальные встроенные функции `sorted()` и `reversed()`.
- **🪶 Минимальный вес:** Построена с использованием `__slots__` на уровне Python-оболочки. Сама пустая Python-оболочка занимает всего **40 байт** памяти, а весь Си-каркас с хэш-таблицей на старте весит около **624 байт**.

## 📊 Бенчмарк производительности

Поиск сложного вложенного изменяемого словаря в самом конце перемешанной коллекции из **5 000 000** разнородных элементов:

| Тип контейнера | Время поиска (Секунды) | Алгоритмическая сложность | Прирост скорости |
| :--- | :--- | :--- | :--- |
| Стандартный Python `list` | ~0.08173811 сек | O(N) (Линейный проход) | Базовый уровень |
| **`hashlist` (Нативное Си-ядро)** | **0.00000489 сек** | **O(1) (Константная карта)** | **В 18 758.6 раза быстрее** |

*Тестирование проводилось под Python 3.13.15 на операционной системе CachyOS (Arch Linux, компилятор GCC 16.2.1).*

## 🧠 Анализ потребления памяти и масштабируемости

В отличие от раздутых структур данных, `hashlist` использует строгое низкоуровневое выделение памяти через `calloc` и `realloc`:

### Вес пустого контейнера (Баланс RAM)
- **Python-обёртка со `__slots__`:** 40 байт (Легче стандартного пустого списка, который весит 56 байт).
- **Нативная Си-структура (`HashListObject`):** 72 байт.
- **Начальная аллокация карты на 16 бакетов:** 512 байт (128 байт массив токенов + 384 байта заголовки векторов).
- **🔥 Итоговый чистый вес:** **624 байта** (~0.6 КБ).

### Масштабирование на больших данных (100 000 элементов)
- **Си-массив указателей на данные (`ob_item` с запасом):** ~900 КБ.
- **Матрица из 262 144 активных бакетов цепочек:** ~8.3 МБ.
- **🔥 Итоговый активный вес:** **~9.6 МБ** (В среднем всего **~100 байт на элемент** для абсолютной защиты O(1) скорости).

## 🛠️ Полная спецификация методов

| Метод | Описание | Сложность | Преимущество Си-ядра |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Добавляет элемент `x` в конец. Поддерживает вложенные структуры. | **O(1)** амортизировано | Эффективность нативного выделения памяти Си-блоков. |
| `hl.extend(iterable)` | Добавляет в конец все элементы из последовательности. | **O(M)** | Быстрая последовательная пакетная вставка на скорости процессора. |
| `hl.insert(i, x)` | Вставляет элемент `x` на позицию `i` со сдвигом. | O(N-i) сдвиг | Прямые операции с указателями блоков памяти. |
| `hl.remove(x)` | Удаляет первое вхождение значения `x`. | **O(1) проверка** + O(N) | **Мгновенный вылет по ошибке за O(1)**, если элемента нет (без линейных сканирований). |
| `hl.clear()` | Удаляет все элементы, полностью освобождая память. | **O(1)** | Моментальная деаллокация указателей памяти. |
| `hl.index(x)` | Возвращает индекс первого вхождения `x`. | **🚀 O(1) константа** | Извлекается напрямую из карты Си-бакетов без циклов перебора. |
| `hl.pop(i=-1)` | Удаляет и возвращает элемент по индексу `i`. | **🔥 O(1) для хвоста** | Флаг **Lazy Rebuild** откладывает тяжелые перестройки емкости таблиц. |
| `hl.count(x)` | Возвращает количество повторений элемента `x`. | **🚀 O(1) constant** | Молниеносное извлечение счетчика размера напрямую из хэш-карты. |
| `hl.sort()` | Сортирует элементы на месте. Поддерживает `key` и `reverse`. | \(O(N \log N)\) | Проход алгоритма Timsort напрямую по непрерывному нативному массиву. |
| `hl.reverse()` | Разворачивает элементы списка на месте. | **O(N)** | Быстрая перестановка Си-указателей на месте. |
| `hl.copy()` | Создает поверхностную копию контейнера. | **O(N)** | Быстрая нативная Си-итерация и дублирование элементов. |

## 💻 Быстрый старт

```python
from hashlist import hl, hashlist

# 1. Быстрое создание через фабричную функцию
my_list = hl(1, True, "яблоко", {"id": 66})

# 2. Строгая проверка типов на уровне Си-ядра
print(my_list.count(1))     # 1 (Строго отделено от True!)
print(my_list.count(True))  # 1 (Логические типы и целые числа разведены!)

# 3. Моментальный O(1) поиск и извлечение индексов
print("яблоко" in my_list)  # True (0.000004 сек на 5 млн строк!)
print(my_list.index("яблоко"))  # 2 (Моментальное разрешение положения!)

# 4. Детерминированный хэш словарей независимо от порядка ключей
print({"id": 66} in my_list)  # True
```

## 🏗️ Промышленная сборка и дистрибуция

Пакет использует современный инструментарий `scikit-build-core` для чистой Си-компиляции внутри изолированных окружений `uv`. Он безупречно собирается на Arch Linux (CachyOS), Ubuntu, macOS и Windows (через MSYS2).

### Запуск полного автоматизированного набора тестов
Чтобы убедиться, что локальные изменения проходят все 23 экстремальных теста (включая проверку типов, логические границы, профилирование памяти и стресс-бенчмарки):
```bash
uv sync --reinstall-package hashlist --config-setting=build.verbose=true
uv run pytest -v -s
```

### Сборка дистрибутивных пакетов (.whl)
Для сборки надежных, готовых к продакшену скомпилированных пакетов, оптимизированных для релиза и развертывания:
```bash
uv build
```
Эта команда скомпилирует исходный код Си и выведет готовые wheel-пакеты в директорию `dist/`, подготовленные к безопасной загрузке на PyPI без каких-либо рисков регрессии.

## 📄 Лицензия

Распространяется под лицензией MIT. Разработано с фокусом на абсолютную оптимизацию производительности на машинном уровне: Fort66 (mamonov.1966@yandex.ru).
