# Universal Pipeline Implementation Plan — SLMaster

> **For Hermes:** Use subagent-driven-development skill to implement this plan phase-by-phase.

**Goal:** Make SLMaster build and run the full calibration → stripe-encoding → reconstruction → post-processing pipeline on Linux AND macOS as tier-1 platforms (parity with Windows), with hardware backends that work WITHOUT proprietary SDKs — not just Windows + Huaray/DLP hardware.

**Architecture:** The Windows lock-in is concentrated in two places, NOT in the algorithm core:
1. **Build recipes** (MSVC-only CMake flags, Windows-only CI, exe packaging)
2. **Device layer SDKs** (Huaray `MVSDKmd.lib`, Cypress `cyusbserial.dll` for DLP I2C)

Strategy: keep the existing abstraction interfaces (`camera.h`, `projector.h` + factories), make the core portable first (fast win — zero device deps), then add **universal backends** (OpenCV camera + monitor-as-projector) so any webcam + any HDMI display can run the whole pipeline. Proprietary Linux SDK support comes last, as parity work.

**Tech Stack:** C++17, CMake ≥3.20 + CMakePresets, OpenCV 4.x (CPU path first, CUDA optional), Qt 5.15 QML, VTK 9.x, PCL 1.12, googletest, GitHub Actions matrix.

---

## Evidence baseline (from repo audit 2026-08-01, commit `885234c`)

- `src/algorithm`, `src/calibration`, `src/cameras`: **zero** `windows.h` / `_WIN32` API usage (only vendored jsoncpp `__declspec` macros, which already have portable `#else` branches).
- `src/common.h`, `src/device/*/common/typeDef.h`: `SLMASTER_API`/`DEVICE_API` export macros already have non-Windows `#else` branches. ✓
- Root `CMakeLists.txt:8`: `set(CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} /O2 /Zi")` — MSVC-only flags, breaks GCC/Clang.
- Root `CMakeLists.txt:7`: `set(CMAKE_BINARY_DIR ...)` override — bad practice, breaks presets.
- Root `CMakeLists.txt:28`: `if(BUILD_TEST)` guards the `perf/` subdir — should be `if(BUILD_PERF)` (real bug).
- `gui/CMakeLists.txt:27`: `add_executable(SLMasterGui WIN32)` — hardcoded WIN32.
- `src/device/camera/module/huaray_camera/lib/MVSDKmd.lib`: Windows import lib only. `IMVApi.h` is already dual-platform (`#if _WIN32 … #else`). Huaray ships a Linux MVViewer SDK (.so) from the same download page.
- `src/device/projector/module/projector_dlpc_api/third_party/cyusbserial/`: only `cyusbserial.dll` + `.lib` vendored. Cypress ships a Linux CyUSBSerial; alternatively `cypress_i2c.cpp` is one contained file that can be ported to libusb.
- `data/` contains 7 datasets (real mono/bino, laser line, 3 simulation sets) — a ready-made **cross-platform test oracle** for offline reconstruction.
- CI: only `.github/workflows/windows.yml` (windows-2019, MSVC, builds OpenCV/VTK/PCL from source — slow).

## Platform decisions (confirmed 2026-08-01)

- **macOS is tier-1** alongside Windows and Linux — full core + GUI + CI parity. Primary arch: **Apple Silicon (arm64)** via Homebrew (`/opt/homebrew`); Intel mac is best-effort. GHA runner: `macos-14` (arm64).
- **Dependencies:** system packages are primary — `apt` on Ubuntu, `brew` on macOS. Version drift vs upstream pins is **accepted** (ubuntu-22.04: VTK 9.1 / OpenCV 4.5; brew: rolling latest; upstream pin: VTK 9.2 / OpenCV 4.8). CI validates both drift ends; source-builds only as fallback if a hard incompatibility is hit.
- **Huaray/DLP hardware availability: TBD** — therefore **Phase 4 is non-blocking**. Hardware-dependent tests stay gated behind `SLMASTER_WITH_HARDWARE=1` and are excluded from CI.
- **CI runners:** GHA-hosted only (`windows-2019`, `ubuntu-22.04`, `macos-14`). No self-hosted runner. Local dev on the user's Mac (arm64); Ubuntu coverage comes from CI.

---

## Phase 0 — Portable build scaffold + Linux core build (proof)

**Objective:** `libslmaster` + gtest suite build green on Ubuntu with `BUILD_GUI=OFF`. Small, fully knowable tasks.

