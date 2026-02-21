# Code Inventory Scanner

Code Inventory Scanner is a CLI tool that scans a folder for Git repositories and nested software projects, then exports a structured CSV inventory.

It is designed for personal and small-team codebase inventory workflows where you want a fast, repeatable way to answer questions like:

- What projects do I have?
- Which repos are monorepos?
- What languages and project types are present?
- Which folders are nested projects inside larger repositories?

## What it detects

The scanner identifies:

- **Repository roots** (folders containing `.git`)
- **Nested projects** inside repositories using common project markers, including:
  - Python (`pyproject.toml`, `setup.py`, `requirements.txt`)
  - Node/JavaScript/TypeScript (`package.json`, `tsconfig.json`)
  - Generic markers (`Cargo.toml`, `go.mod`, `*.csproj`, `composer.json`)

## Output

The tool writes a CSV inventory with core fields such as:

- project ID
- project name
- project type
- primary language
- location
- GitHub URL
- status
- keywords

It also includes relationship fields to preserve repo structure, such as:

- repo root
- parent repo
- nested vs repo-root flag
- detection source

## Documentation guide

- **Architecture**: System design, responsibilities, and Mermaid diagrams
- **Design**: Design patterns, detection rules, and extension points (see `DESIGN.md` in the project root)
- **README**: Installation, CLI usage, and development workflow

## Quick example

```bash
code-inventory --input "/path/to/repos" --output "/path/to/inventory.csv"
```