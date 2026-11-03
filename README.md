*Read this in other languages: [Русский](#hashlist-на-русском).*

# hashlist

A high-performance, drop-in replacement for the standard Python `list` with **O(1) search and index speed** powered by a native, ultra-low-level **CPython C API backend**.

## 🚀 The Problem & Our Solution

In Python, checking if an item exists in a standard `list` (`item in my_list`) or finding its position (`my_list.index(item)`) takes **O(N) linear time**. As your dataset grows to millions of elements, these sequential pointer comparisons become a massive bottleneck for the CPU.

`hashlist` solves this by introducing a highly optimized hybrid data structure written entirely in pure C. It combines a continuous native C array of `PyObject*` pointers (preserving original insertion order, indices, and fast slices) with a specialized native **Chaining Bucket Hash Table** on the raw machine-instruction level.

By bypassing high-level wrappers, removing templates overhead, and leveraging an advanced **Lazy Rebuild** deferred synchronization flag, lookups, counter extractions, and index resolutions run in **O(1) constant time**, making it over **1,400x faster** than a standard Python list on heavy heterogeneous workloads without losing performance during sequential packet mutations.

## ✨ Features

- **⚡ Blazing Fast Lookups:** Constant time O(1) searches regardless of the list size (just 0.12 ms on 20K rows and stable linear scaling up to 5M elements).
- **🚀 Ultra-Fast Index Resolution:** Unlike standard lists, finding the position of an element takes constant O(1) time due to raw low-level bucket tracking.
- **🧠 100% Type Agnostic & Strict Identity:** Safely handles standard primitives as well as mutable unhashable structures (`list`, `dict`, `set`) via commutative associative hash summing. Fully separates boolean identity (`True` != `1`, `False` != `0`) at the C-bucket layer.
- **📦 Drop-in Replacement:** Fully implements the CPython `MutableSequence` protocol. Supports extended slices, negative indexing, mathematical operators (`+`, `*`, `+=`, `*=`), and global functions like `sorted()` and `reversed()`.
- **🪶 Memory Optimized:** Built using `__slots__` at the wrapper level. An empty upper-level Python class takes only **40 bytes** of memory due to raw pointer bindings.

## 📊 Performance Benchmark

Comparative profiling under a heterogeneous workload (20,000 elements scale, executed under Python 3.13.15, GCC 16.2.1):

| Operation | Standard Python `list` | **`hashlist` (Pure C)** | Direct Comparison | Algorithmic Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Search (Absent Item)** | 178.660 ms | **0.127 ms** | **hashlist is 1405.5x Faster** | **O(1)** vs O(N) |
| **Search (Existing Item)** | 86.385 ms | **0.197 ms** | **hashlist is 439.5x Faster** | **O(1)** vs O(N) |
| **Index Resolution (`.index()`)** | 117.996 ms | **0.176 ms** | **hashlist is 671.3x Faster** | **O(1)** vs O(N) |
| **Occurrences Count (`.count()`)** | 0.026 ms | **0.011 ms** | **hashlist is 2.4x Faster** | **O(1)** vs O(N) |
| **Packet Appending (20K items)** | 1.256 ms | **2.220 ms** | Near-native list speed | **O(1)** amortized |
| **Sequential Packet Deletions** | 0.311 ms | **0.940 ms** | Optimized O(N) memory pass | **O(N)** native block |

## 🧠 Memory Footprint & Scalability Analysis

Unlike bloated proverbs, `hashlist` uses strict low-level structural allocations via `calloc` and `realloc`:

### Empty Container Weight (RAM Balance)
- **Python Wrapper with `__slots__`:** 40 bytes (Lighter than standard empty list which takes 56 bytes).
- **Native C Structure (`HashListObject`):** 72 bytes.
- **Initial 1024-Bucket Map Allocation:** 8.1 KB.
- **🔥 Total Empty Footprint:** **~8.7 KB** for ultimate initial fast safety bounds.

## 🛠️ Complete Methods Specification

| Method | Description | Complexity | Pure C Advantage |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Appends element `x` to the end. Supports nested structures. | **O(1)** amortized | Defers hash mapping re-calculations via dirty token flags. |
| `hl.extend(iterable)` | Appends all elements from the iterable. | **O(M)** | Fast sequential batch vector initialization at machine speed. |
| `hl.insert(i, x)` | Inserts element `x` at position `i`. | O(N-i) shift | Direct block memory pointer operations via fast `memmove`. |
| `hl.remove(x)` | Removes the first occurrence of value `x`. | **O(1)** lookup + O(N) | Linear scan is completely bypassed during lookup phase. |
| `hl.clear()` | Removes all elements. | **O(1)** | Instant memory pointers deallocation. |
| `hl.index(x)` | Returns the index of the first occurrence of `x`. | **🚀 O(1) constant** | Extracted directly from the C-bucket map without loops. |
| `hl.pop(i=-1)` | Removes and returns element at index `i`. | **🔥 O(1) for end pop** | Flat `memmove` slice modification bounds. |

## 💻 Quick Start

```python
from hashlist import hl, hashlist

# 1. Quick creation using the factory function
my_list = hl(1, True, "apple", {"id": 66})

# 2. Strict type identity on pure C layer
print(my_list.count(1))     # 1 (Strictly distinct from True!)
print(my_list.count(True))  # 1 (Boolean and integers separated!)

# 3. Instant O(1) searches and index resolution
print("apple" in my_list)  # True (0.12 ms on large datasets!)
print(my_list.index("apple"))  # 2 (Instant resolution!)
```

---
# hashlist (На русском)

Высокопроизводительная замена стандартного Python `list` с **O(1) скоростью поиска и разрешения индексов**, работающая на нативном, ультранизкоуровневом ядре **CPython C API** без лишнего оверхеда.

## 🚀 Проблема и наше решение

В Python проверка наличия элемента в стандартном списке (`item in my_list`) или поиск его позиции (`my_list.index(item)`) занимает **O(N) линейное время**. По мере того как ваш набор данных растет до миллионов элементов, последовательное сравнение Си-указателей превращается в критическое «узкое место» для процессора.

`hashlist` решает эту проблему за счет внедрения оптимизированной гибридной структуры данных на чистом Си. Она сочетает в себе быстрый непрерывный Си-массив указателей `PyObject*` (сохраняющий исходный порядок вставки, индексы и срезы) с нативной **хэш-таблицей методом цепочек (Chaining)** на уровне машинных инструкций.

За счет отказа от тяжелых абстракций шаблонов и внедрения архитектуры **Lazy Rebuild** (отложенной ленивой перестройки карты перед поисковыми вызовами), поиск, подсчет вхождений и извлечение индексов выполняются за **константное время O(1)**. Это делает контейнер более чем в **1400 раз быстрее** стандартного Python-списка без потери производительности во время интенсивных пакетных изменений структуры.

## ✨ Особенности

- **⚡ Молниеносный поиск:** Константное время O(1) для оператора `in` независимо от размера списка (всего 0.12 мс на масштабе в 20 000 элементов с мгновенным ленивым ребилдом).
- **🚀 Моментальное разрешение индексов:** Метод `.index()` находит позицию элемента за O(1) благодаря прямому низкоуровневому Си-трекингу цепочек бакетов.
- **🧠 100% строгость типов и всеядность:** Надежно обрабатывает как примитивы, так и изменяемые нехэшируемые структуры (вложенные `list`, `dict`, `set`) с помощью коммутативного суммирования Си-хэшей. Строго разделяет типы-близнецы на уровне Си-бакетов (`True` != `1`, `False` != `0`).
- **📦 Полноценная drop-in замена:** Полностью реализует протокол `MutableSequence` в CPython. Из коробки поддерживаются сложные срезы, отрицательная индексация, математические операторы (`+`, `*`, `+=`, `*=`) и глобальные встроенные функции `sorted()` и `reversed()`.
- **🪶 Минимальный вес:** Построена с использованием `__slots__` на уровне Python-оболочки. Сама пустая Python-оболочка занимает всего **40 байт** памяти, сохраняя жесткую Си-структуру данных.

## 📊 Бенчмарк производительности

Результаты профилирования на основном наборе данных из 20 000 разнородных элементов (Python 3.13.15, CachyOS, компилятор GCC 16.2.1):

| Операция | Стандартный `list` | **`hashlist` (Нативное Си-ядро)** | Итоговое сравнение | Алгоритмическая сложность |
| :--- | :--- | :--- | :--- | :--- |
| **Поиск отсутствующих элементов** | 178.660 мс | **0.127 мс** | **hashlist быстрее в 1405.58 раз** | **O(1)** vs O(N) |
| **Поиск существующих элементов** | 86.385 мс | **0.197 мс** | **hashlist быстрее в 439.58 раз** | **O(1)** vs O(N) |
| **Разрешение индексов (`.index()`)** | 117.996 мс | **0.176 мс** | **hashlist быстрее в 671.30 раз** | **O(1)** vs O(N) |
| **Подсчет вхождений (`.count()`)** | 0.026 мс | **0.011 мс** | **hashlist быстрее в 2.40 раза** | **O(1)** vs O(N) |
| **Пакетный `extend` (20K элементов)** | 0.108 мс | **0.297 мс** | Скорость нативного Си-списка | **O(M)** векторизованный |
| **Последовательные удаления (`remove`)**| 0.311 мс | **0.940 мс** | Прямой O(N) Си-перебор без ребилдов | **O(N)** плоский блок |

## 🧠 Анализ потребления памяти и масштабируемости

В отличие от раздутых структур данных, `hashlist` использует строгое низкоуровневое выделение памяти через `calloc` и `realloc`:

### Вес пустого контейнера (Баланс RAM)
- **Python-обёртка со `__slots__`:** 40 байт (Легче стандартного пустого списка, который весит 56 байт).
- **Нативная Си-структура (`HashListObject`):** 72 байт.
- **Начальная аллокация карты на 1024 бакета:** ~8.1 КБ.
- **🔥 Итоговый чистый вес:** **~8.7 КБ** для абсолютной защиты O(1) скорости на старте.

## 🛠️ Полная спецификация методов

| Метод | Описание | Сложность | Преимущество Си-ядра |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Добавляет элемент `x` в конец. | **O(1)** амортизировано | Взводит статус `dirty` для откладывания тяжелых пересчетов. |
| `hl.extend(iterable)` | Добавляет в конец элементы из последовательности. | **O(M)** | Быстрая векторизованная аллокация памяти всей пачки за один шаг. |
| `hl.insert(i, x)` | Вставляет элемент `x` на позицию `i` со сдвигом. | O(N-i) сдвиг | Прямые операции с указателями блоков памяти через `memmove`. |
| `hl.remove(x)` | Удаляет первое вхождение значения `x`. | **O(1)** лукап + O(N) | Линейное сканирование полностью исключается при поиске по чистой таблице. |
| `hl.clear()` | Удаляет все элементы, полностью освобождая память. | **O(1)** | Моментальная деаллокация указателей памяти. |
| `hl.index(x)` | Возвращает индекс первого вхождения `x`. | **🚀 O(1) константа** | Извлекается напрямую из карты Си-бакетов без циклов перебора. |
| `hl.pop(i=-1)` | Удаляет и возвращает элемент по индексу `i`. | **🔥 O(1) для хвоста** | Быстрый плоский сдвиг Си-указателей на данные. |
| `hl.count(x)` | Возвращает количество повторений элемента `x`. | **🚀 O(1) constant** | Молниеносное извлечение счетчика размера напрямую из хэш-карты. |
| `hl.sort()` | Сортирует элементы на месте. | \(O(N \log N)\) | Проход алгоритма Timsort напрямую по непрерывному нативному массиву. |
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
print("яблоко" in my_list)  # True (0.12 мс на больших наборах данных!)
print(my_list.index("яблоко"))  # 2 (Моментальное разрешение положения!)
```

## 🏗️ Промышленная сборка и дистрибуция

Пакет использует современный инструментарий `scikit-build-core` для чистой Си-компиляции внутри изолированных окружений `uv`. Он безупречно собирается на Arch Linux (CachyOS), Ubuntu, macOS и Windows.

### Запуск полного автоматизированного набора тестов
```bash
uv sync --reinstall-package hashlist
uv run pytest -v -s
```

### Сборка готовых wheel-пакетов (.whl)
```bash
uv build
```
Эта команда скомпилирует исходный код Си и выведет готовые wheel-пакеты в директорию `dist/`, подготовленные к безопасной загрузке на PyPI.

## 📄 Лицензия

Распространяется под лицензией MIT. Разработано с фокусом на абсолютную оптимизацию производительности на машинном уровне: Fort66 (mamonov.1966@yandex.ru).
