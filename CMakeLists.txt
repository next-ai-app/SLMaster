cmake_minimum_required(VERSION 3.20)

project(SLMaster)

set(CMAKE_EXPORT_COMPILE_COMMANDS TRUE)
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(MSVC)
    set(CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} /O2 /Zi")
else()
    set(CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} -O3")
endif()

add_subdirectory(src)

option(BUILD_GUI "build the gui." ON)

if(BUILD_GUI)
    add_subdirectory(gui)
    message(NOTICE "[SLMaster]: build gui...")
endif()

option(BUILD_TEST "build the test case with google_test." ON)

if(BUILD_TEST)
    message(STATUS "[SLMaster]: build test case...")
    enable_testing()
    add_subdirectory(test)
endif()

option(BUILD_PERF "build the perfermance case with google benchmark." ON)

if(BUILD_PERF)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/perf)
    message(NOTICE "[SLMaster]: build perfermance case...")
endif()
