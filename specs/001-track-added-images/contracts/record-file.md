# Contract: Ledger File (Location & Format)

**Feature**: 001-track-added-images | **Date**: 2026-11-05

The ledger file is the tool's persistent on-disk interface. Field semantics and validation rules are defined in [../data-model.md](../data-model.md); this contract fixes where the file lives and what its bytes must look like.

## Location

```text
%APPDATA%\ms-teams-backgrounds\added-images.json
```

Resolved via `platformdirs.PlatformDirs(appname="ms-teams-backgrounds", appauthor=False, roaming=True).user_data_dir` (research R2 — explicit `roaming=True` is required because platformdirs 4.x defaults to AppData\Local). The parent directory is created if missing. The location is independent of the source directory and persists across runs (FR-004).

## Format

- **Encoding**: UTF-8, pretty-printed JSON (`indent=2`), trailing newline.
- **Schema** (research R6):

```json
{
  "version": 1,
  "entries": [
    {
      "hash": "9f2c…(64 lowercase hex chars)",
      "original_filename": "sunset.png",
      "mapped_name": "3f2a1b….jpeg",
      "added_at": "2026-11-05T14:30:00Z"
    }
  ]
}
```

- `version` MUST be the integer `1`. Any other value, missing `entries`, non-object top level, or invalid JSON makes the file **corrupt** for FR-008 purposes.
- Entry fields and their validation rules: see [../data-model.md](../data-model.md#image-record-entry).
- Unknown extra keys (top-level or per-entry) MUST be ignored on read; `added_at` is optional.

## Read/Write Semantics

| Operation | Contract |
|-----------|----------|
| Read | Missing file → empty ledger, no error. Unreadable/corrupt file → warning to stderr naming the file and cause, then empty ledger (FR-008). |
| Write | Full-file atomic rewrite: write temp file in the same directory, `os.replace` over the ledger. Never written unless at least one image was added this run. Entries are appended only after successful copy of both physical files (FR-003). |

## Consumer Expectations

- Users MAY inspect or back up the file without running the tool; it is self-describing plain text (FR-006, SC-003).
- The tool does NOT reconcile the ledger against the Teams folder: out-of-band deletions of background files do not invalidate entries (spec assumption).
