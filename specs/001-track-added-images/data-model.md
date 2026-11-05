# Data Model: Track Added Images

**Feature**: 001-track-added-images | **Date**: 2026-11-05

## Entities

### Image Record Entry

One logical image addition to the MS Teams backgrounds folder (full-size JPEG plus its matching thumbnail — one entry covers both physical files, per spec assumption).

| Field | Type | Required | Validation / Notes |
|-------|------|----------|--------------------|
| `hash` | string | yes | Lowercase hex SHA-256 digest of the source file's raw bytes; exactly 64 characters. Identity key (FR-005). |
| `original_filename` | string | yes | Basename only (no path) of the source image at the time it was added. Non-empty. May repeat across entries when an image is re-added after its content changed (US3). |
| `mapped_name` | string | yes | Exact filename of the full-size JPEG written to the Teams backgrounds folder, e.g. `3f2a1b….jpeg`. The matching thumbnail is derived as `<stem>_thumb.jpeg`. Non-empty; unique across entries. |
| `added_at` | string (ISO-8601) | no | Timestamp of the successful addition. Optional metadata permitted by FR-001 ("at least"); ignored if absent. |

**Uniqueness constraint**: at most one entry per distinct `hash` (SC-002: exactly one record entry per added image). A changed image produces a *new* entry alongside any prior entry with the same `original_filename`.

### Record File

The persistent collection of Image Record Entries — the single source of truth for "which images have already been added" (spec Key Entities).

| Attribute | Value / Rule |
|-----------|--------------|
| Location | `%APPDATA%\ms-teams-backgrounds\added-images.json` (FR-004; see research R2) |
| Format | Pretty-printed JSON document: `{"version": 1, "entries": [...]}` (research R6) |
| Encoding | UTF-8 |
| Write policy | Full-file atomic rewrite (temp file + `os.replace`) after each run that adds at least one image; never written mid-run per entry (FR-003: entries appear only after successful copy) |
| Missing behavior | Created on first run with an empty `entries` list (spec edge case) |
| Corrupt/unreadable behavior | Clear warning to stderr, then treated as empty for the current run (FR-008; research R4) |

## Relationships

```text
Record File 1 ──── * Image Record Entry
Image Record Entry ──── physical files in Teams folder: <mapped_name> + <stem>_thumb.jpeg
```

- The ledger is global across all runs and source directories (spec assumption); there is no per-source-directory partitioning.
- Entries are append-only: nothing in the model mutates or deletes an existing entry during normal operation.

## State Transitions

The ledger has no lifecycle states beyond existence; entries are immutable once written:

```text
(image not in ledger) ── successful copy ──▶ (entry appended, persisted)
(image hash in ledger) ─────────────────────▶ skipped, no state change
(copy fails) ───────────────────────────────▶ no entry created; retryable next run (FR-003)
```

## Validation Rules (derived from requirements)

1. An image is "already added" **iff** its SHA-256 hash appears in the ledger (FR-002, FR-005). Filename alone never determines identity.
2. An entry may be persisted only after both physical files (full-size JPEG and thumbnail) have been successfully written to the Teams backgrounds folder (FR-003).
3. The ledger must always contain at most one entry per distinct hash; duplicate hashes are impossible by construction because hashing happens before the skip decision (SC-002, SC-004).
4. Every persisted entry must satisfy the field validation above so that FR-006 inspectability holds for any file produced by the tool.
