"""Trace a transparent black line image into one SVG path (like Figma's Tracer plugin)."""
import numpy as np
import potrace


def _fmt(value: float) -> str:
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return "0" if text == "-0" else text


def _pt(point) -> str:
    return f"{_fmt(point.x)},{_fmt(point.y)}"


def trace_to_svg(rgba: np.ndarray, smoothness: float = 1.0, turdsize: int = 2) -> str:
    """Return SVG text with a single even-odd filled path covering the opaque pixels.

    smoothness maps to potrace's alphamax: 0 = sharp polygons, 1.334 = very round.
    """
    height, width = rgba.shape[:2]
    mask = rgba[..., 3] > 127
    commands = []
    if mask.any():
        # potracer treats True as white and inverts internally, so pass the background.
        plist = potrace.Bitmap(~mask).trace(
            turdsize=turdsize, alphamax=smoothness, opticurve=True, opttolerance=0.2
        )
        for curve in plist:
            commands.append(f"M{_pt(curve.start_point)}")
            for segment in curve.segments:
                if segment.is_corner:
                    commands.append(f"L{_pt(segment.c)}L{_pt(segment.end_point)}")
                else:
                    commands.append(
                        f"C{_pt(segment.c1)} {_pt(segment.c2)} {_pt(segment.end_point)}"
                    )
            commands.append("Z")
    d = "".join(commands)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        f'<path d="{d}" fill="#000000" fill-rule="evenodd"/></svg>\n'
    )
