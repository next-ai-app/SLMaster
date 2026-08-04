# Universal Backend Quickstart / 通用後端快速上手

[English below | 中文在後]

## English

### What this is

SLMaster can now run **without any proprietary SDK** on Windows, Linux and
macOS:

- **`OpenCvCamera`** — camera backend on `cv::VideoCapture`. Uses the OS-native
  stack (V4L2 / AVFoundation / MSMF), so any UVC webcam works. Also accepts a
  video file, an image sequence (`dir/%d.bmp`), or an RTSP stream instead of a
  device index.
- **`MonitorProjector`** — monitor-as-projector backend. Renders
  structured-light patterns fullscreen on any display (standard lab practice).
  No DLPC347x, no Cypress driver.

### Live hardware setup (5 minutes)

1. Plug in a webcam and a second monitor (HDMI). Dark room recommended.
2. Edit your pipeline config (e.g. `gui/qml/res/config/monocularCameraConfig.json`):
   - `"DLP Evm"` → `"Monitor"`
   - `"2D Camera Manufactor"` → `"OpenCV"`
   - camera name fields → `"0"` (first webcam) or a URI
3. Calibrate as usual (projector = the monitor, so calibrate intrinsics of the
   camera + "projector intrinsics" of the displayed pattern plane).
4. Scan.

**Timing floor:** a monitor can only change the pattern once per refresh
(~16.7 ms @ 60 Hz). Pattern exposures shorter than that are clamped with a
warning. Use ≥ 20 ms per pattern and long camera exposure.

**macOS notes:**
- Camera access requires `NSCameraUsageDescription` in the app's `Info.plist`
  (already present for the GUI app). CLI binaries inherit the permission of
  the terminal that launches them.
- Cocoa requires window operations on the main thread. Drive the projector
  from the GUI main thread via `step()`, or use virtual mode (below).

### No hardware? Full pipeline simulation

```bash
export SLMASTER_MONITOR_VIRTUAL=1   # projector renders "virtually" (accurate timing, no window)
# camera name "../../data/shiftGraycode/%d.bmp" — reads the bundled dataset as frames
```

`MonitorProjector::currentPattern()` exposes the pattern currently "on screen"
so a simulator loop can feed it into synthetic camera images.

---

## 中文

### 呢度係咩

SLMaster 而家**唔使任何閉源 SDK** 都可以喺 Windows / Linux / macOS 行：

- **`OpenCvCamera`** — 相機後端，基於 `cv::VideoCapture`，用 OS 原生棧
  （V4L2 / AVFoundation / MSMF），任何 UVC webcam 即用。亦可以餵影片檔、
  圖片序列（`dir/%d.bmp`）或 RTSP 串流當相機。
- **`MonitorProjector`** — 顯示器當投影儀後端：全芒顯示結構光圖案
  （實驗室標準做法）。唔使 DLPC347x、唔使 Cypress 驅動。

### 真機五分鐘設置

1. 插 webcam + 第二部顯示器（HDMI），環境越黑越好。
2. 改 pipeline config（例：`gui/qml/res/config/monocularCameraConfig.json`）：
   - `"DLP Evm"` → `"Monitor"`
   - `"2D Camera Manufactor"` → `"OpenCV"`
   - 相機名 → `"0"`（第一個 webcam）或 URI
3. 照舊標定（投影儀＝顯示器，「投影儀內參」即顯示圖案平面嘅參數）。
4. 掃描。

**時序下限**：顯示器每個 refresh 先可以換一次圖案（60 Hz ≈ 16.7 ms）。
低過呢個值嘅曝光會被 clamp 兼警告。建議每張圖案 ≥ 20 ms，相機曝光配合。

**macOS 注意**：
- 相機權限要喺 app 嘅 `Info.plist` 寫 `NSCameraUsageDescription`（GUI app 已有）；
  CLI 程式繼承啟動佢嘅 terminal 嘅權限。
- Cocoa 規定窗口操作要喺主線程：GUI 主線程用 `step()` 驅動投影，
  或者用虛擬模式（下面）。

### 冇硬件？全管線模擬

```bash
export SLMASTER_MONITOR_VIRTUAL=1   # 投影儀「虛擬」渲染（計時準確、冇窗口）
# 相機名 "../../data/shiftGraycode/%d.bmp" — 將內置數據集當相機幀讀
```

`MonitorProjector::currentPattern()` 會暴露而家「芒上」嘅圖案，
模擬迴路可以攞佢合成相機影像。
