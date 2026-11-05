"""Tests for ledger traceability (US2): the record file alone maps every
original image to the exact background in the Teams backgrounds folder."""

import json
from datetime import datetime
from pathlib import Path

import main
from PIL import Image


def make_image(path: Path, color) -> None:
    Image.new("RGB", (16, 12), color).save(path)


def test_ledger_entries_map_to_existing_files(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "sunset.png", (200, 30, 30))
    make_image(source / "mountain.jpg", (30, 200, 30))

    main.run(source, dest, record)

    # The ledger is plain JSON inspectable without the tool.
    raw = record.read_text(encoding="utf-8")
    doc = json.loads(raw)
    assert doc["version"] == 1
    entries = doc["entries"]
    assert len(entries) == 2

    for entry in entries:
        # Required fields present and well-formed (data-model.md).
        assert isinstance(entry["hash"], str)
        assert len(entry["hash"]) == 64
        assert set(entry["hash"]) <= set("0123456789abcdef")
        assert entry["original_filename"] in {"sunset.png", "mountain.jpg"}
        # The mapped file exists alongside its matching thumbnail.
        mapped = dest / entry["mapped_name"]
        assert mapped.is_file()
        stem = Path(entry["mapped_name"]).stem
        assert (dest / f"{stem}_thumb.jpeg").is_file()


def test_entry_field_set_is_exactly_the_recorded_fields(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "sunset.png", (200, 30, 30))

    main.run(source, dest, record)

    entries = json.loads(record.read_text(encoding="utf-8"))["entries"]
    assert len(entries) == 1
    # No extra fields beyond the recorded set (data-model.md; T010).
    assert set(entries[0]) == {"hash", "original_filename", "mapped_name", "added_at"}


def test_added_at_is_valid_iso_8601_when_present(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "sunset.png", (200, 30, 30))

    main.run(source, dest, record)

    entries = json.loads(record.read_text(encoding="utf-8"))["entries"]
    for entry in entries:
        if "added_at" in entry:
            datetime.fromisoformat(entry["added_at"])  # raises on invalid


def test_ledger_is_pretty_printed_with_trailing_newline(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "sunset.png", (200, 30, 30))

    main.run(source, dest, record)

    raw = record.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    # Pretty-printed JSON: top-level keys are indented.
    assert '  "version": 1' in raw
