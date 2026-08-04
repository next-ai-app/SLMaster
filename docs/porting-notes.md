# Porting Notes — Universal Pipeline

Log of every portability fix discovered while bringing SLMaster up on Linux/macOS.
Newest entries at the bottom. Each entry: symptom → root cause → fix (commit).

## 2026-08-01 — Phase 0 scaffold (commit c737276)

1. **Root CMake MSVC-only flags** — `CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} /O2 /Zi"` breaks GCC/Clang.
   → Compiler-conditional flags; `CMAKE_BUILD_TYPE` only set if absent; dropped `CMAKE_BINARY_DIR` override (breaks presets/out-of-source); added C++17 standard.

2. **`BUILD_PERF` option dead** — `perf/` subdir guarded by `if(BUILD_TEST)` instead of `if(BUILD_PERF)`.
   → Fixed guard.

3. **algorithm CUDA-branch include typo** — `{CMAKE_CURRENT_SOURCE_DIR}` (missing `$`) in `target_include_directories` of the CUDA path.
   → Fixed. Only affects CUDA builds; CPU path unaffected.

4. **Device layer hard-locked to Windows** — `huaray_camera` links vendored `MVSDKmd.lib`; `projector_dlpc_api` links `cyusbserial` + `setupapi` (Windows system DLL). Factory *headers* directly include module headers, so consumers fail to compile even before linking.
   → CMake options `SLMASTER_WITH_HUARAY` / `SLMASTER_WITH_DLPC` (default ON only on WIN32); PUBLIC compile defs `WITH_HUARAY_CAMERA` / `WITH_DLPC_PROJECTOR`; `#ifdef` guards in `cameraFactory.h`, `projectorFactory.h`, `device.h`; factories return `nullptr` when no backend compiled in.

5. **ctest found zero tests** — `include(GoogleTest)` present but no `gtest_discover_tests` calls.
   → Registered all test targets; hardware tests gated behind the backend options.

6. **Core lib needs PCL + Eigen3** (not just OpenCV) — `src/algorithm` links PCL for point-cloud output.
   → Deps documented: apt `libpcl-dev libeigen3-dev` / brew `eigen pcl`.

## Environment drift log

- macOS (local dev machine): cmake 4.4.2, ninja 1.13.2, **OpenCV 5.0.0** (brew, vs upstream pin 4.8) — API-drift fixes tracked below as they surface.

## 2026-08-01 — Phase 0 build fixes (macOS arm64 first green build)

7. **cameraFactory.h transitive-include dependency** — `DEVICE_API` macro and `Camera` type reached the factory only via `huarayCamera.h`; gating that include broke compilation on all non-Windows platforms.
   → Include `typeDef.h` + `camera.h` unconditionally in the factory header.

8. **OpenCV 5: `cv::projectPoints` not declared** — `opencv2/opencv.hpp` in OpenCV 5 no longer pulls in the geometry/calib3d declarations (moved to `opencv2/geometry/3d.hpp`, exposed via legacy umbrella `opencv2/calib3d.hpp`).
   → `#include <opencv2/calib3d.hpp>` in `calibrator.h` (header exists on both 4.x and 5.x → portable).

9. **Test exes took >60s to start (dyld) / discovery timed out at 5s** — `find_package(PCL REQUIRED)` links ALL PCL components; `pcl_visualization` drags VTK 9.6 + Qt frameworks into a GUI-free core (~150-dylib closure; sample showed all threads in `dyld4::loadDependents`).
   → `find_package(PCL REQUIRED COMPONENTS common)` — core code only uses `pcl::PointCloud`. GUI phase must re-extend (io/features/filters/visualization). Test binary startup: >60s → <1s.

10. **`pcl::PLYWriter` undefined in TestLasterLine** — after (9), pcl_io no longer linked.
    → `find_package(PCL REQUIRED COMPONENTS io)` + link in the test target only.

11. **`ctest` found zero tests** (again) — `enable_testing()` was only called in `test/` subdir scope; top-level `CTestTestfile.cmake` never generated.
    → `enable_testing()` in root CMakeLists before `add_subdirectory(test)`.

12. **`LaserLineSuit.testStegerExtract` timeout (the only failing test)** — not an algorithm bug: the test ended with `namedWindow + imshow + waitKey(0)`, waiting for a human keypress forever; it also had **zero assertions** (visual-inspection test).
    → Removed GUI block + `circle()` debug drawing; added `ASSERT_FALSE(outPoints.empty())`.

**Result: 13/13 tests pass on macOS 26.5.2 arm64, OpenCV 5.0.0, PCL 1.15 (brew).** Also fixed en route: `gtest_discover_tests(... WORKING_DIRECTORY ${CMAKE_BINARY_DIR})` so `../../data` resolves to the repo's datasets.

## 2026-08-05 — Phase 3 universal backends

13. **`SafeQueue::pop()` is not value-returning** — signature is `void pop(T& item)`; `return imgs_.pop()` fails to compile.
    → `try_move_pop(img)` + return (same as Huaray backend).

14. **27 hardcoded `"Huaray" ? Huaray : Halcon` ternaries** in `src/cameras/{monocular,binocular,trinocular}` — adding a third backend via config string was impossible (unknown strings silently mapped to Halcon).
    → `CameraFactory::manufactorFromString()` helper; all 27 call sites replaced.

15. **Zero-hardware camera testing** — `cv::VideoCapture` accepts printf-style image-sequence URIs (`../../data/shiftGraycode/%d.bmp`), so the `OpenCvCamera` backend is testable end-to-end with the bundled datasets (no webcam, works headless in CI).

16. **`MonitorProjector` headless design** — OpenCV highgui windows can't open without a display server (CI) and Cocoa demands the main thread (macOS).
    → Virtual-display mode (`setVirtualDisplay(true)` or `SLMASTER_MONITOR_VIRTUAL=1`) keeps accurate pattern timing without any window; `currentPattern()`/`projectedCount()` hooks make the projector testable and simulation-ready; auto-fallback to virtual when window creation throws.

17. **Monitor timing floor** — an LCD can't change pattern faster than one refresh; sub-16.7 ms exposures are clamped with a one-time stderr warning (virtual mode keeps exact timing for fast tests).

**Result: 25/25 tests pass (13 prior + 12 new) in ~7 s on macOS arm64.**
