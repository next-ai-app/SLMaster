cmake_minimum_required(VERSION 3.20)

project(monitorProjector)

file(GLOB_RECURSE MONITOR_PROJECTOR_SOURCES CONFIGURE_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)

add_library(monitorProjector STATIC ${MONITOR_PROJECTOR_SOURCES})

find_package(OpenCV REQUIRED)

target_include_directories(monitorProjector PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../../common
    ${OpenCV_INCLUDE_DIRS})

target_link_libraries(monitorProjector PUBLIC ${OpenCV_LIBRARIES})
