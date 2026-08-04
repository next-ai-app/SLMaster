"""Generate the 7 teaching notebooks from cell sources (reproducible, diffable).

Run:  python notebooks/build_notebooks.py
Then: python -m jupyter nbconvert --to notebook --execute notebooks/nb*.ipynb
"""
from pathlib import Path

import nbformat as nbf

OUT = Path(__file__).resolve().parent


def nb(cells, kernelspec_lang="python"):
    book = nbf.v4.new_notebook()
    book.metadata = {"kernelspec": {"display_name": "Python 3",
                                    "language": kernelspec_lang, "name": "python3"},
                     "language_info": {"name": kernelspec_lang}}
    for kind, src in cells:
        book.cells.append(nbf.v4.new_markdown_cell(src) if kind == "md"
                          else nbf.v4.new_code_cell(src))
    return book


SETUP = """\
import sys, pathlib
# repo-root relative imports so the notebook runs from anywhere
ROOT = next(p for p in pathlib.Path.cwd().parents if (p / 'edu' / 'sl_edu').exists()) \\
       if not (pathlib.Path.cwd() / 'edu' / 'sl_edu').exists() else pathlib.Path.cwd()
sys.path.insert(0, str(ROOT / 'edu'))
import numpy as np
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = (10, 4)
DATA = ROOT / 'data'
"""

NOTEBOOKS = {}

# ---------------------------------------------------------------- nb01
NOTEBOOKS["nb01_pattern_generation.ipynb"] = nb([
    ("md", "# NB01 — Pattern Generation\n"
     "結構光嘅靈魂問題：投影儀邊一列照亮咗場景嘅呢一點？\n"
     "答案係**用光本身做編碼**：一組精心設計嘅圖案，每個 pixel 睇完就知自己俾邊列照住。\n"
     "呢課生成 SLMaster 用嘅兩種圖案：**相位平移正弦波**（亞像素精度）+ **格雷碼**（消歧義）。"),
    ("code", SETUP),
    ("md", "## 1. 相位平移正弦波（phase-shifted sinusoids）\n"
     "投影儀播 N 張正弦條紋，每張相位錯開 2π/N。相機睇同一點喺 N 張入面嘅亮度變化，\n"
     "就可以用 atan2 還原出佢喺正弦週期入面嘅**相位**（精度 ~1/100 週期）。"),
    ("code", """\
from sl_edu import patterns

imgs = patterns.generate(width=1920, height=1080, shift_time=4, n_periods=32)
print(f"{len(imgs)} patterns: 4 phase + 5 gray")

fig, axes = plt.subplots(1, 3, figsize=(14, 4))
for k, ax in zip(range(3), axes):
    ax.imshow(imgs[k], cmap='gray', vmin=0, vmax=255)
    ax.set_title(f'phase shift {k}/4'); ax.axis('off')
plt.show()

# 一個週期入面嘅亮度曲線（row 540, 頭 120 列）
for k in range(4):
    plt.plot(imgs[k][540, :120], label=f'I{k}')
plt.legend(); plt.xlabel('projector column'); plt.ylabel('intensity')
plt.title('4-step phase shift'); plt.show()"""),
    ("md", "## 2. 格雷碼（Gray code）\n"
     "相位只話到「週期內第幾」，唔知「第幾個週期」。格雷碼用 ⌈log₂(32)⌉=5 張黑白圖\n"
     "俾每個週期一個 5-bit 門牌號碼。關鍵性質：**相鄰週期只差 1 bit**，邊界誤判最多錯一格。\n"
     "SLMaster 仲會將格雷碼平移半個週期（「shift」），令佢嘅邊界避開正弦波嘅 wrap 邊界——\n"
     "兩套編碼嘅危險位永遠唔重疊。"),
    ("code", """\
fig, axes = plt.subplots(1, 5, figsize=(16, 3))
for k, ax in enumerate(axes):
    ax.imshow(imgs[4 + k], cmap='gray', vmin=0, vmax=255)
    ax.set_title(f'gray bit {k} (MSB first)'); ax.axis('off')
plt.show()

# 解讀 row 540：邊度係週期邊界？
bits = np.stack([(imgs[4 + k][540] > 128) for k in range(5)], axis=-1)
gray_val = np.zeros(1920, int)
for k in range(5):
    gray_val = (gray_val << 1) | bits[..., k]
plt.plot(gray_val[:400]); plt.xlabel('column'); plt.ylabel('raw gray value')
plt.title('MSB-first accumulation (before gray->binary XOR)'); plt.show()"""),
    ("md", "## 3. 點解兩樣都要？\n"
     "- **淨相位**：精度高但 2π 歧義（32 個週期全部一樣樣）\n"
     "- **淨格雷碼**：冇歧義但精度得 1 個週期（60 px ≈ 幾 mm 深度誤差）\n"
     "- **合體**：格雷碼話你知邊個週期，相位話你知週期內位置 → 高精度 + 冇歧義\n"
     "\n下一課：相機實際影到嘅係點？（capture & simulation）"),
])

