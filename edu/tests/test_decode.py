import numpy as np

from sl_edu import decode, patterns


def _roundtrip(width=1920, height=1080):
    imgs = patterns.generate(width, height, shift_time=4, n_periods=32,
                             horizontal=False)
    conf = decode.confidence_map(imgs[:4])
    wrapped = decode.wrapped_phase(imgs[:4], shift_time=4)
    floor = decode.floor_map(imgs[4:], conf, wrapped, n_periods=32,
                             threshold=5.0, horizontal=False)
    absolute = decode.unwrap(wrapped, floor, conf, threshold=5.0)
    return absolute


def test_confidence_is_mean():
    a = np.full((4, 4), 100, np.uint8)
    b = np.full((4, 4), 200, np.uint8)
    conf = decode.confidence_map([a, b])
    assert np.allclose(conf, 150.0)


def test_wrapped_phase_range():
    imgs = patterns.generate(640, 480, 4, 32, False)
    wrapped = decode.wrapped_phase(imgs[:4], 4)
    assert wrapped.min() >= -np.pi and wrapped.max() <= np.pi


def test_decode_roundtrip_identity():
    """Identity projection: generated patterns 'captured' as-is must decode
    to a monotonically increasing absolute phase along the stripe axis."""
    absolute = _roundtrip()
    # Crop one period on each side: the shifted gray code wraps at the right
    # edge (rotation artifact, present in the C++ impl too) -> last half-period
    # decodes to floor 0. Real captures exclude edges via confidence/ROI.
    mid = absolute[540, 60:-60]
    valid = mid[mid > 0]
    assert np.all(np.diff(valid) >= -1e-4)
    # span nearly the full 32 periods (2*pi each)
    assert valid.max() - valid.min() > 0.9 * 32 * 2 * np.pi


def test_unwrap_zeroes_low_confidence():
    wrapped = np.zeros((2, 2), np.float32)
    floor = np.ones((2, 2), np.int32)
    conf = np.array([[0.0, 10.0], [0.0, 10.0]])
    out = decode.unwrap(wrapped, floor, conf, threshold=5.0)
    assert out[0, 0] == 0.0 and out[0, 1] > 0.0
