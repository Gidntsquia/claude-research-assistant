#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pymupdf"]
# ///
"""Make a page-image copy of a PDF: every page a JPEG at 130 dpi, no text layer.

    uv run tools/make_scanned.py test-set/caprolace.pdf test-set/caprolace-scanned.pdf [--dpi 130]

Stands in for a scanned older article whose true text we hold (the source PDF).
"""
import argparse

import pymupdf


def make_scanned(src: str, dst: str, dpi: int = 130, quality: int = 70) -> int:
    out = pymupdf.open()
    with pymupdf.open(src) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            new = out.new_page(width=page.rect.width, height=page.rect.height)
            new.insert_image(new.rect, stream=pix.tobytes("jpeg", jpg_quality=quality))
    out.set_metadata({})            # same bytes on every run: no creation date
    out.save(dst, garbage=4, deflate=True, no_new_id=True)
    n = len(out)
    out.close()
    return n


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--dpi", type=int, default=130)
    a = ap.parse_args()
    print(f"{a.dst}: {make_scanned(a.src, a.dst, a.dpi)} pages at {a.dpi} dpi")