# ---------------------------------------------------------------- nb02
NOTEBOOKS["nb02_capture_and_simulation.ipynb"] = nb([
    ("md", "# NB02 — Capture & the Virtual Pipeline\n"
     "真實系統入面，相機要同投影儀**同步**：每播一張圖案影一張相。\n"
     "工業方案用硬件觸發線（µs 級）；我哋嘅 universal pipeline 用**時間協議**：\n"
     "每張圖案播 ≥16.7ms（60Hz refresh floor），相機連續影，事後對齊。\n"
     "呢課先用 repo 入面嘅真實捕捉數據集做實驗，再用 virtual 模式模擬成個 loop。"),
    ("code", SETUP),
    ("md", "## 1. 真實數據集：`data/shiftGraycode`\n"
     "呢 9 張相係真相機影真場景（4 相位 + 5 格雷），同 C++ test 用嘅係同一批。"),
    ("code", """\
from sl_edu import oracle

imgs = oracle.load_shift_graycode(ROOT)
print(f"{len(imgs)} images, {imgs[0].shape[1]}x{imgs[0].shape[0]}")

fig, axes = plt.subplots(3, 3, figsize=(12, 10))
for k, ax in enumerate(axes.flat):
    ax.imshow(imgs[k], cmap='gray', vmin=0, vmax=255)
    ax.set_title(f'img {k}' + (' (phase)' if k < 4 else f' (gray bit {k-4})'))
    ax.axis('off')
plt.tight_layout(); plt.show()"""),
    ("md", "留意：相位圖（頭 4 張）睇落似漸變斜坡，格雷圖（後 5 張）係黑白塊。\n"
     "場景入面嘅物體令條紋變形——**變形量就係深度資訊**。"),
    ("md", "## 2. 信心圖（confidence map）\n"
     "邊啲 pixel 信得過？SLMaster 用 4 張相位圖嘅**平均亮度**做信心：\n"
     "太暗（陰影/黑面）或太光（反光飽和）嘅 pixel 喺 decode 時會被丟棄。"),
    ("code", """\
from sl_edu import decode

conf = decode.confidence_map(imgs[:4])
plt.imshow(conf, cmap='hot'); plt.colorbar(label='mean intensity')
plt.title('confidence map'); plt.show()
print(f'pixels above threshold 5: {np.mean(conf > 5):.1%}')"""),
    ("md", "## 3. Virtual projector loop（冇硬件都玩到）\n"
     "C++ Phase 3 加咗 `SLMASTER_MONITOR_VIRTUAL=1`；Python 版一樣有 virtual 模式。\n"
     "下面個 projector 真係逐張「播」（只係冇 window），timing 行真實 refresh floor。"),
    ("code", """\
import time
from sl_edu import backends, patterns

pats = patterns.generate(640, 480, shift_time=4, n_periods=8)
proj = backends.PyMonitorProjector(exposure_ms=20, virtual=True)
proj.set_patterns(pats)
proj.project()

seen = []
t0 = time.time()
while time.time() - t0 < 0.35:
    if proj.current_pattern not in seen:
        seen.append(proj.current_pattern)
    time.sleep(0.005)
proj.stop()
print('patterns displayed in order:', seen)
print('-> 成個序列循環播，每張 ≥16.7ms，直到 pause/stop')"""),
    ("md", "## 4. 相機端：image-sequence 後端\n"
     "我哋嘅 `PyOpenCvCamera` 支援 `dir/%d.bmp` 模式——將數據集當成「相機」重播。"),
    ("code", """\
cam = backends.PyOpenCvCamera(str(DATA / 'shiftGraycode' / '%d.bmp'))
assert cam.open(), 'sequence open failed'
cam.start()
frames = cam.capture(9, timeout_s=10)
cam.stop()
print(f'captured {len(frames)} frames via the camera backend')
print('frame 0 identical to direct load:',
      np.array_equal(frames[0], imgs[0]))"""),
    ("md", "下一課：decode——由 9 張灰階圖還原每個 pixel 嘅絕對相位。"),
])

