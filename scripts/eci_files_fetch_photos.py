"""Self-host the ECI Files commissioner photos: crop and resize each `self_host: true` entry in
`data/eci_files/people_media.json` into `web/public/eci-files/people/{slug}.jpg`.

Run with Pillow available (it is not a dependency of any package here):

    uv run --with pillow python scripts/eci_files_fetch_photos.py [--force]

Every photo listed is on Wikimedia Commons under the Government Open Data License - India
(docs/eci-files/PHASE4-SPEC.md section 4). This script only downloads and crops; the licence and
attribution checks already happened when `people_media.json` was written, and nothing is fetched at
request time — the site serves the file this script writes.
"""

from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
MEDIA_FILE = ROOT / "data" / "eci_files" / "people_media.json"
OUT_DIR = ROOT / "web" / "public" / "eci-files" / "people"

USER_AGENT = "neta-resume/1.0 (+https://github.com/citizen-apps-india/neta-resume; editorial)"
TIMEOUT_SECONDS = 60
TARGET_SIZE = 480
JPEG_QUALITY = 84


def _fetch(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for _attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as e:
            last_error = e
    assert last_error is not None
    raise last_error


def _crop_box(width: int, height: int, cx: float, cy: float, size: float) -> tuple[int, int, int, int]:
    """A square crop, side `size * min(width, height)`, centred at `(cx*width, cy*height)`, clamped
    inside the image."""
    side = round(size * min(width, height))
    side = max(1, min(side, width, height))
    center_x = cx * width
    center_y = cy * height
    left = round(center_x - side / 2)
    top = round(center_y - side / 2)
    left = max(0, min(left, width - side))
    top = max(0, min(top, height - side))
    return (left, top, left + side, top + side)


def _process(raw: bytes, crop: dict | None) -> Image.Image:
    image = Image.open(io.BytesIO(raw))
    image = image.convert("RGB")
    if crop is not None:
        box = _crop_box(image.width, image.height, crop["cx"], crop["cy"], crop["size"])
        image = image.crop(box)
    else:
        side = min(image.width, image.height)
        left = (image.width - side) // 2
        top = (image.height - side) // 2
        image = image.crop((left, top, left + side, top + side))

    side = image.width  # square after cropping
    if side > TARGET_SIZE:
        image = image.resize((TARGET_SIZE, TARGET_SIZE), Image.LANCZOS)
    return image


def main(argv: list[str]) -> int:
    force = "--force" in argv
    payload = json.loads(MEDIA_FILE.read_text())
    people = [p for p in payload.get("people", []) if p.get("self_host")]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for person in people:
        slug = person["slug"]
        out_path = OUT_DIR / f"{slug}.jpg"
        if out_path.exists() and not force:
            print(f"{slug}  skipped (exists)")
            continue

        raw = _fetch(person["image_url"])
        image = _process(raw, person.get("crop"))
        image.save(out_path, "JPEG", quality=JPEG_QUALITY, progressive=True, optimize=True)
        size_bytes = out_path.stat().st_size
        print(f"{slug}  {image.width}x{image.height}  {size_bytes} bytes")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
