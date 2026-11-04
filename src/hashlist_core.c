#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <structmember.h>
#include <string.h>

#define EMPTY_BUCKET -1

typedef struct {
    PyObject_HEAD
    PyObject **ob_item;          // 1-й массив: плоская лента указателей на объекты Python
    Py_ssize_t *flat_hashes;     // 2-й массив: синхронная лента предвычисленных хэшей контента
    
    Py_ssize_t *head;            // Хэш-сетка: головы цепочек коллизий физических индексов
    Py_ssize_t *next;            // Массив связей цепочек (прямые индексы элементов)
    
    Py_ssize_t allocated;        // Выделенная физическая емкость под элементы
    Py_ssize_t size;             // Текущий логический размер списка
    Py_ssize_t table_capacity;   // Размер индексной сетки head (степень 2) или -2 если dirty
    int tokens_ready;            // 1 = flat_hashes синхронны с ob_item, пересчёт не нужен
} HashListObject;

typedef struct {
    PyObject_HEAD
    Py_ssize_t it_index;
    HashListObject *it_seq;      
} HashListIterObject;

static PyTypeObject HashListType; 
static PyTypeObject HashListIterType; 

// === КОНЕЦ ШАГА 1: МОНОЛИТНАЯ СТРУКТУРА ЦЕПОЧЕК ===







static inline int fast_rich_compare_strict(PyObject *s, PyObject *i) {
    if (s == i) return 1;
    return PyObject_RichCompareBool(s, i, Py_EQ) == 1;
}

static inline Py_ssize_t get_safe_token_c(PyObject *item) {
    if (item == NULL) return 0;
    // FAST-PATH: булевы и малые целые — их хэш в CPython совпадает со значением,
    // поэтому вызов PyObject_Hash заменяется прямым извлечением.
    if (PyBool_Check(item)) return item == Py_True ? 1 : 0;
    if (PyLong_CheckExact(item)) {
        int overflow = 0;
        long v = PyLong_AsLongAndOverflow(item, &overflow);
        // Граница заведомо внутри области, где hash(n) == n
        if (!overflow && v > -((long)1 << 59) && v < ((long)1 << 59)) return (Py_ssize_t)v;
    }
    if (PyList_Check(item) || PyDict_Check(item) || PySet_Check(item)) {
        return (Py_ssize_t)Py_TYPE(item); 
    }
    Py_ssize_t h = PyObject_Hash(item);
    if (h == -1) {
        PyErr_Clear();
        return (Py_ssize_t)Py_TYPE(item);
    }
    return h;
}

static void hashlistiter_dealloc(HashListIterObject *it) {
    Py_XDECREF(it->it_seq);
    Py_TYPE(it)->tp_free((PyObject *)it);
}

static PyObject *hashlistiter_next(HashListIterObject *it) {
    HashListObject *seq = it->it_seq;
    if (seq == NULL) return NULL;
    if (it->it_index < seq->size) {
        PyObject *item = seq->ob_item[it->it_index++];
        Py_INCREF(item);
        return item;
    }
    it->it_seq = NULL;
    Py_DECREF(seq);
    return NULL;
}

static PyObject *hashlist_iter(HashListObject *self) {
    HashListIterObject *it = PyObject_New(HashListIterObject, &HashListIterType);
    if (it == NULL) return NULL;
    it->it_index = 0;
    Py_INCREF(self);
    it->it_seq = self;
    return (PyObject *)it;
}

// === КОНЕЦ ШАГА 2: СИ-ИТЕРАТОР ===









