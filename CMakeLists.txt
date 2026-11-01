cmake_minimum_required(VERSION 3.15)
project(hashlist LANGUAGES C)

# Используем стандартный классический компонент для сборки Си-модулей Python
find_package(Python COMPONENTS Development.Module REQUIRED)

python_add_library(hashlist_backend MODULE src/hashlist_core.c)
set_target_properties(hashlist_backend PROPERTIES C_VISIBILITY_HIDDEN ON)

# Явно указываем scikit-build-core, куда положить собранный Си-бинарник
install(TARGETS hashlist_backend DESTINATION hashlist)
