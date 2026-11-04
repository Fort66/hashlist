*Read this in other languages: [Русский](#hashlist-на-русском).*

# hashlist

A high-performance, drop-in replacement for the standard Python `list` with **O(1) search and index resolution** powered by a native, ultra-low-level **CPython C API backend**.

## 🚀 The Problem & Our Solution

In Python, checking if an item exists in a standard `list` (`item in my_list`) or finding its position (`my_list.index(item)`) takes **O(N) linear time**. As your dataset grows to millions of elements, these sequential pointer comparisons become a massive bottleneck for the CPU.

`hashlist` solves this with a single native C object built on the raw machine-instruction level. It combines:

- a continuous C ribbon of `PyObject*` pointers — preserving insertion order, indices and fast slices, exactly like `list`;
- a **Chaining Bucket Hash Table** built lazily, only when the first search actually happens;
- a two-level token cache (`tokens_ready` flag): pointer-ribbon mutations keep the hash cache valid by touching a single slot, position-shifting mutations drop down to plain block moves and defer everything else to one deferred rebuild.

Under this design, membership tests and index resolution run in **O(1) constant time — up to ~2,500x faster** than a standard list on the latest measured run — while hot mutations (append/extend/pop/sort/copy) stay at native C speed, and several list pain-points (insert/delete at the front, mixed search-then-mutate workloads) actually become *faster* than `list`.

## ✨ Features

- **⚡ Blazing Fast Lookups:** Constant-time O(1) `in` and `.index()` regardless of list size — ~0.14 ms per search on 20K elements (vs ~90 ms for `list`), stable at 5M scale.
- **🎯 O(1) Absence Confirmation:** Searching for a *missing* item is O(1) too (the bucket map proves absence without scanning): ~0.07 ms vs ~178 ms for `list`.
- **🎯 Ultra-Fast Index Resolution:** `.index()` returns the position of the first occurrence directly from bucket chains with an early exit — ~645x faster than `list`.
- **🧠 100% Type Agnostic, `list`-Parity Equality:** Hashable items are tokenized by their real `hash()`; *unhashable* structures (`list`, `dict`, `set`) get a stable structural token — so an unhashable `{"id": 66}` is found in O(1), regardless of its keys' insertion order. Equality semantics are byte-identical to `list`: `True == 1`, `False == 0`, first occurrence wins; a nested object mutated after insertion remains findable (its token is stable).
- **📦 Drop-in Replacement:** Fully implements the CPython `MutableSequence` protocol: extended slices, negative indexing, `+`, `*`, `+=`, `*=`, `sorted()`, `reversed()`, `copy()`, `clear()`, `count()`, `pop()` and pickling of acyclic containers.
- **🪶 One C Object, Zero Preallocation:** `hashlist` is a subclass of a native C class (`__slots__ = ()`). An empty container takes **96 bytes**; no buffers exist until the first append; the bucket map (~2N machine words) is allocated only at the first search — no 8.1 KB bucket map at construction time.
- **🛡️ Hardened C Core:** reference-counting discipline (refcount parity with `list`), GC-safe (a hashlist may contain itself and is still collected), generator exceptions propagate (never swallowed), `METH_FASTCALL` hot paths, native Timsort-based `sort()`.

## 📊 Performance Benchmark

Comparative profiling under a heterogeneous workload (20,000 elements, 7 repetitions, Python 3.13.15, GCC 16.2.1). The full honest table — including rows where `list` still wins and why:

| Operation | Standard Python `list` | **`hashlist` (Pure C)** | Result | Complexity |
| :--- | :--- | :--- | :--- | :--- |
| **Search (Absent Item)** | 177.879 ms | **0.071 ms** | **hashlist 2,495x faster** | O(1) vs O(N) |
| **Search (Existing Item)** | 90.477 ms | **0.142 ms** | **hashlist 637x faster** | O(1) vs O(N) |
| **Index Resolution (`.index()`)** | 117.016 ms | **0.181 ms** | **hashlist 645x faster** | O(1) vs O(N) |
| **Mixed Ops (insert/search alternating)** | 85.599 ms | **63.627 ms** | **hashlist 1.35x faster** | — |
| **Insert at Front (500)** | 2.083 ms | **1.388 ms** | **hashlist 1.50x faster** | O(N) pointer shift |
| **Occurrences Count (`.count()`)** | 0.026 ms | **0.011 ms** | **hashlist 2.4x faster** | O(N), C-speed pass |
| **Extended Slices** | 0.021 ms | **0.019 ms** | hashlist 1.10x faster | O(N) |
| **Full Iteration** | 0.384 ms | 0.388 ms | parity | O(N) |
| **Packet `extend` (20K items)** | 0.091 ms | 0.106 ms | ~parity (1.16x) | O(M) |
| **Deletions at End (1,000)** | 0.119 ms | 0.130 ms | ~parity (1.09x) | O(1) |
| **`copy()`** | 0.067 ms | 0.072 ms | ~parity (1.09x) | O(N) block copy |
| **`reverse()`** | 0.076 ms | 0.084 ms | ~parity (1.11x) | O(N) pointer swap |
| **Insert at End (1,000)** | 0.188 ms | 0.226 ms | ~parity (1.20x) | O(1) amortized |
| **Deletions at Front (500)** | 1.326 ms | 1.335 ms | parity | O(N) block move |
| **`sort()`** | 2.775 ms | 2.834 ms | ~parity, native Timsort | O(N log N) |
| **`remove` (100 dups)** | 0.314 ms | 0.423 ms | ~parity (1.35x) | O(N) |
| **Packet Appending (20K items)** | 1.030 ms | 1.671 ms | list 1.6x faster* | O(1) amortized |
| **Creation from a list** | 0.070 ms | 0.263 ms | list 3.8x faster* | O(N) + hash import |

\* **The honest O(1)-search tax.** Creating a structure with instant search requires eagerly tokenizing every imported element (~9 ns per element, paid once; the subsequent builds are bucket-only and all searches stay O(1) forever). Packet `append` carries the residual floor of a C-method call on a C-type subclass (~+30 ns/item vs `list.append` at ~50 ns). On this micro-scale `list` keeps ~1.6x on `append` and ~3.8x on creation; the trade reverses completely as soon as any search happens.

All timings above are reproducible with the bundled script `test_run.py` (benchmark block 6).

## 🧠 Memory Footprint

`hashlist` is **one native C object** — a Python-side subclass of a C class with `__slots__ = ()` (zero per-instance Python overhead):

### Weight balance
- **Empty `hashlist`:** **96 bytes** on a 64-bit interpreter (empty standard `list`: 56 bytes).
- **Zero preallocation:** no pointer ribbons, no token ribbon and no bucket map exist until the first append; the bucket map (~2N machine words) is allocated lazily at the first search, and the map itself carries *pointers*, not copies of items.
- **Live footprint:** ``N × 8`` bytes for the item ribbon + ``N × 8`` bytes for the token cache + one bucket map. After deletions, the lazy compaction rebuild shrinks the allocation instead of leaving tombstones.

## 🛠️ Complete Methods Specification

| Method | Description | Complexity | Notes |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Appends element `x` to the end. Supports nested structures. | **O(1)** amortized | Pure C hot path; fills a single token when the token cache is warm. |
| `hl.extend(iterable)` | Appends all elements from the iterable. | **O(M)** | One resize + a single INCREF block; list/tuple inputs take a block-copy fast path. |
| `hl.insert(i, x)` | Inserts element `x` at position `i`. | O(N−i) shift | Direct `memmove` on the pointer ribbon; a mid-shift marks the token cache dirty (recomputed once, at the next search). |
| `hl.remove(x)` | Removes the first occurrence of value `x`. | **O(1)** lookup on a clean map, O(N) scan when dirty | Detailed scan comparable to `list.remove` is completely bypassed while the map is clean; then a block `memmove`. Raises `ValueError` if missing. |
| `hl.clear()` | Removes all elements. | O(N) | DECREF walk over the ribbon, same as `list.clear()`; frees the ribbons and the bucket map. |
| `hl.index(x)` | Returns the index of the first occurrence of `x`. | **🚀 O(1) constant** | Extracted directly from the bucket chain, equality-verified, early exit. |
| `hl.count(x)` | Counts occurrences of `x`. | O(N) linear | list-parity equality pass at C pointer-walk speed (~2.4x faster than `list`). |
| `hl.pop(i=-1)` | Removes and returns the element at index `i`. | **O(1)** for the tail, O(N−i) shift otherwise | Block pointer move; tail pops never invalidate the token cache. |
| `hl.sort()` | Sorts in place. Without `key`/`reverse` arguments it routes into the native C Timsort path. | O(N log N) | Native Timsort over the pointer ribbon. |
| `hl.reverse()` | Reverses in place. | **O(N)** | Pure pointer swap. |
| `hl.copy()` | Creates a shallow copy (returns exactly the `hashlist` type). | **O(N)** | Block copy of the pointer ribbon; no bucket map copying. |
| `hl[i]` / `hl[i] = x` / `del hl[i]` | Item access, assignment, deletion; slices and negative indices fully supported. | O(1) / O(N−i) | Slices return real `hashlist` objects and are searched in O(1) after their first lookup. |

## 💻 Quick Start

```python
from hashlist import hl, hashlist

# 1. Quick creation using the factory function
my_list = hl(1, True, "apple", {"id": 66})

# 2. Equality semantics are exactly like list (True == 1 — and nothing breaks):
print(my_list.count("apple"))        # 1

# 3. Instant O(1) searches and index resolution — even for an UNHASHABLE dict:
print("apple" in my_list)            # True (~0.1 ms at 20K scale!)
print(my_list.index({"id": 66}))     # 3  (the dict's key order doesn't matter)
```

## 🏗️ Architecture in One Screen

- **Pointer ribbon** (`ob_item`) — the single source of truth for `list parity`: order, indices, slices, iteration are plain C.
- **Token cache** (`flat_hashes`) — `8 bytes/element` of precomputed identifiers, kept in sync by the `tokens_ready` flag. Ribbon-preserving mutations (append, tail insert, `setitem`, tail pop) touch *one* slot; shifting mutations (mid insert/delete, front pop, remove, sort, reverse) just mark the map dirty and rely on the deferred rebuild.
- **Bucket map** (`head`/`next`) — a chaining hash index sized ~2N, built only at the first real search when the ribbon tokens are in sync. Chain heads store the minimal index, so the first strictly-equal match found is the first occurrence — early exit instead of scanning the whole chain.
- **Unhashable mutables** (list/dict/set) — tokenized by a stable structural `Py_TYPE` marker; actual element identity is then resolved by the exact same rich comparison `list` uses, so mutated nested objects stay findable.
- **Exceptions** from user iterators/generators during `hashlist(...)` and `extend()` propagate untouched (never swallowed).
- **GC support:** `Py_TPFLAGS_HAVE_GC` + `tp_traverse`/`tp_clear` — a hashlist can reference itself and is still collected.

## 🧱 Build, Install & Test

```bash
pip install hashlist          # prebuilt wheel, or
uv sync --reinstall-package hashlist   # build from the local source
uv run pytest -q              # full test suite
```

Ready-to-ship wheels: `uv build` (the C extension compiles under `scikit-build-core`; tested on Arch Linux/CachyOS, Ubuntu, macOS and Windows).

## 📄 License

Distributed under the MIT license. Built with a focus on absolute machine-level performance: Fort66 (mamonov.1966@yandex.ru).

---
# hashlist (На русском)

Высокопроизводительная замена стандартного Python `list` с **O(1) скоростью поиска и разрешения индексов**, работающая на нативном, ультранизкоуровневом ядре **CPython C API** без лишнего оверхеда.

## 🚀 Проблема и наше решение

В Python проверка наличия элемента в стандартном списке (`item in my_list`) или поиск его позиции (`my_list.index(item)`) занимает **O(N) линейное время**. По мере того как ваш набор данных растет до миллионов элементов, последовательное сравнение Си-указателей превращается в критическое «узкое место» для процессора.

`hashlist` решает эту проблему одним нативным C-объектом, построенным на уровне машинных инструкций. Внутри совмещены:

- непрерывная Си-лента указателей `PyObject*` — порядок вставки, индексы и срезы работают ровно как у `list`;
- **хэш-таблица методом цепочек (Chaining)**, которая строится лениво — только когда происходит первый настоящий поиск;
- двухуровневый кэш токенов (флаг `tokens_ready`): мутации, не сдвигающие позиции, сохраняют кэш хэшей досыпкой одного слота, а сдвигающие мутации уходят в обычные блочные сдвиги и откладывают всё остальное до одной отложенной пересборки.

Итог: поиск и разрешение индексов выполняются за **константное время O(1) — до ~2500 раз быстрее** стандартного списка на последнем измеренном прогоне, при этом горячие мутации (append/extend/pop/sort/copy) работают на скорости нативного Си, а болевые точки `list` — вставка и удаление в начало, смешанные нагрузки «поиск-изменение» — становятся даже *быстрее* стандартного списка.

## ✨ Особенности

- **⚡ Молниеносный поиск:** Константное время O(1) для оператора `in` и `.index()` независимо от размера списка — ~0.14 мс на масштабе в 20 000 элементов (против ~90 мс у `list`), стабильность сохраняется на масштабе 5 миллионов.
- **🎯 O(1) подтверждение отсутствия:** Поиск *несуществующего* элемента тоже O(1): карта бакетов доказывает отсутствие без перебора — ~0.07 мс против ~178 мс у `list`.
- **🚀 Моментальное разрешение индексов:** Метод `.index()` возвращает позицию первого вхождения напрямую из цепочек бакетов с ранним выходом — примерно в 645 раз быстрее `list`.
- **🧠 100% всеядность и паритет семантики `list`:** Хэшируемые элементы токенизируются своим настоящим `hash()`; изменяемые нехэшируемые структуры (`list`, `dict`, `set`) получают стабильный структурный токен — так что нехэшируемый `{"id": 66}` находится за O(1) независимо от порядка вставки ключей. Семантика равенства побайтово совпадает с `list`: `True == 1`, `False == 0`, возвращается первое вхождение; вложенный объект, мутировавший после вставки, остаётся находимым (его токен стабилен).
- **📦 Полноценная drop-in замена:** Полностью реализует протокол `MutableSequence` в CPython: сложные срезы, отрицательная индексация, операторы `+`, `*`, `+=`, `*=`, встроенные `sorted()` и `reversed()`, `copy()`, `clear()`, `count()`, `pop()` и пикллинг ациклических контейнеров.
- **🪶 Один C-объект, нулевая предвыделка:** `hashlist` — подкласс нативного C-класса (`__slots__ = ()`). Пустой контейнер весит **96 байт**; никаких буферов нет до первого append; карта бакетов (~2N машинных слов) выделяется только в момент первого поиска — никаких 8.1 КБ при создании.
- **🛡️ Закалённое Си-ядро:** дисциплина рефкаунтов (паритет со `list`), безопасная сборка мусора (список может содержать сам себя и при этом убирается GC), исключения генераторов не проглатываются, горячие пути на `METH_FASTCALL`, нативная сортировка на Timsort.

## 📊 Бенчмарк производительности

Результаты профилирования на гетерогенном наборе из 20 000 элементов (7 повторов, Python 3.13.15, GCC 16.2.1). Полная честная таблица — включая строки, в которых `list` всё ещё выигрывает, и почему:

| Операция | Стандартный `list` | **`hashlist` (Нативное Си-ядро)** | Итог | Сложность |
| :--- | :--- | :--- | :--- | :--- |
| **Поиск отсутствующих элементов** | 177.879 мс | **0.071 мс** | **hashlist быстрее в 2 495 раз** | O(1) vs O(N) |
| **Поиск существующих элементов** | 90.477 мс | **0.142 мс** | **hashlist быстрее в 637 раз** | O(1) vs O(N) |
| **Разрешение индексов (`.index()`)** | 117.016 мс | **0.181 мс** | **hashlist быстрее в 645 раз** | O(1) vs O(N) |
| **Смешанные операции (вставка/поиск)** | 85.599 мс | **63.627 мс** | **hashlist быстрее в 1.35 раза** | — |
| **Вставка в начало (500)** | 2.083 мс | **1.388 мс** | **hashlist быстрее в 1.50 раза** | O(N) сдвиг указателей |
| **Подсчет вхождений (`.count()`)** | 0.026 мс | **0.011 мс** | **hashlist быстрее в 2.4 раза** | O(N), Си-скорость |
| **Срезы** | 0.021 мс | **0.019 мс** | hashlist быстрее в 1.10 раза | O(N) |
| **Полный перебор элементов** | 0.384 мс | 0.388 мс | паритет | O(N) |
| **Пакетный `extend` (20K элементов)** | 0.091 мс | 0.106 мс | ~паритет (1.16x) | O(M) |
| **Удаление с конца (1 000)** | 0.119 мс | 0.130 мс | ~паритет (1.09x) | O(1) |
| **`copy()`** | 0.067 мс | 0.072 мс | ~паритет (1.09x) | O(N) блочное копирование |
| **`reverse()`** | 0.076 мс | 0.084 мс | ~паритет (1.11x) | O(N) перестановка |
| **Вставка в конец (1 000)** | 0.188 мс | 0.226 мс | ~паритет (1.20x) | O(1) амортизировано |
| **Удаление с начала (500)** | 1.326 мс | 1.335 мс | паритет | O(N) блочный сдвиг |
| **`sort()`** | 2.775 мс | 2.834 мс | ~паритет, нативный Timsort | O(N log N) |
| **`remove` (100 дубликатов)** | 0.314 мс | 0.423 мс | ~паритет (1.35x) | O(N) |
| **Пакетный `append` (20K элементов)** | 1.030 мс | 1.671 мс | list быстрее в 1.6 раза* | O(1) амортизировано |
| **Создание из списка** | 0.070 мс | 0.263 мс | list быстрее в 3.8 раза* | O(N) + хэш-импорт |

\* **Честный налог за мгновенный O(1)-поиск.** Чтобы структура ищала мгновенно, каждый импортированный элемент токенизируется при создании (~9 нс на элемент, платится один раз; последующие пересборки — только раскладка бакетов, и поиск остаётся O(1) навсегда). Пакетный `append` несёт нижний предел вызова C-метода на подклассе C-типа (~+30 нс/элемент против ~50 нс у `list.append`). На этом микро-масштабе `list` удерживает ~1.6x на `append` и ~3.8x на создании — но раскладка меняется мгновенно, как только случается хоть один поиск.

Все тайминги воспроизводимы прилагаемым скриптом `test_run.py` (бенчмарк-блок 6).

## 🧠 Вес в памяти

`hashlist` — **один нативный C-объект**: Python-подкласс C-класса с `__slots__ = ()` (нулевые на-инстансные расходы Python-уровня).

### Баланс веса
- **Пустой `hashlist`:** **96 байт** на 64-битном интерпретаторе (пустой стандартный `list` — 56 байт).
- **Нулевая предвыделка:** ни ленты элементов, ни ленты токенов, ни карты бакетов не существует до первого append; карта бакетов (~2N машинных слов) выделяется лениво в момент первого поиска и хранит *ссылки*, а не копии элементов.
- **Вес при работе:** `N × 8` байт лента элементов + `N × 8` байт кэш токенов + одна карта бакетов. После удалений ленивый дворник (компактация при пересборке) возвращает память вместо накопления надгробий.

## 🛠️ Полная спецификация методов

| Метод | Описание | Сложность | Примечание |
| :--- | :--- | :--- | :--- |
| `hl.append(x)` | Добавляет элемент `x` в конец (включая вложенные структуры). | **O(1)** амортизировано | Чистый горячий путь на Си; при горячем кэше токенов досыпается один слот. |
| `hl.extend(iterable)` | Добавляет все элементы из последовательности. | **O(M)** | Один resize + один INCREF-блок; list/tuple идут быстрым блочным путём. |
| `hl.insert(i, x)` | Вставляет элемент `x` на позицию `i`. | O(N−i) сдвиг | Прямой `memmove` по ленте указателей; сдвиг в середине помечает кэш токенов dirty (пересчёт один раз — при следующем поиске). |
| `hl.remove(x)` | Удаляет первое вхождение значения `x`. | **O(1)** по чистой карте, O(N) скан при dirty | Пока карта чиста, линейный перебор полностью обходится; затем блочный `memmove`. Нет значения — `ValueError`. |
| `hl.clear()` | Удаляет все элементы. | O(N) | DECREF-обход ленты, как у `list.clear()`; освобождает ленты и карту бакетов. |
| `hl.index(x)` | Возвращает индекс первого вхождения `x`. | **🚀 O(1) константа** | Извлекается напрямую из цепочки бакетов с проверкой равенства и ранним выходом. |
| `hl.count(x)` | Возвращает количество повторений `x`. | O(N) линейный | Паритет семантики `list` на скорости Си-обхода ленты (~2.4x быстрее `list`). |
| `hl.pop(i=-1)` | Удаляет и возвращает элемент по индексу `i`. | **O(1)** для хвоста, O(N−i) сдвиг | Блочный сдвиг указателей; хвостовые удаления не ломают кэш токенов. |
| `hl.sort()` | Сортирует на месте. Без `key`/`reverse` аргументов идёт в нативный C-путь Timsort. | O(N log N) | Нативный Timsort поверх ленты указателей. |
| `hl.reverse()` | Разворачивает список на месте. | **O(N)** | Перестановка указателей. |
| `hl.copy()` | Поверхностная копия (возвращает ровно тип `hashlist`). | **O(N)** | Блочное копирование ленты указателей; карта не копируется. |
| `hl[i]` / `hl[i] = x` / `del hl[i]` | Чтение, запись, удаление по индексу; срезы и отрицательные индексы полностью поддержаны. | O(1) / O(N−i) | Срезы возвращают настоящие `hashlist` и ищутся за O(1) после первого лукапа. |

## 💻 Быстрый старт

```python
from hashlist import hl, hashlist

# 1. Быстрое создание через фабричную функцию
my_list = hl(1, True, "яблоко", {"id": 66})

# 2. Семантика равенства ровно как у list (True == 1 — и ничего не ломается):
print(my_list.count("яблоко"))       # 1

# 3. Моментальный O(1) поиск и разрешение индексов — даже для НЕхэшируемого dict:
print("яблоко" in my_list)           # True (~0.1 мс на масштабе 20K!)
print(my_list.index({"id": 66}))     # 3  (порядок ключей dict не имеет значения)
```

## 🏗️ Архитектура на одном экране

- **Лента указателей** (`ob_item`) — единственный источник истины для паритета со `list`: порядок, индексы, срезы, итерация — обычный C.
- **Кэш токенов** (`flat_hashes`) — `8 байт/элемент` предвычисленных идентификаторов, синхронизируемых флагом `tokens_ready`. Мутации без сдвига позиций (append, вставка в хвост, `setitem`, pop с хвоста) трогают *один* слот; сдвигающие мутации (insert в середину, удаление с начала, remove, sort, reverse) лишь помечают карту dirty и полагаются на отложенную пересборку.
- **Карта бакетов** (`head`/`next`) — цепочечный хэш-индекс размером ~2N; строится только при первом настоящем поиске, когда токены ленты синхронны. Головы цепочек хранят минимальный индекс, поэтому первое же строго-равное совпадение и есть первое вхождение — ранний выход вместо прохода всей цепочки.
- **Нехэшируемые мутабельные типы** (list/dict/set) — токенизируются стабильным структурным маркером `Py_TYPE`; реальная идентичность элемента затем разрешается тем же rich-сравнением, что использует `list`, поэтому мутировавшие вложенные объекты остаются находимыми.
- **Исключения** пользовательских итераторов/генераторов в `hashlist(...)` и `extend()` распространяются без изменений (не проглатываются).
- **Поддержка GC:** `Py_TPFLAGS_HAVE_GC` + `tp_traverse`/`tp_clear` — hashlist может ссылаться сам на себя и всё равно соберётся сборщиком мусора.

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
