# Quickstart Validation: Track Added Images

**Feature**: 001-track-added-images | **Date**: 2026-11-05

Runnable scenarios that prove the feature works end-to-end. Interfaces are defined in [contracts/cli.md](./contracts/cli.md) and [contracts/record-file.md](./contracts/record-file.md); field semantics in [data-model.md](./data-model.md).

## Prerequisites

- Windows with the new Microsoft Teams app installed (or at least a writable `%APPDATA%`).
- Python 3.14 venv: `python -m venv .venv` then activate it.
- Dependencies: `pip install -r requirements.txt` (add `-r requirements-dev.txt` to run the test suite).

Key paths used by these scenarios:

```text
Ledger:   %APPDATA%\ms-teams-backgrounds\added-images.json
Uploads:  %LOCALAPPDATA%\Packages\MSTeams_8wekyb3d8bbwe\LocalCache\Microsoft\MSTeams\Backgrounds\Uploads
```

## Setup (shared)

Create a scratch source directory with two distinct images and reset the ledger to a known state:

```powershell
mkdir $env:TEMP\tbg-source
# copy any two real images into $env:TEMP\tbg-source as a.png and b.jpg
Remove-Item "$env:APPDATA\ms-teams-backgrounds\added-images.json" -ErrorAction SilentlyContinue
```

## Scenario 1 — First run adds everything (US1, FR-001/FR-002)

```powershell
python main.py $env:TEMP\tbg-source
```

**Expected**: report shows `Added:` for both images; the Uploads folder gains two `<uuid>.jpeg` files plus their matching `_thumb.jpeg` files; the ledger exists and contains exactly 2 entries, each with a 64-char hash, the original filename, and the mapped name that actually appears in the Uploads folder.

## Scenario 2 — Re-run is idempotent (US1, SC-001)

```powershell
python main.py $env:TEMP\tbg-source
```

**Expected**: report shows `Skipped:` for both images and a summary of `Added 0`; the Uploads folder file count is unchanged; the ledger still has exactly 2 entries.

## Scenario 3 — Incremental add (US1, SC-004)

```powershell
# copy a third image c.png into $env:TEMP\tbg-source
python main.py $env:TEMP\tbg-source
```

**Expected**: only `c.png` is reported as added; the ledger grows from 2 to exactly 3 entries.

## Scenario 4 — Traceability (US2, SC-003)

Open `%APPDATA%\ms-teams-backgrounds\added-images.json`. For every entry, confirm `<mapped_name>` exists in the Uploads folder and maps back to a recognizable original filename — no tooling or renaming required.

## Scenario 5 — Changed image is re-added (US3, FR-005)

```powershell
# modify a.png's content (e.g., append bytes / re-save with different pixels), keeping the name
python main.py $env:TEMP\tbg-source
```

**Expected**: `a.png` is reported as added again under a *new* mapped name; the Uploads folder now holds two full-size JPEGs for it; the ledger has 4 entries total (the old `a.png` entry remains alongside the new one).

## Scenario 6 — Identical content, different names (US3)

```powershell
Copy-Item "$env:TEMP\tbg-source\a.png" "$env:TEMP\tbg-source\acopy.png"   # after Scenario 5's modification
python main.py $env:TEMP\tbg-source
```

**Expected**: `acopy.png` is skipped (its hash already exists from the modified `a.png`) — or, if run before any modification of `a.png`, exactly one of the two names is added. Either way: one physical background per distinct content hash.

## Scenario 7 — Corrupt ledger (FR-008)

```powershell
Set-Content "$env:APPDATA\ms-teams-backgrounds\added-images.json" "not json at all"
python main.py $env:TEMP\tbg-source
```

**Expected**: a clear warning on stderr naming the ledger file; exit code 0; images are treated as new and re-added; the ledger is rewritten validly.

## Scenario 8 — Failed copy is not recorded (FR-003)

```powershell
Set-Content "$env:TEMP\tbg-source\broken.jpg" "this is not an image"
python main.py $env:TEMP\tbg-source
# then fix the file and re-run
Remove-Item "$env:TEMP\tbg-source\broken.jpg"
```

**Expected**: `Failed:` line with a reason for `broken.jpg`; no ledger entry exists for it; after removal, subsequent runs report only added/skipped.

## Automated tests

```powershell
pytest tests/ -v
```

**Expected**: all unit and integration-style tests pass (dedup decisions, load/save round-trip, corrupt-ledger handling, run flow against temporary directories).

## Cleanup

These scenarios write to real user state. To reset: delete the mapped `<uuid>.jpeg` / `_thumb.jpeg` files listed in the ledger from the Uploads folder, remove `%APPDATA%\ms-teams-backgrounds\added-images.json`, and delete `$env:TEMP\tbg-source`.
