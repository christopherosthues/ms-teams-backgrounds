"""Unit tests for image hashing and ledger load/save (FR-005, FR-006, FR-008)."""

import hashlib
import json

import main


def test_hash_image_is_stable_64_char_lowercase_hex(tmp_path):
    path = tmp_path / "a.png"
    data = b"\x89PNG\r\n\x1a\nsome-bytes"
    path.write_bytes(data)

    digest = main.hash_image(path)

    assert digest == hashlib.sha256(data).hexdigest()
    assert len(digest) == 64
    assert digest == digest.lower()


def test_hash_image_changes_when_any_byte_changes(tmp_path):
    a = tmp_path / "a.png"
    b = tmp_path / "b.png"
    a.write_bytes(b"content-one")
    b.write_bytes(b"content-two")

    assert main.hash_image(a) != main.hash_image(b)


def test_hash_image_ignores_filename(tmp_path):
    a = tmp_path / "one.png"
    b = tmp_path / "two.jpg"
    data = b"identical-content"
    a.write_bytes(data)
    b.write_bytes(data)

    assert main.hash_image(a) == main.hash_image(b)


def test_save_then_load_round_trip_preserves_entries(tmp_path):
    record = tmp_path / "added-images.json"
    entries = [
        {
            "hash": "a" * 64,
            "original_filename": "sunset.png",
            "mapped_name": "3f2a1b.jpeg",
            "added_at": "2026-11-05T14:30:00+00:00",
        },
        {
            "hash": "b" * 64,
            "original_filename": "mountain.jpg",
            "mapped_name": "9c8d7e.jpeg",
            "added_at": "2026-11-05T14:31:00+00:00",
        },
    ]

    main.save_record(record, entries)
    loaded = main.load_record(record)

    assert loaded == entries


def test_saved_file_is_pretty_printed_version_1_json_with_trailing_newline(tmp_path):
    record = tmp_path / "added-images.json"
    entry = {"hash": "c" * 64, "original_filename": "x.png", "mapped_name": "abcd.jpeg"}

    main.save_record(record, [entry])

    raw = record.read_text(encoding="utf-8")
    assert raw.endswith("\n")
    doc = json.loads(raw)
    assert doc == {"version": 1, "entries": [entry]}
    # Pretty-printed: the entries key is indented on its own line.
    assert '  "entries"' in raw


def test_save_record_creates_parent_directory(tmp_path):
    record = tmp_path / "nested" / "dir" / "added-images.json"

    main.save_record(record, [])

    assert record.is_file()
    assert main.load_record(record) == []


def test_load_missing_file_yields_empty_list_without_error(tmp_path, capsys):
    missing = tmp_path / "does-not-exist.json"

    result = main.load_record(missing)

    assert result == []
    assert capsys.readouterr().err == ""


def test_load_corrupt_json_warns_and_yields_empty_list(tmp_path, capsys):
    record = tmp_path / "added-images.json"
    record.write_text("not json at all", encoding="utf-8")

    result = main.load_record(record)

    assert result == []
    err = capsys.readouterr().err
    assert str(record) in err


def test_load_wrong_version_warns_and_yields_empty_list(tmp_path, capsys):
    record = tmp_path / "added-images.json"
    record.write_text(json.dumps({"version": 999, "entries": []}), encoding="utf-8")

    result = main.load_record(record)

    assert result == []
    assert str(record) in capsys.readouterr().err


def test_load_non_object_top_level_warns_and_yields_empty_list(tmp_path, capsys):
    record = tmp_path / "added-images.json"
    record.write_text(json.dumps([{"hash": "d" * 64}]), encoding="utf-8")

    result = main.load_record(record)

    assert result == []
    assert str(record) in capsys.readouterr().err


def test_load_ignores_unknown_extra_keys(tmp_path):
    record = tmp_path / "added-images.json"
    record.write_text(
        json.dumps(
            {
                "version": 1,
                "entries": [
                    {
                        "hash": "e" * 64,
                        "original_filename": "x.png",
                        "mapped_name": "m.jpeg",
                        "unknown_entry_key": True,
                    }
                ],
                "unknown_top_level": True,
            }
        ),
        encoding="utf-8",
    )

    entries = main.load_record(record)

    assert len(entries) == 1
    assert entries[0] == {"hash": "e" * 64, "original_filename": "x.png", "mapped_name": "m.jpeg"}
