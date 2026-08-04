cmake_minimum_required(VERSION 3.20)

project(camera)

set(CAMERA_ROOT_HEADER ${CMAKE_CURRENT_SOURCE_DIR}/common/camera.h
                       ${CMAKE_CURRENT_SOURCE_DIR}/common/cameraFactory.h
                       ${CMAKE_CURRENT_SOURCE_DIR}/common/typeDef.h)
set(CAMERA_ROOT_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/common/cameraFactory.cpp ${CMAKE_CURRENT_SOURCE_DIR}/common/safeQueue.hpp)

find_package(OpenCV REQUIRED)

if(WIN32)
    set(SLMASTER_WITH_HUARAY_DEFAULT ON)
else()
    # Huaray ships Windows/Linux SDKs only; gated off until a platform SDK
    # is wired in (see docs/plans/2026-08-01-universal-pipeline.md Phase 4).
    set(SLMASTER_WITH_HUARAY_DEFAULT OFF)
endif()
option(SLMASTER_WITH_HUARAY "build huaray camera backend" ${SLMASTER_WITH_HUARAY_DEFAULT})

if(SLMASTER_WITH_HUARAY)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/module/huaray_camera)
endif()

if(BUILD_SLMASTER_SHARED)
    add_library(camera SHARED)
    target_compile_definitions(camera PUBLIC -DBUILD_SHARED_LIBS)
    target_compile_definitions(camera PRIVATE -DDLL_EXPORTS)
else()
    add_library(camera)
endif()

target_sources(camera PUBLIC ${CAMERA_ROOT_HEADER} ${CAMERA_ROOT_SOURCES})

target_include_directories(camera PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/common)

target_link_libraries(
    camera
    PUBLIC
    ${OpenCV_LIBRARIES}
)

if(SLMASTER_WITH_HUARAY)
    target_include_directories(camera PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/module/huaray_camera/include)
    target_link_libraries(camera PUBLIC huarayCamera)
    target_compile_definitions(camera PUBLIC WITH_HUARAY_CAMERA)
endif()
