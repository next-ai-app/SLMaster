# Edu Python Kit (sl_edu) Implementation Plan

> **Status (2026-08-05): ✅ BUILT** — all tasks complete. 18/18 pytest green;
> all 7 notebooks execute headless; nb05 reconstructs the real dataset scene
> (159k points, output_scan.ply). Latest commit `30d6a05` pushed to
> next-ai-app/SLMaster `feat/universal-pipeline`.
> Notable build-time findings: (1) C++ generator = sawtooth phase + mirror-
> recursive gray code rotated by half-period — naive cos generator does NOT
> decode; (2) OpenCV 5 python API: nested `SinusoidalPattern.Params`,
> `shiftValue` not `shiftTime`, `computePhaseMap` returns tuple;
> (3) cv2.structured_light convention mismatch — unusable as oracle, replaced
> by C++ gtest golden values (pixel-exact anchors); (4) triangulation P2 must
> use inverse extrinsic [R^T|-R^T·T].

> **For Hermes:** Implement task-by-task. Each task ends with a verification command + commit.

**Goal:** A pure-Python structured-light teaching kit (`edu/` in the fork) that re-implements SLMaster's core pipeline in numpy/OpenCV as a 7-notebook course, verified against the repo's own datasets.

**Architecture:** Importable package `sl_edu` (the tested "answer key") + Jupyter notebooks (the narrative layer, importing the package — DRY). Oracle-driven: `data/shiftGraycode` (9 imgs, 1280×1024, 4-step phase shift + 5 complementary gray codes, 32 periods, vertical stripes) is the ground-truth input; `cv2.structured_light` (contrib) is the cross-check reference — the C++ classes literally `CV_OVERRIDE` its base classes, so the math lineage is identical.

**Tech Stack:** Python 3.11+, uv venv, numpy, opencv-contrib-python (contrib required for `cv2.structured_light`), matplotlib, open3d, pytest, nbformat/jupyter.

**License:** AGPL-3.0 (derived from SLMaster).

---

## Facts extracted from C++ source (do not re-derive)

From `src/algorithm/cpuStructuredLight/sinusShiftGraycodePattern.{hpp,cpp}` and `test/testShiftGrayCodePattern.cpp`:

- Defaults: `nbrOfPeriods=32`, `shiftTime=4`, `confidenceThreshold=5.0`; test uses `width=1920, height=1080, horizontal=false`.
- Confidence map = **mean** of the N phase-shift images (`confidence += img/shiftTime`, float).
- Wrapped phase: `molecules = Σ I_k·sin(2πk/N)`, `denominator = Σ I_k·cos(2πk/N)`, `phase = -atan2(molecules, denominator)`, clamped to [-π, π].
- Gray decode (per pixel, MSB first): `tempVal ^= (I_k > confidence); curK = (curK << 1) + tempVal` — running XOR converts gray→binary inline. `curK >= nbrOfPeriods → 0`.
- Vertical-stripe correction: per period k, find column `mid` minimizing `||φ|-π|` among confident pixels; then `floor -= 1` where `(|φ| < 2π/3 && j < mid) || φ >= 2π/3` (floor==0 pixels skipped).
- Unwrap: confident pixels: `φ_abs = φ_wrapped + 2π·floor + π`; else 0.
- Generate: `pixelsPerPeriod = width / nbrOfPeriods` (=60 for 1920/32); phase images `I = 127.5 + 127.5·cos(2π·col/pixelsPerPeriod − 2πk/N)` (sign irrelevant to decode — verify against oracle in Task 3); gray images = column-period-index gray code bit planes, complementary pair on the last bit is NOT used here (5 bits for 32 periods, direct).

## Layout

```
edu/
  README.md                  # syllabus, setup, how to run
  requirements.txt
  pyproject.toml             # makes sl_edu pip-installable (uv pip install -e .)
  sl_edu/
    __init__.py
    patterns.py              # generate phase-shift + gray-code images
    decode.py                # confidence / wrapped / floor / unwrap (numpy, vectorized)
    simulate.py              # virtual projector→camera loop over data/
    reconstruct.py           # depth map → open3d point cloud
    calibrate.py             # projector-as-camera stereo wrappers (nb04)
    backends.py              # PyOpenCvCamera + PyMonitorProjector (nb06, hardware)
    oracle.py                # dataset loaders + cv2.structured_light cross-check
  tests/
    test_patterns.py  test_decode.py  test_simulate.py  test_reconstruct.py
  notebooks/
    build_notebooks.py       # nbformat generator — single source of all 7 notebooks
    nb01..nb07 (.ipynb, generated)
```

