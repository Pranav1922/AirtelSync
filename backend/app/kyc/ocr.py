"""Local OCR: image quality checks, watermark removal, deskew, Tesseract with per-line confidence.

Runs fully offline with the system `tesseract` binary. No document leaves the machine.
"""
from __future__ import annotations

import hashlib
import io
import shutil
import subprocess
from functools import lru_cache

import numpy as np
from PIL import Image, ImageFilter

TESSERACT = shutil.which("tesseract")


def ocr_available() -> bool:
    return TESSERACT is not None


def _arr(im: Image.Image) -> np.ndarray:
    return np.asarray(im.convert("RGB")).astype(np.int16)


def quality(im: Image.Image) -> dict:
    a = _arr(im)
    g = a.mean(axis=2)
    sharp = float(np.abs(np.diff(g, 2, axis=0)).mean() + np.abs(np.diff(g, 2, axis=1)).mean())
    r, gr, b = a[..., 0], a[..., 1], a[..., 2]
    pink = float(((r > 200) & (gr > 130) & (gr < 200) & (b < 210)).mean())
    return {"width": im.width, "height": im.height, "sharpness": round(sharp, 2),
            "watermark_ratio": round(pink, 4), "blurred": sharp < 2.0}


def remove_watermark(im: Image.Image) -> Image.Image:
    """Specimen watermark is light red; real text is dark. Keep only dark pixels."""
    a = _arr(im)
    return Image.fromarray(np.where(a.max(axis=2) < 140, 0, 255).astype(np.uint8))


def estimate_skew(bw: Image.Image) -> float:
    """Angle (deg) that maximises row-projection variance: text lines line up horizontally."""
    small = bw.resize((bw.width // 3, bw.height // 3))
    best, best_score = 0.0, -1.0
    for ang in np.arange(-12, 12.5, 0.5):
        rot = np.asarray(small.rotate(float(ang), fillcolor=255)) < 128
        score = float(rot.sum(axis=1).var())
        if score > best_score:
            best, best_score = float(ang), score
    return best


def _tesseract_tsv(im: Image.Image) -> list[dict]:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    out = subprocess.run([TESSERACT, "stdin", "stdout", "--psm", "6", "tsv"], input=buf.getvalue(),
                         capture_output=True, timeout=60).stdout.decode("utf-8", "ignore")
    lines: dict[tuple, dict] = {}
    for row in out.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or not cols[11].strip():
            continue
        key = (cols[2], cols[3], cols[4])
        ln = lines.setdefault(key, {"words": [], "conf": []})
        ln["words"].append(cols[11])
        ln["conf"].append(float(cols[10]))
    return [{"text": " ".join(v["words"]), "conf": round(sum(v["conf"]) / len(v["conf"]), 1)} for v in lines.values()]


@lru_cache(maxsize=64)
def _ocr_cached(digest: str, data: bytes) -> dict:
    im = Image.open(io.BytesIO(data))
    im.load()
    q = quality(im)
    bw = remove_watermark(im)
    skew = estimate_skew(bw)
    if abs(skew) >= 1.0:
        bw = bw.rotate(skew, expand=True, fillcolor=255)
    if q["blurred"]:
        bw = remove_watermark(im.filter(ImageFilter.UnsharpMask(radius=4, percent=250)))
    lines = _tesseract_tsv(bw)
    conf = round(sum(ln["conf"] for ln in lines) / len(lines), 1) if lines else 0.0
    q["skew_corrected_deg"] = skew if abs(skew) >= 1.0 else 0.0
    return {"lines": lines, "mean_confidence": conf, "quality": q, "sha256": digest}


def run_ocr(data: bytes) -> dict:
    digest = hashlib.sha256(data).hexdigest()
    return _ocr_cached(digest, data)