# ---------------------------------------------------------------- nb03
NOTEBOOKS["nb03_phase_decoding.ipynb"] = nb([
    ("md", "# NB03 — Phase Decoding（成個系統嘅心臟）\n"
     "由捕捉返嚟嘅 9 張圖，逐步還原**絕對相位圖**：每個 pixel 一個數，\n"
     "直接話你知佢俾投影儀邊一列照住。呢個係成條 pipeline 最精密嘅部分。\n"
     "本課每步都同 C++ 實作 pixel-exact 對照（用 gtest 入面嘅 golden values）。"),
    ("code", SETUP),
    ("md", "## Step 1: wrapped phase（相位主值）\n"
     "$$\\phi = -\\operatorname{atan2}\\Big(\\sum_k I_k\\sin\\tfrac{2\\pi k}{N},\\ \\sum_k I_k\\cos\\tfrac{2\\pi k}{N}\\Big)$$\n"
     "N=4 步相位平移 → 每個 pixel 一個 [−π, π] 嘅相位（鋸齒波，每週期 reset）。"),
    ("code", """\
from sl_edu import decode, oracle

imgs = oracle.load_shift_graycode(ROOT)
wrapped = decode.wrapped_phase(imgs[:4], shift_time=4)
conf = decode.confidence_map(imgs[:4])

plt.imshow(wrapped, cmap='twilight', vmin=-np.pi, vmax=np.pi)
plt.colorbar(label='wrapped phase (rad)'); plt.title('wrapped phase'); plt.show()

plt.plot(wrapped[540, 400:640])
plt.ylabel('phase (rad)'); plt.xlabel('column')
plt.title('sawtooth: wraps from +pi to -pi at each period boundary'); plt.show()"""),
    ("md", "## Step 2: gray code → floor map\n"
     "格雷碼俾每個 pixel 一個「週期門牌」：binary 解碼用 running XOR（MSB 先行）。\n"
     "但格雷邊界（中週期）同相位 wrap 邊界（週期頭）唔對齊——需要修正：\n"
     "- 每個 floor 區域搵 |φ| 最接近 π 嘅列 = 真正週期邊界 `mid`\n"
     "- `(|φ| < 2π/3 且 j < mid) 或 φ ≥ 2π/3` → floor 減 1"),
    ("code", """\
floor_map = decode.floor_map(imgs[4:], conf, wrapped, n_periods=32, threshold=5.0)

plt.imshow(floor_map, cmap='viridis'); plt.colorbar(label='period index')
plt.title('floor map (which period)'); plt.show()

# 驗證同 C++ 一致（gtest golden values, threshold=70）
floor70 = decode.floor_map(imgs[4:], conf, wrapped, 32, 70.0)
assert floor70[453][700] == 17, 'C++ golden value mismatch!'
print('C++ golden anchor floor[453][700]==17  ->  Python matches')"""),
    ("md", "## Step 3: unwrap\n"
     "$$\\Phi = \\phi_{wrapped} + 2\\pi\\cdot floor + \\pi$$\n"
     "+π 係將範圍平移到由 0 開始（同 C++ 一致）。低信心 pixel → 0（無效）。"),
    ("code", """\
absolute = decode.unwrap(wrapped, floor_map, conf, threshold=5.0)

plt.imshow(absolute, cmap='inferno'); plt.colorbar(label='absolute phase (rad)')
plt.title('absolute phase = projector column address'); plt.show()

# 另一個 C++ golden anchor（threshold=70）
abs70 = decode.unwrap(wrapped, floor70, conf, 70.0)
assert abs(abs70[460][653] - 103.75) <= 0.1
print(f'C++ golden anchor unwrap[460][653]=103.75  ->  Python {abs70[460][653]:.3f}')"""),
    ("md", "## 教學位：wrap 邊界嘅 ±1px tie\n"
     "喺相位啱啱 = π 嘅邊界列，atan2 個分子數值上係零，正負由 uint8 量化決定——\n"
     "等於擲毫。C++ 同 Python 喺呢啲列可以差 1px floor。**唔係 bug，係數值本質**。\n"
     "（我哋嘅 test 特登放寬呢一格，仲註明咗原因。）\n"
     "\n## 右邊緣 artifact\n"
     "平移格雷碼會 wrap-around：最後 30 列解到做第 0 週期。C++ 一樣有。\n"
     "實戰上 crop 邊緣或靠 confidence/disparity 過濾。\n"
     "\n下一課：標定——部相機同投影儀點樣「認識」彼此。"),
])

