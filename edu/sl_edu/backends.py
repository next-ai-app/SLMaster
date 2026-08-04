"""Live hardware backends — Python ports of the C++ universal backends.

- PyOpenCvCamera: cv2.VideoCapture capture loop (webcam / video / image seq)
- PyMonitorProjector: fullscreen pattern display with a refresh-rate floor,
  plus a headless "virtual" mode for CI/teaching without hardware.

These mirror src/device/camera/module/opencv_camera and
src/device/projector/module/monitor_projector (Phase 3, commit 445654e).
"""
from __future__ import annotations

import threading
import time
from collections import deque

import cv2
import numpy as np

REFRESH_FLOOR_S = 1 / 60  # 16.7ms — a displayed frame survives a refresh cycle


class PyOpenCvCamera:
    """Continuous-stream camera feeding a thread-safe frame queue."""

    def __init__(self, source=0, to_gray: bool = True, max_queue: int = 64):
        """source: int (device index), path to video, or 'dir/%d.bmp' pattern."""
        self.source = source
        self.to_gray = to_gray
        self.frames: deque[np.ndarray] = deque(maxlen=max_queue)
        self._cap: cv2.VideoCapture | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.source)
        return self._cap.isOpened()

    def start(self):
        assert self._cap is not None, "call open() first"
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            ok, img = self._cap.read()
            if not ok:
                self._running = False  # video/sequence exhausted
                break
            if self.to_gray and img.ndim == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            self.frames.append(img)

    def capture(self, n: int, timeout_s: float = 5.0) -> list[np.ndarray]:
        """Wait until n frames have accumulated; returns the newest n."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if len(self.frames) >= n:
                return list(self.frames)[-n:]
            time.sleep(0.01)
        raise TimeoutError(f"only {len(self.frames)} frames in {timeout_s}s")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if self._cap:
            self._cap.release()


class PyMonitorProjector:
    """Pattern display loop with refresh floor; virtual mode = no window."""

    def __init__(self, exposure_ms: float = 20.0, virtual: bool = False):
        self.exposure_s = max(exposure_ms / 1000.0, REFRESH_FLOOR_S)
        if exposure_ms / 1000.0 < REFRESH_FLOOR_S:
            print(f"[projector] exposure clamped to {REFRESH_FLOOR_S*1000:.1f}ms "
                  "(display refresh floor)")
        self.virtual = virtual
        self.current_pattern: int = -1
        self._patterns: list[np.ndarray] = []
        self._running = False
        self._paused = False
        self._thread: threading.Thread | None = None

    def set_patterns(self, patterns: list[np.ndarray]):
        self._patterns = list(patterns)

    def project(self, blocking: bool = False):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        if blocking:
            self._thread.join()

    def _loop(self):
        while self._running:
            for i, pat in enumerate(self._patterns):
                if not self._running:
                    return
                while self._paused:
                    time.sleep(0.01)
                self.current_pattern = i
                if not self.virtual:
                    cv2.imshow("sl_edu projector", pat)
                    cv2.waitKey(1)
                time.sleep(self.exposure_s)
            # continuous projection loops forever until pause/stop

    def pause(self):
        self._paused = True

    def resume(self):
        self._paused = False

    def step(self, n: int = 1):
        """Advance n patterns while paused (single-step debugging)."""
        self._paused = True
        if self._patterns:
            self.current_pattern = (self.current_pattern + n) % len(self._patterns)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
        if not self.virtual:
            cv2.destroyAllWindows()
