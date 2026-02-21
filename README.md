# Code Inventory Scanner

Scan a folder for software repositories and nested projects, then export a CSV inventory.

This tool is designed for a personal code/project inventory workflow. It detects both:

- **Standalone repositories** (a repo that is itself the project)
- **Monorepos** containing **nested projects** (Python, Node, and other common marker-based project types)

The output is a CSV you can review in Excel, Numbers, or a spreadsheet tool, while still preserving useful structure like repo root, nested project relationship, and detection source.

---

## Recent updates

This version brings the project up to a stricter engineering baseline:

- Improved **PEP 8** consistency across modules
- Added/expanded **Sphinx-style docstrings**
- Strengthened **logging** across CLI, scanner, service, and CSV writer
- Added safer **path normalization** and validation
- Improved **CSV writer robustness** (path checks, better writer config)
- Improved **detector pipeline** with clearer marker handling and debug logs
- Updated **project ID generation** to use a deterministic hash (stable across runs)
- Better handling of duplicate records and nested project detection
- Service layer now supports **dependency injection** for easier testing

So now it behaves less like a quick script and more like a small tool you can actually maintain.

---

## Features

- CLI workflow with `--input` and `--output`
- Optional `--verbose` logging for troubleshooting
- Recursive scan of a root folder
- Detects Git repository roots (`.git` directory or file)
- Detects nested projects inside repositories using project markers
- Writes CSV output suitable for spreadsheet review
- Structured design (service layer, detectors, scanner, writer)
- Unit and integration tests with PyTest
- MkDocs documentation support with Mermaid diagrams

---

## Detection model

### Repository root detection
A folder is treated as a repository root if it contains:

- `.git/` directory, or
- `.git` file (common in some git layouts/worktrees)

### Nested project detection
Inside each repository, the scanner looks for project markers, including:

- **Python**
  - `pyproject.toml`
  - `setup.py`
  - `requirements.txt`
- **Node / JavaScript / TypeScript**
  - `package.json`
  - `tsconfig.json` (used to infer TypeScript)
- **Generic markers**
  - `Cargo.toml` (Rust)
  - `go.mod` (Go)
  - `*.csproj` (.NET / C#)
  - `composer.json` (PHP)

Each detected project becomes a CSV row.

---

## CSV output schema

### Core columns
- `project_id`
- `project_name`
- `project_type`
- `primary_language`
- `location`
- `github_url`
- `status`
- `keywords`
- `purpose`

### Supporting columns
- `repo_root`
- `is_repo_root`
- `parent_repo`
- `detection_source`

### Notes on values
- `project_id` is a **deterministic ID** generated from the normalized path.
- `keywords` are normalized and exported as a **semicolon-separated string** in CSV.
- `purpose` is currently a placeholder and defaults to blank.

---

## Installation

Use a virtual environment. You already know why, but here we are.

### 1. Create and activate a virtual environment

#### macOS / Linux
```bash
python3 -m venv .venv
source .venv/bin/activate
```

#### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install the package in editable mode

```bash
pip install -e .
```

### 3. Install development tools (recommended)

```bash
pip install -e ".[dev]"
```

---

## Usage

### Basic command
```bash
code-inventory --input "/path/to/projects" --output "/path/to/inventory.csv"
```

### Example
```bash
code-inventory \
  --input "/Volumes/Matt_files/Git" \
  --output "/Users/mattbriggs/Downloads/code_inventory.csv"
```

### Enable verbose logging
```bash
code-inventory \
  --input "/Volumes/Matt_files/Git" \
  --output "/Users/mattbriggs/Downloads/code_inventory.csv" \
  --verbose
```

---

## How the output behaves

A single monorepo can produce multiple rows:

- **1 repo-root row** (the repository itself)
- **0..N nested project rows** (projects found inside it)

For example, a repo containing `apps/frontend` and `tools/etl` may produce:

- `big_repo` (repo root)
- `frontend` (nested project)
- `etl` (nested project)

This is intentional. The point is to inventory the repo *and* the projects inside it without flattening everything into one row.

---

## Development workflow

### Run tests
```bash
pytest
```

### Run tests with coverage
```bash
pytest --cov=code_inventory --cov-report=term-missing
```

### Lint
```bash
ruff check .
```

### Type check
```bash
mypy src
```

---

## Documentation (MkDocs)

### Serve docs locally
```bash
mkdocs serve
```

Then open the local URL shown in the terminal.

### Build docs
```bash
mkdocs build
```

---

## Project structure

```text
code_inventory_scanner/
├── pyproject.toml
├── README.md
├── DESIGN.md
├── mkdocs.yml
├── docs/
│   ├── index.md
│   └── architecture.md
├── src/
│   └── code_inventory/
│       ├── __init__.py
│       ├── cli.py
│       ├── logging_config.py
│       ├── models.py
│       ├── csv_writer.py
│       ├── detectors.py
│       ├── scanner.py
│       └── service.py
└── tests/
    ├── unit/
    └── integration/
```

---

## Troubleshooting

### `Input folder does not exist`
Check the `--input` path and make sure it exists and is a directory.

### `Input path is not a directory`
You passed a file path to `--input`. The scanner expects a folder.

### CSV writes but looks sparse
That usually means the folders are not Git repos or the nested folders do not contain supported project marker files yet.

### `github_url` is blank
This is expected when:

- the repo has no remote configured
- `.git/config` cannot be read
- the repo uses a git layout where `.git` is a file and config is not directly available

### Too much output in logs
Do not use `--verbose` unless you need to troubleshoot. Debug logs are useful, but they are also a lot.

---

## Design and documentation standards

This project is maintained with:

- **PEP 8** formatting/style conventions
- **Sphinx-style docstrings**
- **Structured logging**
- **Design-pattern-oriented architecture** (detectors, factory, service orchestration)
- **PyTest** unit/integration coverage
- **MkDocs** documentation with Mermaid diagrams

See `DESIGN.md` for architecture and design details.

---

## Roadmap ideas

Likely next improvements:

- JSON output (`--format json`) to preserve arrays without CSV flattening
- `.inventoryignore` support
- Better Git remote extraction for worktrees/submodules
- README parsing to populate `purpose`
- More detector types (Swift, Java, etc.)
- Language inference by source file counts

Because once you start inventorying code projects, the next step is inevitably building a better inventory system than the one you started with.