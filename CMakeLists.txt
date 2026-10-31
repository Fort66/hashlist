cmake_minimum_required(VERSION 3.15)
project(hashlist LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(hashlist_backend src/main.cpp)

install(TARGETS hashlist_backend DESTINATION hashlist)