### Task 0.1: Branch

```bash
cd SLMaster && git checkout -b feat/universal-pipeline
```

### Task 0.2: Fix root CMakeLists.txt compiler flags

**Files:** Modify `CMakeLists.txt:6-8`

Replace:

```cmake
set(CMAKE_BUILD_TYPE Release)
set(CMAKE_BINARY_DIR ${CMAKE_CURRENT_SOURCE_DIR}/build)
set(CMAKE_CXX_FLAGS_RELEASE "$ENV{CXXFLAGS} /O2 /Zi")
```

with:

```cmake
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
```

**Verify:** `cmake -S . -B build -DBUILD_GUI=OFF` configures on both Windows and Linux.

### Task 0.3: Fix BUILD_PERF guard bug

**Files:** Modify `CMakeLists.txt:28` — change `if(BUILD_TEST)` to `if(BUILD_PERF)` above `add_subdirectory(perf)`.

### Task 0.4: Add CMakePresets.json

**Files:** Create `CMakePresets.json`

```json
{
  "version": 3,
  "configurePresets": [
    {
      "name": "linux-core",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/linux-core",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "BUILD_GUI": "OFF",
        "BUILD_TEST": "ON",
        "BUILD_PERF": "OFF"
      }
    },
    {
      "name": "linux-gui",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/linux-gui",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "BUILD_GUI": "ON",
        "BUILD_TEST": "ON",
        "BUILD_PERF": "OFF"
      }
    },
    {
      "name": "macos-core",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/macos-core",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "BUILD_GUI": "OFF",
        "BUILD_TEST": "ON",
        "BUILD_PERF": "OFF"
      }
    },
    {
      "name": "macos-gui",
      "generator": "Ninja",
      "binaryDir": "${sourceDir}/build/macos-gui",
      "cacheVariables": {
        "CMAKE_BUILD_TYPE": "Release",
        "BUILD_GUI": "ON",
        "BUILD_TEST": "ON",
        "BUILD_PERF": "OFF",
        "CMAKE_PREFIX_PATH": "/opt/homebrew/opt/qt@5"
      }
    }
  ]
}
```

### Task 0.5: Build core on Ubuntu AND macOS

Ubuntu (Upcloud box or GHA):

```bash
sudo apt update && sudo apt install -y build-essential cmake ninja-build libopencv-dev
cmake --preset linux-core
cmake --build build/linux-core --parallel
```

macOS (Apple Silicon, Homebrew):

```bash
brew install cmake ninja opencv
cmake --preset macos-core
cmake --build build/macos-core --parallel
```

**Expected:** OpenCV version drift on both (ubuntu-22.04: 4.5.4, brew: 4.12+) may emit deprecations vs pinned 4.8 — fix any hard errors; keep a `docs/porting-notes.md` log of every fix (each becomes its own micro-commit).

### Task 0.6: Run gtest suite on Linux

```bash
ctest --test-dir build/linux-core --output-on-failure
```

Tests live in `test/` (vendored googletest 1.12.0 zip): `testInterzoneSinusFourGrayscalePattern`, `testShiftGrayCodePattern`, `testThreeFrequencyHeterodynePattern`, `testLaserLine`, plus device tests needing hardware (expect skip/fail — gate hardware tests behind an env flag, e.g. `SLMASTER_WITH_HARDWARE=1`).

### Task 0.7: Commit + push phase

```bash
git add -A && git commit -m "build: portable CMake scaffold for Linux core build"
git push -u origin feat/universal-pipeline
```

---

## Phase 1 — Offline reconstruction test oracle (cross-platform correctness)

**Objective:** the 7 `data/` datasets produce identical reconstruction results on Windows and Linux — proves algorithm portability, catches UB/endianness/floating-point drift.

### Task 1.1: Reference-output snapshot

Write `test/snapshotReconstruction.cpp` (gtest): for each dataset, run the matching pattern pipeline end-to-end, then assert on stable metrics — point-cloud point count, bounding-box extents, mean/σ of depth, checksum of the wrapped-phase map. Capture reference values from the Windows build first (document in `test/reference/README.md`).

### Task 1.2: Register with CTest + tolerance policy

Exact match for integer/count metrics; relative tolerance (e.g. 1e-5) for float metrics. Document why (FP non-associativity across compilers).

### Task 1.3: GHA cross-platform core jobs

