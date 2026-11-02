"""Build the custom profile images.

Run from the repository root:
    python scripts/build_assets.py

Sources:
  - Eye banner: assets/source/eye.png (original artwork)
  - Bruce McCandless II during EVA, STS-41-B (NASA / Wikimedia Commons, public domain)
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps

import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
CACHE = ASSETS / ".cache"
SOURCE_VIDEO = ASSETS / "source" / "eye-blink.mp4"
ASTRONAUT_URL = (
    "https://thumb.wikimedia.org/wikipedia/commons/thumb/9/97/"
    "STS41B-35-1613_-_Bruce_McCandless_II_during_EVA_%28Retouched%29_%28cropped%29.jpg/"
    "1280px-STS41B-35-1613_-_Bruce_McCandless_II_during_EVA_%28Retouched%29_%28cropped%29.jpg"
)

BG = (13, 17, 23)
INK = (230, 237, 243)
MUTED = (139, 148, 158)

BAYER_4 = [
    [0, 8, 2, 10],
    [12, 4, 14, 6],
    [3, 11, 1, 9],
    [15, 7, 13, 5],
]


def extract_first_frame(video: Path) -> Path:
    """Extract the first frame of `video` into the cache (ignoring the result if cached)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "eye-frame.png"
    if not out.exists():
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-frames:v", "1", str(out)],
            check=True,
        )
    return out


def download(url: str, path: Path) -> Path:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading {path.name}...")
        req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-builder/1.0"})
        with urllib.request.urlopen(req) as response, path.open("wb") as fh:
            fh.write(response.read())
    return path


def bayer_dither(image: Image.Image, scale: int = 1) -> Image.Image:
    """Return a 1-bit white-on-black ordered-dither image."""
    image = image.convert("L")
    if scale > 1:
        image = image.resize(
            (max(1, image.width // scale), max(1, image.height // scale)),
            Image.Resampling.LANCZOS,
        )
    pixels = image.load()
    out = Image.new("L", image.size, 0)
    out_pixels = out.load()
    for y in range(image.height):
        row = BAYER_4[y % 4]
        for x in range(image.width):
            threshold = (row[x % 4] + 0.5) * 16
            if pixels[x, y] > threshold:
                out_pixels[x, y] = 255
    if scale > 1:
        out = out.resize((out.width * scale, out.height * scale), Image.Resampling.NEAREST)
    return out


def fit_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    return ImageOps.fit(image, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def build_hero() -> None:
    """Render the dithered eye as the README banner."""
    image = Image.open(extract_first_frame(SOURCE_VIDEO)).convert("L")

    # Upscale before thresholding so the halftone dots stay crisp when GitHub
    # stretches the banner to the width of the README.
    width = 1280
    height = round(image.height * width / image.width)
    image = image.resize((width, height), Image.Resampling.LANCZOS)
    dots = image.point(lambda value: 255 if value >= 128 else 0)

    # Soft vignette so the artwork dissolves into the page background instead
    # of ending in a hard rectangle.
    mask = Image.new("L", dots.size, 0)
    mask_pixels = mask.load()
    for y in range(dots.height):
        for x in range(dots.width):
            left = min(1.0, x / 32)
            right = min(1.0, (dots.width - 1 - x) / 32)
            top = min(1.0, y / 32)
            bottom = min(1.0, (dots.height - 1 - y) / 32)
            mask_pixels[x, y] = int(255 * min(left, right, top, bottom))
    mask = mask.filter(ImageFilter.GaussianBlur(8))

    layer = Image.new("RGBA", dots.size, INK + (255,))
    layer.putalpha(Image.composite(dots, Image.new("L", dots.size, 0), mask))
    canvas = Image.new("RGBA", dots.size, BG + (255,))
    canvas.alpha_composite(layer)

    canvas.convert("RGB").save(ASSETS / "hero.png", optimize=True)
    print("Wrote assets/hero.png")


def build_avatar() -> None:
    source = download(ASTRONAUT_URL, CACHE / "mccandless.jpg")
    image = Image.open(source).convert("RGB")

    # A tight, high-contrast crop of the helmet for the profile photo.
    crop = image.crop((700, 200, 960, 460))
    gray = ImageOps.autocontrast(ImageOps.grayscale(crop), cutoff=1)
    dots = bayer_dither(gray, scale=2).convert("L").resize((400, 400), Image.Resampling.LANCZOS)
    avatar = Image.new("RGB", (400, 400), BG)
    avatar.paste(INK, (0, 0), dots)
    avatar.save(ASSETS / "avatar.png", optimize=True)
    print("Wrote assets/avatar.png")


def build_astronaut() -> None:
    source = download(ASTRONAUT_URL, CACHE / "mccandless.jpg")
    image = Image.open(source).convert("RGB")

    # The suit is white against black space; crop out the Earth at the bottom.
    crop = image.crop((255, 0, 1025, 865))
    gray = ImageOps.autocontrast(ImageOps.grayscale(crop), cutoff=1)
    gray = gray.point(lambda value: int(min(255, max(0, (value - 8) * 1.08))))

    # Ordered dither, then turn the black pixels transparent. This gives the
    # astronaut the same stippled look as the hero image.
    dots = bayer_dither(gray, scale=2)
    rgba = Image.new("RGBA", dots.size, (0, 0, 0, 0))
    rgba.paste(Image.new("RGBA", dots.size, (235, 240, 246, 255)), (0, 0), dots)
    rgba = rgba.resize((420, int(420 * rgba.height / rgba.width)), Image.Resampling.LANCZOS)
    rgba.save(ASSETS / "astronaut.png", optimize=True)
    print("Wrote assets/astronaut.png")


if __name__ == "__main__":
    ASSETS.mkdir(parents=True, exist_ok=True)
    build_hero()
    build_astronaut()
    build_avatar()
