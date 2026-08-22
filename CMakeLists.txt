cmake_minimum_required(VERSION 3.16)

project(BHBenchCR LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(bh_generator cpp/generator.cpp)
add_executable(bh_cpp_v1 cpp/1brute_force.cpp)
add_executable(bh_cpp_v2 cpp/2without_vector_node.cpp)
add_executable(bh_cpp_v3 cpp/3without_next_pointer.cpp)
add_executable(bh_cpp_v4 cpp/4without_recursion.cpp)
add_executable(bh_cpp_v5 cpp/5multi_thread.cpp)

find_package(OpenMP)

if(OpenMP_CXX_FOUND)
    target_link_libraries(bh_cpp_v5 PRIVATE OpenMP::OpenMP_CXX)
endif()
