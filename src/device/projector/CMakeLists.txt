cmake_minimum_required(VERSION 3.20)

project(projector)

set(PROJECTOR_ROOT_HEADER ${CMAKE_CURRENT_SOURCE_DIR}/common/projector.h
                          ${CMAKE_CURRENT_SOURCE_DIR}/common/projectorFactory.h
                          ${CMAKE_CURRENT_SOURCE_DIR}/common/typeDef.h)
set(PROJECTOR_ROOT_SOURCES ${CMAKE_CURRENT_SOURCE_DIR}/common/projectorFactory.cpp)

find_package(OpenCV REQUIRED)

if(WIN32)
    set(SLMASTER_WITH_DLPC_DEFAULT ON)
else()
    # DLPC347x path depends on Cypress CyUSBSerial (+ setupapi on Windows);
    # gated off until a Linux/macOS I2C backend lands
    # (see docs/plans/2026-08-01-universal-pipeline.md Phase 4).
    set(SLMASTER_WITH_DLPC_DEFAULT OFF)
endif()
option(SLMASTER_WITH_DLPC "build DLPC347x projector backend" ${SLMASTER_WITH_DLPC_DEFAULT})
# Monitor-as-projector backend — always available, pure OpenCV.
option(SLMASTER_WITH_MONITOR "build monitor projector backend" ON)

find_package(OpenCV REQUIRED)

if(SLMASTER_WITH_DLPC)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/module/projector_dlpc_api)
endif()

if(SLMASTER_WITH_MONITOR)
    add_subdirectory(${CMAKE_CURRENT_SOURCE_DIR}/module/monitor_projector)
endif()

if(BUILD_SLMASTER_SHARED)
    add_library(projector SHARED)
    target_compile_definitions(projector PUBLIC -DBUILD_SHARED_LIBS)
    target_compile_definitions(projector PRIVATE -DDLL_EXPORTS)
else()
    add_library(projector)
endif()

target_sources(projector PUBLIC ${PROJECTOR_ROOT_HEADER} ${PROJECTOR_ROOT_SOURCES})

target_include_directories(projector PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/common)

if(SLMASTER_WITH_DLPC)
    target_include_directories(projector PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/module/projector_dlpc_api/include)
    target_link_libraries(projector PUBLIC projectorDlpcApi)
    target_compile_definitions(projector PUBLIC WITH_DLPC_PROJECTOR)
endif()

if(SLMASTER_WITH_MONITOR)
    target_include_directories(projector PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/module/monitor_projector/include)
    target_link_libraries(projector PUBLIC monitorProjector)
    target_compile_definitions(projector PUBLIC WITH_MONITOR_PROJECTOR)
endif()
