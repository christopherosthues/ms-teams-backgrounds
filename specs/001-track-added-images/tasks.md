# Tasks: Track Added Images

**Input**: Design documents from `/specs/001-track-added-images/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Included — plan.md commits to pytest and quickstart.md defines an automated-test scenario.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `main.py` at repository root; `tests/` at repository root (per plan.md — flat single-script layout, no new packages).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create `requirements-dev.txt` at repo root containing `-r requirements.txt` and `pytest`, then install it into the project venv (`pip install -r requirements-dev.txt`) so pytest is available for all later phases.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 Implement `hash_image(image_path) -> str` in `main.py`: SHA-256 of the raw file bytes, streamed in 1 MiB chunks via `hashlib`, returning the lowercase hex digest (research.md R3).
- [X] T003 Implement `record_file_path() -> Path` in `main.py`: resolves `%APPDATA%\ms-teams-backgrounds\added-images.json` using `platformdirs.PlatformDirs(appname="ms-teams-backgrounds", appauthor=False, roaming=True).user_data_dir` — explicit `roaming=True` is required because platformdirs 4.x defaults to AppData\Local (research.md R2; contracts/record-file.md).
- [X] T004 Implement `load_record(path) -> list[dict]` and `save_record(path, entries)` in `main.py`: schema v1 document `{"version": 1, "entries": [...]}`; pretty-printed JSON (`indent=2`), UTF-8, trailing newline; writes are atomic (temp file in the same directory + `os.replace`) and only performed when at least one entry is added; missing file returns an empty list; corrupt/unreadable/unsupported-version files print a clear warning to stderr naming the file and cause, then return an empty list (research.md R4/R6; contracts/record-file.md).
- [X] T005 Write unit tests in `tests/test_record.py`: `hash_image` returns a stable 64-character lowercase hex digest for identical content and a different digest when any byte changes; `load_record`/`save_record` round-trip preserves entries exactly (order and fields); missing file yields `[]`; corrupt JSON, wrong `version`, and non-object top level each yield a warning plus `[]` (FR-008).

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Idempotent Background Upload (Priority: P1) 🎯 MVP

**Goal**: A run adds only images not yet recorded, writes ledger entries only after successful copies, and reports per-image outcomes.

**Independent Test**: Run twice against a scratch source directory; the second run reports `Added 0` and writes zero new files to the destination folder.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T006 [US1] Write tests in `tests/test_main.py` covering: first run adds every image (full-size JPEG + `_thumb.jpeg` created and one ledger entry per image); re-run skips everything with zero new destination files (SC-001); a third image added later is the only one added on the next run (SC-004). Use `tmp_path` for destination/ledger paths injected into the orchestrator `run(source_dir, dest_dir, record_path)` defined in T007.

### Implementation for User Story 1

- [X] T007 [US1] Refactor orchestration in `main.py` into `run(source_dir, dest_dir, record_path)`: load the ledger once; skip any image whose hash is already recorded (FR-002); modify `process_image` to return the generated mapped base name so `run()` can append an entry `{hash, original_filename, mapped_name}` only after both physical files were successfully written (FR-003); `main()` wires in the real paths from T003 and existing behavior.
- [X] T008 [US1] Implement the per-run report in `main.py`: one line per image prefixed `Added:`, `Skipped:` (with "already recorded"), or `Failed:` (with reason), followed by a summary line `Done. Added X, skipped Y, failed Z. Ledger: <path>`; keep exit codes — 0 on completion including runs with per-image failures, non-zero only for missing source directory or no images found (contracts/cli.md).

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Traceability from Original Image to Teams Background (Priority: P2)

**Goal**: The ledger is human-readable standalone and maps every original image to the exact background file in the Teams folder.

**Independent Test**: Open the ledger after a run; every entry's `mapped_name` exists as a file in the destination alongside its `_thumb.jpeg`, with hash, original filename, and mapped name present — no tooling required (SC-003).

### Tests for User Story 2 ⚠️

- [X] T009 [P] [US2] Write tests in `tests/test_traceability.py`: after a run the ledger is valid pretty-printed JSON parseable without the tool; every entry's `mapped_name` exists as a file in the destination alongside its `_thumb.jpeg`; entries contain `hash`, `original_filename`, and `mapped_name`, with `added_at` (when present) a valid ISO-8601 timestamp (SC-003; contracts/record-file.md).

### Implementation for User Story 2

- [X] T010 [US2] In `main.py`, have `run()` include an `added_at` ISO-8601 timestamp in each new entry and confirm the persisted entry field set is exactly `{hash, original_filename, mapped_name, added_at}` — no extra fields (data-model.md; contracts/record-file.md).

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Detecting Changed Images (Priority: P3)

**Goal**: Hash-based identity — a modified image is re-added under a fresh mapped name while its old entry remains; identical content under different names is added only once.

**Independent Test**: Modify an already-added image and re-run → new entry alongside the old one; copy an image under a second filename → exactly one addition (FR-005).

### Tests for User Story 3 ⚠️

- [X] T011 [P] [US3] Write tests in `tests/test_changed_images.py`: (a) modified content with the same original filename produces a new mapped name, preserves the prior entry, and grows the ledger by exactly one (FR-005); (b) two source files with identical content but different filenames result in exactly one added image (spec edge case).

### Implementation for User Story 3

- [X] T012 [US3] In `main.py`, ensure `run()` is strictly append-only: existing ledger entries are never mutated, replaced, or deduplicated across runs, and multiple entries may share the same `original_filename` (data-model.md state transitions); adjust the code path if any mutation exists.

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T013 Update the module docstring in `main.py` to document ledger behavior: location (`%APPDATA%\ms-teams-backgrounds\added-images.json`), idempotent re-run semantics, and the report format (contracts/cli.md).
- [X] T014 Run the full test suite (`pytest tests/ -v`) and quickstart.md scenarios 1–8 end-to-end; confirm exit codes per contracts/cli.md and clean up scratch state per the quickstart Cleanup section.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories; T005 depends on T002–T004
- **User Stories (Phases 3–5)**: All depend on Foundational phase completion
  - US1 (P1) first, then US2 and US3 may proceed in parallel (both depend only on US1's `run()`)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Requires US1's `run()` and ledger entries; independently testable once US1 checkpoint passes
- **User Story 3 (P3)**: Requires US1's `run()` append-only behavior; independent of US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Core implementation before report/integration polish
- Story complete before moving to next priority

### Parallel Opportunities

- T009 ∥ T010 (US2: new test file vs. `main.py` change)
- T011 ∥ T012 (US3: new test file vs. `main.py` verification)
- US2 and US3 phases can be worked in parallel once the US1 checkpoint passes

---

## Parallel Example: User Story 1

```bash
# Sequential — all implementation tasks touch main.py; only the test task is independent:
Task: "Write tests for first-run/re-run/incremental behavior in tests/test_main.py" (T006, written first)
Task: "Refactor orchestration into run() with dedup + entry persistence in main.py" (T007)
Task: "Implement per-run report and summary line in main.py" (T008)
```

## Parallel Example: User Story 2

```bash
# Launch together — different files, no mutual dependency:
Task: "Write traceability tests in tests/test_traceability.py" (T009)
Task: "Add added_at timestamp and fix entry field set in main.py" (T010)
```

## Parallel Example: User Story 3

```bash
# Launch together — different files, no mutual dependency:
Task: "Write changed-image tests in tests/test_changed_images.py" (T011)
Task: "Ensure append-only ledger semantics in main.py run()" (T012)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `pytest tests/` — first-run, idempotent re-run, and incremental scenarios pass; ledger exists under `%APPDATA%`

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once US1 checkpoint passes:
   - Developer A: User Story 2 (T009 ∥ T010)
   - Developer B: User Story 3 (T011 ∥ T012)
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
