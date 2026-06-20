#!/usr/bin/env python3
"""
Generates synthetic damage test images for local development.
Run once before running the test suite.

Usage: python tests/generate_test_images.py
"""

import base64
import os
import struct
import zlib
from pathlib import Path

OUT = Path(__file__).parent / "test_images"
OUT.mkdir(exist_ok=True)


def make_png(w: int, h: int, pixels_fn) -> bytes:
    def chunk(name: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + name + data
        return c + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)

    raw = b""
    for y in range(h):
        raw += b"\x00"
        for x in range(w):
            raw += bytes(pixels_fn(x, y, w, h))

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def car_dent(x, y, w, h):
    """Silver car with visible dent depression + paint scratches + red transfer."""
    cx, cy = w * 0.4, h * 0.5
    dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
    r, g, b = 175, 175, 180  # silver body

    # Dent shadow — dark concave area
    if dist < w * 0.22:
        f = 1.0 - (dist / (w * 0.22)) * 0.65
        r, g, b = int(r * f * 0.45), int(g * f * 0.45), int(b * f * 0.45)
    # Highlight rim around dent edge
    elif dist < w * 0.26:
        r, g, b = 230, 230, 235

    # Deep scratch lines
    if abs(y - h * 0.44) < 2 and w * 0.18 < x < w * 0.72:
        r, g, b = 30, 30, 30
    if abs(y - h * 0.56) < 1.5 and w * 0.28 < x < w * 0.62:
        r, g, b = 50, 50, 50
    # Red paint transfer from other vehicle
    if abs(y - h * 0.49) < 4 and w * 0.22 < x < w * 0.52:
        r, g, b = 185, 28, 28
    # Body panel edge (darker)
    if x < 8 or y < 8 or x > w - 8 or y > h - 8:
        r, g, b = 60, 60, 65

    return [min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))]


def laptop_crack(x, y, w, h):
    """Dark laptop screen with diagonal crack + dead pixel zone."""
    r, g, b = 12, 12, 18  # off screen base

    border = 18
    # Bezel
    if x < border or x > w - border or y < border or y > h - border:
        r, g, b = 45, 45, 48
        return [r, g, b]

    # Dead pixel zone (upper left quadrant — completely dark)
    if x < w * 0.42 and y < h * 0.52:
        r, g, b = 2, 2, 4
    # Faint screen glow right side (still partially working)
    elif x > w * 0.52:
        intensity = (x - w * 0.52) / (w * 0.48)
        r, g, b = int(15 * intensity), int(35 * intensity), int(75 * intensity)

    # Main diagonal crack (thick, white/silver)
    crack_y = h * 0.18 + x * 0.55
    if abs(y - crack_y) < 3:
        r, g, b = 215, 215, 220
    elif abs(y - crack_y) < 5:
        r, g, b = 120, 120, 130

    # Spider crack branches from main line
    branch1_y = h * 0.18 + x * 0.55 + (x - w * 0.3) * 0.4
    if x > w * 0.3 and abs(y - branch1_y) < 1.5:
        r, g, b = 160, 160, 170

    branch2_y = h * 0.18 + x * 0.55 - (x - w * 0.2) * 0.3
    if x > w * 0.2 and y < h * 0.5 and abs(y - branch2_y) < 1.5:
        r, g, b = 140, 140, 150

    return [min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))]


def crushed_box(x, y, w, h):
    """Brown cardboard shipping box, heavily crushed on right side."""
    # Cardboard base colour
    r, g, b = 145, 95, 48

    # Crushed right side — progressively darker
    if x > w * 0.58:
        crush = (x - w * 0.58) / (w * 0.42)
        r = int(r * (1.0 - crush * 0.62))
        g = int(g * (1.0 - crush * 0.62))
        b = int(b * (1.0 - crush * 0.62))

    # Tape across middle — suspicious colour variation
    if abs(y - h * 0.48) < 5:
        r, g, b = 215, 195, 115
    if abs(y - h * 0.52) < 3:
        r, g, b = 200, 180, 100

    # Crush deformation fold lines
    if x > w * 0.55 and abs(y - (h * 0.28 + (x - w * 0.55) * 0.15)) < 2:
        r, g, b = 55, 35, 12
    if x > w * 0.65 and abs(y - (h * 0.72 - (x - w * 0.65) * 0.1)) < 2:
        r, g, b = 55, 35, 12

    # Heavy impact zone corner
    if x > w * 0.78 and y > h * 0.62:
        r, g, b = int(r * 0.35), int(g * 0.35), int(b * 0.35)

    # Cardboard fibre texture (subtle noise)
    if (x * 3 + y * 7) % 11 == 0:
        r = min(255, r + 8)

    # Box edges
    if x < 4 or y < 4 or x > w - 4 or y > h - 4:
        r, g, b = int(r * 0.7), int(g * 0.7), int(b * 0.7)

    return [min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b))]


IMAGES = [
    ("car_dent_front.png",         car_dent,    400, 300),
    ("laptop_cracked_screen.png",  laptop_crack, 400, 300),
    ("crushed_package_box.png",    crushed_box,  400, 300),
]


def main():
    print("Generating test images...")
    for fname, fn, w, h in IMAGES:
        png = make_png(w, h, fn)
        path = OUT / fname
        path.write_bytes(png)
        b64_len = len(base64.b64encode(png))
        print(f"  ✓ {fname}  ({len(png):,} bytes  b64={b64_len:,})")
    print(f"\nAll images saved to: {OUT}/")
    print("Run the test suite: python tests/run_local_tests.py")


if __name__ == "__main__":
    main()
