#!/usr/bin/env python3
"""
Batch image-to-WebP converter.

Reads all files in --input-location, filters by accepted image extensions,
and converts each found image to WebP in --output-location using a per-type
conversion function (png2webp, jpgtowebp, etc.).

Usage:
  python convert_to_webp.py --input-location ./in --output-location ./out
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable, Dict

from PIL import Image, ImageSequence
from pathlib import Path
from PIL import Image
import tempfile
import shutil

# -----------------------------
# Configuration / Data structures
# -----------------------------

# Accepted image extensions (lowercase, include the dot)
ACCEPTED_EXTS = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif"}

# Registry for converters: maps file extension -> conversion function
# Each converter has signature: (src: Path, dst: Path) -> None
CONVERTERS: Dict[str, Callable[[Path, Path], None]] = {}


def register_converter(*exts: str):
    """
    Decorator to register a conversion function for one or more extensions.

    Example:
        @register_converter(".png")
        def png2webp(src, dst): ...
    """
    def _decorator(func: Callable[[Path, Path], None]):
        for ext in exts:
            CONVERTERS[ext.lower()] = func
        return func
    return _decorator


# -----------------------------
# Utility functions
# -----------------------------

def is_image(path: Path) -> bool:
    """Return True if the file extension is in the accepted list."""
    return path.is_file() and path.suffix.lower() in ACCEPTED_EXTS


def ensure_writable_dir(path: Path) -> None:
    """Create directory if missing; raise if not writable."""
    path.mkdir(parents=True, exist_ok=True)
    if not path.exists() or not path.is_dir():
        raise RuntimeError(f"Output location is not a directory: {path}")
    # Basic writability check by trying to open a temp file
    test = path / ".write_test"
    try:
        with test.open("w") as fh:
            fh.write("ok")
    except Exception as e:
        raise RuntimeError(f"Output location not writable: {path}") from e
    finally:
        try:
            test.unlink(missing_ok=True)  # type: ignore[call-arg]
        except TypeError:
            # For Python < 3.8 compatibility
            if test.exists():
                test.unlink()


def build_dst_path(src: Path, out_dir: Path) -> Path:
    """Return the destination path in out_dir with .webp extension."""
    return out_dir / f"{src.stem}.webp"


# -----------------------------
# Core conversion helpers (Pillow)
# -----------------------------

def _save_webp(img: Image.Image, dst: Path, **kwargs) -> None:
    """
    Save Pillow image to WebP with provided kwargs.
    """
    img.save(dst, format="WEBP", **kwargs)


def _convert_still_image(src: Path, dst: Path, **webp_kwargs) -> None:
    """
    Convert a still image (single frame) to WebP.
    """
    with Image.open(src) as im:
        im = im.convert("RGBA") if im.mode in ("P", "LA") else im.convert("RGB") if im.mode == "CMYK" else im
        _save_webp(im, dst, **webp_kwargs)


def _convert_gif(src: Path, dst: Path) -> None:
    """
    Convert GIFs. If animated, store as animated WebP; otherwise treat as still.
    """
    with Image.open(src) as im:
        frames = [frame.copy() for frame in ImageSequence.Iterator(im)]
        durations = im.info.get("duration", 100)

        if len(frames) <= 1:
            _convert_still_image(src, dst, quality=85, method=6)
            return

        # Animated GIF -> Animated WebP
        # durations might be scalar or list; normalize
        if isinstance(durations, int):
            durations = [durations] * len(frames)

        frames_rgb = []
        for f in frames:
            # Preserve transparency if present
            if f.mode in ("P", "RGBA"):
                f = f.convert("RGBA")
            else:
                f = f.convert("RGB")
            frames_rgb.append(f)

        frames_rgb[0].save(
            dst,
            format="WEBP",
            save_all=True,
            append_images=frames_rgb[1:],
            duration=durations,
            loop=0,
            method=6,
            quality=80,
        )


# -----------------------------
# Type-specific converters
# -----------------------------


def _save_webp_lossy_with_alpha(im: Image.Image, dst: Path, quality: int) -> None:
    """
    Save as lossy WebP while preserving alpha. `exact=False` allows the encoder
    to optimize fully transparent pixels (significantly smaller files).
    """
    im.save(
        dst,
        format="WEBP",
        lossless=False,
        quality=quality,   # 0..100 (lower = smaller)
        method=6,          # 0..6 (higher = slower/smaller)
        exact=False        # allow optimizing transparent pixels
    )

@register_converter(".png")
def png2webp(src: Path, dst: Path) -> None:
    """
    PNG -> WebP (aggressive). Use lossy WebP with alpha and pick the smallest
    among a few quality levels.
    """
    # Qualities to try (from "good" to "very aggressive").
    # Tune this list if you want even smaller output.
    trial_qualities = [65, 55, 45]

    with Image.open(src) as im:
        # Normalize mode: keep alpha if present, otherwise RGB
        if "A" in im.getbands():
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")

        src_size = src.stat().st_size

        best_path = None
        best_size = None

        # Use a temp dir to avoid partially written outputs
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            for q in trial_qualities:
                trial = td / f"trial_q{q}.webp"
                _save_webp_lossy_with_alpha(im, trial, quality=q)
                s = trial.stat().st_size

                if best_size is None or s < best_size:
                    best_size = s
                    best_path = trial

            # Optional: if the “best” lossy result is larger than original PNG,
            # fall back to lossless WebP (rare for photos, common for tiny icons).
            if best_size is not None and best_size >= src_size:
                fallback = td / "lossless.webp"
                im.save(fallback, format="WEBP", lossless=True, method=6, exact=False)
                if fallback.stat().st_size < best_size:
                    best_path = fallback

            # Move the chosen file to dst
            assert best_path is not None
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(best_path), str(dst))

'''
Original impl, yields bigger files
@register_converter(".png")
def png2webp(src: Path, dst: Path) -> None:
    """
    PNG -> WebP. Prefer lossless to preserve crispness/transparency.
    """
    with Image.open(src) as im:
        if im.mode not in ("RGBA", "RGB", "LA", "L", "P"):
            im = im.convert("RGBA")
        _save_webp(im, dst, lossless=True, method=6)
'''

@register_converter(".jpg", ".jpeg")
def jpg2webp(src: Path, dst: Path) -> None:
    """
    JPEG -> WebP. Use lossy with reasonable quality.
    """
    _convert_still_image(src, dst, quality=85, method=6)


@register_converter(".tif", ".tiff")
def tiff2webp(src: Path, dst: Path) -> None:
    """
    TIFF -> WebP. Default to lossy unless you need archival (use lossless=True).
    """
    _convert_still_image(src, dst, quality=90, method=6)


@register_converter(".bmp")
def bmp2webp(src: Path, dst: Path) -> None:
    """
    BMP -> WebP.
    """
    _convert_still_image(src, dst, quality=85, method=6)


@register_converter(".gif")
def gif2webp(src: Path, dst: Path) -> None:
    """
    GIF -> WebP (animated if the source is animated).
    """
    _convert_gif(src, dst)


# -----------------------------
# Pipeline
# -----------------------------

def process_directory(input_dir: Path, output_dir: Path) -> None:
    """
    Convert all accepted images in input_dir (non-recursive) to WebP in output_dir.
    """
    logging.info("Scanning input: %s", input_dir)

    count_total = 0
    count_converted = 0
    count_skipped = 0
    count_failed = 0

    for entry in sorted(input_dir.iterdir()):
        if not entry.is_file():
            continue

        count_total += 1
        ext = entry.suffix.lower()

        if not is_image(entry):
            logging.debug("Skipping non-image: %s", entry.name)
            count_skipped += 1
            continue

        converter = CONVERTERS.get(ext)
        if not converter:
            logging.warning("No converter for extension '%s'; skipping %s", ext, entry.name)
            count_skipped += 1
            continue

        dst = build_dst_path(entry, output_dir)

        try:
            converter(entry, dst)
            logging.info("Converted: %s -> %s", entry.name, dst.name)
            count_converted += 1
        except Exception as e:
            logging.exception("Failed converting %s: %s", entry.name, e)
            count_failed += 1

    logging.info(
        "Done. total=%d converted=%d skipped=%d failed=%d",
        count_total, count_converted, count_skipped, count_failed
    )


# -----------------------------
# CLI
# -----------------------------

def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert images in a folder to WebP using per-type converters."
    )
    parser.add_argument(
        "--input-location",
        required=True,
        type=Path,
        help="Readable folder containing input files (non-recursive).",
    )
    parser.add_argument(
        "--output-location",
        required=True,
        type=Path,
        help="Writable folder to store converted .webp files.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging."
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s"
    )

    in_dir: Path = args.input_location
    out_dir: Path = args.output_location

    if not in_dir.exists() or not in_dir.is_dir():
        logging.error("Input location is not a readable directory: %s", in_dir)
        return 2

    try:
        ensure_writable_dir(out_dir)
    except Exception as e:
        logging.error(str(e))
        return 3

    process_directory(in_dir, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
