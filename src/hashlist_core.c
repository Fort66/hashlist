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
                    self->flat_hashes[write_ptr] = self->flat_hashes[i];
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

    Py_ssize_t capacity = 1024;
    while (capacity <= self->size * 2) {
        capacity <<= 1;
    }
    self->head = (Py_ssize_t *)malloc(capacity * sizeof(Py_ssize_t));
    self->table_capacity = capacity;
    for (Py_ssize_t i = 0; i < capacity; i++) {
        self->head[i] = EMPTY_BUCKET;
    }
    Py_ssize_t mask = capacity - 1;
    for (Py_ssize_t i = 0; i < self->size; i++) {
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
    Py_ssize_t pos = self->head[z & mask];
    
    Py_ssize_t min_idx = -1;
    while (pos != EMPTY_BUCKET) {
        if (pos < self->size && self->flat_hashes[pos] == token) {
            if (fast_rich_compare_strict(self->ob_item[pos], item)) {
                if (min_idx == -1 || pos < min_idx) {
                    min_idx = pos;
                }
            }
        }
        pos = self->next[pos];
    }
    return min_idx;
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
    if (self->ob_item != NULL) {
        for (Py_ssize_t i = 0; i < self->size; i++) Py_XDECREF(self->ob_item[i]);
        free(self->ob_item);
    }
    if (self->flat_hashes != NULL) free(self->flat_hashes);
    if (self->next != NULL) free(self->next);
    if (self->head != NULL) free(self->head);
    Py_TYPE(self)->tp_free((PyObject *)self);
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
    
    if (iterable != NULL && iterable != Py_None) {
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
            self->flat_hashes[cur_idx] = get_safe_token_c(item);
        }
        Py_DECREF(iterator);
        if (PyErr_Occurred()) return -1;
    }
    return 0;
}

// === КОНЕЦ ШАГА 6 ===









