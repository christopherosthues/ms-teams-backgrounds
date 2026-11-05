# Feature Specification: Track Added Images

**Feature Branch**: `001-track-added-images`

**Created**: 2026-11-05

**Status**: Draft

**Input**: User description: "The script should maintain a file which contains which images with hash of the file, original filename and mapped file name for MS Teams were added. The script should check this file and add only images that are not yet added."

## Clarifications

### Session 2026-11-05

- Q: Where must the record file be stored? → A: In the AppData folder — %APPDATA% (AppData\Roaming) under Windows; since the tool targets Windows only, no other platform folders apply.
- Q: Should the script itself run on Linux and macOS — locating each platform's MS Teams backgrounds folder — or is only the record file location meant to be portable while the script remains Windows-only? → A: No — Windows-only; %APPDATA% (AppData\Roaming) is used as the record location and other platforms are disregarded entirely.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Idempotent background upload (Priority: P1)

The user runs the script to copy images into the Microsoft Teams custom backgrounds folder. On every subsequent run, the script remembers which images it has already added and only adds new ones — so re-running never creates duplicate backgrounds in Teams.

**Why this priority**: This is the core value of the feature. Without it, every run duplicates all backgrounds in Teams; with it, the tool becomes safe to run repeatedly as a "sync" operation.

**Independent Test**: Run the script once against a source directory and verify images appear in the Teams backgrounds folder along with entries in the record file. Run again without changing anything and verify no new files are created in the Teams backgrounds folder.

**Acceptance Scenarios**:

1. **Given** a source directory containing images that have never been added, **when** the user runs the script, **then** each image is copied to the Teams backgrounds folder and an entry recording its content hash, original filename, and mapped Teams filename is written to the record file.
2. **Given** a previous successful run with no changes since, **when** the user runs the script again, **then** no images are added and the Teams backgrounds folder is unchanged.
3. **Given** a source directory containing both previously-added and new images, **when** the user runs the script, **then** only the new images are added and exactly one record entry is created for each of them.

---

### User Story 2 - Traceability from original image to Teams background (Priority: P2)

The user can open the record file and see, for every image the script has added, which original filename it came from and what mapped filename now exists in the Teams backgrounds folder. This lets the user find or remove a specific background later without guessing among UUID-named files.

**Why this priority**: The record is not just an internal deduplication mechanism; its mapping data is directly useful to the user for managing their Teams backgrounds.

**Independent Test**: After adding images, open the record file and confirm each entry contains the original filename, a content hash of the source image, and the mapped Teams filename that actually exists in the backgrounds folder.

**Acceptance Scenarios**:

1. **Given** a successful run that added one or more images, **when** the user inspects the record file, **then** each added image has an entry containing its content hash, original filename, and mapped Teams filename.
2. **Given** an entry in the record file, **when** the user looks for the corresponding background in the Teams backgrounds folder, **then** a file with exactly the recorded mapped filename is present (plus its matching thumbnail).

---

### User Story 3 - Detecting changed images (Priority: P3)

If the content of an image changes after it was previously added (same original filename, different pixels), the script recognizes it as a new image and adds it again under a fresh mapped name.

**Why this priority**: Supports the realistic workflow of updating a background image in place; lower priority because first-time and incremental additions cover the primary use case.

**Independent Test**: Add an image, then modify its content (e.g., re-export with different pixels) keeping the same filename, run the script again, and verify a new mapped file is created and recorded while the old entry remains.

**Acceptance Scenarios**:

1. **Given** an image previously added under a given original filename, **when** its content changes so its hash differs and the user runs the script, **then** it is treated as a new image: copied to the Teams backgrounds folder with a fresh mapped name and recorded alongside (not replacing) the prior entry for that original filename.
2. **Given** two source files with identical content but different filenames, neither previously added, **when** the user runs the script, **then** only one of them is added — identity is based on file content, not filename.

---

### Edge Cases

- What happens when the record file does not exist yet (first run)? It is created and all images are treated as new.
- How does the system handle a corrupted or unreadable record file? The script reports a clear error message instead of crashing with an unhandled failure, and continues by treating the record as empty so the user can still add images; the problem is visible in the output.
- What happens when an image fails to be copied (e.g., unsupported format)? It is reported as skipped with the reason and no record entry is created for it, so a later retry will attempt it again.
- How does the system handle two source files with identical content? Only one copy is added; both filenames are not separately recorded as distinct images.
- What happens when the Teams backgrounds folder is missing at run time? It is created before adding, preserving existing behavior.
- What happens when a previously-added background file is deleted from the Teams folder out-of-band (e.g., by the user or an app reset)? The record still lists it as added; the script does not re-add it unless its content hash changes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST maintain a persistent record file that lists every image the script has added, with each entry containing at least: (a) a content hash of the source image file, (b) the original filename, and (c) the mapped filename used in the MS Teams backgrounds folder.
- **FR-002**: System MUST check the record file before adding an image; any image whose content hash is already recorded MUST be skipped without being copied again.
- **FR-003**: System MUST write a record entry for an image only after that image has been successfully added to the Teams backgrounds folder, so failed copies are never marked as added.
- **FR-004**: System MUST store the record file under %APPDATA% (AppData\Roaming) on Windows, at a stable location that persists across runs and is independent of the source directory used in any given run.
- **FR-005**: System MUST treat image identity as based on content hash: an unchanged image is never re-added, while an image whose content changes is added again under a new mapped name.
- **FR-006**: System MUST keep the record file human-readable and machine-parseable (plain text), so users can inspect it without running the script.
- **FR-007**: System MUST report on each run which images were added, which were skipped as already recorded, and any that failed with a reason.
- **FR-008**: System MUST handle a missing record file by creating one, and a corrupted or unreadable record file by reporting a clear error while continuing to add new images (treating the record as empty).

### Key Entities *(include if feature involves data)*

- **Image Record Entry**: One logical image addition. Attributes: content hash of the source file (identity), original filename, mapped Teams filename. A single entry covers both the full-size background and its matching thumbnail, since they share one mapped name.
- **Record File**: The persistent collection of Image Record Entries. It is the single source of truth for "which images have already been added."

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the script twice in a row with an unchanged source directory adds zero new files on the second run (fully idempotent).
- **SC-002**: 100% of images added by the script have exactly one corresponding record entry containing its content hash, original filename, and mapped Teams filename.
- **SC-003**: A user can identify, from the record file alone, which original image corresponds to any given background in the Teams backgrounds folder without opening or renaming files.
- **SC-004**: Adding N distinct images across any number of runs results in exactly N mapped backgrounds (plus their thumbnails) being created in total — no duplicates.

## Assumptions

- The record file is a single global ledger for all runs of the script (not one per source directory), because "already added" refers to what exists in the shared Teams backgrounds folder.
- Cross-platform support is out of scope: the script targets Windows only; %APPDATA% (AppData\Roaming) is the record location and no other platform folders are considered.
- The record file is stored under %APPDATA% (AppData\Roaming), outside the Teams backgrounds folder, so it survives app resets and is not mistaken for a background image. The exact subfolder and file naming follow the tool's established conventions.
- Image identity is determined solely by the content hash of the source file; renaming an unchanged image does not cause re-adding.
- One record entry represents one logical image (full-size file plus its matching thumbnail), not each physical file written.
- The script does not reconcile the record against the Teams backgrounds folder: if background files are deleted out-of-band, they remain recorded and will not be re-added unless their content hash changes.
- Existing behavior is preserved: images are converted to JPEG, renamed with a unique identifier, and given a matching thumbnail; this feature only adds the record-based skip logic around that existing flow.
