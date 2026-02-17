"""Generate application icon: shield + document motif.

Creates icon PNGs at 16, 32, 48, 256, 512 sizes and a Windows ICO file.
Run with: poetry run python scripts/generate_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    try:
        from PySide6.QtCore import QRect, QSize, Qt
        from PySide6.QtGui import (
            QColor,
            QFont,
            QImage,
            QPainter,
            QPainterPath,
            QPen,
        )
    except ImportError:
        print("PySide6 required. Install with: poetry install --extras gui")
        sys.exit(1)

    # Need QGuiApplication for font metrics
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    out_dir = Path(__file__).parent.parent / "gdpr_pseudonymizer" / "gui" / "resources" / "icons"
    out_dir.mkdir(parents=True, exist_ok=True)

    sizes = [16, 32, 48, 256, 512]
    images = []

    for size in sizes:
        img = _render_icon(size)
        img.save(str(out_dir / f"icon_{size}.png"))
        images.append((size, img))
        print(f"  Generated icon_{size}.png")

    # Generate ICO (Windows) — use 16, 32, 48, 256
    _save_ico(
        [img for s, img in images if s in (16, 32, 48, 256)],
        out_dir / "app.ico",
    )
    print(f"  Generated app.ico")

    print("Icon generation complete.")


def _render_icon(size: int) -> "QImage":
    """Render the icon at a given size."""
    from PySide6.QtCore import QPoint, QRect, QRectF, Qt
    from PySide6.QtGui import (
        QColor,
        QFont,
        QImage,
        QLinearGradient,
        QPainter,
        QPainterPath,
        QPen,
    )

    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)

    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = max(1, size // 16)
    s = size - margin * 2

    # Shield shape (rounded rect with pointed bottom)
    shield = QPainterPath()
    cx = size / 2
    top = margin
    bot = size - margin
    left = margin
    right = size - margin
    shield_h = s * 0.65

    shield.moveTo(left + s * 0.15, top)
    shield.lineTo(right - s * 0.15, top)
    shield.quadTo(right, top, right, top + s * 0.15)
    shield.lineTo(right, top + shield_h)
    shield.quadTo(right, top + shield_h + s * 0.15, cx, bot)
    shield.quadTo(left, top + shield_h + s * 0.15, left, top + shield_h)
    shield.lineTo(left, top + s * 0.15)
    shield.quadTo(left, top, left + s * 0.15, top)

    # Fill with gradient
    gradient = QLinearGradient(0, top, 0, bot)
    gradient.setColorAt(0, QColor("#1565C0"))
    gradient.setColorAt(1, QColor("#0D47A1"))
    p.setBrush(gradient)
    p.setPen(Qt.PenStyle.NoPen)
    p.drawPath(shield)

    # Document symbol inside shield (white lines)
    if size >= 32:
        pen_w = max(1, size // 32)
        p.setPen(QPen(QColor("#FFFFFF"), pen_w))
        doc_left = cx - s * 0.18
        doc_right = cx + s * 0.18
        doc_top = top + s * 0.25
        line_spacing = s * 0.1
        for i in range(3):
            y = doc_top + i * line_spacing
            w = (doc_right - doc_left) * (1 - i * 0.15)
            p.drawLine(QPoint(int(doc_left), int(y)), QPoint(int(doc_left + w), int(y)))

    # Lock/checkmark at bottom
    if size >= 48:
        check_x = cx
        check_y = top + s * 0.68
        pen_w = max(2, size // 24)
        p.setPen(QPen(QColor("#FFFFFF"), pen_w))
        p.drawLine(
            QPoint(int(check_x - s * 0.08), int(check_y)),
            QPoint(int(check_x - s * 0.02), int(check_y + s * 0.06)),
        )
        p.drawLine(
            QPoint(int(check_x - s * 0.02), int(check_y + s * 0.06)),
            QPoint(int(check_x + s * 0.1), int(check_y - s * 0.06)),
        )

    p.end()
    return img


def _save_ico(images: list, path: Path) -> None:
    """Save multiple QImage as a Windows ICO file.

    ICO format: header + directory entries + image data (as embedded PNGs).
    """
    import struct
    from io import BytesIO

    png_data_list: list[bytes] = []
    for img in images:
        buf = BytesIO()
        # Save as PNG to bytes
        from PySide6.QtCore import QBuffer, QIODevice

        qbuf = QBuffer()
        qbuf.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(qbuf, "PNG")
        png_data_list.append(bytes(qbuf.data()))

    num = len(images)
    # ICO header: reserved(2) + type(2) + count(2) = 6 bytes
    header = struct.pack("<HHH", 0, 1, num)
    # Directory entries: 16 bytes each
    dir_offset = 6 + num * 16
    directory = b""
    for i, img in enumerate(images):
        w = img.width() if img.width() < 256 else 0
        h = img.height() if img.height() < 256 else 0
        png_bytes = png_data_list[i]
        entry = struct.pack(
            "<BBBBHHII",
            w, h, 0, 0,  # width, height, palette, reserved
            1, 32,       # planes, bpp
            len(png_bytes), dir_offset,
        )
        directory += entry
        dir_offset += len(png_bytes)

    with open(path, "wb") as f:
        f.write(header)
        f.write(directory)
        for png_bytes in png_data_list:
            f.write(png_bytes)


if __name__ == "__main__":
    main()