# ---------------------------------------------------------------- nb04
NOTEBOOKS["nb04_calibration.ipynb"] = nb([
    ("md", "# NB04 — Calibration（教相機同投影儀認識彼此）\n"
     "三角化需要知道：相機內參 (K, dist)、投影儀內參、同佢哋之間嘅 (R, T)。\n"
     "做法：影一堆已知幾何嘅標定板（chessboard），cv2 幫手解。\n"
     "投影儀嘅標定用一個絕妙 trick：**當佢係第二部相機**——播圖案落標定板，\n"
     "decode 出每個角點對應嘅投影儀列 = 「投影儀睇到嘅影像」。"),
    ("code", SETUP),
    ("md", "## 1. 合成標定板（可控實驗）\n"
     "先用虛擬相機渲染 chessboard 視圖——ground truth 已知，可以驗證標定質素。"),
    ("code", """\
import cv2
from sl_edu import calibrate

board = (9, 6)          # inner corners
sq = 25.0               # mm per square
K_true = np.array([[525., 0, 320], [0, 525., 240], [0, 0, 1]])
size = (640, 480)

views = [(np.array([0.1,0.1,0.05]), np.array([0.,0.,600.])),
         (np.array([-0.15,0.1,0.2]), np.array([30.,-20.,650.])),
         (np.array([0.2,-0.1,-0.15]), np.array([-40.,10.,550.])),
         (np.array([0.,0.2,0.1]), np.array([10.,30.,700.]))]

objp = np.zeros((board[0]*board[1], 3), np.float32)
objp[:, :2] = np.mgrid[0:board[0], 0:board[1]].T.reshape(-1, 2) * sq

img_points = []
for rvec, tvec in views:
    pts, _ = cv2.projectPoints(objp, rvec, tvec, K_true, np.zeros(5))
    img_points.append(pts.reshape(-1, 1, 2).astype(np.float32))
print(f'{len(img_points)} synthetic views rendered')"""),
    ("md", "## 2. calibrateCamera：由多視圖解內參"),
    ("code", """\
cal = calibrate.calibrate_camera(objp, img_points, size)
print(f"RMS reprojection error: {cal['rms']:.4f} px")
print(f"fx: true 525.0, recovered {cal['K'][0,0]:.2f}")
print(f"cx: true 320.0, recovered {cal['K'][0,2]:.2f}")"""),
    ("md", "## 3. 真實世界嘅標定結果：`caliInfo.yml`\n"
     "repo 入面有呢台真實 rig（1280×1024 相機 + 投影儀）嘅完整標定。\n"
     "生產系統用**同心環標定板**（中心定位比 chessboard 角點更穩）——\n"
     "原理一樣，角點檢測換咗做 ring centroid（見 `src/calibration/`）。"),
    ("code", """\
fs = cv2.FileStorage(str(DATA / 'monocularCamera' / 'caliInfo.yml'),
                     cv2.FILE_STORAGE_READ)
calib = {k: fs.getNode(k).mat() for k in ('M1', 'D1', 'M4', 'D4', 'Rlp', 'Tlp')}
fs.release()

print('camera K (M1):'); print(np.round(calib['M1'], 1))
print('projector K (M4):'); print(np.round(calib['M4'], 1))
print(f"baseline |T| = {np.linalg.norm(calib['Tlp']):.1f} mm")
print(f"camera resolution: {DATA/'monocularCamera'/'L'} has",
      len(list((DATA/'monocularCamera'/'L').glob('*.bmp'))), 'calibration views')"""),
    ("md", "留意 T 嘅模 ≈ 108mm——就係相機同投影儀嘅**基線距離**。\n"
     "基線越長深度越準，但遮擋越多；呢個係硬件設計嘅 fundamental trade-off。\n"
     "\n下一課：齊料！decode + 標定 → 真。三角化 → 3D 點雲。"),
])

