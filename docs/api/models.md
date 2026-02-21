# Models Module

Module: `code_inventory.models`

This module defines the core data model for inventory records.

## Class: `ProjectInventoryRecord`

A frozen dataclass representing one CSV row (one detected project).

## Responsibilities

- Hold normalized project metadata
- Normalize string fields and keywords
- Convert itself to a CSV row
- Generate deterministic project IDs

## Fields

### Core fields

- `project_id: str`
- `project_name: str`
- `project_type: str`
- `primary_language: str`
- `location: str`
- `github_url: str`
- `status: str`
- `keywords: list[str]`
- `purpose: str`

### Relationship and metadata fields

- `repo_root: str`
- `is_repo_root: bool`
- `parent_repo: str`
- `detection_source: str`

## Methods

### `__post_init__() -> None`

Normalizes field values after initialization (while preserving frozen dataclass behavior).

### Normalization performed

- trims whitespace on string fields
- normalizes `keywords`
  - strips whitespace
  - removes blanks
  - deduplicates
  - sorts alphabetically

---

### `to_csv_row() -> dict[str, str]`

Converts the record into a CSV-compatible dictionary.

### CSV behavior

- `keywords` are flattened to a semicolon-separated string
- `is_repo_root` is converted to string (`"True"` / `"False"`)

---

### `make_project_id(base_path: Path) -> str` (classmethod)

Generates a deterministic project ID from a normalized path.

### Why deterministic IDs matter

Python’s built-in `hash()` is not stable across interpreter sessions, so this method uses a path-based SHA-1 digest (truncated) instead.

This keeps project IDs stable across repeated scans.

---

### `_normalize_keywords(keywords: list[str]) -> list[str]` (staticmethod)

Internal keyword normalization helper.

## Constants

The module also defines constants for:

- keyword separator (`;`)
- project ID prefix (`proj-`)
- project ID digest length

## Model lifecycle diagram

```mermaid
flowchart TD
    A[Raw values from scanner] --> B[ProjectInventoryRecord()]
    B --> C[__post_init__ normalization]
    C --> D[Normalized record]
    D --> E[to_csv_row()]
    E --> F[CSV-compatible dict]
```

## Design notes

This class acts as a **DTO (Data Transfer Object)** and a small normalization boundary.

It keeps the scanner and writer simpler by centralizing:

- field shape
- normalization rules
- CSV row conversion
```

---

## `docs/api/csv_writer.md`

```markdown
# CSV Writer Module

Module: `code_inventory.csv_writer`

This module writes inventory records to a CSV file.

## Class: `CsvInventoryWriter`

Writes `ProjectInventoryRecord` objects to CSV using a stable field order.

## Responsibilities

- Validate output file path
- Ensure output directory exists
- Write header row
- Write record rows
- Log write progress

## CSV columns

The writer uses a fixed `FIELDNAMES` order:

1. `project_id`
2. `project_name`
3. `project_type`
4. `primary_language`
5. `location`
6. `github_url`
7. `status`
8. `keywords`
9. `purpose`
10. `repo_root`
11. `is_repo_root`
12. `parent_repo`
13. `detection_source`

## Public methods

### `write(output_file: Path, records: Sequence[ProjectInventoryRecord]) -> None`

Writes records to a CSV file.

### Behavior

1. Validate output path
2. Ensure parent directory exists
3. Open file (`utf-8`, `newline=""`)
4. Write CSV header
5. Convert each record via `to_csv_row()`
6. Write rows

### CSV writer settings

- `extrasaction="ignore"` (extra keys are ignored)
- `quoting=csv.QUOTE_MINIMAL`

## Internal helpers

### `_validate_output_path(output_file: Path) -> None`

Validates basic output path quality.

### Notes
- Warns (does not fail) if extension is not `.csv`

---

### `_ensure_output_directory(output_file: Path) -> None`

Creates parent directories as needed.

## Data boundary diagram

```mermaid
flowchart LR
    A[list[ProjectInventoryRecord]] --> B[CsvInventoryWriter.write]
    B --> C[record.to_csv_row()]
    C --> D[csv.DictWriter]
    D --> E[inventory.csv]
```

## Design notes

This module acts as an output adapter between internal model objects and the external CSV format.

Keeping CSV logic here prevents format concerns from leaking into the scanner or service layer.