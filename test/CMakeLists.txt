cmake_minimum_required(VERSION 3.20)

project(TestSLMaster)

include(FetchContent)
FetchContent_Declare(
    googletest
    URL ${CMAKE_CURRENT_SOURCE_DIR}/third_party/googletest-1.12.0.zip
)

set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)

FetchContent_MakeAvailable(googletest)
enable_testing()

if(SLMASTER_WITH_HUARAY)
    add_executable(
        TestHuarayCamera
        ${CMAKE_CURRENT_SOURCE_DIR}/testHuarayCamera.cpp
    )

    target_link_libraries(
        TestHuarayCamera
        PUBLIC
        camera
        GTest::gtest_main
    )
endif()

if(SLMASTER_WITH_DLPC)
    add_executable(
        TestProjectorDlpcApi4710
        ${CMAKE_CURRENT_SOURCE_DIR}/testProjectorDlpcApi4710.cpp
    )

    target_link_libraries(
        TestProjectorDlpcApi4710
        PUBLIC
        projector
        GTest::gtest_main
    )

    add_executable(
        TestProjectorDlpcApi3010
        ${CMAKE_CURRENT_SOURCE_DIR}/testProjectorDlpcApi3010.cpp
    )

    target_link_libraries(
        TestProjectorDlpcApi3010
        PUBLIC
        projector
        GTest::gtest_main
    )
endif()

add_executable(
    TestLasterLine
    ${CMAKE_CURRENT_SOURCE_DIR}/testLaserLine.cpp
)

# testLaserLine writes point clouds via pcl::PLYWriter (pcl_io); the core lib
# deliberately links only pcl_common.
find_package(PCL REQUIRED COMPONENTS io)

target_link_libraries(
    TestLasterLine
    PUBLIC
    slmaster
    ${PCL_LIBRARIES}
    GTest::gtest_main
)

add_executable(
    TestShiftGrayCodePattern
    ${CMAKE_CURRENT_SOURCE_DIR}/testShiftGrayCodePattern.cpp
)

target_link_libraries(
    TestShiftGrayCodePattern
    PUBLIC
    slmaster
    GTest::gtest_main
)

add_executable(
    TestInterzoneSinusFourGrayscalePattern
    ${CMAKE_CURRENT_SOURCE_DIR}/testInterzoneSinusFourGrayscalePattern.cpp
)

target_link_libraries(
    TestInterzoneSinusFourGrayscalePattern
    PUBLIC
    slmaster
    GTest::gtest_main
)

add_executable(
    TestThreeFrequencyHeterodynePattern
    ${CMAKE_CURRENT_SOURCE_DIR}/testThreeFrequencyHeterodynePattern.cpp
)

target_link_libraries(
    TestThreeFrequencyHeterodynePattern
    PUBLIC
    slmaster
    GTest::gtest_main
)

include(GoogleTest)

# Tests reference data via ../../data — resolves to the repo's data/ dir only
# when cwd is the binary dir (build/<preset>).
gtest_discover_tests(TestLasterLine WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
gtest_discover_tests(TestShiftGrayCodePattern WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
gtest_discover_tests(TestInterzoneSinusFourGrayscalePattern WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
gtest_discover_tests(TestThreeFrequencyHeterodynePattern WORKING_DIRECTORY ${CMAKE_BINARY_DIR})

if(TARGET TestHuarayCamera)
    gtest_discover_tests(TestHuarayCamera WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
endif()

if(TARGET TestProjectorDlpcApi4710)
    gtest_discover_tests(TestProjectorDlpcApi4710 WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
endif()

if(TARGET TestProjectorDlpcApi3010)
    gtest_discover_tests(TestProjectorDlpcApi3010 WORKING_DIRECTORY ${CMAKE_BINARY_DIR})
endif()
