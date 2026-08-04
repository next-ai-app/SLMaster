cmake_minimum_required(VERSION 3.20)

project(opencvCamera)

file(GLOB_RECURSE OPENCV_CAMERA_SOURCES CONFIGURE_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)

add_library(opencvCamera STATIC ${OPENCV_CAMERA_SOURCES})

find_package(OpenCV REQUIRED)

target_include_directories(opencvCamera PUBLIC
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/../../common
    ${OpenCV_INCLUDE_DIRS})

target_link_libraries(opencvCamera PUBLIC ${OpenCV_LIBRARIES})
