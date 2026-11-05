# Implementation Plan: Track Added Images

**Branch**: `001-track-added-images` | **Date**: 2026-11-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-track-added-images/spec.md`

## Summary

Extend the existing single-script CLI tool (`main.py`) so that every image it copies into the MS Teams backgrounds folder is recorded in a persistent, human-readable ledger under `%APPDATA%` (AppData\Roaming). Each record entry stores the source file's content hash (SHA-256), its original filename, and the mapped Teams filename. On each run the script checks the ledger first and only adds images whose hash is not yet recorded — making repeated runs idempotent while preserving the existing copy/convert/thumbnail behavior unchanged.

## Technical Context

**Language/Version**: Python 3.14 (project venv); standard library `hashlib`, `json`, `pathlib`, `argparse` for the new record logic.

**Primary Dependencies**: Pillow >= 10.0 and platformdirs >= 4.0 (both existing, unchanged). No new runtime dependencies; pytest added as a dev-only dependency for tests.

**Storage**: Plain-text JSON ledger file at `%APPDATA%\ms-teams-backgrounds\added-images.json` (FR-004), written atomically (temp file + `os.replace`).

**Testing**: pytest — unit tests for hashing/record load-save/dedup decisions, and integration-style tests of the run flow using temporary directories.

**Target Platform**: Windows only (clarified in spec; Linux/macOS explicitly out of scope).

**Project Type**: CLI tool (single entry point `main.py`).

**Performance Goals**: Hashing overhead negligible for a personal utility — a full run over hundreds of images completes within seconds; no perceptible slowdown vs. the current copy-only behavior.

**Constraints**: Existing copy/convert/thumbnail behavior must be preserved exactly (spec assumption); record file must remain human-readable plain text (FR-006); failed copies are never recorded (FR-003).

**Scale/Scope**: Personal utility — tens to low-thousands of background images per user; one global ledger for all runs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

The project constitution at `.specify/memory/constitution.md` currently contains only unfilled template placeholders (no ratified principles, gates, or governance rules). There are therefore no enforceable gates to evaluate; this check passes vacuously and no Complexity Tracking entries are required. If the constitution is ratified later, re-run this gate before implementation.

**Re-check after Phase 1 design**: unchanged — constitution still contains only template placeholders; no violations introduced by the design (flat layout, stdlib-only additions, single ledger file).

## Project Structure

### Documentation (this feature)

```text
specs/001-track-added-images/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
└── contracts/           # Phase 1 output (/speckit.plan command)
    ├── cli.md           # CLI interface contract
    └── record-file.md   # Ledger file location + format contract
```

### Source Code (repository root)

```text
ms-teams-backgrounds/
├── main.py              # CLI entry point — extended with ledger-based dedup logic
├── requirements.txt     # pillow, platformdirs (unchanged)
├── requirements-dev.txt # NEW: -r requirements.txt + pytest
└── tests/               # NEW
    ├── test_record.py   # unit: hashing, record load/save, dedup decisions
    └── test_main.py     # integration-style: run flow with tmp dirs
```

**Structure Decision**: Keep the existing flat single-script layout. The ledger logic (hashing, load/save, dedup decision) is added to `main.py` as small importable functions — consistent with the current code style and keeping the tool a zero-install single file. No new packages or modules; tests live in `tests/`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations — section intentionally empty (constitution is an unfilled template).
