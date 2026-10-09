import numpy as np

from wireframe_studio.core.cleanup import remove_background, to_line_map


def _antialiased_line():
    img = np.full((40, 40), 255, np.uint8)
    img[:, 18] = 180  # grey anti-aliasing fringe
    img[:, 19] = 0
    img[:, 20] = 0
    img[:, 21] = 230  # light fringe, above threshold
    return img


def test_remove_background_has_only_two_pixel_states():
    rgba = remove_background(_antialiased_line(), threshold=200)
    assert rgba.shape == (40, 40, 4)
    assert set(np.unique(rgba[..., 3])) == {0, 255}
    opaque = rgba[..., 3] == 255
    assert (rgba[opaque][:, :3] == 0).all()


def test_remove_background_threshold_boundary():
    rgba = remove_background(_antialiased_line(), threshold=200)
    alpha = rgba[0, :, 3]
    assert alpha[18] == 255  # 180 < 200 -> black
    assert alpha[19] == 255
    assert alpha[21] == 0  # 230 >= 200 -> transparent
    assert alpha[0] == 0


def test_remove_background_accepts_rgb_and_rgba():
    gray = _antialiased_line()
    rgb = np.dstack([gray] * 3)
    rgba_in = np.dstack([gray] * 3 + [np.full_like(gray, 255)])
    assert (remove_background(rgb, 200) == remove_background(gray, 200)).all()
    assert (remove_background(rgba_in, 200) == remove_background(gray, 200)).all()


def test_remove_background_treats_transparent_input_as_background():
    rgba_in = np.zeros((10, 10, 4), np.uint8)  # fully transparent black
    out = remove_background(rgba_in, 200)
    assert (out[..., 3] == 0).all()


def test_to_line_map_inverts_dark_background():
    dark = np.zeros((20, 20), np.uint8)
    dark[5, :] = 255  # white line on black
    out = to_line_map(dark)
    assert out[0, 0] == 255 and out[5, 0] == 0


def test_to_line_map_keeps_white_background():
    light = np.full((20, 20), 255, np.uint8)
    light[5, :] = 0
    assert (to_line_map(light) == light).all()
