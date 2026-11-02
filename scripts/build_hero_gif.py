"""Build the animated hero eye from the source clip.

Run from the repository root:
    python scripts/build_hero_gif.py

Source clip: assets/source/eye-blink.mp4 (a short, loop-friendly clip of the
halftone eye looking around and blinking). Frames are extracted with ffmpeg,
converted to the profile's two-colour palette, and written as an animated GIF.
"""

from __future__ import annotations

import glob
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SOURCE = ASSETS / "source" / "eye-blink.mp4"
OUT = ASSETS / "hero.gif"

BG = (13, 17, 23)
INK = (230, 237, 243)


def extract_frames() -> list[str]:
    if not SOURCE.exists():
        raise FileNotFoundError(f"Source clip not found: {SOURCE}")
    tmp = Path(tempfile.mkdtemp(prefix="hero_frames_"))
    pattern = str(tmp / "f%03d.png")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(SOURCE), pattern],
        check=True,
    )
    files = sorted(glob.glob(str(tmp / "*.png")))
    if not files:
        raise RuntimeError("ffmpeg produced no frames")
    return files


def main() -> None:
    files = extract_frames()
    frames = []
    for f in files:
        img = Image.open(f).convert("L")
        if img.size != (960, 540):
            img = img.resize((960, 540), Image.Resampling.LANCZOS)
        arr = np.asarray(img, dtype=np.float32)
        dots = np.where(arr >= 128, 255, 0).astype(np.uint8)
        frames.append(ImageOps.colorize(Image.fromarray(dots, "L"), black=BG, white=INK))

    qframes = [f.quantize(colors=2, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE) for f in frames]
    qframes[0].save(
        OUT,
        save_all=True,
        append_images=qframes[1:],
        duration=round(1000 / 12),
        loop=0,
        optimize=True,
        disposal=1,
    )
    print(f"Wrote {OUT} ({len(qframes)} frames, {OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