static PyObject *hashlist_append(HashListObject *self, PyObject *item) {
    if (hashlist_resize(self, self->size + 1) < 0) return NULL;
    
    Py_ssize_t cur_idx = self->size - 1;
    Py_INCREF(item);
    self->ob_item[cur_idx] = item;
    self->flat_hashes[cur_idx] = get_safe_token_c(item);
    
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

static PyObject *hashlist_extend(HashListObject *self, PyObject *iterable) {
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
        self->flat_hashes[cur_idx] = get_safe_token_c(item);
    }
    Py_DECREF(iterator);
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

// === КОНЕЦ ШАГА 7 ===










static PyObject *hashlist_copy(HashListObject *self, PyObject *Py_UNUSED(ignored)) {
    HashListObject *copy = (HashListObject *)PyType_GenericNew(&HashListType, NULL, NULL);
    if (copy == NULL) return NULL;
    
    copy->size = self->size;
    copy->allocated = self->size; 
    copy->table_capacity = self->table_capacity;
    
    if (self->size > 0) {
        copy->ob_item = (PyObject **)malloc(sizeof(PyObject *) * copy->allocated);
        copy->flat_hashes = (Py_ssize_t *)malloc(sizeof(Py_ssize_t) * copy->allocated);
        copy->next = (Py_ssize_t *)malloc(sizeof(Py_ssize_t) * copy->allocated);
        
        if (!copy->ob_item || !copy->flat_hashes || !copy->next) {
            Py_DECREF(copy); return PyErr_NoMemory();
        }
        
        memcpy(copy->ob_item, self->ob_item, sizeof(PyObject *) * self->size);
        memcpy(copy->flat_hashes, self->flat_hashes, sizeof(Py_ssize_t) * self->size);
        memcpy(copy->next, self->next, sizeof(Py_ssize_t) * self->size);
        
        for (Py_ssize_t i = 0; i < self->size; i++) {
            Py_INCREF(copy->ob_item[i]);
        }
    } else {
        copy->ob_item = NULL;
        copy->flat_hashes = NULL;
        copy->next = NULL;
    }
    
    if (self->table_capacity > 0 && self->head != NULL) {
        copy->head = (Py_ssize_t *)malloc(sizeof(Py_ssize_t) * self->table_capacity);
        if (!copy->head) { Py_DECREF(copy); return PyErr_NoMemory(); }
        memcpy(copy->head, self->head, sizeof(Py_ssize_t) * self->table_capacity);
    } else {
        copy->head = NULL;
    }
    
    return (PyObject *)copy;
}

// === КОНЕЦ ШАГА 8: СКОРОСТНОЙ COPY ===








static PyObject *hashlist_insert(HashListObject *self, PyObject *args) {
    Py_ssize_t idx; PyObject *item;
    if (!PyArg_ParseTuple(args, "nO", &idx, &item)) return NULL;
    if (idx < 0) { idx += self->size; if (idx < 0) idx = 0; }
    if (idx > self->size) idx = self->size;
    
    if (hashlist_resize(self, self->size + 1) < 0) return NULL;
    if (idx < self->size - 1) {
        memmove(&self->ob_item[idx + 1], &self->ob_item[idx], sizeof(PyObject *) * (self->size - 1 - idx));
        memmove(&self->flat_hashes[idx + 1], &self->flat_hashes[idx], sizeof(Py_ssize_t) * (self->size - 1 - idx));
    }
    Py_INCREF(item);
    self->ob_item[idx] = item;
    self->flat_hashes[idx] = get_safe_token_c(item);
    
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

static inline void hash_table_delete_slot_mapping(HashListObject *self, Py_ssize_t idx) {
    if (idx < self->size - 1) {
        memmove(&self->ob_item[idx], &self->ob_item[idx + 1], sizeof(PyObject *) * (self->size - 1 - idx));
        memmove(&self->flat_hashes[idx], &self->flat_hashes[idx + 1], sizeof(Py_ssize_t) * (self->size - 1 - idx));
    }
    self->size--;
}

static PyObject *hashlist_remove(HashListObject *self, PyObject *item) {
    Py_ssize_t idx = -1;
    
    // ИСПРАВЛЕНO: Если таблица dirty, ищем элемент быстрым линейным Си-перебором БЕЗ вызова тяжелого rebuild!
    if (self->table_capacity == -2 || self->head == NULL) {
        Py_ssize_t token = get_safe_token_c(item);
        for (Py_ssize_t i = 0; i < self->size; i++) {
            if (self->flat_hashes[i] == token && fast_rich_compare_strict(self->ob_item[i], item)) {
                idx = i;
                break;
            }
        }
    } else {
        // Если таблица чистая — забираем индекс из хэш-сетки за O(1)
        idx = hash_table_lookup(self, item);
    }
    
    if (idx == -1) { PyErr_SetString(PyExc_ValueError, "hashlist.remove(x): x not in list"); return NULL; }
    
    Py_DECREF(self->ob_item[idx]);
    hash_table_delete_slot_mapping(self, idx);
    
    self->table_capacity = -2; // Оставляем статус dirty: никакого rebuild при удалении пачкой!
    hashlist_resize(self, self->size);
    Py_RETURN_NONE;
}

static PyObject *hashlist_pop(HashListObject *self, PyObject *args) {
    Py_ssize_t idx = -1;
    if (!PyArg_ParseTuple(args, "|n", &idx)) return NULL;
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
















static PyObject *hashlist_delitem_c(HashListObject *self, PyObject *args) {
    Py_ssize_t idx;
    if (!PyArg_ParseTuple(args, "n", &idx)) return NULL;
    if (idx < 0) idx += self->size;
    if (idx < 0 || idx >= self->size) { PyErr_SetString(PyExc_IndexError, "hashlist deletion index out of range"); return NULL; }
    Py_DECREF(self->ob_item[idx]);
    hash_table_delete_slot_mapping(self, idx);
    self->table_capacity = -2; 
    hashlist_resize(self, self->size);
    Py_RETURN_NONE;
}

static PyObject *hashlist_setitem_c(HashListObject *self, PyObject *args) {
    Py_ssize_t idx; PyObject *value;
    if (!PyArg_ParseTuple(args, "nO", &idx, &value)) return NULL;
    if (idx < 0) idx += self->size;
    if (idx < 0 || idx >= self->size) { PyErr_SetString(PyExc_IndexError, "hashlist assignment index out of range"); return NULL; }
    Py_DECREF(self->ob_item[idx]); Py_INCREF(value);
    self->ob_item[idx] = value;
    self->flat_hashes[idx] = get_safe_token_c(value);
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

static PyObject *hashlist_clear(HashListObject *self, PyObject *Py_UNUSED(ignored)) {
    for (Py_ssize_t i = 0; i < self->size; i++) Py_XDECREF(self->ob_item[i]);
    hashlist_resize(self, 0);
    if (self->head != NULL) { free(self->head); self->head = NULL; }
    self->table_capacity = -2; 
    Py_RETURN_NONE;
}

static PyObject *hashlist_index_of(HashListObject *self, PyObject *item) {
    Py_ssize_t idx = hash_table_lookup(self, item);
    if (idx == -1) { PyErr_SetString(PyExc_ValueError, "x not in hashlist"); return NULL; }
    return PyLong_FromSsize_t(idx);
}

static PyObject *hashlist_count(HashListObject *self, PyObject *item) {
    Py_ssize_t cnt = 0;
    for (Py_ssize_t i = 0; i < self->size; i++) {
        if (fast_rich_compare_strict(self->ob_item[i], item)) cnt++;
    }
    return PyLong_FromSsize_t(cnt);
}

static PyObject *hashlist_reverse(HashListObject *self, PyObject *Py_UNUSED(ignored)) {
    Py_ssize_t i = 0, j = self->size - 1;
    while (i < j) {
        PyObject *tmp = self->ob_item[i]; self->ob_item[i] = self->ob_item[j]; self->ob_item[j] = tmp;
        Py_ssize_t h_tmp = self->flat_hashes[i]; self->flat_hashes[i] = self->flat_hashes[j]; self->flat_hashes[j] = h_tmp;
        i++; j--;
    }
    self->table_capacity = -2; 
    Py_RETURN_NONE;
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
        HashListObject *result = (HashListObject *)PyType_GenericNew(&HashListType, NULL, NULL);
        if (result == NULL) return NULL;
        result->size = 0; result->allocated = 0; result->ob_item = NULL; result->flat_hashes = NULL;
        result->head = NULL; result->next = NULL; result->table_capacity = -2;
        if (slicelength > 0) {
            if (hashlist_resize(result, slicelength) < 0) { Py_DECREF(result); return NULL; }
            Py_ssize_t cur = start;
            for (Py_ssize_t i = 0; i < slicelength; i++) {
                PyObject *obj = self->ob_item[cur]; Py_INCREF(obj);
                result->ob_item[i] = obj;
                result->flat_hashes[i] = self->flat_hashes[cur];
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







static PyMethodDef hashlist_methods[] = {
    {"append", (PyCFunction)hashlist_append, METH_O, ""},
    {"extend", (PyCFunction)hashlist_extend, METH_O, ""},
    {"insert", (PyCFunction)hashlist_insert, METH_VARARGS, ""},
    {"remove", (PyCFunction)hashlist_remove, METH_O, ""},
    {"pop", (PyCFunction)hashlist_pop, METH_VARARGS, ""},
    {"clear", (PyCFunction)hashlist_clear, METH_NOARGS, ""},
    {"index_of", (PyCFunction)hashlist_index_of, METH_O, ""},
    {"count", (PyCFunction)hashlist_count, METH_O, ""},
    {"reverse", (PyCFunction)hashlist_reverse, METH_NOARGS, ""},
    {"contains", (PyCFunction)hashlist_contains, METH_O, ""},
    {"copy", (PyCFunction)hashlist_copy, METH_NOARGS, ""},
    {"delitem_c", (PyCFunction)hashlist_delitem_c, METH_VARARGS, ""},
    {"setitem_c", (PyCFunction)hashlist_setitem_c, METH_VARARGS, ""},
    {NULL}
};

static PySequenceMethods hashlist_as_sequence = {
    (lenfunc)hashlist_len, 0, 0, (ssizeargfunc)hashlist_getitem, 0, 0, 0, (objobjproc)hashlist_contains,
};

static PyMappingMethods hashlist_as_mapping = {
    (lenfunc)hashlist_len, (binaryfunc)hashlist_subscript, 0,
};

static PyTypeObject HashListType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "hashlist_backend.HashListCpp",
    .tp_basicsize = sizeof(HashListObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_dealloc = (destructor)hashlist_dealloc,
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