**Files:** Create `.github/workflows/ubuntu.yml` — ubuntu-22.04, apt deps, `cmake --preset linux-core`, build, `ctest`. Create `.github/workflows/macos.yml` — macos-14 (arm64), `brew install cmake ninja opencv`, `cmake --preset macos-core`, build, `ctest`. Hardware-gated tests excluded via env flag on both.

**Verify:** PR shows green checkmarks for `windows.yml`, `ubuntu.yml` and `macos.yml`.

---

## Phase 2 — GUI on Linux and macOS

**Objective:** `SLMasterGui` builds and launches on Ubuntu and macOS (offline scan mode usable on both).

### Task 2.1: Dependencies

Ubuntu:

```bash
sudo apt install -y qtbase5-dev qtdeclarative5-dev qtquickcontrols2-5-dev \
  libvtk9-dev libpcl-dev
```

If VTK 9.1 vs pinned 9.2 causes issues → build VTK 9.2 from source with `VTK_GROUP_ENABLE_Qt=YES` (document in `docs/build-linux.md`).

macOS:

```bash
brew install qt@5 vtk pcl
# qt@5 is keg-only: CMAKE_PREFIX_PATH=/opt/homebrew/opt/qt@5 (already in macos-gui preset)
```

### Task 2.2: Fix hardcoded WIN32 executable flag

**Files:** Modify `gui/CMakeLists.txt:27`

```cmake
if(WIN32)
    add_executable(SLMasterGui WIN32)
elseif(APPLE)
    add_executable(SLMasterGui MACOSX_BUNDLE)
else()
    add_executable(SLMasterGui)
endif()
```

### Task 2.3: Build with `linux-gui` and `macos-gui` presets; fix QML import path / FluentUI / QuickQanava issues as they surface (log each in porting-notes). On macOS, QML plugin paths inside the bundle need `qt.conf` or `macdeployqt -qmldir` handling.

### Task 2.4: Headless smoke test (both)

```bash
QT_QPA_PLATFORM=offscreen ./SLMasterGui --smoke  # or timeout-kill after 10s clean start
```

Add to `ubuntu.yml` and `macos.yml` as a non-blocking step first, blocking once stable.

---

## Phase 3 — Universal hardware backends (the actual "universal" payoff)

**Objective:** any UVC webcam + any HDMI display/projector runs the full live pipeline — zero proprietary SDK.

### Task 3.1: OpenCV camera backend

**Files:**
- Create `src/device/camera/module/opencv_camera/include/opencvCamera.h`
- Create `src/device/camera/module/opencv_camera/src/opencvCamera.cpp`
- Modify `src/device/camera/common/cameraFactory.cpp` — register `"opencv"` backend

Implement the existing `camera.h` interface using `cv::VideoCapture` (V4L2 on Linux, AVFoundation on macOS, MSMF on Windows). Properties (exposure, resolution, trigger) mapped via `cv::CAP_PROP_*`; software-trigger emulation via latest-frame grab.

**macOS gotcha:** camera access requires `NSCameraUsageDescription` in the app `Info.plist` (and screen-recording permission if capturing another window) — add plist keys to the `MACOSX_BUNDLE` target in Phase 2.2's CMake block.

**Test:** extend `testHuarayCamera.cpp` pattern → `testOpencvCamera.cpp` using a virtual device or recorded frames when no camera present.

### Task 3.2: Monitor-as-projector backend

**Files:**
- Create `src/device/projector/module/monitor_projector/include/monitorProjector.h`
- Create `src/device/projector/module/monitor_projector/src/monitorProjector.cpp`
- Modify `src/device/projector/common/projectorFactory.cpp` — register `"monitor"` backend

Implement `projector.h` by rendering pattern images fullscreen on a selected display (QWindow/QML fullscreen window; patterns already exist as `cv::Mat`). This is the standard lab technique — turns any HDMI monitor/DLP into the pattern source with gamma/brightness notes documented.

### Task 3.3: Config schema

Camera config JSON (`gui/qml/res/config/*.json`) gains `"camera_backend"` / `"projector_backend"` fields, defaulting to current huaray/dlpc values — zero behavior change for existing users.

### Task 3.4: End-to-end demo

Webcam + laptop HDMI monitor: calibrate, encode, scan a real object; document in `docs/universal-quickstart.md` (EN+CN) with photos of setup + resulting point cloud.

---

## Phase 4 — Proprietary SDK Linux parity

**Objective:** existing Huaray + DLP hardware works on Linux.

