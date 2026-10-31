#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <vector>
#include <unordered_map>
#include <string>
#include <functional>
#include <stdexcept>
#include <algorithm>

namespace py = pybind11;

class HashListCpp {
private:
    std::vector<py::object> storage;
    std::unordered_map<ssize_t, std::vector<size_t>> hash_map;

    py::object freeze_internal(const py::object& item) {
        if (py::isinstance<py::dict>(item)) {
            py::dict d = py::reinterpret_borrow<py::dict>(item);
            py::list pairs;
            for (auto handle : d) {
                py::object k = py::reinterpret_borrow<py::object>(handle.first);
                py::object v = py::reinterpret_borrow<py::object>(handle.second);
                pairs.append(py::make_tuple(freeze_internal(k), freeze_internal(v)));
            }
            pairs.attr("sort")();
            return py::make_tuple("dict_token", py::tuple(pairs));
        }
        if (py::isinstance<py::list>(item)) {
            py::list l = py::reinterpret_borrow<py::list>(item);
            py::list frozen_elements;
            for (auto el : l) {
                frozen_elements.append(freeze_internal(py::reinterpret_borrow<py::object>(el)));
            }
            return py::make_tuple("list_token", py::tuple(frozen_elements));
        }
        if (py::isinstance<py::set>(item)) {
            py::set s = py::reinterpret_borrow<py::set>(item);
            py::list frozen_elements;
            for (auto el : s) {
                frozen_elements.append(freeze_internal(py::reinterpret_borrow<py::object>(el)));
            }
            frozen_elements.attr("sort")();
            return py::make_tuple("set_token", py::tuple(frozen_elements));
        }
        return item;
    }

    ssize_t get_safe_token(const py::object& item) {
        if (py::hasattr(item, "__hash__") && !item.attr("__hash__").is_none()) {
            try {
                return py::hash(item);
            } catch (...) {}
        }
        py::object frozen = freeze_internal(item);
        std::string str_repr = py::str(frozen).cast<std::string>();
        return std::hash<std::string>{}(str_repr);
    }

    void rebuild_hash_map() {
        hash_map.clear();
        for (size_t i = 0; i < storage.size(); ++i) {
            ssize_t token = get_safe_token(storage[i]);
            hash_map[token].push_back(i);
        }
    }

    void fix_indices_after_remove(size_t removed_idx, ssize_t removed_token, size_t old_size) {
        auto& vec = hash_map[removed_token];
        auto it = std::find(vec.begin(), vec.end(), removed_idx);
        if (it != vec.end()) {
            vec.erase(it);
        }
        if (vec.empty()) {
            hash_map.erase(removed_token);
        }

        if (removed_idx >= old_size - 1) {
            return;
        }

        for (auto& pair : hash_map) {
            for (auto& idx : pair.second) {
                if (idx > removed_idx) {
                    idx--;
                }
            }
        }
    }

public:
    HashListCpp() = default;

    void append(const py::object& item) {
        ssize_t token = get_safe_token(item);
        hash_map[token].push_back(storage.size());
        storage.push_back(item);
    }

    void extend(const py::object& iterable) {
        for (auto item : iterable) {
            py::object obj = py::reinterpret_borrow<py::object>(item);
            append(obj);
        }
    }

    void remove(const py::object& item) {
        ssize_t token = get_safe_token(item);
        auto it = hash_map.find(token);
        if (it == hash_map.end() || it->second.empty()) {
            throw py::value_error("hashlist.remove(x): x not in list");
        }

        size_t target_idx = it->second.front();
        size_t old_size = storage.size();
        storage.erase(storage.begin() + target_idx);
        
        fix_indices_after_remove(target_idx, token, old_size);
    }
    py::object pop(ssize_t index) {
        if (storage.empty()) {
            throw py::index_error("pop from empty hashlist");
        }
        if (index < 0) index += storage.size();
        if (index < 0 || index >= static_cast<ssize_t>(storage.size())) {
            throw py::index_error("pop index out of range");
        }

        py::object item = storage[index];
        ssize_t token = get_safe_token(item);
        size_t old_size = storage.size();
        
        storage.erase(storage.begin() + index);
        fix_indices_after_remove(index, token, old_size);
        return item;
    }

    void clear() {
        storage.clear();
        hash_map.clear();
    }

    ssize_t index_of(const py::object& item) {
        ssize_t token = get_safe_token(item);
        auto it = hash_map.find(token);
        if (it != hash_map.end() && !it->second.empty()) {
            return static_cast<ssize_t>(it->second.front());
        }
        throw py::value_error("x not in hashlist");
    }

    size_t count(const py::object& item) {
        ssize_t token = get_safe_token(item);
        auto it = hash_map.find(token);
        return (it != hash_map.end()) ? it->second.size() : 0;
    }

    void reverse() {
        std::reverse(storage.begin(), storage.end());
        rebuild_hash_map();
    }

    void sort(const py::args& args, const py::kwargs& kwargs) {
        py::list py_list;
        for (const auto& obj : storage) py_list.append(obj);
        py_list.attr("sort")(*args, **kwargs);
        
        storage.clear();
        for (auto item : py_list) {
            storage.push_back(py::reinterpret_borrow<py::object>(item));
        }
        rebuild_hash_map();
    }

