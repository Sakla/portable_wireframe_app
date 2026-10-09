import xml.etree.ElementTree as ET

import cv2
import numpy as np

from wireframe_studio.core.cleanup import remove_background
from wireframe_studio.core.vectorize import trace_to_svg

SVG_NS = "{http://www.w3.org/2000/svg}"


def _ring_rgba():
    gray = np.full((120, 160), 255, np.uint8)
    cv2.circle(gray, (80, 60), 40, 0, thickness=10)
    return remove_background(gray, 200)


def _paths(svg):
    root = ET.fromstring(svg)
    return root, root.findall(f".//{SVG_NS}path")


def test_svg_has_single_black_evenodd_path_and_image_viewbox():
    root, paths = _paths(trace_to_svg(_ring_rgba()))
    assert root.get("viewBox") == "0 0 160 120"
    assert root.get("width") == "160" and root.get("height") == "120"
    assert len(paths) == 1
    assert paths[0].get("fill") == "#000000"
    assert paths[0].get("fill-rule") == "evenodd"


def test_ring_keeps_its_hole():
    _, paths = _paths(trace_to_svg(_ring_rgba()))
    assert paths[0].get("d").count("M") == 2


def test_coordinates_stay_inside_image():
    _, paths = _paths(trace_to_svg(_ring_rgba()))
    nums = [float(t) for t in paths[0].get("d").replace("M", " ").replace("C", " ")
            .replace("L", " ").replace("Z", " ").replace(",", " ").split()]
    xs, ys = nums[0::2], nums[1::2]
    # Bezier control points may overshoot the ring slightly.
    assert min(xs) >= 25 and max(xs) <= 135
    assert min(ys) >= 5 and max(ys) <= 115


def test_empty_image_gives_valid_svg():
    rgba = np.zeros((10, 20, 4), np.uint8)
    _, paths = _paths(trace_to_svg(rgba))
    assert len(paths) == 1 and paths[0].get("d") == ""