### Task 4.1: Huaray Linux MVSDK

Download Linux SDK from irayple (same MVViewer page). Add per-OS find logic in `src/device/camera/module/huaray_camera/cmake/CameraConfig.cmake` (`if(WIN32) .lib else() find .so`). Do NOT commit SDK binaries; document install path / use `MVSDK_DIR` cache var.

### Task 4.2: DLPC347x I2C on Linux

Two options, decide at execution (both contained in `src/device/projector/module/projector_dlpc_api/`):
- (a) Cypress CyUSBSerial Linux library (drop-in, same API)
- (b) Port `cypress_i2c.cpp` to libusb-1.0 (one file; no Cypress dependency)

### Task 4.3: Hardware validation

Run the existing `testHuarayCamera` / `testProjectorDlpcApi*` tests on Linux with `SLMASTER_WITH_HARDWARE=1`. (Requires physical hardware — see open question 3.)

---

## Phase 5 — CI matrix, packaging, docs

### Task 5.1: GHA matrix (three tier-1 platforms)

`windows.yml` (existing) + `ubuntu.yml` + `macos.yml` (macos-14, arm64), all blocking. Consider the Upcloud box as self-hosted Ubuntu runner for faster builds (install docker + actions runner as a service); macOS stays on GHA-hosted runners.

### Task 5.2: Packaging

- Windows: exe installer (existing pipeline)
- Linux: AppImage (linuxdeploy + linuxdeploy-plugin-qt) or `.deb` via CPack
- macOS: `.dmg` via `macdeployqt -qmldir=...` + ad-hoc codesign (skip Apple notarization for research distribution — document `--no-quarantine` install note)

### Task 5.3: Docs

- `docs/build-linux.md` + `docs/build-macos.md` (EN+CN): dep one-liners, preset builds, known issues (VTK version, Qt theming, keg-only qt@5, camera permissions)
- README badge matrix (Windows | Ubuntu | macOS)
- README quickstart: offline mode → universal mode (webcam+monitor) → pro hardware

---

## Risks and tradeoffs

| Risk | Impact | Mitigation |
|---|---|---|
| VTK version drift (apt 9.1 / brew 9.x vs pin 9.2) | GUI build breaks | Accept distro versions if API-compatible; else source-build (slow CI) |
| Qt 5.15 distro quirks (OpenSSL, theming; brew keg-only qt@5) | GUI runtime issues | aqtinstall 5.15.14 parity option; `CMAKE_PREFIX_PATH` in preset; offscreen smoke test in CI |
| OpenCV drift (4.5 apt / 4.12+ brew vs pin 4.8) | Core compile errors | Phase 0.5 fixes; CI exercises both ends |
| brew formula churn (rolling) | macOS CI breaks unexpectedly | Pin CI to `macos-14` image; cache brew; document versions in build docs |
| macOS camera/screen permissions | Universal camera backend dead on arrival | `NSCameraUsageDescription` in bundle plist; document permission grant step |
| Huaray Linux SDK redistribution license | Can't vendor .so | Document user-side install; `MVSDK_DIR` var |
| Huaray has **no macOS SDK** at all | Pro hardware unreachable on mac | Accept: universal backends (webcam+monitor) ARE the mac hardware story; Phase 4 stays Linux+Windows only |
| FP drift in reconstruction metrics | Flaky oracle | Tolerance policy in Phase 1.2; integer metrics exact |
| Monitor-projector gamma/timing inaccuracy | Scan quality | Document gamma-correction guidance; still fine for dev/demos |
| Scope creep (Qt6, ROS, Python bindings) | Plan never lands | Explicit non-goals below |

## Non-goals (YAGNI)

- Qt6 migration, ROS/ROS2 integration, Python bindings, macOS notarization/App Store, Wayland-specific work, ARM-Linux builds (Jetson), Intel-mac CI — all deferred; revisit after Phase 5.

## Validation checklist (definition of done)

- [ ] `ubuntu.yml` + `macos.yml` CI green: core lib + tests, alongside existing `windows.yml`
- [ ] Offline datasets produce matching metrics on Windows + Linux + macOS
- [ ] `SLMasterGui` launches on Ubuntu AND macOS; offline scan works on both
- [ ] Webcam + monitor completes a live scan (documented with evidence; macOS and Linux)
- [ ] Huaray/DLP hardware tests pass on Linux (if hardware available)
- [ ] Release page ships Windows exe + Linux AppImage + macOS dmg