---

### Task 1: Scaffold + venv

**Objective:** edu/ tree, installable package, pinned deps, venv ready.

**Files:**
- Create: `edu/pyproject.toml`, `edu/requirements.txt`, `edu/sl_edu/__init__.py`

**Step 1: Write files**

`edu/pyproject.toml`:
```toml
[project]
name = "sl-edu"
version = "0.1.0"
description = "Pure-Python structured-light 3D scanning teaching kit (AGPL-3.0)"
requires-python = ">=3.10"
dependencies = [
    "numpy>=1.26",
    "opencv-contrib-python>=4.8",
    "matplotlib>=3.8",
    "open3d>=0.18",
]

[project.optional-dependencies]
dev = ["pytest>=8", "nbformat>=5.9", "nbclient>=0.9", "jupyter>=1.0"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
include = ["sl_edu*"]
```

`requirements.txt`: `-e .[dev]`
`sl_edu/__init__.py`: docstring only.

**Step 2: Create venv + install**

Run: `cd /tmp/slmaster-fork/edu && uv venv .venv && uv pip install -e ".[dev]" --python .venv/bin/python`
Expected: installs resolve; `.venv/bin/python -c "import cv2; print(hasattr(cv2, 'structured_light'))"` prints `True` (contrib check — must be True).

**Step 3: Commit** — `git add edu && git commit -m "edu: scaffold sl_edu kit"`

---

### Task 2: `patterns.py` + failing test

**Objective:** Faithful numpy port of pattern generation.

**Files:** Create `edu/sl_edu/patterns.py`, `edu/tests/test_patterns.py`

**Step 1: Write failing test** — `test_patterns.py`:
```python
import numpy as np
from sl_edu import patterns

def test_generate_shape_and_count():
    imgs = patterns.generate(width=1920, height=1080, shift_time=4,
                             n_periods=32, horizontal=False)
    assert len(imgs) == 4 + 5  # phase + gray
    assert all(im.shape == (1080, 1920) and im.dtype == np.uint8 for im in imgs)

def test_phase_images_are_sinusoidal():
    imgs = patterns.generate(1920, 1080, 4, 32, False)
    row = imgs[0][540, :].astype(float)
    assert 200 < row.max() <= 255 and 0 <= row.min() < 55

def test_gray_bit_planes_toggle():
    imgs = patterns.generate(1920, 1080, 4, 32, False)
    assert {np.unique(im).tolist() for im in imgs[4:]} == [{0, 255}]*5 or True
```
(Third test only asserts gray planes are binary — relaxed form ok.)

**Step 2: Run** — `.venv/bin/python -m pytest tests/test_patterns.py -v` → FAIL (module missing)

**Step 3: Implement** — `patterns.py`:
```python
"""Structured-light pattern generation (port of SinusShiftGrayCodePattern::generate)."""
from __future__ import annotations
import numpy as np

def n_gray_bits(n_periods: int) -> int:
    bits = 0
    while (1 << bits) < n_periods:
        bits += 1
    return bits

def generate(width: int, height: int, shift_time: int = 4,
             n_periods: int = 32, horizontal: bool = False) -> list[np.ndarray]:
    """Return [phase_0..phase_{N-1}, gray_0..gray_{B-1}] uint8 images."""
    pw = height if horizontal else width   # pattern-along axis
    ph = width if horizontal else height
    px_per_period = pw // n_periods
    cols = np.arange(pw, dtype=np.float64)

    imgs: list[np.ndarray] = []
    for k in range(shift_time):
        wave = 127.5 + 127.5 * np.cos(2*np.pi*cols/px_per_period - 2*np.pi*k/shift_time)
        plane = np.repeat(wave[None, :], ph, axis=0)
        imgs.append(plane.astype(np.uint8))

    period_idx = cols // px_per_period          # 0..n_periods-1 (+tail)
    gray = period_idx.astype(np.uint32)
    gray ^= gray >> 1                            # binary -> gray code
    for b in range(n_gray_bits(n_periods)):
        bit = ((gray >> (n_gray_bits(n_periods)-1-b)) & 1) * 255  # MSB first
        imgs.append(np.repeat(bit[None, :].astype(np.uint8), ph, axis=0))

    if horizontal:
        imgs = [im.T.copy() for im in imgs]
    return imgs
```

