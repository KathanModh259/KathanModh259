"""Photo -> self-typing monochrome ASCII SVG. Local only (needs opencv-python, numpy).

usage: python scripts/make_ascii_svg.py source-photo.jpg [x0 y0 x1 y1]
"""
import sys

import cv2
import numpy as np

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense); leading space clears the background
COLS, FS = 80, 10       # grid width, font size
CW, LH = FS * 0.6, FS   # monospace cell width / line height
OUT = "kathan-ascii.svg"


def prep(path, box):
    img = cv2.imread(path)
    if box:
        x0, y0, x1, y1 = box
        img = img[y0:y1, x0:x1]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # ponytail: assumes a flat, unsaturated backdrop sampled at the top-left; use rembg for busy ones
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    bg = int(hsv[:20, :20, 2].mean())
    cand = ((hsv[..., 1] < 30) & (np.abs(hsv[..., 2].astype(int) - bg) < 18)).astype(np.uint8)
    _, lab = cv2.connectedComponents(cand)
    bg_labels = {lab[0, 0], lab[0, -1]} - {0}
    gray = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8)).apply(gray)
    gray[np.isin(lab, list(bg_labels))] = 255
    return gray


def to_rows(gray):
    rows = int(COLS * gray.shape[0] / gray.shape[1] * CW / LH)
    small = cv2.resize(gray, (COLS, rows), interpolation=cv2.INTER_AREA)
    idx = ((255 - small.astype(int)) * len(RAMP) // 256)
    lines = ["".join(RAMP[i] for i in r) for r in idx]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


def render(lines):
    w, h = COLS * CW + 20, len(lines) * LH + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="0 0 {w:.0f} {h:.0f}" '
           f'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" font-size="{FS}">',
           f'<rect width="100%" height="100%" rx="8" fill="#0d1117"/>']
    for i, line in enumerate(lines):
        y, b = 10 + i * LH, i * 0.06
        out.append(f'<clipPath id="r{i}"><rect x="10" y="{y}" width="0" height="{LH}">'
                   f'<animate attributeName="width" from="0" to="{COLS * CW}" begin="{b:.2f}s" dur="0.35s" fill="freeze"/>'
                   f'</rect></clipPath>')
        out.append(f'<text x="10" y="{y + LH * 0.8}" fill="#c9d1d9" xml:space="preserve" textLength="{COLS * CW}" '
                   f'lengthAdjust="spacing" clip-path="url(#r{i})">{line}</text>')
        # block cursor riding the wipe edge, gone once the row is printed
        out.append(f'<rect x="10" y="{y}" width="{CW}" height="{LH}" fill="#39d353" opacity="0">'
                   f'<animate attributeName="x" from="10" to="{10 + COLS * CW}" begin="{b:.2f}s" dur="0.35s" fill="freeze"/>'
                   f'<animate attributeName="opacity" values="1;1;0" begin="{b:.2f}s" dur="0.36s"/></rect>')
    out.append("</svg>")
    return "\n".join(out)


if __name__ == "__main__":
    box = tuple(map(int, sys.argv[2:6])) if len(sys.argv) >= 6 else None
    lines = to_rows(prep(sys.argv[1], box))
    assert all(len(l) == COLS for l in lines) and set("".join(lines)) <= set(RAMP)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(lines))
    print("\n".join(lines))
