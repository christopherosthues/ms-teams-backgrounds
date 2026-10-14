"""Copy images from a source directory into the new Microsoft Teams
custom backgrounds folder, renaming them with UUIDs and converting them
to JPEG (plus a matching ``_thumb.jpeg`` thumbnail).

Destination: %LOCALAPPDATA%\\Packages\\MSTeams_8wekyb3d8bbwe\\LocalCache\\Microsoft\\MSTeams\\Backgrounds\\Uploads
"""

import argparse
import sys
import uuid
from pathlib import Path

from PIL import Image, ImageOps
from platformdirs import user_data_dir

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff", ".gif"}
JPEG_QUALITY = 90
# Teams renders upload thumbnails scaled to fit this box (width x height).
THUMB_BOX = (293, 158)


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


def process_image(image_path: Path, dest_dir: Path) -> None:
    with Image.open(image_path) as image:
        rgb = to_jpeg_compatible(image)

        name = str(uuid.uuid4())
        full_path = dest_dir / f"{name}.jpeg"
        thumb_path = dest_dir / f"{name}_thumb.jpeg"

        rgb.save(full_path, format="JPEG", quality=JPEG_QUALITY)

        size = thumbnail_size(rgb.size, THUMB_BOX)
        thumb = rgb.resize(size, Image.LANCZOS) if size != rgb.size else rgb.copy()
        thumb.save(thumb_path, format="JPEG", quality=JPEG_QUALITY)


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

    copied = 0
    for image_path in images:
        try:
            process_image(image_path, dest_dir)
        except Exception as exc:
            print(f"Skipped {image_path.name}: {exc}", file=sys.stderr)
            continue
        copied += 1
        print(f"Copied: {image_path.name}")

    print(f"\nDone. Copied {copied} image(s) to:")
    print(dest_dir)


if __name__ == "__main__":
    main()
