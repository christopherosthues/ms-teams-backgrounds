"""Copy images from a source directory into the new Microsoft Teams
custom backgrounds folder, renaming them with UUIDs and converting them
to JPEG (plus a matching ``_thumb.jpeg`` thumbnail).

Destination: %LOCALAPPDATA%\\Packages\\MSTeams_8wekyb3d8bbwe\\LocalCache\\Microsoft\\MSTeams\\Backgrounds\\Uploads

A persistent ledger at %APPDATA%\\ms-teams-backgrounds\\added-images.json
records every image that has been added (content hash, original filename,
mapped Teams filename). Re-running is idempotent: images whose content hash
is already recorded are skipped and no new files are written. Each run prints
one line per image prefixed ``Added:``, ``Skipped:``, or ``Failed:``, followed
by a summary line with the counts and the ledger path; exit code 0 means the
run completed (per-image failures included), non-zero only when the source
directory is missing or contains no images.
"""

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps
from platformdirs import PlatformDirs, user_data_dir

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".gif"}
JPEG_QUALITY = 90
# Teams renders upload thumbnails scaled to fit this box (width x height).
THUMB_BOX = (293, 158)

RECORD_VERSION = 1


def teams_uploads_dir() -> Path:
    """Uploads folder of the new Microsoft Teams app package."""
    local_appdata = Path(user_data_dir())  # %USERPROFILE%\AppData\Local on Windows
    return (
        local_appdata
        / "Packages"
        / "MSTeams_8wekyb3d8bbwe"
        / "LocalCache"
        / "Microsoft"
        / "MSTeams"
        / "Backgrounds"
        / "Uploads"
    )


def record_file_path() -> Path:
    """Ledger file under %APPDATA% (AppData\\Roaming) tracking added images."""
    data_dir = PlatformDirs(
        appname="ms-teams-backgrounds", appauthor=False, roaming=True
    ).user_data_dir
    return Path(data_dir) / "added-images.json"


def hash_image(image_path: Path) -> str:
    """Return the SHA-256 of ``image_path``'s raw bytes as a lowercase hex digest."""
    digest = hashlib.sha256()
    with open(image_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_record(path: Path) -> list[dict]:
    """Load ledger entries from ``path``.

    A missing file yields an empty list without error. An unreadable,
    malformed, or unsupported-version file prints a warning to stderr and
    yields an empty list so the run continues treating the record as empty.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f)
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        print(
            f"Warning: record file {path} is unreadable ({exc}); treating it as empty.",
            file=sys.stderr,
        )
        return []
    if (
        not isinstance(doc, dict)
        or doc.get("version") != RECORD_VERSION
        or not isinstance(doc.get("entries"), list)
    ):
        print(
            f"Warning: record file {path} does not match the expected ledger "
            f"(version {RECORD_VERSION}); treating it as empty.",
            file=sys.stderr,
        )
        return []
    entries = []
    for raw_entry in doc["entries"]:
        if not isinstance(raw_entry, dict):
            continue
        # Unknown per-entry keys are ignored on read (contracts/record-file.md).
        entries.append(
            {
                key: raw_entry[key]
                for key in ("hash", "original_filename", "mapped_name", "added_at")
                if key in raw_entry
            }
        )
    return entries


def save_record(path: Path, entries: list[dict]) -> None:
    """Atomically rewrite the ledger at ``path`` as pretty-printed JSON (schema v1)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump({"version": RECORD_VERSION, "entries": entries}, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def to_jpeg_compatible(image: Image.Image) -> Image.Image:
    """Apply EXIF orientation and convert to a JPEG-compatible mode."""
    image = ImageOps.exif_transpose(image)
    if image.mode in ("RGB", "L"):
        return image
    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, (255, 255, 255))
    background.paste(rgba, mask=rgba.split()[-1])
    return background


def thumbnail_size(size: tuple[int, int], box: tuple[int, int]) -> tuple[int, int]:
    """Scale ``size`` to fit inside ``box``, preserving the aspect ratio."""
    width, height = size
    scale = min(box[0] / width, box[1] / height)
    return max(1, int(width * scale)), max(1, int(height * scale))


def process_image(image_path: Path, dest_dir: Path) -> str:
    """Convert ``image_path`` to a JPEG plus matching thumbnail in ``dest_dir``.

    Returns the mapped base name (the UUID); the full-size file is
    ``<name>.jpeg`` and the thumbnail ``<name>_thumb.jpeg``.
    """
    with Image.open(image_path) as image:
        rgb = to_jpeg_compatible(image)

        name = str(uuid.uuid4())
        full_path = dest_dir / f"{name}.jpeg"
        thumb_path = dest_dir / f"{name}_thumb.jpeg"

        rgb.save(full_path, format="JPEG", quality=JPEG_QUALITY)

        size = thumbnail_size(rgb.size, THUMB_BOX)
        thumb = rgb.resize(size, Image.LANCZOS) if size != rgb.size else rgb.copy()
        thumb.save(thumb_path, format="JPEG", quality=JPEG_QUALITY)

    return name


def run(source_dir: Path, dest_dir: Path, record_path: Path) -> None:
    """Copy images from ``source_dir`` into ``dest_dir``, skipping any image
    whose content hash is already recorded in the ledger at ``record_path``.

    A ledger entry is appended only after both physical files (full-size JPEG
    and thumbnail) have been written, so failed copies are never recorded.
    """
    entries = load_record(record_path)
    recorded_hashes = {
        entry["hash"] for entry in entries if isinstance(entry, dict) and "hash" in entry
    }

    dest_dir.mkdir(parents=True, exist_ok=True)

    added = skipped = failed = 0
    images = sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    for image_path in images:
        try:
            digest = hash_image(image_path)
        except OSError as exc:
            print(f"Failed: {image_path.name} ({exc})")
            failed += 1
            continue

        if digest in recorded_hashes:
            print(f"Skipped: {image_path.name} (already recorded)")
            skipped += 1
            continue

        try:
            name = process_image(image_path, dest_dir)
        except Exception as exc:
            print(f"Failed: {image_path.name} ({exc})")
            failed += 1
            continue

        entries.append(
            {
                "hash": digest,
                "original_filename": image_path.name,
                "mapped_name": f"{name}.jpeg",
                "added_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        recorded_hashes.add(digest)
        added += 1
        print(f"Added: {image_path.name} -> {name}.jpeg")

    if added:
        save_record(record_path, entries)

    print(
        f"\nDone. Added {added}, skipped {skipped}, failed {failed}. "
        f"Ledger: {record_path}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Copy images to the new Microsoft Teams backgrounds folder."
    )
    parser.add_argument(
        "source",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "backgrounds",
        help=f"Source directory containing images (default: {{script dir}}/backgrounds)",
    )
    args = parser.parse_args()

    source_dir = args.source
    if not source_dir.is_dir():
        sys.exit(f"Source directory not found: {source_dir}")

    dest_dir = teams_uploads_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)

    images = sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )
    if not images:
        sys.exit(f"No images found in {source_dir}")

    run(source_dir, dest_dir, record_file_path())


if __name__ == "__main__":
    main()
