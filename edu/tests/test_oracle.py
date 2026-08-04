from pathlib import Path

import numpy as np
import pytest

from sl_edu import oracle

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data" / "shiftGraycode"


@pytest.mark.skipif(not DATA.exists(), reason="repo dataset not present")
def test_shift_graycode_dataset_decodes():
    imgs = oracle.load_shift_graycode(REPO_ROOT)
    assert len(imgs) == 9  # 4 phase + 5 gray
    wrapped, conf, absolute = oracle.decode_all(imgs)
    # most pixels confident on this real capture
    assert np.count_nonzero(absolute) > 0.5 * absolute.size
    # absolute phase stays inside the 32-period code range
    roi = absolute[:, 60:-60]
    vals = roi[roi > 0]
    assert np.percentile(vals, 99) < 34 * 2 * np.pi
    # the map encodes projector columns -> scene structure, NOT camera
    # columns: it must vary substantially and NOT be monotonic in x
    assert vals.std() > 2 * np.pi
    thirds = np.array_split(np.median(roi, axis=0), 3)
    mono_inc = np.all(np.diff(np.median(roi, axis=0)) >= -1e-3)
    assert not mono_inc
    # wrapped phase fills [-pi, pi] (sawtooth of a real fringe)
    assert wrapped.min() < -2.5 and wrapped.max() > 2.5


@pytest.mark.skipif(not DATA.exists(), reason="repo dataset not present")
def test_opencv_cross_check_agrees():
    imgs = oracle.load_shift_graycode(REPO_ROOT)
    ref = oracle.cross_check_opencv(imgs)
    if ref is None:
        pytest.skip("cv2.structured_light unavailable")
    wrapped, conf, _ = oracle.decode_all(imgs)
    # Compare on confident pixels only; circular difference must cluster at 0
    mask = conf > 20
    diff = np.angle(np.exp(1j * (wrapped[mask] - ref[mask])))
    assert np.abs(np.median(diff)) < 0.1
    assert (np.abs(diff) < 0.3).mean() > 0.9
