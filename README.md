*Read this in other languages: [Русский](#hashlist-1).*
# hashlist

A high-performance, drop-in replacement for the standard Python `list` with **O(1) search and index speed** powered by a native C++17 backend via `pybind11`.

## 🚀 The Problem & Our Solution

In Python, checking if an item exists in a standard `list` (`item in my_list`) or finding its position (`my_list.index(item)`) takes **O(N) linear time**. As your dataset grows to millions of elements, these operations become a massive bottleneck for the CPU.

`hashlist` solves this by introducing a highly optimized hybrid data structure. It combines a fast native C++ `std::vector` (preserving original insertion order, indices, and slices) with an advanced C++ `std::unordered_map<ssize_t, std::vector<size_t>>` lookup bucket map on the machine-instruction level.

The result? Lookups, counter extractions, and index resolutions run in **O(1) constant time**, making it over **6,100x faster** than a standard Python list on heavy heterogeneous workloads.

## ✨ Features

- **⚡ Blazing Fast Lookups:** Constant time O(1) searches regardless of the list size.
- **🚀 Ultra-Fast Index Resolution:** Unlike standard lists, finding the position of an element takes constant O(1) time due to low-level continuous index bucket tracking.
- **🧠 100% Type Agnostic & Safe:** Safely handles standard hashable types (ints, strings) as well as mutable unhashable structures (nested `list`, `dict`, `set`) through a deterministic C++ recursive freeze algorithm.
- **📦 Drop-in Replacement:** Fully implements the CPython `MutableSequence` protocol. Supports extended slices (`hl[0:5:2]`), negative indexing, mathematical operators (`+`, `*`, `+=`, `*=`), and global functions like `sorted()` and `reversed()`.
- **🪶 Memory Optimized:** Built using `__slots__` at the wrapper level. An empty `hashlist` takes only **40 bytes** of memory due to lazy structures initialization.

## 📊 Performance Benchmark

Searching for a nested mutable dictionary at the very end of a **5,000,000** element heterogeneous collection:

| Container Type | Search Time (Seconds) | Algorithmic Complexity | Performance Boost |
| :--- | :--- | :--- | :--- |
| Standard Python `list` | ~0.14096335 s | O(N) (Linear scan) | Baseline |
| **`hashlist` (C++ Backend)** | **0.00002302 s** | **O(1) (Constant map)** | **6,123x Faster** |

*Benchmark executed under Python 3.13.15 on CachyOS (Arch Linux, GCC 16.2.1).*

## 🛠️ Complete Methods Specification

`hashlist` fully supports all 12 canonical Python list mutation and lookup methods with unique C++ architectural optimizations:

| Method | Description | Complexity | C++ Advantage |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Appends element `x` to the end. Supports nested structures. | **O(1)** amortized | Native C++ memory allocation efficiency |
| `hl.extend(iterable)` | Appends all elements from the iterable to the end. | **O(M)** | Fast sequential batch insertion |
| `hl.insert(i, x)` | Inserts element `x` at position `i` shifting vectors. | O(N-i) native shift | Direct block memory shift on native CPU instructions level |
| `hl.remove(x)` | Removes the first occurrence of value `x`. | **O(1) lookup check** + O(N) shift | **Instant failure** if item is missing (completely avoids linear vector scans) |
| `hl.clear()` | Removes all elements, completely resetting container. | **O(1)** | Instant bucket and vector memory deallocation |
| `hl.index(x)` | Returns the integer index of the first occurrence of `x`. | **🚀 O(1) constant** | **Instant index resolution** directly from the C++ bucket map without linear scans |
| `hl.pop(i=-1)` | Removes and returns the element at index `i`. | **🔥 O(1) for end pop** / O(N-i) shift | Activated **Fast-Path optimization** during end pop operations |
| `hl.count(x)` | Returns the number of times `x` appears in the list. | **🚀 O(1) constant** | Blazing fast value counter extracted directly from hash-map |
| `hl.sort()` | Sorts the items on place. Supports `key` and `reverse`. | \(O(N \log N)\) | Fast Timsort pass directly over continuous native storage |
| `hl.reverse()` | Reverses the elements of the list on place. | **O(N)** | Highly optimized `std::reverse` pointer swapping |
| `hl.copy()` | Returns a shallow copy of the container. | **O(N)** | Fast iteration and element mirroring |

## 💻 Quick Start

```python
from hashlist import hl, hashlist

# 1. Quick creation using the factory function
my_list = hl(10, 20, 30, "apple")

# 2. Add complex nested unhashable structures safely
my_list.append({"name": "Ivan", "id": 66})

# 3. Instant O(1) searches and index resolution on C++ level
print("apple" in my_list)  # True
print(my_list.index("apple"))  # 3 (Instant O(1) extraction!)
print({"id": 66, "name": "Ivan"} in my_list)  # True (Order independent!)

# 4. Standard Python functions and slices work seamlessly
for item in reversed(my_list):
    print(item)

sub_slice = my_list[1:4]
print(20 in sub_slice)  # True
```

## 🏗️ Development & Testing

The package uses `scikit-build-core` and `pybind11` for seamless native compilation inside `uv` environments.

To run the complete automated test suite (including performance, memory, and stress testing):
```bash
uv run pytest -v -s
```

## 📄 License

Distributed under the MIT License. Developed by Fort66 (mamonov.1966@yandex.ru).







# hashlist

Высокопроизводительная замена стандартного Python `list` с **O(1) скоростью поиска и разрешения индексов**, работающая на нативном C++17 бэкенде через `pybind11`.

## 🚀 Проблема и наше решение

В Python проверка наличия элемента в стандартном списке (`item in my_list`) или поиск его позиции (`my_list.index(item)`) занимает **O(N) линейное время**. По мере того как ваш набор данных растет до миллионов элементов, эти операции превращаются в критическое «узкое место» для процессора.

`hashlist` решает эту проблему за счет внедрения оптимизированной гибридной структуры данных. Она сочетает в себе быстрый нативный C++ `std::vector` (сохраняющий исходный порядок вставки, индексы и срезы) с продвинутой хэш-картой `std::unordered_map<ssize_t, std::vector<size_t>>` на уровне машинных инструкций.

Результат? Поиск, подсчет вхождений и извлечение индексов выполняются за **константное время O(1)**, что делает контейнер более чем в **6100 раз быстрее** стандартного Python-списка на тяжелых разнородных нагрузках.

## ✨ Особенности

- **⚡ Молниеносный поиск:** Константное время O(1) для оператора `in` независимо от размера списка.
- **🚀 Моментальное разрешение индексов:** В отличие от стандартных списков, метод `.index()` находит позицию элемента за O(1) благодаря непрерывному низкоуровневому отслеживанию бакетов.
- **🧠 100% всеядность и безопасность типов:** Надежно обрабатывает как стандартные хэшируемые типы (числа, строки), так и изменяемые нехэшируемые структуры (вложенные `list`, `dict`, `set`) с помощью детерминированного алгоритма рекурсивной «заморозки» на C++.
- **📦 Полноценная drop-in замена:** Полностью реализует протокол `MutableSequence` в CPython. Из коробки поддерживаются сложные срезы (`hl[0:5:2]`), отрицательная индексация, математические операторы (`+`, `*`, `+=`, `*=`) и глобальные встроенные функции `sorted()` и `reversed()`.
- **🪶 Оптимизация памяти:** Построена с использованием `__slots__` на уровне Python-оболочки. Пустой `hashlist` занимает всего **40 байт** памяти благодаря ленивой инициализации внутренних C++ структур.

## 📊 Бенчмарк производительности

Поиск сложного вложенного изменяемого словаря в самом конце перемешанной коллекции из **5 000 000** разнородных элементов:

| Тип контейнера | Время поиска (Секунды) | Алгоритмическая сложность | Прирост скорости |
| :--- | :--- | :--- | :--- |
| Стандартный Python `list` | ~0.14096335 сек | O(N) (Линейный проход) | Базовый уровень |
| **`hashlist` (C++ ядро)** | **0.00002302 сек** | **O(1) (Константная карта)** | **В 6123.5 раза быстрее** |

*Тестирование проводилось под Python 3.13.15 на операционной системе CachyOS (Arch Linux, компилятор GCC 16.2.1).*

## 🛠️ Спецификация поддерживаемых методов

`hashlist` полностью поддерживает все 12 канонических методов мутации и поиска стандартного списка со специальными архитектурными оптимизациями C++:

| Метод | Описание | Сложность | Преимущество C++ бэкенда |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Добавляет элемент `x` в конец. Поддерживает вложенные структуры. | **O(1)** амортизировано | Эффективность нативного выделения памяти C++ |
| `hl.extend(iterable)` | Добавляет в конец все элементы из переданной последовательности. | **O(M)** | Быстрая последовательная пакетная вставка (зависит только от размера принесенных данных) |
| `hl.insert(i, x)` | Вставляет элемент `x` на позицию `i` со сдвигом вектора. | O(N-i) нативный сдвиг | Прямой сдвиг блока памяти на уровне машинных инструкций процессора |
| `hl.remove(x)` | Удаляет первое вхождение значения `x`. | **O(1) проверка поиска** + O(N) сдвиг | **Мгновенный вылет с ошибкой** за O(1), если элемента нет (без линейного сканирования вектора) |
| `hl.clear()` | Удаляет все элементы, полностью освобождая память. | **O(1)** | Моментальная очистка бакетов хэш-карты и деаллокация вектора |
| `hl.index(x)` | Возвращает целочисленный индекс первого вхождения `x`. | **🚀 O(1) константа** | **Мгновенное разрешение индекса** напрямую из карты бакетов без линейных переборов |
| `hl.pop(i=-1)` | Удаляет и возвращает элемент по индексу `i`. | **🔥 O(1) для извлечения с конца** / O(N-i) сдвиг | Активация оптимизации **Fast-Path** при дефолтном удалении последнего элемента |
| `hl.count(x)` | Возвращает количество повторений элемента `x` в списке. | **🚀 O(1) константа** | Молниеносное извлечение размера вектора индексов напрямую из хэш-карты |
| `hl.sort()` | Сортирует элементы на месте. Поддерживает `key` и `reverse`. | \(O(N \log N)\) | Быстрый проход алгоритма Timsort напрямую по непрерывному C-массиву |
| `hl.reverse()` | Разворачивает элементы списка на месте. | **O(N)** | Высокооптимизированная перестановка указателей через `std::reverse` |
| `hl.copy()` | Создает поверхностную копию контейнера. | **O(N)** | Быстрая нативная итерация и зеркалирование элементов |

## 💻 Быстрый старт

```python
from hashlist import hl, hashlist

# 1. Быстрое создание через фабричную функцию
my_list = hl(10, 20, 30, "яблоко")

# 2. Безопасное добавление сложных нехэшируемых структур
my_list.append({"имя": "Иван", "id": 66})

# 3. Моментальный O(1) поиск и извлечение индексов на уровне C++
print("яблоко" in my_list)  # True
print(my_list.index("яблоко"))  # 3 (Мгновенно за O(1)!)
print({"id": 66, "имя": "Иван"} in my_list)  # True (Независимо от порядка ключей!)

# 4. Стандартные функции Python и срезы работают бесшовно
for item in reversed(my_list):
    print(item)

sub_slice = my_list[1:4]
print(20 in sub_slice)  # True
```

## 🏗️ Разработка и тестирование

Для автоматической компиляции и сборки расширения внутри изолированных окружений `uv` используются `scikit-build-core` и `pybind11`.

Чтобы запустить полный автоматизированный набор тестов (включая нагрузочное стресс-тестирование и бенчмарки скорости):
```bash
uv run pytest -v -s
```

## 📄 Лицензия

Распространяется под лицензией MIT. Разработчик: Fort66 (mamonov.1966@yandex.ru).
