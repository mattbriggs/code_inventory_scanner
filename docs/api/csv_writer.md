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