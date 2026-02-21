# Scanner Module

Module: `code_inventory.scanner`

This module contains the core filesystem traversal and project inventory logic.

## Class: `RepositoryScanner`

Scans a root folder for Git repositories and nested projects.

## Responsibilities

- Find repository roots (`.git`)
- Traverse directories while skipping ignored folders
- Detect nested projects using detector strategies
- Extract GitHub remote URLs from Git config
- Build `ProjectInventoryRecord` objects
- Deduplicate results by normalized path

## Constructor

### `RepositoryScanner(detectors: Sequence[ProjectDetector])`

Accepts an ordered detector pipeline.

Detector order matters because classification is first-match-wins.

## Public methods

### `scan(root_folder: Path) -> list[ProjectInventoryRecord]`

Main entry point for scanning.

#### Behavior

1. Normalize root path
2. Find repository roots
3. Create a repo-root record for each repo
4. Scan each repo for nested projects
5. Deduplicate by normalized path
6. Return sorted records

## Internal methods

### `_append_if_new(...) -> None`

Adds a record only if its normalized location path has not already been seen.

---

### `_find_repo_roots(root_folder: Path) -> list[Path]`

Finds directories containing `.git` (directory or file).

---

### `_scan_nested_projects(repo_root: Path, github_url: str) -> list[ProjectInventoryRecord]`

Walks subfolders inside a repo and applies the detector pipeline.

---

### `_detect_project(folder: Path) -> DetectionResult | None`

Runs detectors in order until one matches.

Handles detector-level `OSError` defensively.

---

### `_make_repo_root_record(repo_root: Path, github_url: str) -> ProjectInventoryRecord`

Creates the repo-root inventory row.

If no detector matches the root folder, uses a fallback detection:

- `project_type = "Repository"`
- `primary_language = "Unknown"`

---

### `_build_record(...) -> ProjectInventoryRecord`

Builds a normalized inventory record from a `DetectionResult`.

Adds relationship metadata and extra keywords:

- `repo-root`
- `nested-project`

---

### `_walk_dirs(root_folder: Path) -> list[Path]`

Recursively traverses directories and skips ignored folder names.

Returns a deterministic sorted list of paths.

---

### `_should_ignore_dir(path: Path) -> bool`

Checks whether a directory should be skipped.

---

### `_extract_github_url(repo_root: Path) -> str`

Parses `.git/config` (when available) to extract a remote URL.

Handles parse errors and missing config gracefully.

---

### `_normalize_remote_url(url: str) -> str`

Normalizes common GitHub remote URL formats:

- SSH → HTTPS
- strips trailing `.git`

## Ignored directories

The scanner ignores common non-source and generated folders, including:

- `.git`
- `.venv`, `venv`
- `node_modules`
- `__pycache__`
- `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
- `.idea`, `.vscode`
- `build`, `dist`

## Scanner workflow diagram

```mermaid
flowchart TD
    A[scan(root_folder)] --> B[Find repo roots]
    B --> C[For each repo root]
    C --> D[Extract GitHub URL]
    C --> E[Create repo-root record]
    C --> F[Walk nested folders]
    F --> G[Run detector pipeline]
    G --> H{Matched?}
    H -- Yes --> I[Build nested record]
    H -- No --> J[Skip folder]
    E --> K[Deduplicate by path]
    I --> K
    K --> L[Return sorted records]
```

## Design notes

This module is the domain core and should remain focused on discovery and classification, not output formatting.

CSV concerns belong to `CsvInventoryWriter`.