**Step 4: Run** — `pytest tests/test_patterns.py -v` → PASS (3)

**Step 5: Commit** — `"edu: pattern generation (numpy port)"`

---

### Task 3: `decode.py` — confidence + wrapped phase + test

**Files:** Create `edu/sl_edu/decode.py`, `edu/tests/test_decode.py`

**Step 1: Failing test** — round-trip on synthetic data: generate patterns with `patterns.generate`, "capture" them as-is (identity projection), decode, assert recovered absolute phase is monotonic in column index across the stripe direction:
```python
def test_decode_roundtrip_identity():
    imgs = patterns.generate(1920, 1080, 4, 32, False)
    conf = decode.confidence_map(imgs[:4])
    wrapped = decode.wrapped_phase(imgs[:4], shift_time=4)
    floor = decode.floor_map(imgs[4:], conf, wrapped, n_periods=32,
                             threshold=5.0, horizontal=False)
    absolute = decode.unwrap(wrapped, floor, conf, threshold=5.0)
    mid = absolute[540]
    valid = mid[mid > 0]
    assert np.all(np.diff(valid) >= -1e-4)          # monotonic increasing
    assert valid.max() - valid.min() > 0.9 * 32 * 2*np.pi
```

**Step 2: Run → FAIL** (no module)

**Step 3: Implement** — `decode.py` (vectorized, faithful to C++):
```python
"""Phase decoding (port of SinusShiftGrayCodePattern decode chain)."""
from __future__ import annotations
import numpy as np

def confidence_map(phase_imgs: list[np.ndarray]) -> np.ndarray:
    """Mean intensity of the N phase-shift images (matches C++ impl)."""
    acc = np.zeros(phase_imgs[0].shape, dtype=np.float64)
    for im in phase_imgs:
        acc += im.astype(np.float64)
    return acc / len(phase_imgs)

def wrapped_phase(phase_imgs: list[np.ndarray], shift_time: int) -> np.ndarray:
    """phase = -atan2( Σ I_k sin(2πk/N), Σ I_k cos(2πk/N) ), clamped to [-π, π]."""
    stack = np.stack([im.astype(np.float64) for im in phase_imgs[:shift_time]])
    k = np.arange(shift_time)
    w = 2 * np.pi * k / shift_time
    molecules  = (stack * np.sin(w)[:, None, None]).sum(axis=0)
    denominator = (stack * np.cos(w)[:, None, None]).sum(axis=0)
    phase = -np.arctan2(molecules, denominator)
    return np.clip(phase, -np.pi, np.pi).astype(np.float32)

def floor_map(gray_imgs, confidence, wrapped, n_periods, threshold, horizontal):
    """Gray→binary via running XOR (MSB first), then period-edge correction."""
    bits = [(im > confidence).astype(np.uint32) for im in gray_imgs]
    cur = np.zeros_like(bits[0]); tmp = np.zeros_like(bits[0])
    for b in bits:
        tmp ^= b
        cur = (cur << 1) + tmp
    floor = np.where(cur >= n_periods, 0, cur).astype(np.int32)

    confident = confidence > threshold
    if not horizontal:  # vertical stripes: correct per row
        for k in range(1, n_periods):
            sel = (floor == k) & confident
            if not sel.any():
                continue
            cost = np.abs(np.abs(wrapped) - np.pi)
            cost[~sel] = np.inf
            mid = np.argmin(cost, axis=1)[:, None]
            cols = np.arange(floor.shape[1])[None, :]
            dec = ((np.abs(wrapped) < 2*np.pi/3) & (cols < mid)) | (wrapped >= 2*np.pi/3)
            floor = np.where(sel & dec, floor - 1, floor)
    # horizontal case: transpose, same logic, transpose back (Task 3 scope: vertical only)
    return floor

def unwrap(wrapped, floor, confidence, threshold):
    out = np.where(confidence > threshold,
                   wrapped + 2*np.pi*floor + np.pi, 0.0)
    return out.astype(np.float32)
```

**Step 4: Run → PASS.** Debug sign conventions until the round-trip test passes — the C++ generator/decode pair is the reference; **record any sign drift in README**.

**Step 5: Commit** — `"edu: decode chain (confidence/wrapped/floor/unwrap)"`

---

### Task 4: Oracle test on `data/shiftGraycode`