static void hash_table_rebuild(HashListObject *self) {
    if (self->head != NULL) {
        free(self->head);
        self->head = NULL;
    }
    
    // ЛЕНИВЫЙ ДВОРНИК (Compaction): Сдвигаем живые элементы влево, полностью уничтожая NULL и освобождая память
    if (self->size > 0 && self->ob_item != NULL) {
        Py_ssize_t write_ptr = 0;
        for (Py_ssize_t i = 0; i < self->size; i++) {
            if (self->ob_item[i] != NULL) {
                if (write_ptr != i) {
                    self->ob_item[write_ptr] = self->ob_item[i];
                }
                write_ptr++;
            }
        }
        self->size = write_ptr; // Срезаем логический размер до честных живых элементов
    }

    if (self->size == 0) {
        self->table_capacity = 0;
        return;
    }

    // ЛЕНИВЫЕ ТОКЕНЫ: если мутации invalidated токены — пересчитываем здесь,
    // перед поисковой фазой (не при каждой мутации). Если токены ещё живы
    // (импорт без мутаций) — пропускаем пересчёт и сразу строим бакеты.
    if (!self->tokens_ready) {
        for (Py_ssize_t i = 0; i < self->size; i++) {
            self->flat_hashes[i] = get_safe_token_c(self->ob_item[i]);
        }
        self->tokens_ready = 1;
    }

    Py_ssize_t capacity = 1024;
    while (capacity <= self->size * 2) {
        capacity <<= 1;
    }
    self->head = (Py_ssize_t *)malloc(capacity * sizeof(Py_ssize_t));
    self->table_capacity = capacity;
    if (self->head == NULL) {
        self->table_capacity = 0; // Мягкая деградация: count уйдёт в линейный fallback
        return;
    }
    // EMPTY_BUCKET = -1 = байт-паттерн 0xFF: один memset вместо посимвольного цикла
    memset(self->head, 0xFF, (size_t)capacity * sizeof(Py_ssize_t));
    Py_ssize_t mask = capacity - 1;
    // Головы цепочек должны хранить МИНИМАЛЬНЫЙ индекс (семантика first-occurrence),
    // поэтому вставляем элементы справа налево: цепочка идёт по возрастанию индекса.
    for (Py_ssize_t i = self->size - 1; i >= 0; i--) {
        Py_ssize_t token = self->flat_hashes[i];
        size_t z = ((size_t)token) + 0x9e3779b97f4a7c15;
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9;
        Py_ssize_t bucket_idx = z & mask;
        self->next[i] = self->head[bucket_idx];
        self->head[bucket_idx] = i;
    }
}

// === КОНЕЦ ШАГА 3 ===












static Py_ssize_t hash_table_lookup(HashListObject *self, PyObject *item) {
    if (self->size == 0) return -1;
    if (self->table_capacity == -2 || self->head == NULL) {
        hash_table_rebuild(self);
    }
    if (self->table_capacity <= 0 || self->head == NULL) return -1;
    
    Py_ssize_t token = get_safe_token_c(item);
    size_t z = ((size_t)token) + 0x9e3779b97f4a7c15;
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9;
    Py_ssize_t mask = self->table_capacity - 1;
    
    // Цепочки идут по возрастанию индекса: первое же полное совпадение
    // (токен + строгое сравнение) — минимальный индекс. Ранний выход вместо
    // прохода всей цепочки ради min_idx.
    Py_ssize_t pos = self->head[z & mask];
    while (pos != EMPTY_BUCKET) {
        if (pos < self->size && self->flat_hashes[pos] == token &&
            fast_rich_compare_strict(self->ob_item[pos], item)) {
            return pos;
        }
        pos = self->next[pos];
    }
    return -1;
}

// === КОНЕЦ ШАГА 4: ПОИСК ПО ЦЕПОЧКАМ ===












static int hashlist_resize(HashListObject *self, Py_ssize_t newsize) {
    Py_ssize_t allocated = self->allocated;
    if (allocated >= newsize && newsize >= (allocated >> 1)) {
        self->size = newsize;
        return 0;
    }
    Py_ssize_t new_allocated = (newsize >> 3) + (newsize < 9 ? 3 : 6) + newsize;
    if (newsize == 0) new_allocated = 0;
    
    PyObject **items = (PyObject **)realloc(self->ob_item, sizeof(PyObject *) * new_allocated);
    Py_ssize_t *hashes = (Py_ssize_t *)realloc(self->flat_hashes, sizeof(Py_ssize_t) * new_allocated);
    Py_ssize_t *nxt = (Py_ssize_t *)realloc(self->next, sizeof(Py_ssize_t) * new_allocated);
    
    if ((items == NULL || hashes == NULL || nxt == NULL) && new_allocated > 0) {
        PyErr_NoMemory(); return -1;
    }
    
    self->ob_item = items;
    self->flat_hashes = hashes;
    self->next = nxt;
    self->size = newsize;
    self->allocated = new_allocated;
    return 0;
}

