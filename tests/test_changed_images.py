"""Tests for changed-image detection (US3): identity is the content hash."""

# pylint: disable=duplicate-code  # Tests intentionally mirror each other's setup.
import json

import main


def test_modified_image_is_re_added_alongside_prior_entry(tmp_path, make_image):
    """A modified image is re-added while the prior entry is preserved."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))

    main.run(source, dest, record)
    first_entries = json.loads(record.read_text(encoding="utf-8"))["entries"]
    assert len(first_entries) == 1
    original_mapped_name = first_entries[0]["mapped_name"]

    # Modify the content in place, keeping the same filename.
    make_image(source / "a.png", (30, 200, 30))

    main.run(source, dest, record)

    entries = json.loads(record.read_text(encoding="utf-8"))["entries"]
    assert len(entries) == 2
    # The prior entry is preserved unchanged (append-only ledger).
    assert entries[0] == first_entries[0]
    new_entry = entries[1]
    assert new_entry["original_filename"] == "a.png"
    assert new_entry["mapped_name"] != original_mapped_name
    assert (dest / new_entry["mapped_name"]).is_file()


def test_identical_content_different_filenames_added_once(tmp_path, capsys, make_image):
    """Identical content under different filenames is added only once."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))
    (source / "acopy.png").write_bytes((source / "a.png").read_bytes())

    main.run(source, dest, record)

    out = capsys.readouterr().out
    added_lines = [line for line in out.splitlines() if line.startswith("Added:")]
    assert len(added_lines) == 1

    entries = json.loads(record.read_text(encoding="utf-8"))["entries"]
    assert len(entries) == 1


def test_renamed_unchanged_image_is_not_re_added(tmp_path, capsys, make_image):
    """Renaming without changing content does not re-add the image."""
    source = tmp_path / "source"
    dest = tmp_path / "dest"
    record = tmp_path / "added-images.json"
    source.mkdir()
    make_image(source / "a.png", (200, 30, 30))

    main.run(source, dest, record)
    capsys.readouterr()

    # Rename without changing content.
    (source / "a.png").rename(source / "renamed.png")

    main.run(source, dest, record)
    out = capsys.readouterr().out

    assert "Skipped: renamed.png (already recorded)" in out
    entries = json.loads(record.read_text(encoding="utf-8"))["entries"]
    assert len(entries) == 1
    assert entries[0]["original_filename"] == "a.png"
