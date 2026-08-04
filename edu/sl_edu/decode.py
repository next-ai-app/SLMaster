"""Phase decoding chain (numpy port of SinusShiftGrayCodePattern decode).

C++ reference semantics (src/algorithm/cpuStructuredLight/sinusShiftGraycodePattern.cpp):
- confidence  = mean of the N phase-shift images
- wrapped     = -atan2( Σ I_k sin(2πk/N), Σ I_k cos(2πk/N) ), clamped to [-π, π]
- floor       = gray→binary via running XOR (MSB first), then period-edge correction
- unwrapped   = wrapped + 2π·floor + π   (confident pixels only; 0 otherwise)
"""
from __future__ import annotations

import numpy as np


def confidence_map(phase_imgs: list[np.ndarray]) -> np.ndarray:
    """Mean intensity of the N phase-shift images (matches C++ impl)."""
    acc = np.zeros(phase_imgs[0].shape, dtype=np.float64)
    for im in phase_imgs:
        acc += im.astype(np.float64)
    return acc / len(phase_imgs)


def wrapped_phase(phase_imgs: list[np.ndarray], shift_time: int) -> np.ndarray:
    stack = np.stack([im.astype(np.float64) for im in phase_imgs[:shift_time]])
    w = 2 * np.pi * np.arange(shift_time) / shift_time
    molecules = (stack * np.sin(w)[:, None, None]).sum(axis=0)
    denominator = (stack * np.cos(w)[:, None, None]).sum(axis=0)
    phase = -np.arctan2(molecules, denominator)
    return np.clip(phase, -np.pi, np.pi).astype(np.float32)


def floor_map(gray_imgs: list[np.ndarray], confidence: np.ndarray,
              wrapped: np.ndarray, n_periods: int, threshold: float,
 horizontal: bool = False) -> np.ndarray:
    """Gray->binary (running XOR, MSB first), then period-edge correction.

    Vertical-stripe correction (horizontal=False) is implemented; the
    horizontal case is handled by transposing in and out.

    Known edge artifact (inherited from C++): the gray-code images are
    left-rotated by half a period, so the LAST half-period of columns wraps
    around to gray code 0 -> floor 0 there. Callers should treat the outer
    ~1 period of columns as unreliable (real pipelines do via ROI/confidence).
    """
    if horizontal:
        flip = [im.T for im in gray_imgs]
        return floor_map(flip, confidence.T, wrapped.T, n_periods,
                         threshold, False).T

    bits = [(im > confidence).astype(np.uint32) for im in gray_imgs]
    cur = np.zeros_like(bits[0])
    tmp = np.zeros_like(bits[0])
    for b in bits:
        tmp ^= b
        cur = (cur << 1) + tmp
    floor = np.where(cur >= n_periods, 0, cur).astype(np.int32)

    confident = confidence > threshold
    cost_all = np.abs(np.abs(wrapped) - np.pi)
    cols = np.arange(floor.shape[1])[None, :]

    # Per period k, find the column whose |wrapped| is closest to π
    # (the period's "middle"), then re-assign borderline pixels.
    for k in range(1, n_periods):
        sel = (floor == k) & confident
        if not sel.any():
            continue
        cost = np.where(sel, cost_all, np.inf)
        mid = np.argmin(cost, axis=1)[:, None]
        has_sel = sel.any(axis=1)[:, None]
        dec = ((np.abs(wrapped) < 2 * np.pi / 3) & (cols < mid)) | \
              (wrapped >= 2 * np.pi / 3)
        floor = np.where(sel & dec & has_sel, floor - 1, floor)
    return floor


def unwrap(wrapped: np.ndarray, floor: np.ndarray,
           confidence: np.ndarray, threshold: float) -> np.ndarray:
    out = np.where(confidence > threshold,
                   wrapped + 2 * np.pi * floor + np.pi, 0.0)
    return out.astype(np.float32)