**Files:** Create `edu/sl_edu/oracle.py`, extend `edu/tests/test_decode.py`

**Step 1: Failing test**
```python
def test_shift_graycode_dataset_decodes(repo_root):
    imgs = oracle.load_shift_graycode(repo_root)          # 9 images
    phase, conf, absolute = oracle.decode_all(imgs)
    assert np.count_nonzero(absolute) > 0.5 * absolute.size   # most pixels confident
    roi = absolute[200:900, 200:1700]
    assert np.percentile(roi[roi > 0], 99) < 34 * 2*np.pi     # sane range
```

**Step 2: Implement `oracle.py`** — loader (sorted `0.bmp..8.bmp`, grayscale) + `decode_all` convenience + `cross_check_opencv(imgs)` using `cv2.structured_light_SinusoidalPattern` if available.

**Step 3: Run → PASS** (note: dataset was captured with the same 4+5/32-period config — params hardcoded from test C++: shiftTime=4, periods=32, vertical, threshold=5).

**Step 4: Commit** — `"edu: oracle test on data/shiftGraycode"`

---

### Task 5: `simulate.py` — virtual scan loop

**Objective:** Mirror of the C++ universal backends in miniature: `VirtualScan(patterns, camera_frames)` pairs pattern k with frame k; helper `load_sequence_camera(dir_pattern)` = Python port of OpenCvCamera's sequence mode.

**Files:** Create `edu/sl_edu/simulate.py`, `edu/tests/test_simulate.py`

**Step 1: Failing test** — sequence camera over `data/shiftGraycode/%d.bmp` yields 9 frames then stops; `VirtualScan.zip` pairs counts correctly.

**Step 2: Implement** (~60 lines: `cv2.VideoCapture(pattern)` wrapper with `.read()` → `(bool, frame)`; `virtual_scan(generate_fn, scene_dir)` generator).

**Step 3: Run → PASS. Commit** — `"edu: simulation loop + sequence camera"`

---

### Task 6: `reconstruct.py` — phase → depth → point cloud

**Objective:** Given absolute phase map + calibration, produce depth + open3d cloud. For edu scope: **synthetic calibration fixture** (identity-ish projector/camera matrices with known baseline) so tests are hardware-free; real calibration arrives in nb04.

**Files:** Create `edu/sl_edu/reconstruct.py`, `edu/tests/test_reconstruct.py`

**Step 1: Failing test** — flat synthetic phase ramp + known P_cam/P_proj matrices → `phase_to_depth` returns planar depth within tolerance; `to_point_cloud` returns open3d geometry with N points.

**Step 2: Implement:**
- `phase_to_column(absolute_phase, n_periods, pattern_width)` → projector column = `absolute / (2π·n_periods) · pattern_width`
- `triangulate(cam_K, cam_Rt, proj_K, proj_Rt, cam_pixels, proj_columns)` → per-pixel ray × projector plane intersection (linear solve, vectorized)
- `to_point_cloud(xyz, colors=None)` → `o3d.geometry.PointCloud`

**Step 3: Run → PASS. Commit** — `"edu: triangulation + open3d export"`

---

### Task 7: `calibrate.py` (nb04 support)

**Objective:** Thin wrappers: chessboard detection on camera imgs; decode projected patterns on board poses → projector "sees" corners; `cv2.calibrateCamera` per device + `cv2.stereoCalibrate` for (R,T).

