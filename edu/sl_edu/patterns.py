"""Structured-light pattern generation.

Numpy port of SinusShiftGrayCodePattern::generate (C++):
phase-shifted sinusoids + gray-code bit planes.
"""
from __future__ import annotations

import numpy as np


def n_gray_bits(n_periods: int) -> int:
    bits = 0
    while (1 << bits) < n_periods:
        bits += 1
    return bits


def generate(width: int, height: int, shift_time: int = 4,
             n_periods: int = 32, horizontal: bool = False) -> list[np.ndarray]:
    """Return [phase_0..phase_{N-1}, gray_0..gray_{B-1}] uint8 images.

    Faithful port of SinusShiftGrayCodePattern::generate:
    - phase images: sawtooth phase ramp (x % P)/P*2π − π, cos with +2πk/N shift
      (fringe starts at intensity 0 to align with the gray-code interval)
    - gray images: recursive mirror sequence [0,255] -> [0,255,255,0] -> ...,
      each block width = pw/2^i, then left-rotated by half the finest block
      (== half a period) so gray edges land at period midpoints — the "shift"
      in SinusShiftGrayCode. This is what makes the decode-side edge
      correction possible.
    """
    pw = height if horizontal else width   # axis the pattern varies along
    ph = width if horizontal else height
    px_per_period = pw // n_periods
    cols = np.arange(pw, dtype=np.float64)

    imgs: list[np.ndarray] = []
    sawtooth = (cols % px_per_period) / px_per_period * 2 * np.pi - np.pi
    for k in range(shift_time):
        wave = 127.5 + 127.5 * np.cos(sawtooth + 2 * np.pi * k / shift_time)
        imgs.append(np.repeat(wave[None, :].astype(np.uint8), ph, axis=0))

    n_bits = n_gray_bits(n_periods)
    px_last_half_block = int((pw / (1 << n_bits)) / 2)
    seq = [0, 255]
    for _ in range(n_bits):
        px_per_block = pw // len(seq)
        plane = np.concatenate([np.full(px_per_block, v, np.uint8) for v in seq])
        plane = np.roll(plane, -px_last_half_block)  # left-rotate by half period
        imgs.append(np.repeat(plane[None, :], ph, axis=0))
        seq = seq + seq[::-1]                        # mirror-extend

    if horizontal:
        imgs = [im.T.copy() for im in imgs]
    return imgs
