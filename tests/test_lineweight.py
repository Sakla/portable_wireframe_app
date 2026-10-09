import cv2
import numpy as np

from wireframe_studio.core.lineweight import apply_line_weight


def _thick_line_image():
    img = np.full((100, 100), 255, np.uint8)
    cv2.line(img, (10, 50), (90, 50), 0, thickness=9)
    return img


def _stroke_width(img):
    ink = (img < 128).astype(np.uint8)
    dist = cv2.distanceTransform(ink, cv2.DIST_L2, 5)
    return dist.max() * 2


def test_weight_one_gives_single_pixel_line():
    out = apply_line_weight(_thick_line_image(), 1)
    column = out[:, 50]
    assert (column < 128).sum() == 1


def test_weight_four_gives_four_pixel_line():
    out = apply_line_weight(_thick_line_image(), 4)
    assert (out[:, 50] < 128).sum() == 4


def test_weight_three_on_thin_input_thickens():
    img = np.full((100, 100), 255, np.uint8)
    cv2.line(img, (10, 50), (90, 50), 0, thickness=1)
    out = apply_line_weight(img, 3)
    assert (out[:, 50] < 128).sum() == 3
    assert 2 <= _stroke_width(out) <= 4


def test_natural_returns_input_unchanged():
    img = _thick_line_image()
    img[0, 0] = 120
    out = apply_line_weight(img, None)
    assert (out == img).all()


def test_threshold_decides_what_counts_as_a_line():
    img = np.full((50, 50), 255, np.uint8)
    img[25, 5:45] = 190  # light grey line
    assert (apply_line_weight(img, 1, threshold=200) < 128).any()
    assert not (apply_line_weight(img, 1, threshold=150) < 128).any()


def test_output_is_binary_white_background():
    out = apply_line_weight(_thick_line_image(), 2)
    assert set(np.unique(out)) == {0, 255}
    assert out[0, 0] == 255