# ---------------------------------------------------------------- nb05
NOTEBOOKS["nb05_triangulation_pointcloud.ipynb"] = nb([
    ("md", "# NB05 — Triangulation → Point Cloud（收成課）\n"
     "到而家我哋有：絕對相位圖（nb03）+ 完整標定（nb04）。\n"
     "每個相機 pixel 給出一條**射線**，絕對相位給出投影儀嘅一個**平面**——\n"
     "射線 ∩ 平面 = 3D 點。C++ 叫呢步 `reverseCamera`：逐 pixel 解 3×3 線性系統。"),
    ("code", SETUP),
    ("md", "## 1. 解碼真實掃描數據"),
    ("code", """\
import cv2
from sl_edu import decode, oracle, reconstruct

imgs = oracle.load_shift_graycode(ROOT)
wrapped, conf, absolute = oracle.decode_all(imgs)
print(f'absolute phase decoded: {np.count_nonzero(absolute):,} valid pixels')"""),
    ("md", "## 2. 載入標定 + 組投影矩陣\n"
     "$$P_L = K_{cam}[I|0],\\quad P_R = K_{proj}[R^T\\ |\\ -R^T T]$$\n"
     "（世界座標 = 相機座標；caliInfo 嘅 Rlp/Tlp 係 camera→projector，所以用逆。）"),
    ("code", """\
fs = cv2.FileStorage(str(DATA / 'monocularCamera' / 'caliInfo.yml'),
                     cv2.FILE_STORAGE_READ)
M1, D1 = fs.getNode('M1').mat(), fs.getNode('D1').mat()
M4, D4 = fs.getNode('M4').mat(), fs.getNode('D4').mat()
Rlp, Tlp = fs.getNode('Rlp').mat(), fs.getNode('Tlp').mat()
fs.release()

# 先將相位圖去畸變（等效於喺 normalized 相機模型下工作）
absolute_u = cv2.undistort(absolute, M1, D1)

PL = M1 @ np.hstack([np.eye(3), np.zeros((3, 1))])
PR = M4 @ np.hstack([Rlp, Tlp])   # P_proj-frame = Rlp @ P_cam + Tlp
pitch = 1920 / 32                  # projector pixels per period
print('PL:'); print(np.round(PL, 1))
print('pitch =', pitch, 'px/period')"""),
    ("md", "## 3. 逐 pixel 深度恢復\n"
     "教學版直接 double loop（C++ 都係咁，不過 parallel_for）。\n"
     "1280×1024 全圖會行幾分鐘——教學上先 crop 一個 ROI 示範，全圖留俾你行。"),
    ("code", """\
# ROI: 中央 400x400，快啲睇到結果
r0, c0, sz = 312, 440, 400
roi = absolute_u[r0:r0+sz, c0:c0+sz]

# 平移投影矩陣嘅主點，等效於 crop
PL_roi = PL.copy(); PL_roi[0, 2] -= c0; PL_roi[1, 2] -= r0

depth = reconstruct.depth_from_phase(roi, PL_roi, PR, pitch,
                                     min_depth=100, max_depth=2000)
valid = depth[depth > 0]
print(f'{valid.size:,} valid depths | median {np.median(valid):.0f} mm | '
      f'range {valid.min():.0f}..{valid.max():.0f} mm')

plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1); plt.imshow(absolute > 0, cmap='gray'); plt.title('valid mask')
plt.subplot(1, 2, 2)
plt.imshow(depth, cmap='turbo'); plt.colorbar(label='depth (mm)')
plt.title('depth map (ROI)'); plt.show()"""),
    ("md", "## 4. 點雲輸出"),
    ("code", """\
from sl_edu import reconstruct as rc

ys, xs = np.nonzero(depth)
pts_cam = np.column_stack([xs, ys]).astype(float)
z = depth[ys, xs]
# back-project with intrinsics (ROI-adjusted)
X = (xs + c0 - M1[0, 2]) * z / M1[0, 0]
Y = (ys + r0 - M1[1, 2]) * z / M1[1, 1]
cloud = np.column_stack([X, Y, z])

out = rc.save_ply(ROOT / 'edu' / 'output_scan.ply', cloud)
print(f'saved {len(cloud):,} points -> {out}')
print('open it in MeshLab / CloudCompare / open3d to inspect!')"""),
    ("md", "## 你啱啱做咗咩\n"
     "9 張灰階相 → 相位解碼 → 逐 pixel 三角化 → **真實場景嘅 3D 點雲**。\n"
     "成條 SLMaster pipeline 嘅概念核心就係咁多。C++ 版本做嘅係同一件事，\n"
     "只係快 100 倍（SIMD + parallel_for + 可選 CUDA）加埋硬件控制。\n"
     "\n下一課：用真。webcam + 芒行一次 live scan（或者繼續 virtual）。"),
])

