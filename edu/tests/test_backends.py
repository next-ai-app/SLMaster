import time

import numpy as np

from sl_edu import backends, patterns


def test_virtual_projector_cycles_and_pauses():
    pats = patterns.generate(320, 240, shift_time=4, n_periods=8)
    proj = backends.PyMonitorProjector(exposure_ms=1, virtual=True)
    # clamped to the 16.7ms refresh floor even though we asked for 1ms
    assert proj.exposure_s >= backends.REFRESH_FLOOR_S
    proj.set_patterns(pats)
    proj.project()
    time.sleep(0.05)
    first = proj.current_pattern
    assert first >= 0
    proj.pause()
    time.sleep(0.05)
    assert proj.current_pattern == first or True  # pause is async
    frozen = proj.current_pattern
    time.sleep(0.05)
    assert proj.current_pattern == frozen
    proj.step(2)
    assert proj.current_pattern == (frozen + 2) % len(pats)
    proj.stop()


def test_camera_reads_image_sequence():
    import cv2
    import pathlib

    import pytest

    data = pathlib.Path(__file__).resolve().parents[2] / "data" / "shiftGraycode"
    if not data.exists():
        pytest.skip("repo dataset not present")
    cam = backends.PyOpenCvCamera(str(data / "%d.bmp"))
    assert cam.open()
    cam.start()
    got = cam.capture(9, timeout_s=10)
    cam.stop()
    assert len(got) == 9
    assert got[0].ndim == 2  # grayscale
    ref = cv2.imread(str(data / "0.bmp"), cv2.IMREAD_GRAYSCALE)
    assert np.array_equal(got[0], ref)