    py::object getitem(const py::object& index) {
        if (py::isinstance<py::int_>(index)) {
            ssize_t idx = index.cast<ssize_t>();
            if (idx < 0) idx += storage.size();
            if (idx < 0 || idx >= static_cast<ssize_t>(storage.size())) {
                throw py::index_error("hashlist index out of range");
            }
            return storage[idx];
        }
        
        if (py::isinstance<py::slice>(index)) {
            py::slice s = index.cast<py::slice>();
            ssize_t start, stop, step, slicelength;
            if (!s.compute(storage.size(), &start, &stop, &step, &slicelength)) {
                throw py::error_already_set();
            }

            auto result_backend = std::make_unique<HashListCpp>();
            ssize_t cur = start;
            for (ssize_t i = 0; i < slicelength; ++i) {
                result_backend->append(storage[cur]);
                cur += step;
            }
            return py::cast(result_backend.release());
        }
        throw py::type_error("hashlist indices must be integers or slices");
    }

    void setitem(const py::object& index, const py::object& value) {
        if (py::isinstance<py::int_>(index)) {
            ssize_t idx = index.cast<ssize_t>();
            if (idx < 0) idx += storage.size();
            if (idx < 0 || idx >= static_cast<ssize_t>(storage.size())) {
                throw py::index_error("hashlist assignment index out of range");
            }

            storage[idx] = value;
            rebuild_hash_map();
            return;
        }

        if (py::isinstance<py::slice>(index)) {
            py::slice s = index.cast<py::slice>();
            ssize_t start, stop, step, slicelength;
            if (!s.compute(storage.size(), &start, &stop, &step, &slicelength)) {
                throw py::error_already_set();
            }

            py::list values_list = py::list(value);
            
            if (step == 1) {
                std::vector<py::object> new_values;
                for (auto item : values_list) {
                    new_values.push_back(py::reinterpret_borrow<py::object>(item));
                }
                auto erase_start = storage.begin() + start;
                auto erase_end = storage.begin() + stop;
                auto next_it = storage.erase(erase_start, erase_end);
                storage.insert(next_it, new_values.begin(), new_values.end());
            } else {
                if (static_cast<size_t>(slicelength) != values_list.size()) {
                    throw py::value_error("attempt to assign sequence to extended slice");
                }
                ssize_t cur = start;
                for (size_t i = 0; i < values_list.size(); ++i) {
                    storage[cur] = py::reinterpret_borrow<py::object>(values_list[i]);
                    cur += step;
                }
            }
            rebuild_hash_map();
            return; // Явный оператор return добавлен для стабильности MSVC на Windows
        }
    }

    void delitem(const py::object& index) {
        if (py::isinstance<py::int_>(index)) {
            ssize_t idx = index.cast<ssize_t>();
            if (idx < 0) idx += storage.size();
            if (idx < 0 || idx >= static_cast<ssize_t>(storage.size())) {
                throw py::index_error("hashlist deletion index out of range");
            }

            py::object item = storage[idx];
            ssize_t token = get_safe_token(item);
            size_t old_size = storage.size();
            
            storage.erase(storage.begin() + idx);
            fix_indices_after_remove(idx, token, old_size);
            return;
        }

        if (py::isinstance<py::slice>(index)) {
            py::slice s = index.cast<py::slice>();
            ssize_t start, stop, step, slicelength;
            if (!s.compute(storage.size(), &start, &stop, &step, &slicelength)) {
                throw py::error_already_set();
            }

            if (step == 1) {
                storage.erase(storage.begin() + start, storage.begin() + stop);
            } else {
                std::vector<ssize_t> indices;
                ssize_t cur = start;
                for (ssize_t i = 0; i < slicelength; ++i) {
                    indices.push_back(cur);
                    cur += step;
                }
                std::sort(indices.rbegin(), indices.rend());
                for (auto idx_del : indices) {
                    storage.erase(storage.begin() + idx_del);
                }
            }
            rebuild_hash_map();
        }
    }

    void insert(ssize_t index, const py::object& value) {
        if (index < 0) index += storage.size();
        if (index < 0) index = 0;
        if (index > static_cast<ssize_t>(storage.size())) index = storage.size();

        for (auto& pair : hash_map) {
            for (auto& idx : pair.second) {
                if (idx >= static_cast<size_t>(index)) {
                    idx++;
                }
            }
        }
        
        storage.insert(storage.begin() + index, value);
        ssize_t token = get_safe_token(value);
        
        auto& vec = hash_map[token];
        vec.push_back(index);
        std::sort(vec.begin(), vec.end());
    }

    bool contains(const py::object& item) {
        ssize_t token = get_safe_token(item);
        auto it = hash_map.find(token);
        return (it != hash_map.end() && !it->second.empty());
    }

    size_t len() const { return storage.size(); }
};

PYBIND11_MODULE(hashlist_backend, m) {
    py::class_<HashListCpp>(m, "HashListCpp")
        .def(py::init<>())
        .def("append", &HashListCpp::append)
        .def("extend", &HashListCpp::extend)
        .def("remove", &HashListCpp::remove)
        .def("pop", &HashListCpp::pop)
        .def("clear", &HashListCpp::clear)
        .def("index_of", &HashListCpp::index_of)
        .def("count", &HashListCpp::count)
        .def("reverse", &HashListCpp::reverse)
        .def("sort", &HashListCpp::sort)
        .def("getitem", &HashListCpp::getitem)
        .def("setitem", &HashListCpp::setitem)
        .def("delitem", &HashListCpp::delitem)
        .def("insert", &HashListCpp::insert)
        .def("__contains__", &HashListCpp::contains)
        .def("__len__", &HashListCpp::len);
}
