"""Dataset oracles + cross-checks against OpenCV's structured_light.

The repo's data/ directory contains real captures from the C++ pipeline with
known configurations — the ground truth for verifying the Python port.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from sl_edu import decode

# Config the C++ test uses for data/shiftGraycode (testShiftGrayCodePattern.cpp)
SHIFT_GRAYCODE = dict(shift_time=4, n_periods=32, threshold=5.0,
                      horizontal=False)


def load_sequence(directory: str | Path, count: int | None = None) -> list[np.ndarray]:
    """Load 0.bmp..N.bmp grayscale from a dataset directory."""
    d = Path(directory)
    imgs = []
    i = 0
    while True:
        p = d / f"{i}.bmp"
        if not p.exists() or (count is not None and i >= count):
            break
        imgs.append(cv2.imread(str(p), cv2.IMREAD_GRAYSCALE))
        i += 1
    if not imgs:
        raise FileNotFoundError(f"no numbered .bmp sequence in {d}")
    return imgs


def load_shift_graycode(repo_root: str | Path) -> list[np.ndarray]:
    return load_sequence(Path(repo_root) / "data" / "shiftGraycode")


def decode_all(imgs: list[np.ndarray], cfg: dict | None = None):
    """Full decode chain; returns (wrapped, confidence, absolute)."""
    cfg = cfg or SHIFT_GRAYCODE
    n = cfg["shift_time"]
    conf = decode.confidence_map(imgs[:n])
    wrapped = decode.wrapped_phase(imgs[:n], n)
    floor = decode.floor_map(imgs[n:], conf, wrapped, cfg["n_periods"],
                             cfg["threshold"], cfg["horizontal"])
    absolute = decode.unwrap(wrapped, floor, conf, cfg["threshold"])
    return wrapped, conf, absolute


def cross_check_opencv(imgs: list[np.ndarray], cfg: dict | None = None
                       ) -> np.ndarray | None:
    """Reference decode via cv2.structured_light (same math lineage as the
    C++ SLMaster classes, which CV_OVERRIDE its base classes).

    Returns OpenCV's wrapped phase map, or None if contrib module missing.
    """
    if not hasattr(cv2, "structured_light"):
        return None
    cfg = cfg or SHIFT_GRAYCODE
    params = cv2.structured_light.SinusoidalPattern.Params()
    params.width = imgs[0].shape[1]
    params.height = imgs[0].shape[0]
    params.nbrOfPeriods = cfg["n_periods"]
    params.shiftValue = float(2 * np.pi / cfg["shift_time"])  # OpenCV 5 API
    params.horizontal = cfg["horizontal"]
    pat = cv2.structured_light.SinusoidalPattern.create(params)
    try:
        out = pat.computePhaseMap(imgs[: cfg["shift_time"]])
    except cv2.error:
        return None
    wrapped = out[0] if isinstance(out, tuple) else out  # (wrapped, shadowMask)
    return wrapped if wrapped.size else None
