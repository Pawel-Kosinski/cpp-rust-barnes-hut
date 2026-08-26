cmake_minimum_required(VERSION 3.16)

project(BHBenchCR LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE Release CACHE STRING "Build type" FORCE)
endif()

add_executable(bh_generator cpp/generator.cpp)
add_executable(bh_cpp_v1 cpp/bh_v1_direct.cpp)
add_executable(bh_cpp_v2 cpp/bh_v2_pointer_tree.cpp)
add_executable(bh_cpp_v3 cpp/bh_v3_vector_tree.cpp)
add_executable(bh_cpp_v4 cpp/bh_v4_threaded_tree.cpp)
add_executable(bh_cpp_v5 cpp/bh_v5_parallel_force.cpp)

set(BHBENCH_TARGETS bh_generator bh_cpp_v1 bh_cpp_v2 bh_cpp_v3 bh_cpp_v4 bh_cpp_v5)
foreach(target IN LISTS BHBENCH_TARGETS)
    if(MSVC)
        target_compile_options(${target} PRIVATE /W4)
    else()
        target_compile_options(${target} PRIVATE -Wall -Wextra -Wpedantic)
    endif()
endforeach()

find_package(OpenMP REQUIRED)
target_link_libraries(bh_cpp_v5 PRIVATE OpenMP::OpenMP_CXX)
