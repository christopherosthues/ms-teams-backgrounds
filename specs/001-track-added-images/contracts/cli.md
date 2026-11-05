# Contract: CLI Interface

**Feature**: 001-track-added-images | **Date**: 2026-11-05

The tool is a single-command CLI. This feature adds no new arguments; it changes the run behavior (dedup via ledger) and the per-run report (FR-007).

## Invocation

```text
python main.py [source]
```

| Argument | Default | Description |
|----------|---------|-------------|
| `source` | `<script dir>/backgrounds` | Directory containing source images. Unchanged from existing behavior. |

No new flags are introduced by this feature (research R5). The ledger path and Teams uploads directory are fixed by the tool, not configurable via CLI.

## Run Behavior Contract

For each image found in `source` (same discovery rules as today: files with supported image suffixes), the run MUST produce exactly one of three outcomes:

| Outcome | Condition | Report line prefix |
|---------|-----------|--------------------|
| Added | Hash not in ledger and copy succeeded | `Added:` |
| Skipped | Hash already in ledger (no file written) | `Skipped:` |
| Failed | Copy/conversion raised an error; no ledger entry created | `Failed:` |

The run report MUST end with a summary line stating the counts of added, skipped, and failed images, followed by the ledger file path. Example:

```text
Added: sunset.png -> 3f2a1b….jpeg
Skipped: mountain.jpg (already recorded)
Failed: broken.gif (cannot identify image file)

Done. Added 1, skipped 1, failed 1. Ledger: C:\Users\chris\AppData\Roaming\ms-teams-backgrounds\added-images.json
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Run completed (including runs where some images failed — per-image failures are reported, not fatal; unchanged from existing behavior) |
| non-zero | Fatal precondition failure: source directory missing or contains no images (unchanged from existing behavior) |

A corrupt ledger does **not** change the exit code; it produces a warning line on stderr and the run proceeds with an empty ledger (FR-008).

## Invariants

- Re-running with an unchanged `source` writes zero new files to the Teams backgrounds folder (SC-001) and leaves the ledger byte-for-byte equivalent in content.
- The CLI surface (arguments, help text intent) is otherwise unchanged from the pre-feature tool.
