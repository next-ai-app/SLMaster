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


def test_gray_bit_planes_are_binary():
    imgs = patterns.generate(1920, 1080, 4, 32, False)
    for im in imgs[4:]:
        assert set(np.unique(im).tolist()) <= {0, 255}
