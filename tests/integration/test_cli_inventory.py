"""Integration tests for CLI-driven inventory generation."""

from __future__ import annotations

import csv
from pathlib import Path

from code_inventory.cli import EXIT_SUCCESS, main


def test_cli_generates_csv_for_standalone_and_monorepo_projects(tmp_path: Path) -> None:
    """Verify the CLI generates a CSV inventory for mixed repository layouts.

    This integration test exercises the full CLI -> service -> scanner -> CSV
    writer path using a temporary filesystem workspace containing:

    - A standalone Python repository
    - A monorepo repository root
    - A nested Node project inside the monorepo
    - A nested Python project inside the monorepo

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()

    _create_standalone_python_repo(workspace_root)
    monorepo_root = _create_monorepo_with_nested_projects(workspace_root)

    output_csv = tmp_path / "out" / "inventory.csv"

    exit_code = main(
        [
            "--input",
            str(workspace_root),
            "--output",
            str(output_csv),
        ]
    )

    assert exit_code == EXIT_SUCCESS
    assert output_csv.exists()

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert rows, "Expected CSV rows but file was empty."

    expected_columns = {
        "project_id",
        "project_name",
        "project_type",
        "primary_language",
        "location",
        "github_url",
        "status",
        "keywords",
        "purpose",
        "repo_root",
        "is_repo_root",
        "parent_repo",
        "detection_source",
    }
    assert set(rows[0].keys()) == expected_columns

    # There should be at least:
    # - standalone repo root
    # - monorepo repo root
    # - nested frontend app
    # - nested etl tool
    assert len(rows) >= 4

    rows_by_name = {row["project_name"]: row for row in rows}

    assert "standalone_tool" in rows_by_name
    assert "big_repo" in rows_by_name
    assert "frontend" in rows_by_name
    assert "etl" in rows_by_name

    standalone_row = rows_by_name["standalone_tool"]
    monorepo_row = rows_by_name["big_repo"]
    frontend_row = rows_by_name["frontend"]
    etl_row = rows_by_name["etl"]

    # Repo-root rows
    assert standalone_row["is_repo_root"] == "True"
    assert monorepo_row["is_repo_root"] == "True"
    assert standalone_row["parent_repo"] == ""
    assert monorepo_row["parent_repo"] == ""
    assert "repo-root" in standalone_row["keywords"].split(";")
    assert "repo-root" in monorepo_row["keywords"].split(";")

    # Nested rows should link back to the monorepo root
    normalized_monorepo_path = str(monorepo_root.resolve())
    assert frontend_row["is_repo_root"] == "False"
    assert etl_row["is_repo_root"] == "False"
    assert frontend_row["parent_repo"] == normalized_monorepo_path
    assert etl_row["parent_repo"] == normalized_monorepo_path
    assert frontend_row["repo_root"] == normalized_monorepo_path
    assert etl_row["repo_root"] == normalized_monorepo_path
    assert "nested-project" in frontend_row["keywords"].split(";")
    assert "nested-project" in etl_row["keywords"].split(";")

    # Detection behavior should reflect the current detector implementations
    assert frontend_row["detection_source"] == "node-markers"
    assert etl_row["detection_source"] == "python-markers"

    # Default status comes from scanner/service defaults
    assert all(row["status"] == "Active" for row in rows)

    # Basic language sanity checks
    assert frontend_row["primary_language"] in {"JavaScript", "TypeScript"}
    assert etl_row["primary_language"] == "Python"


def _create_standalone_python_repo(workspace_root: Path) -> Path:
    """Create a standalone Python repository fixture.

    :param workspace_root: Root workspace path.
    :type workspace_root: Path
    :return: Path to the created standalone repository.
    :rtype: Path
    """
    standalone_repo = workspace_root / "standalone_tool"
    standalone_repo.mkdir()

    (standalone_repo / ".git").mkdir()
    (standalone_repo / "pyproject.toml").write_text(
        "[project]\nname = 'standalone-tool'\n",
        encoding="utf-8",
    )
    (standalone_repo / "src").mkdir()

    return standalone_repo


def _create_monorepo_with_nested_projects(workspace_root: Path) -> Path:
    """Create a monorepo fixture with nested Node and Python projects.

    :param workspace_root: Root workspace path.
    :type workspace_root: Path
    :return: Path to the created monorepo.
    :rtype: Path
    """
    monorepo_root = workspace_root / "big_repo"
    monorepo_root.mkdir()

    (monorepo_root / ".git").mkdir()

    # Nested Node project
    nested_node = monorepo_root / "apps" / "frontend"
    nested_node.mkdir(parents=True)
    (nested_node / "package.json").write_text(
        '{"name":"frontend","version":"1.0.0"}\n',
        encoding="utf-8",
    )

    # Nested Python project
    nested_python = monorepo_root / "tools" / "etl"
    nested_python.mkdir(parents=True)
    (nested_python / "requirements.txt").write_text(
        "pandas\npytest\n",
        encoding="utf-8",
    )

    return monorepo_root