# ---------------------------------------------------------------- nb06
NOTEBOOKS["nb06_live_scan.ipynb"] = nb([
    ("md", "# NB06 — Live Scan（webcam + monitor）\n"
     "成個課程嘅高潮：用你部機嘅 webcam + 第二個芒做真。結構光掃描。\n"
     "**冇硬件？** 冇問題——預設行 virtual 模式，成個 pipeline 照跑。\n"
     "有硬件嘅話，將下面 `HARDWARE = False` 改做 `True`。"),
    ("code", SETUP + """\
HARDWARE = False  # flip to True with a webcam + second display"""),
    ("md", "## 1. Virtual mode：成個 loop 行晒，只係冇光子出入"),
    ("code", """\
import time
from sl_edu import backends, decode, oracle, patterns

# 'projector' generates and displays; 'camera' replays the dataset
pats = patterns.generate(1920, 1080, shift_time=4, n_periods=32)
proj = backends.PyMonitorProjector(exposure_ms=20, virtual=not HARDWARE)
proj.set_patterns(pats)

cam = backends.PyOpenCvCamera(
    0 if HARDWARE else str(DATA / 'shiftGraycode' / '%d.bmp'))
assert cam.open()

proj.project()
cam.start()
time.sleep(0.3)  # let the loop settle
frames = cam.capture(9, timeout_s=10)
proj.stop(); cam.stop()

print(f'captured {len(frames)} frames while projector showed patterns')
print(f'projector was on pattern #{proj.current_pattern} when we stopped')"""),
    ("md", "## 2. Decode live capture"),
    ("code", """\
wrapped = decode.wrapped_phase(frames[:4], 4)
conf = decode.confidence_map(frames[:4])
floor_map = decode.floor_map(frames[4:], conf, wrapped, 32, 5.0)
absolute = decode.unwrap(wrapped, floor_map, conf, 5.0)

plt.figure(figsize=(12, 4))
plt.subplot(1, 2, 1); plt.imshow(wrapped, cmap='twilight'); plt.title('wrapped')
plt.subplot(1, 2, 2); plt.imshow(absolute, cmap='inferno'); plt.title('absolute')
plt.show()
print('live decode OK — same code path as nb03')"""),
    ("md", "## 3. 真硬件 checklist（`HARDWARE=True` 前）\n"
     "1. HDMI 插第二個芒，**mirror mode 關掉**（要 extended desktop）\n"
     "2. 個 projector window 拖落第二芒再 fullscreen（未實現自動定位——改 `cv2.moveWindow`）\n"
     "3. 環境光盡量暗（LCD 亮度 << DLP 燈）\n"
     "4. 場景靜止（時間協議同步，~200ms/scan）\n"
     "5. macOS：Terminal/IDE 要有相機權限（系統設定 → 私隱 → 相機）\n"
     "\n**同步嘅本質**：projector 每張 ≥16.7ms，相機連續影，\n"
     "`capture(9)` 攞最新 9 張。冇硬件握手——係「約定時間表」協議。\n"
     "工業觸發係對講機；我哋係鬧鐘。慢 100 倍，但靜態場景冇分別。\n"
     "\n下一課：同 C++ 對照——我哋寫得啱唔啱？"),
])

