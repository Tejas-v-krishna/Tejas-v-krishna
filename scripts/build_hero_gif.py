"""Build the animated hero eye: looks left, looks right, then blinks.

Run from the repository root:
    python scripts/build_hero_gif.py

The source is a single dithered still. The gaze shift moves the artwork's iris
across the sclera, and the blink squashes the eye opening toward the lid line
while a moving lid (with the artwork's real lashes) slides over it.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "source" / "eye.png"

BG = (13, 17, 23)
INK = (230, 237, 243)

WIDTH = 960
FPS = 25

# Eye opening traced from the artwork (source-image pixels).
ANCHOR_X = [146, 160, 180, 200, 220, 240, 260, 280, 300, 320, 340, 360, 380, 400, 420, 432, 440]
ANCHOR_TOP = [195, 180, 142, 115, 100, 88, 79, 73, 72, 72, 73, 77, 87, 99, 126, 150, 175]
ANCHOR_BOTTOM = [195, 218, 223, 231, 239, 243, 244, 244, 243, 241, 237, 232, 227, 217, 201, 178, 175]
CLOSE_AT = 0.72  # where the lids meet, as a fraction of the opening height

# Iris, measured on the upscaled artwork.
IRIS_X, IRIS_Y, IRIS_R = 480.0, 270.0, 110.0
GAZE = 40.0  # horizontal travel of the pupil, in output pixels

# Blink timing, in frames at FPS.
CLOSING = 5
HOLD_CLOSED = 1
OPENING = 5


def smoothstep(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def load_eye() -> tuple[np.ndarray, float]:
    image = Image.open(SOURCE).convert("L")
    scale = WIDTH / image.width
    height = round(image.height * scale)
    image = image.resize((WIDTH, height), Image.Resampling.LANCZOS)
    return np.asarray(image, dtype=np.float32), scale


def eye_curves(width: int, scale: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    xs = np.arange(width, dtype=np.float32) / scale
    top = np.interp(xs, ANCHOR_X, ANCHOR_TOP) * scale
    bottom = np.interp(xs, ANCHOR_X, ANCHOR_BOTTOM) * scale

    kernel = 9
    pad = kernel // 2
    ones = np.ones(kernel, dtype=np.float32) / kernel
    top = np.convolve(np.pad(top, pad, mode="edge"), ones, mode="valid")
    bottom = np.convolve(np.pad(bottom, pad, mode="edge"), ones, mode="valid")

    closed_line = top + CLOSE_AT * (bottom - top)
    active = (bottom - top) > 4
    return top, bottom, closed_line, active


def prepare_iris(gray: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
    """Cut the iris out and fill the sclera behind it, so it can slide around."""
    height, width = gray.shape
    pad = 4
    radius = int(IRIS_R + pad)
    x0 = int(round(IRIS_X)) - radius
    y0 = int(round(IRIS_Y)) - radius
    sprite = gray[y0:y0 + 2 * radius, x0:x0 + 2 * radius].copy()

    yy, xx = np.mgrid[0:2 * radius, 0:2 * radius]
    dist = np.hypot(xx - radius + 0.5, yy - radius + 0.5)
    alpha = np.clip((IRIS_R + 1.5 - dist) / 3.0, 0, 1).astype(np.float32)

    base = gray.copy()
    yy2, xx2 = np.mgrid[0:height, 0:width]
    inside = np.hypot(xx2 - IRIS_X, yy2 - IRIS_Y) <= IRIS_R + 3
    base[inside] = 255.0
    return base, sprite, alpha, radius


def compose_gaze(base: np.ndarray, sprite: np.ndarray, alpha: np.ndarray, radius: int,
                 dx: float) -> np.ndarray:
    out = base.copy()
    px = int(round(IRIS_X + dx)) - radius
    py = int(round(IRIS_Y)) - radius
    region = out[py:py + 2 * radius, px:px + 2 * radius]
    out[py:py + 2 * radius, px:px + 2 * radius] = region * (1 - alpha) + sprite * alpha
    return out


def blink(gray: np.ndarray, top: np.ndarray, bottom: np.ndarray, closed_line: np.ndarray,
          active: np.ndarray, noise: np.ndarray, p: float) -> Image.Image:
    height, width = gray.shape
    out = gray.copy()
    ys = np.arange(height, dtype=np.float32)

    for x in np.where(active)[0]:
        t, b, c = top[x], bottom[x], closed_line[x]
        margin_top = t + p * (c - t)
        margin_bottom = b + p * (c - b)

        # Squeeze the eyeball into the shrinking aperture.
        if margin_bottom - margin_top > 1.0:
            y0 = int(np.ceil(margin_top))
            y1 = int(np.floor(margin_bottom))
            yy = np.arange(y0, y1 + 1)
            src = t + (yy - margin_top) / (margin_bottom - margin_top) * (b - t)
            out[y0:y1 + 1, x] = np.interp(src, ys, gray[:, x])

        # Upper lid: dark halftone whose pattern is pinned to the moving margin.
        if margin_top - t > 0.5:
            y0 = max(0, int(np.floor(t - 7)))
            y1 = int(np.floor(margin_top))
            yy = np.arange(y0, y1 + 1)
            d = np.clip(np.rint(margin_top - yy), 0, height - 1).astype(int)
            pattern = noise[d, x]
            lid = np.where(pattern < 0.022, 205.0, 0.0)
            fold = np.exp(-((d - 14) ** 2) / (2 * 3.0**2))
            lid = np.maximum(lid, np.where(pattern < 0.10 * fold, 185.0, 0.0))
            out[yy, x] = lid

            # Carry the artwork's own lashes down with the margin.
            for off in range(0, 9):
                sy, oy = int(round(t + off)), int(round(margin_top + off))
                if 0 <= sy < height and 0 <= oy < height and gray[sy, x] < 110:
                    out[oy, x] = gray[sy, x]

        # Lower lid.
        if b - margin_bottom > 0.5:
            y0 = int(np.ceil(margin_bottom))
            y1 = min(height - 1, int(np.floor(b + 5)))
            yy = np.arange(y0, y1 + 1)
            d = np.clip(np.rint(yy - margin_bottom), 0, height - 1).astype(int)
            pattern = noise[d, x]
            out[yy, x] = np.where(pattern < 0.022, 205.0, 0.0)

            for off in range(0, 6):
                sy, oy = int(round(b - off)), int(round(margin_bottom - off))
                if 0 <= sy < height and 0 <= oy < height and gray[sy, x] < 110:
                    out[oy, x] = gray[sy, x]

    image = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "L")
    image = image.filter(ImageFilter.GaussianBlur(0.45))
    dots = np.where(np.asarray(image) >= 128, 255, 0).astype(np.uint8)
    return ImageOps.colorize(Image.fromarray(dots, "L"), black=BG, white=INK)


def schedule() -> list[tuple[float, float]]:
    """(gaze offset, blink amount) per frame."""
    states: list[tuple[float, float]] = []

    def hold(count: int, dx: float) -> None:
        states.extend([(dx, 0.0)] * count)

    def move(count: int, start: float, end: float) -> None:
        states.extend(
            [(start + (end - start) * smoothstep(i / (count - 1)), 0.0) for i in range(count)]
        )

    hold(14, 0.0)
    move(6, 0.0, -GAZE)
    hold(18, -GAZE)
    move(12, -GAZE, GAZE)
    hold(18, GAZE)
    move(6, GAZE, 0.0)
    hold(8, 0.0)

    states.extend([(0.0, smoothstep(i / (CLOSING - 1))) for i in range(CLOSING)])
    states.extend([(0.0, 1.0)] * HOLD_CLOSED)
    states.extend([(0.0, smoothstep(1.0 - i / (OPENING - 1))) for i in range(OPENING)])

    hold(14, 0.0)
    return states


def main() -> None:
    gray, scale = load_eye()
    top, bottom, closed_line, active = eye_curves(gray.shape[1], scale)
    base, sprite, alpha, radius = prepare_iris(gray)

    rng = np.random.default_rng(5)
    noise = rng.random(gray.shape).astype(np.float32)

    frames = []
    for dx, p in schedule():
        view = compose_gaze(base, sprite, alpha, radius, dx)
        frames.append(blink(view, top, bottom, closed_line, active, noise, p).quantize(
            colors=2, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        ))

    out = ASSETS / "hero.gif"
    frames[0].save(
        out,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        optimize=True,
        disposal=1,
    )
    print(f"Wrote {out} ({gray.shape[1]}x{gray.shape[0]}, {len(frames)} frames, {out.stat().st_size / 1024:.0f} KB)")

    ASSETS.joinpath(".cache").mkdir(exist_ok=True)
    sheet = Image.new("RGB", (gray.shape[1] * 4, gray.shape[0]), BG)
    for i, dx in enumerate((-GAZE, 0.0, GAZE)):
        view = compose_gaze(base, sprite, alpha, radius, dx)
        sheet.paste(blink(view, top, bottom, closed_line, active, noise, 0.0), (i * gray.shape[1], 0))
    view = compose_gaze(base, sprite, alpha, radius, 0.0)
    sheet.paste(blink(view, top, bottom, closed_line, active, noise, 1.0), (3 * gray.shape[1], 0))
    sheet.save(ASSETS / ".cache" / "hero-blink-sheet.png")


if __name__ == "__main__":
    main()
