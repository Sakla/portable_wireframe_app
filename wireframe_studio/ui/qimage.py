"""numpy <-> Qt image helpers."""
import numpy as np
from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def to_qimage(array: np.ndarray) -> QImage:
    array = np.ascontiguousarray(array)
    height, width = array.shape[:2]
    if array.ndim == 2:
        fmt, bpl = QImage.Format_Grayscale8, width
    elif array.shape[2] == 3:
        fmt, bpl = QImage.Format_RGB888, width * 3
    else:
        fmt, bpl = QImage.Format_RGBA8888, width * 4
    return QImage(array.data, width, height, bpl, fmt).copy()


def checkerboard(width: int, height: int, cell: int = 8) -> QPixmap:
    pixmap = QPixmap(max(1, width), max(1, height))
    pixmap.fill(QColor("#ffffff"))
    painter = QPainter(pixmap)
    for y in range(0, height, cell):
        for x in range((y // cell % 2) * cell, width, cell * 2):
            painter.fillRect(x, y, cell, cell, QColor("#e4e4e4"))
    painter.end()
    return pixmap


def fit_size(width: int, height: int, box: int) -> tuple[int, int]:
    scale = min(box / width, box / height)
    return max(1, round(width * scale)), max(1, round(height * scale))


def thumbnail(array: np.ndarray, box: int) -> QPixmap:
    """Scaled pixmap; transparent images are shown on a checkerboard."""
    image = to_qimage(array)
    width, height = fit_size(image.width(), image.height(), box)
    scaled = image.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if array.ndim == 3 and array.shape[2] == 4:
        pixmap = checkerboard(scaled.width(), scaled.height())
        painter = QPainter(pixmap)
        painter.drawImage(0, 0, scaled)
        painter.end()
        return pixmap
    return QPixmap.fromImage(scaled)


def svg_thumbnail(svg: str, width: int, height: int, box: int) -> QPixmap:
    w, h = fit_size(width, height, box)
    pixmap = checkerboard(w, h)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode("utf-8"))).render(painter, QRectF(0, 0, w, h))
    painter.end()
    return pixmap