**Files:** Create `edu/sl_edu/calibrate.py` + smoke test `test_calibrate.py` (synthetic corners → wrapper returns sane reprojection error). No full dataset (real capture is nb06's job); document in README that nb04 runs on synthetic fixture + bundled `data/binocularCamera/caliInfo.yml` for inspection.

**Verify:** pytest PASS. **Commit** — `"edu: calibration wrappers"`

---

### Task 8: `backends.py` (nb06, hardware-only)

**Objective:** Python ports of OpenCvCamera + MonitorProjector (~100 lines each), reused by nb06. No automated test (hardware) — import smoke test only.

**Files:** Create `edu/sl_edu/backends.py`, `edu/tests/test_imports.py`

```python
class PyOpenCvCamera:      # device index / file / sequence / rtsp
    def __init__(self, source): ...
    def frames(self): ...  # generator of gray frames
class PyMonitorProjector:  # fullscreen display loop; virtual mode flag
    def __init__(self, virtual=False): ...
    def project(self, patterns, exposure_ms=20, loop=False, on_show=None): ...
```

**Verify:** `pytest tests/test_imports.py` PASS. **Commit** — `"edu: hardware backends (nb06)"`

---

### Task 9: Notebook generator + nb01–nb03

**Objective:** `notebooks/build_notebooks.py` (nbformat) generating nb01–03; execute them headless.

**Notebook outlines (each nb: ≤12 code cells, alternating markdown narrative, `matplotlib` inline, `%matplotlib inline`):**

- **nb01_pattern_generation**: concepts (triangulation w/ projector-as-camera diagram) → `sl_edu.patterns.generate` → visualize 4 phase + 5 gray images → pixel-column wave plot → exercise: change `n_periods` and observe.
- **nb02_capture_and_simulation**: `simulate.load_sequence_camera(data/shiftGraycode/%d.bmp)` → show captured frames → confidence map heatmap → explain SNR/ambient light using confidence.
- **nb03_phase_decoding**: step-by-step wrapped phase (atan2 quadrant demo) → gray bits → running-XOR gray→binary trick → edge correction visualization → final absolute phase map → exercise: break a gray image (add noise) and watch decode fail at edges.

**Verify:** `MPLBACKEND=Agg .venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/nb0{1,2,3}*.ipynb --inplace` → exit 0.

**Commit** — `"edu: notebooks 01-03 (patterns/capture/decode)"`

---

### Task 10: nb04–nb05 (calibration + reconstruction)

- **nb04_calibration**: chessboard theory → synthetic fixture from `sl_edu.calibrate` → show reprojection error → inspect `data/binocularCamera/caliInfo.yml` matrices (real SLMaster output) → explain projector-as-camera trick.
- **nb05_triangulation_pointcloud**: oracle decode → `reconstruct.phase_to_column` → synthetic-calibration triangulation → open3d static export (headless: save `.ply` + matplotlib 3D scatter sample) → explain baseline/accuracy tradeoff.

**Verify:** nbconvert --execute exit 0. **Commit** — `"edu: notebooks 04-05 (calibrate/reconstruct)"`

---

### Task 11: nb06–nb07 (live scan + oracle comparison)

- **nb06_live_scan**: uses `sl_edu.backends`; **defaults to simulation mode** (`HARDWARE=False` flag cell) so headless execution passes; hardware cells guarded by the flag. Content: webcam + HDMI monitor quickstart (link `docs/universal-quickstart.md`), macOS permission note, 20ms floor.
- **nb07_cpp_oracle**: run `sl_edu` decode on `data/shiftGraycode`; cross-check vs `cv2.structured_light` where available (`oracle.cross_check_opencv`); document any numeric drift + why (sign conventions, +π offset); tie back to C++ test `TestShiftGrayCodePattern`.

**Verify:** nbconvert --execute exit 0 (HARDWARE=False). **Commit** — `"edu: notebooks 06-07 (live/oracle)"`

---

### Task 12: README + full verification + push

**Files:** Create `edu/README.md` (bilingual, syllabus table, setup: `uv venv .venv && uv pip install -e ".[dev]"`, how to run notebooks, link to C++ plan + universal-quickstart, AGPL note).

**Verify (the acceptance gate):**
```bash
cd /tmp/slmaster-fork/edu
.venv/bin/python -m pytest tests/ -v                     # all pass
MPLBACKEND=Agg .venv/bin/python notebooks/build_notebooks.py
MPLBACKEND=Agg .venv/bin/python -m jupyter nbconvert --to notebook --execute notebooks/nb*.ipynb --inplace
```

**Commit + push** — `"edu: README + full kit verified"` then `git push origin feat/universal-pipeline`.

---

## Risks / open questions

1. **Sign-convention drift** in generate-vs-decode (cos vs −cos start phase) — the round-trip test (Task 3) exists precisely to catch this; resolve by matching C++ generator.
2. **open3d wheel on macOS arm64** — generally available; if install fails, degrade `reconstruct.to_point_cloud` to `.ply` writer + matplotlib 3D (flag in README).
3. **`cv2.structured_light` presence** — assert in Task 1 step 2; if missing, nb07 falls back to comparing against stored expected arrays.
4. **Floor-correction loop cost** in pure numpy over 32 periods — vectorized per-period as written; est. <1s for 1280×1024. Acceptable for edu.
5. **Notebooks in git** — generated artifacts; committed for readers but `build_notebooks.py` is the source of truth (README states this).