static void hashlist_dealloc(HashListObject *self) {
    PyObject_GC_UnTrack(self);
    if (self->ob_item != NULL) {
        for (Py_ssize_t i = 0; i < self->size; i++) Py_XDECREF(self->ob_item[i]);
        free(self->ob_item);
    }
    if (self->flat_hashes != NULL) free(self->flat_hashes);
    if (self->next != NULL) free(self->next);
    if (self->head != NULL) free(self->head);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int hashlist_traverse(HashListObject *self, visitproc visit, void *arg) {
    if (self->ob_item != NULL) {
        for (Py_ssize_t i = 0; i < self->size; i++) {
            Py_VISIT(self->ob_item[i]);
        }
    }
    return 0;
}

// GC-очистка: разрывает ссылочные циклы (например, список, содержащий сам себя)
static int hashlist_gc_clear(HashListObject *self) {
    if (self->ob_item != NULL) {
        for (Py_ssize_t i = 0; i < self->size; i++) Py_XDECREF(self->ob_item[i]);
        free(self->ob_item);
        self->ob_item = NULL;
    }
    if (self->flat_hashes != NULL) { free(self->flat_hashes); self->flat_hashes = NULL; }
    if (self->next != NULL) { free(self->next); self->next = NULL; }
    if (self->head != NULL) { free(self->head); self->head = NULL; }
    self->size = 0;
    self->allocated = 0;
    self->table_capacity = -2;
    self->tokens_ready = 0;
    return 0;
}

// === КОНЕЦ ШАГА 5 ===









static int hashlist_init(HashListObject *self, PyObject *args, PyObject *kwds) {
    PyObject *iterable = NULL;
    if (!PyArg_ParseTuple(args, "|O", &iterable)) return -1;
    
    self->size = 0; 
    self->allocated = 0; 
    self->ob_item = NULL; 
    self->flat_hashes = NULL; 
    self->head = NULL;
    self->next = NULL;
    self->table_capacity = -2; 
    self->tokens_ready = 0; 
    
    if (iterable != NULL && iterable != Py_None) {
        // Нативная клона: hashlist(другой hashlist) копирует ленты указателей и
        // готовые токены напрямую — без итерации, INCREF-цикла и повторного хэширования
        if (PyObject_TypeCheck(iterable, &HashListType)) {
            HashListObject *src = (HashListObject *)iterable;
            self->size = src->size;
            self->allocated = src->size;
            if (src->size > 0) {
                self->ob_item = (PyObject **)malloc(sizeof(PyObject *) * self->allocated);
                self->flat_hashes = (Py_ssize_t *)malloc(sizeof(Py_ssize_t) * self->allocated);
                self->next = (Py_ssize_t *)malloc(sizeof(Py_ssize_t) * self->allocated);
                if (!self->ob_item || !self->flat_hashes || !self->next) {
                    self->size = 0; self->allocated = 0;
                    if (self->ob_item) { free(self->ob_item); self->ob_item = NULL; }
                    if (self->flat_hashes) { free(self->flat_hashes); self->flat_hashes = NULL; }
                    if (self->next) { free(self->next); self->next = NULL; }
                    PyErr_NoMemory(); return -1;
                }
                memcpy(self->ob_item, src->ob_item, sizeof(PyObject *) * self->size);
                self->tokens_ready = src->tokens_ready;
                if (src->tokens_ready) {
                    memcpy(self->flat_hashes, src->flat_hashes, sizeof(Py_ssize_t) * self->size);
                }
                for (Py_ssize_t i = 0; i < self->size; i++) Py_INCREF(self->ob_item[i]);
            } else {
                self->tokens_ready = 1;
            }
            self->table_capacity = -2;
            return 0;
        }

        // FAST-PATH: готовые list/tuple копируются блоком указателей без посимвольной
        // итерации PyIter_Next — скорость на уровне нативного list(list).
        // Токены импорта считаем eagerly: первый поиск обязан остаться O(1).
        int is_list = PyList_CheckExact(iterable);
        int is_tuple = PyTuple_CheckExact(iterable);
        if (is_list || is_tuple) {
            Py_ssize_t n = is_list ? PyList_GET_SIZE(iterable) : PyTuple_GET_SIZE(iterable);
            if (n > 0) {
                if (hashlist_resize(self, n) < 0) return -1;
                for (Py_ssize_t i = 0; i < n; i++) {
                    PyObject *v = is_list ? PyList_GET_ITEM(iterable, i) : PyTuple_GET_ITEM(iterable, i);
                    Py_INCREF(v);
                    self->ob_item[i] = v;
                    self->flat_hashes[i] = get_safe_token_c(v);
                }
                self->tokens_ready = 1;
            } else {
                self->tokens_ready = 1; // Пустой импорт: пересчитывать нечего
            }
            return 0;
        }

        // Узнаем размер входящей коллекции и выделяем память под всю пачку разом
        Py_ssize_t hint = PyObject_Size(iterable);
        if (hint < 0) PyErr_Clear();
        else if (hint > 0) {
            if (hashlist_resize(self, hint) < 0) return -1;
            self->size = 0; // Сбрасываем счетчик для наполнения
        }

        PyObject *iterator = PyObject_GetIter(iterable);
        if (iterator == NULL) return -1;
        PyObject *item;
        while ((item = PyIter_Next(iterator))) {
            Py_ssize_t cur_idx = self->size;
            if (hashlist_resize(self, cur_idx + 1) < 0) {
                Py_DECREF(item); Py_DECREF(iterator); return -1;
            }
            self->ob_item[cur_idx] = item; 
            self->flat_hashes[cur_idx] = get_safe_token_c(item); // Импорт: токен eagerly
        }
        Py_DECREF(iterator);
        if (PyErr_Occurred()) return -1;
        self->tokens_ready = 1;
    }
    return 0;
}

// === КОНЕЦ ШАГА 6 ===









static PyObject *hashlist_append(HashListObject *self, PyObject *item) {
    // Инлайн fast-path resize: типичный append не должен трогать вызов функции
    Py_ssize_t newsize = self->size + 1;
    if (self->allocated >= newsize && newsize >= (self->allocated >> 1)) {
        self->size = newsize;
    } else if (hashlist_resize(self, newsize) < 0) {
        return NULL;
    }
    
    // Appending не сдвигает позиции: при живых токенах милостиво доливаем
    // только новый слот (десятки нс) — дешевле, чем пересчёт всех на rebuild.
    Py_ssize_t cur_idx = self->size - 1;
    Py_INCREF(item);
    self->ob_item[cur_idx] = item;
    if (self->tokens_ready) {
        self->flat_hashes[cur_idx] = get_safe_token_c(item);
    }
    
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

static PyObject *hashlist_extend(HashListObject *self, PyObject *iterable) {
    // FAST-PATH: готовые list/tuple — один resize, один блок INCREF, без итератора.
    // Токены считаем по-элементно только при живой ленте; иначе дешевле отдать
    // единый пересчёт в rebuild.
    int is_list = PyList_CheckExact(iterable);
    int is_tuple = PyTuple_CheckExact(iterable);
    if (is_list || is_tuple) {
        Py_ssize_t n = is_list ? PyList_GET_SIZE(iterable) : PyTuple_GET_SIZE(iterable);
        if (n > 0) {
            Py_ssize_t old_size = self->size;
            if (hashlist_resize(self, old_size + n) < 0) return NULL;
            int ready = self->tokens_ready;
            for (Py_ssize_t i = 0; i < n; i++) {
                PyObject *v = is_list ? PyList_GET_ITEM(iterable, i) : PyTuple_GET_ITEM(iterable, i);
                Py_INCREF(v);
                self->ob_item[old_size + i] = v;
                if (ready) self->flat_hashes[old_size + i] = get_safe_token_c(v);
            }
        }
        self->table_capacity = -2;
        Py_RETURN_NONE;
    }

    PyObject *iterator = PyObject_GetIter(iterable);
    if (iterator == NULL) return NULL;
    
    // ВЕКТOРИЗАЦИЯ: Резервируем память под всю прилетевшую пачку элементов за один системный вызов
    Py_ssize_t hint = PyObject_Size(iterable);
    if (hint < 0) PyErr_Clear();
    else if (hint > 0) {
        Py_ssize_t old_size = self->size;
        if (hashlist_resize(self, old_size + hint) < 0) { Py_DECREF(iterator); return NULL; }
        self->size = old_size; 
    }
    
    PyObject *item;
    while ((item = PyIter_Next(iterator))) {
        Py_ssize_t cur_idx = self->size;
        if (hashlist_resize(self, cur_idx + 1) < 0) { Py_DECREF(item); Py_DECREF(iterator); return NULL; }
        self->ob_item[cur_idx] = item;
        if (self->tokens_ready) self->flat_hashes[cur_idx] = get_safe_token_c(item);
    }
    Py_DECREF(iterator);
    if (PyErr_Occurred()) return NULL;
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

// === КОНЕЦ ШАГА 7 ===










static PyObject *hashlist_copy(HashListObject *self, PyObject *Py_UNUSED(ignored)) {
    // Инстанцируем свой фактический тип (поддержка Python-подкласса hashlist)
    HashListObject *copy = (HashListObject *)PyType_GenericNew((PyTypeObject *)Py_TYPE(self), NULL, NULL);
    if (copy == NULL) return NULL;
    
    copy->size = self->size;
    copy->allocated = self->size; 
    copy->table_capacity = -2; // Копия ленива: сетка дешёвая, пересоберётся при первом поиске
    copy->tokens_ready = 0; 
    
    if (self->size > 0) {
        copy->ob_item = (PyObject **)malloc(sizeof(PyObject *) * copy->allocated);
        copy->flat_hashes = (Py_ssize_t *)malloc(sizeof(Py_ssize_t) * copy->allocated);
        copy->next = (Py_ssize_t *)malloc(sizeof(Py_ssize_t) * copy->allocated);
        
        if (!copy->ob_item || !copy->flat_hashes || !copy->next) {
            Py_DECREF(copy); return PyErr_NoMemory();
        }
        
        memcpy(copy->ob_item, self->ob_item, sizeof(PyObject *) * self->size);
        // Готовые токены источника транслируются — копия ищется без пересчёта хэшей
        if (self->tokens_ready) {
            memcpy(copy->flat_hashes, self->flat_hashes, sizeof(Py_ssize_t) * self->size);
            copy->tokens_ready = 1;
        }
        
        for (Py_ssize_t i = 0; i < self->size; i++) {
            Py_INCREF(copy->ob_item[i]);
        }
    } else {
        copy->ob_item = NULL;
        copy->flat_hashes = NULL;
        copy->next = NULL;
    }
    
    return (PyObject *)copy;
}

// === КОНЕЦ ШАГА 8: СКОРОСТНОЙ COPY ===








static PyObject *hashlist_insert(HashListObject *self, PyObject *const *args, Py_ssize_t nargs) {
    if (nargs != 2) {
        PyErr_Format(PyExc_TypeError, "insert expected 2 arguments, got %zd", nargs);
        return NULL;
    }
    Py_ssize_t idx = PyNumber_AsSsize_t(args[0], PyExc_IndexError);
    if (idx == -1 && PyErr_Occurred()) return NULL;
    PyObject *item = args[1];
    if (idx < 0) { idx += self->size; if (idx < 0) idx = 0; }
    if (idx > self->size) idx = self->size;
    
    if (hashlist_resize(self, self->size + 1) < 0) return NULL;
    if (idx < self->size - 1) {
        memmove(&self->ob_item[idx + 1], &self->ob_item[idx], sizeof(PyObject *) * (self->size - 1 - idx));
        self->tokens_ready = 0; // Позиции сдвинуты — пересчёт токенов на rebuild
    } else if (self->tokens_ready) {
        self->flat_hashes[idx] = get_safe_token_c(item); // Вставка в конец: доливаем один токен
    }
    Py_INCREF(item);
    self->ob_item[idx] = item;
    
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

static inline void hash_table_delete_slot_mapping(HashListObject *self, Py_ssize_t idx) {
    if (idx < self->size - 1) {
        memmove(&self->ob_item[idx], &self->ob_item[idx + 1], sizeof(PyObject *) * (self->size - 1 - idx));
        // Сдвиг позиций: токены сместились относительно элементов — пересчёт при первом поиске
        self->tokens_ready = 0;
    }
    self->size--;
}

static PyObject *hashlist_remove(HashListObject *self, PyObject *item) {
    Py_ssize_t idx = -1;
    
    // Таблица чистая: минимальный индекс достаём за O(1) из голов цепочек.
    if (self->table_capacity > 0 && self->head != NULL) {
        idx = hash_table_lookup(self, item);
    } else {
        // Таблица dirty (ленивые токены не вычислены): ловим линейным Си-перебором
        // с нулевого индекса — ровно как list.remove, без тяжёлого rebuild.
        for (Py_ssize_t i = 0; i < self->size; i++) {
            if (fast_rich_compare_strict(self->ob_item[i], item)) { idx = i; break; }
        }
    }
    
    if (idx == -1) { PyErr_SetString(PyExc_ValueError, "hashlist.remove(x): x not in list"); return NULL; }
    
    Py_DECREF(self->ob_item[idx]);
    hash_table_delete_slot_mapping(self, idx);
    
    self->table_capacity = -2; // Удаление сдвигает индексы: сетка lazily пересоберётся
    hashlist_resize(self, self->size);
    Py_RETURN_NONE;
}

static PyObject *hashlist_pop(HashListObject *self, PyObject *const *args, Py_ssize_t nargs) {
    Py_ssize_t idx = -1;
    if (nargs > 1) {
        PyErr_Format(PyExc_TypeError, "pop expected at most 1 argument, got %zd", nargs);
        return NULL;
    }
    if (nargs == 1) {
        idx = PyNumber_AsSsize_t(args[0], PyExc_IndexError);
        if (idx == -1 && PyErr_Occurred()) return NULL;
    }
    if (self->size == 0) { PyErr_SetString(PyExc_IndexError, "pop from empty hashlist"); return NULL; }
    if (idx < 0) idx += self->size;
    if (idx < 0 || idx >= self->size) { PyErr_SetString(PyExc_IndexError, "pop index out of range"); return NULL; }
    
    PyObject *item = self->ob_item[idx];
    hash_table_delete_slot_mapping(self, idx);
    
    self->table_capacity = -2; 
    hashlist_resize(self, self->size);
    return item; 
}

// === КОНЕЦ ШАГА 9 ===
















static PyObject *hashlist_delitem_c(HashListObject *self, PyObject *const *args, Py_ssize_t nargs) {
    if (nargs != 1) {
        PyErr_Format(PyExc_TypeError, "delitem_c expected 1 argument, got %zd", nargs);
        return NULL;
    }
    Py_ssize_t idx = PyNumber_AsSsize_t(args[0], PyExc_IndexError);
    if (idx == -1 && PyErr_Occurred()) return NULL;
    if (idx < 0) idx += self->size;
    if (idx < 0 || idx >= self->size) { PyErr_SetString(PyExc_IndexError, "hashlist deletion index out of range"); return NULL; }
    Py_DECREF(self->ob_item[idx]);
    hash_table_delete_slot_mapping(self, idx);
    self->table_capacity = -2; 
    hashlist_resize(self, self->size);
    Py_RETURN_NONE;
}

static PyObject *hashlist_setitem_c(HashListObject *self, PyObject *const *args, Py_ssize_t nargs) {
    if (nargs != 2) {
        PyErr_Format(PyExc_TypeError, "setitem_c expected 2 arguments, got %zd", nargs);
        return NULL;
    }
    Py_ssize_t idx = PyNumber_AsSsize_t(args[0], PyExc_IndexError);
    if (idx == -1 && PyErr_Occurred()) return NULL;
    PyObject *value = args[1];
    if (idx < 0) idx += self->size;
    if (idx < 0 || idx >= self->size) { PyErr_SetString(PyExc_IndexError, "hashlist assignment index out of range"); return NULL; }
    Py_DECREF(self->ob_item[idx]); Py_INCREF(value);
    self->ob_item[idx] = value;
    if (self->tokens_ready) {
        self->flat_hashes[idx] = get_safe_token_c(value); // Замена не сдвигает позиции
    }
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

static PyObject *hashlist_clear(HashListObject *self, PyObject *Py_UNUSED(ignored)) {
    for (Py_ssize_t i = 0; i < self->size; i++) Py_XDECREF(self->ob_item[i]);
    hashlist_resize(self, 0);
    if (self->head != NULL) { free(self->head); self->head = NULL; }
    self->table_capacity = -2; 
    self->tokens_ready = 0; 
    Py_RETURN_NONE;
}

static PyObject *hashlist_index_of(HashListObject *self, PyObject *item) {
    Py_ssize_t idx = hash_table_lookup(self, item);
    if (idx == -1) { PyErr_SetString(PyExc_ValueError, "x not in hashlist"); return NULL; }
    return PyLong_FromSsize_t(idx);
}

static PyObject *hashlist_count(HashListObject *self, PyObject *item) {
    Py_ssize_t cnt = 0;
    // Странная семантика list.count: подсчёт по равенству (rich compare),
    // линейный обход ленты — кэш-дружелюбный и без налога на сетку.
    for (Py_ssize_t i = 0; i < self->size; i++) {
        if (fast_rich_compare_strict(self->ob_item[i], item)) cnt++;
    }
    return PyLong_FromSsize_t(cnt);
}

static PyObject *hashlist_reverse(HashListObject *self, PyObject *Py_UNUSED(ignored)) {
    // Ленивые хэши: свопим только ленту указателей, без второй ленты токенов.
    Py_ssize_t i = 0, j = self->size - 1;
    while (i < j) {
        PyObject *tmp = self->ob_item[i]; self->ob_item[i] = self->ob_item[j]; self->ob_item[j] = tmp;
        i++; j--;
    }
    self->table_capacity = -2; 
    self->tokens_ready = 0; 
    Py_RETURN_NONE;
}

static int hashlist_sq_contains(HashListObject *self, PyObject *item) {
    // Слот протокола `in`: возвращает int (objobjproc), а не PyObject* —
    // каст указателя сюда делал бы `in` всегда TRUE.
    return hash_table_lookup(self, item) != -1;
}

static PyObject *hashlist_contains(HashListObject *self, PyObject *item) {
    if (hash_table_lookup(self, item) != -1) { Py_RETURN_TRUE; } else { Py_RETURN_FALSE; }
}

// === КОНЕЦ ШАГА 10: СЛУЖЕБНЫЕ МЕТОДЫ ===









static PyObject *hashlist_getitem(HashListObject *self, Py_ssize_t index);

static PyObject *hashlist_subscript(HashListObject *self, PyObject *item) {
    if (PyIndex_Check(item)) {
        Py_ssize_t i = PyNumber_AsSsize_t(item, PyExc_IndexError);
        if (i == -1 && PyErr_Occurred()) return NULL;
        return hashlist_getitem(self, i);
    }
    if (PySlice_Check(item)) {
        Py_ssize_t start, stop, step, slicelength;
        if (PySlice_GetIndicesEx(item, self->size, &start, &stop, &step, &slicelength) < 0) return NULL;
        HashListObject *result = (HashListObject *)PyType_GenericNew((PyTypeObject *)Py_TYPE(self), NULL, NULL);
        if (result == NULL) return NULL;
        result->size = 0; result->allocated = 0; result->ob_item = NULL; result->flat_hashes = NULL;
        result->head = NULL; result->next = NULL; result->table_capacity = -2; result->tokens_ready = 0;
        if (slicelength > 0) {
            if (hashlist_resize(result, slicelength) < 0) { Py_DECREF(result); return NULL; }
            Py_ssize_t cur = start;
            for (Py_ssize_t i = 0; i < slicelength; i++) {
                PyObject *obj = self->ob_item[cur]; Py_INCREF(obj);
                result->ob_item[i] = obj;
                cur += step;
            }
        }
        return (PyObject *)result;
    }
    PyErr_SetString(PyExc_TypeError, "hashlist indices must be integers or slices");
    return NULL;
}

static Py_ssize_t hashlist_len(HashListObject *self) { return self->size; }
static PyObject *hashlist_getitem(HashListObject *self, Py_ssize_t index) {
    if (index < 0) index += self->size;
    if (index < 0 || index >= self->size) { PyErr_SetString(PyExc_IndexError, "hashlist index out of range"); return NULL; }
    Py_INCREF(self->ob_item[index]); return self->ob_item[index];
}

// === КОНЕЦ ШАГА 11 ===

static PyObject *hashlist_sort(HashListObject *self, PyObject *Py_UNUSED(ignored)) {
    if (self->size == 0) Py_RETURN_NONE;
    
    // Нативная сортировка: прокидываем указатели во временный встроенный list,
    // прогоняем Timsort CPython и забираем раскладку обратно. Владение ссылками
    // сохраняется: temp инкрементирует (+1) и при DECREF отдаёт свою долю.
    PyObject *temp = PyList_New(self->size);
    if (temp == NULL) return NULL;
    for (Py_ssize_t i = 0; i < self->size; i++) {
        PyObject *v = self->ob_item[i];
        Py_INCREF(v);
        PyList_SET_ITEM(temp, i, v);
    }
    if (PyList_Sort(temp) < 0) { Py_DECREF(temp); return NULL; }
    for (Py_ssize_t i = 0; i < self->size; i++) {
        // Перестановка указателей в тех же слотах: мультиобъектность совпадает,
        // владение ссылками не меняется.
        self->ob_item[i] = PyList_GET_ITEM(temp, i);
    }
    Py_DECREF(temp);
    
    self->table_capacity = -2; 
    self->tokens_ready = 0; 
    Py_RETURN_NONE;
}







static PyMethodDef hashlist_methods[] = {
    {"append", (PyCFunction)hashlist_append, METH_O, ""},
    {"extend", (PyCFunction)hashlist_extend, METH_O, ""},
    {"insert", (PyCFunction)(void(*)(void))hashlist_insert, METH_FASTCALL, ""},
    {"remove", (PyCFunction)hashlist_remove, METH_O, ""},
    {"pop", (PyCFunction)(void(*)(void))hashlist_pop, METH_FASTCALL, ""},
    {"clear", (PyCFunction)hashlist_clear, METH_NOARGS, ""},
    {"index_of", (PyCFunction)hashlist_index_of, METH_O, ""},
    {"count", (PyCFunction)hashlist_count, METH_O, ""},
    {"sort", (PyCFunction)hashlist_sort, METH_NOARGS, ""},
    {"reverse", (PyCFunction)hashlist_reverse, METH_NOARGS, ""},
    {"contains", (PyCFunction)hashlist_contains, METH_O, ""},
    {"copy", (PyCFunction)hashlist_copy, METH_NOARGS, ""},
    {"delitem_c", (PyCFunction)(void(*)(void))hashlist_delitem_c, METH_FASTCALL, ""},
    {"setitem_c", (PyCFunction)(void(*)(void))hashlist_setitem_c, METH_FASTCALL, ""},
    {NULL}
};

static PySequenceMethods hashlist_as_sequence = {
    (lenfunc)hashlist_len, 0, 0, (ssizeargfunc)hashlist_getitem, 0, 0, 0, (objobjproc)hashlist_sq_contains,
};

static PyMappingMethods hashlist_as_mapping = {
    (lenfunc)hashlist_len, (binaryfunc)hashlist_subscript, 0,
};

static PyTypeObject HashListType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "hashlist_backend.HashListCpp",
    .tp_basicsize = sizeof(HashListObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | Py_TPFLAGS_HAVE_GC,
    .tp_dealloc = (destructor)hashlist_dealloc,
    .tp_traverse = (traverseproc)hashlist_traverse,
    .tp_clear = (inquiry)hashlist_gc_clear,
    .tp_init = (initproc)hashlist_init,
    .tp_methods = hashlist_methods,
    .tp_as_sequence = &hashlist_as_sequence,
    .tp_as_mapping = &hashlist_as_mapping,
    .tp_iter = (getiterfunc)hashlist_iter,
    .tp_new = PyType_GenericNew,
};

static PyTypeObject HashListIterType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "hashlist_iterator",
    .tp_basicsize = sizeof(HashListIterObject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_dealloc = (destructor)hashlistiter_dealloc,
    .tp_iter = PyObject_SelfIter,
    .tp_iternext = (iternextfunc)hashlistiter_next,
};

static PyModuleDef hashlist_backend_module = { PyModuleDef_HEAD_INIT, "hashlist_backend", NULL, -1 };
PyMODINIT_FUNC PyInit_hashlist_backend(void) {
    if (PyType_Ready(&HashListType) < 0) return NULL;
    if (PyType_Ready(&HashListIterType) < 0) return NULL;
    PyObject *m = PyModule_Create(&hashlist_backend_module);
    if (m == NULL) return NULL;
    Py_INCREF(&HashListType);
    PyModule_AddObject(m, "HashListCpp", (PyObject *)&HashListType);
    return m;
}

// === КОНЕЦ ШАГА 12 ===





