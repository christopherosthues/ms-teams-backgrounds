# Research: Track Added Images

**Feature**: 001-track-added-images | **Date**: 2026-11-05

All unknowns from the Technical Context were resolved locally (no external research required). Each finding follows Decision / Rationale / Alternatives.

## R1: Ledger file serialization format

**Decision**: A single pretty-printed JSON document using only the standard library `json` module, shaped as `{"version": 1, "entries": [...]}` and rewritten atomically on each run (write to a temp file in the same directory, then `os.replace`).

**Rationale**: FR-006 requires the ledger to be human-readable *and* machine-parseable plain text. JSON with `indent=2` satisfies both; it handles arbitrary filename characters natively (no delimiter/escaping problems), and the size is trivially small for this tool's scale. Atomic replace guarantees a corrupt file can only ever result from OS-level failure, not from an interrupted run — which keeps FR-008's "corrupted record" case rare and well-defined.

**Alternatives considered**:
- *CSV/TSV*: fragile with filenames containing commas, quotes, or newlines; no schema versioning possible. Rejected.
- *JSON Lines (append-only)*: avoids full-file rewrites but offers no readability advantage at this scale and complicates dedup of entries. Rejected.
- *SQLite/binary database*: violates FR-006 (not human-readable). Rejected.

## R2: Ledger file location and name under %APPDATA%

**Decision**: `%APPDATA%\ms-teams-backgrounds\added-images.json`, obtained via `platformdirs.PlatformDirs(appname="ms-teams-backgrounds", appauthor=False, roaming=True).user_data_dir`.

**Rationale**: FR-004 mandates AppData\Roaming. Empirical verification against the installed platformdirs 4.13 showed that its default `user_data_dir()` resolves to **AppData\Local**, and that passing an `appname` appends *both* `appauthor` (defaulting to the appname) and `appname`, producing a doubled folder name (`...\ms-teams-backgrounds\ms-teams-backgrounds`). Therefore Roaming requires explicit `roaming=True`, and `appauthor=False` is needed to avoid the doubling. A dedicated subfolder keeps the tool's state out of the user's general AppData root, and the `.json` extension makes FR-006 inspectability obvious.

**Alternatives considered**:
- *Raw `os.environ["APPDATA"] / "ms-teams-backgrounds"`*: simpler, but bypasses the platformdirs library already used by `main.py`; equivalent result on Windows (the only supported platform). Rejected for consistency with existing code.
- *AppData\Local (`user_data_dir()` default)*: violates FR-004 (must be Roaming). Rejected.

## R3: Content hash algorithm and input

**Decision**: SHA-256 of the raw source file bytes, computed by streaming in chunks (e.g., 1 MiB) via `hashlib.sha256`. The stored value is the lowercase hex digest.

**Rationale**: FR-005 requires content-based identity that is stable across runs and platforms. Hashing the raw bytes (not the decoded image) is cheap, lossless, and independent of Pillow's decoding behavior; SHA-256 is stdlib, collision-safe for this purpose, and its 64-char hex form is readable in a plain-text ledger. Chunked streaming avoids loading large images fully into memory.

**Alternatives considered**:
- *MD5 / SHA-1*: weaker, deprecated in security-sensitive contexts; no benefit here since SHA-256 costs nothing extra. Rejected.
- *Hash of the decoded/converted image*: expensive (full decode per run) and couples identity to conversion behavior. Rejected.

## R4: Corrupted/unreadable ledger handling (FR-008)

**Decision**: On any read or parse failure, print a clear warning to stderr naming the file and the error, then continue with an empty in-memory ledger (all images treated as new). Writes always go through the atomic temp-file + `os.replace` path.

**Rationale**: Matches the spec's edge-case requirement exactly ("reports a clear error message instead of crashing… continues by treating the record as empty"). Atomic writes make corruption unlikely; when it does happen, the user loses dedup state for one run (worst case: duplicates) but never loses the ability to add images.

**Alternatives considered**:
- *Fail hard on corrupt ledger*: blocks the tool until the user deletes a file — disproportionate for a personal utility. Rejected.
- *Auto-backup the corrupt file before overwriting*: nice-to-have, adds complexity without spec-mandated value; can be added later if needed. Deferred.

## R5: Testing strategy and testability seams

**Decision**: pytest with `tmp_path` fixtures. Refactor `main.py`'s orchestration into small importable functions — `hash_image(path) -> str`, `load_record(path) -> list[dict]`, `save_record(path, entries) -> None`, and a run orchestrator that takes explicit `dest_dir`/`record_path` arguments — so tests exercise the real logic against temporary directories without touching `%APPDATA%` or the live Teams folder. The CLI entry point (`main()`) wires in the real paths unchanged.

**Rationale**: The existing code already accepts `dest_dir` as a parameter in `process_image`, establishing this injection pattern. It lets quickstart validation and automated tests share one code path, and keeps the tool's runtime surface (CLI arguments) exactly as specified — no new flags required by the spec.

**Alternatives considered**:
- *Environment-variable overrides for paths*: adds CLI surface area not required by the spec; function parameters are sufficient. Rejected.
- *Monkeypatching `teams_uploads_dir()`/`user_data_dir` in tests*: works but couples tests to module internals; explicit parameters are cleaner. Rejected.

## R6: Ledger schema versioning

**Decision**: Top-level object `{"version": 1, "entries": [...]}` where each entry is `{"hash", "original_filename", "mapped_name"}` (plus optional `added_at` ISO-8601 timestamp). Unknown top-level keys are ignored on read; a missing or unsupported `version` triggers the FR-008 corrupt-ledger path.

**Rationale**: Gives forward-compatible evolution without breaking FR-006 readability, and makes "unreadable" (FR-008) precisely defined: valid JSON with an unrecognized schema is treated as corrupted rather than silently misparsed.

**Alternatives considered**:
- *Flat array of entries*: simpler today, but no place to put a version marker; future changes would be breaking. Rejected.
