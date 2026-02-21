"""Unit tests for the CSV inventory writer."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from code_inventory.csv_writer import CsvInventoryWriter
from code_inventory.models import ProjectInventoryRecord


def _make_record(
    project_name: str = "demo-project",
    location: str = "/tmp/demo-project",
    keywords: list[str] | None = None,
) -> ProjectInventoryRecord:
    """Create a test inventory record.

    :param project_name: Project name value.
    :type project_name: str
    :param location: Project location value.
    :type location: str
    :param keywords: Optional keyword list.
    :type keywords: list[str] | None
    :return: Test record instance.
    :rtype: ProjectInventoryRecord
    """
    return ProjectInventoryRecord(
        project_id="proj-1234567890",
        project_name=project_name,
        project_type="CLI Tool",
        primary_language="Python",
        location=location,
        github_url="https://github.com/example/demo-project",
        status="Active",
        keywords=keywords if keywords is not None else ["python", "cli"],
        purpose="Test project",
        repo_root="/tmp/demo-project",
        is_repo_root=True,
        parent_repo="",
        detection_source="python-markers",
    )


def test_write_creates_csv_with_header_and_rows(tmp_path: Path) -> None:
    """Write records and verify CSV header and row content.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    writer = CsvInventoryWriter()
    output_file = tmp_path / "inventory.csv"

    records = [
        _make_record(project_name="alpha", location="/tmp/alpha", keywords=["python", "cli"]),
        _make_record(project_name="beta", location="/tmp/beta", keywords=["python", "tool"]),
    ]

    writer.write(output_file, records)

    assert output_file.exists()

    with output_file.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == CsvInventoryWriter.FIELDNAMES
    assert len(rows) == 2

    assert rows[0]["project_name"] == "alpha"
    assert rows[0]["primary_language"] == "Python"
    assert rows[0]["keywords"] == "cli;python"  # normalized/sorted by model
    assert rows[0]["is_repo_root"] == "True"

    assert rows[1]["project_name"] == "beta"
    assert rows[1]["location"] == "/tmp/beta"
    assert rows[1]["detection_source"] == "python-markers"


def test_write_creates_missing_output_directory(tmp_path: Path) -> None:
    """Verify writer creates the output directory when missing.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    writer = CsvInventoryWriter()
    output_file = tmp_path / "nested" / "deeper" / "inventory.csv"

    writer.write(output_file, [_make_record()])

    assert output_file.exists()
    assert output_file.parent.exists()
    assert output_file.parent.is_dir()


def test_write_with_empty_records_writes_header_only(tmp_path: Path) -> None:
    """Verify writing zero records still produces a valid CSV header.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    writer = CsvInventoryWriter()
    output_file = tmp_path / "inventory.csv"

    writer.write(output_file, [])

    with output_file.open("r", encoding="utf-8", newline="") as csv_file:
        content = csv_file.read().strip()

    expected_header = ",".join(CsvInventoryWriter.FIELDNAMES)
    assert content == expected_header


def test_validate_output_path_raises_for_empty_like_name() -> None:
    """Verify validation fails for invalid output file names.

    :return: None
    :rtype: None
    """
    writer = CsvInventoryWriter()

    with pytest.raises(ValueError, match="Invalid output file path"):
        writer._validate_output_path(Path("."))

    with pytest.raises(ValueError, match="Invalid output file path"):
        writer._validate_output_path(Path(".."))


def test_validate_output_path_warns_for_non_csv_extension(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verify a warning is logged for non-.csv file extensions.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :param caplog: Pytest log capture fixture.
    :type caplog: pytest.LogCaptureFixture
    :return: None
    :rtype: None
    """
    writer = CsvInventoryWriter()
    output_file = tmp_path / "inventory.txt"

    with caplog.at_level("WARNING"):
        writer._validate_output_path(output_file)

    assert "does not use .csv extension" in caplog.text


def test_write_ignores_extra_fields_from_record_row(tmp_path: Path) -> None:
    """Verify extra keys from ``to_csv_row`` are ignored by DictWriter.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    writer = CsvInventoryWriter()
    output_file = tmp_path / "inventory.csv"

    record = _make_record(project_name="extra-field-project")

    original_to_csv_row = record.to_csv_row

    def patched_to_csv_row() -> dict[str, str]:
        """Return a CSV row with an unexpected extra key.

        :return: CSV row containing an extra field.
        :rtype: dict[str, str]
        """
        row = original_to_csv_row()
        row["unexpected_field"] = "should be ignored"
        return row

    # Monkeypatch the bound method on this instance only.
    object.__setattr__(record, "to_csv_row", patched_to_csv_row)

    writer.write(output_file, [record])

    with output_file.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["project_name"] == "extra-field-project"
    assert "unexpected_field" not in rows[0]


def test_ensure_output_directory_is_idempotent(tmp_path: Path) -> None:
    """Verify ensuring the output directory works when directory exists.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    writer = CsvInventoryWriter()
    output_file = tmp_path / "existing" / "inventory.csv"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    writer._ensure_output_directory(output_file)

    assert output_file.parent.exists()
    assert output_file.parent.is_dir()