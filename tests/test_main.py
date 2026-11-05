"""Integration-style tests for the run flow (US1: idempotent upload)."""

from pathlib import Path

import main
from PIL import Image


def make_image(path: Path, color=(200, 30, 30)) -> None:
    Image.new("RGB", (16, 12), color).save(path)


def test_first_run_adds_every_image(tmp_path, capsys):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))
    make_image(source / "b.jpg", (30, 200, 30))

    main.run(source, dest, record)

    out = capsys.readouterr().out
    assert f"Added: a.png -> " in out
    assert f"Added: b.jpg -> " in out
    assert "Done. Added 2, skipped 0, failed 0." in out

    entries = main.load_record(record)
    assert len(entries) == 2
    original_filenames = {entry["original_filename"] for entry in entries}
    assert original_filenames == {"a.png", "b.jpg"}
    for entry in entries:
        assert len(entry["hash"]) == 64
        full_path = dest / entry["mapped_name"]
        assert full_path.is_file()
        stem = Path(entry["mapped_name"]).stem
        assert (dest / f"{stem}_thumb.jpeg").is_file()


def test_first_run_records_content_hash_of_source_files(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))

    main.run(source, dest, record)

    entries = main.load_record(record)
    assert len(entries) == 1
    assert entries[0]["hash"] == main.hash_image(source / "a.png")


def test_second_run_skips_everything_and_writes_nothing(tmp_path, capsys):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))
    make_image(source / "b.jpg", (30, 200, 30))

    main.run(source, dest, record)
    first_run_files = sorted(p.name for p in dest.iterdir())
    ledger_before = record.read_text(encoding="utf-8")

    main.run(source, dest, record)
    out = capsys.readouterr().out

    assert "Skipped: a.png (already recorded)" in out
    assert "Skipped: b.jpg (already recorded)" in out
    assert "Done. Added 0, skipped 2, failed 0." in out
    assert sorted(p.name for p in dest.iterdir()) == first_run_files
    # The ledger is not rewritten when nothing was added.
    assert record.read_text(encoding="utf-8") == ledger_before


def test_incremental_add_only_adds_the_new_image(tmp_path, capsys):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))
    make_image(source / "b.jpg", (30, 200, 30))

    main.run(source, dest, record)
    capsys.readouterr()

    make_image(source / "c.png", (30, 30, 200))
    main.run(source, dest, record)
    out = capsys.readouterr().out

    assert f"Added: c.png -> " in out
    assert "Skipped: a.png (already recorded)" in out
    assert "Skipped: b.jpg (already recorded)" in out
    assert "Done. Added 1, skipped 2, failed 0." in out

    entries = main.load_record(record)
    assert len(entries) == 3
    assert {entry["original_filename"] for entry in entries} == {"a.png", "b.jpg", "c.png"}


def test_failed_copy_is_reported_and_not_recorded(tmp_path, capsys):
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))
    (source / "broken.jpg").write_bytes(b"this is not an image")

    main.run(source, dest, record)

    out = capsys.readouterr().out
    assert f"Failed: broken.jpg (" in out
    assert "Done. Added 1, skipped 0, failed 1." in out

    entries = main.load_record(record)
    assert len(entries) == 1
    assert entries[0]["original_filename"] == "a.png"


def test_run_creates_missing_destination_directory(tmp_path):
    source = tmp_path / "source"
    dest = tmp_path / "does-not-exist-yet"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))

    main.run(source, dest, record)

    assert dest.is_dir()
    entries = main.load_record(record)
    assert len(entries) == 1
    assert (dest / entries[0]["mapped_name"]).is_file()