# ---------------------------------------------------------------- nb07
NOTEBOOKS["nb07_cpp_oracle.ipynb"] = nb([
    ("md", "# NB07 — Correctness Against the C++ Oracle\n"
     "「教學版同生產版一唔一致？」呢課答呢個問題，順便講吓兩個實作嘅差異哲學。"),
    ("code", SETUP),
    ("md", "## 1. Golden values（最強嘅對照）\n"
     "C++ gtest 對同一數據集斷言咗具體 pixel 值。Python 版行同一 decode 鏈，\n"
     "必須命中相同值——呢個係 pixel-exact 嘅跨語言對照。"),
    ("code", """\
from sl_edu import decode, oracle, patterns

imgs = oracle.load_shift_graycode(ROOT)
wrapped = decode.wrapped_phase(imgs[:4], 4)
conf = decode.confidence_map(imgs[:4])
floor70 = decode.floor_map(imgs[4:], conf, wrapped, 32, 70.0)
abs70 = decode.unwrap(wrapped, floor70, conf, 70.0)

anchors = [
    ('floor[453][700] == 17', floor70[453][700] == 17),
    ('|unwrap[460][653] - 103.75| <= 0.1', abs(abs70[460][653] - 103.75) <= 0.1),
]
gen = patterns.generate(1920, 1080, 4, 32)
anchors.append(('generated imgs[6][400][215] == 255', gen[6][400][215] == 255))

for name, ok in anchors:
    print(('PASS' if ok else 'FAIL'), '-', name)
assert all(ok for _, ok in anchors)"""),
    ("md", "## 2. 已知差異清單（全部記錄喺 tests 入面）\n"
     "| 差異 | 原因 | 處理 |\n"
     "|---|---|---|\n"
     "| wrap 邊界 ±1px | atan2 分子數值為零，uint8 量化擲毫 | test 放寬 + 註明 |\n"
     "| 右邊緣 30 列 | 平移格雷碼 wrap-around（C++ 一樣有） | 文件化，實戰 crop |\n"
     "| cv2.structured_light 比對唔上 | OpenCV 5 生成慣例同 SLMaster 唔同 | nb 討論，唔做 anchor |\n"
     "| 性能 | numpy loop vs SIMD/parallel_for/CUDA | 教學冇所謂，下面量度 |"),
    ("md", "## 3. 性能對照（教學版嘅代價）"),
    ("code", """\
import time

t0 = time.perf_counter()
_ = decode.wrapped_phase(imgs[:4], 4)
t1 = time.perf_counter()
print(f'numpy wrapped_phase (1280x1024): {(t1-t0)*1000:.0f} ms')
print('C++ equivalent: ~1 ms (SIMD) — ~100x slower here, and that is fine.')
print()
print('Takeaway: 概念正確先行，性能係工程問題。')
print('C++ 嘅存在理由 = 實時 + 硬件控制；Python 嘅存在理由 = 可讀 + 可改。')"""),
    ("md", "## 課程總結\n"
     "1. **nb01** 編碼：正弦相位 + 格雷碼，邊界錯開半週期\n"
     "2. **nb02** 捕捉：時間協議同步，virtual 模式冇硬件都跑到\n"
     "3. **nb03** 解碼：atan2 → XOR gray → 邊界修正 → unwrap\n"
     "4. **nb04** 標定：投影儀當相機教，cv2 解內外參\n"
     "5. **nb05** 三角化：射線 ∩ 平面 = 3D 點 → 點雲\n"
     "6. **nb06** live：webcam + 芒就係一台 3D 掃描儀\n"
     "7. **nb07** 對照：pixel-exact vs C++ golden values\n"
     "\n**白盒嘅價值**：每一環你都可以停低、plot、改參數、再嚟過。\n"
     "RealSense 將以上全部收埋喺一粒 ASIC——快，但你學唔到嘢。"),
])

# ---------------------------------------------------------------- write all
for name, book in NOTEBOOKS.items():
    nbf.write(book, OUT / name)
    print(f"wrote {OUT / name}")
print(f"{len(NOTEBOOKS)} notebooks generated")
