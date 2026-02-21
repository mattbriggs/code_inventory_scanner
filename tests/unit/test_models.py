"""Unit tests for code inventory data models."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

from code_inventory.models import (
    KEYWORD_SEPARATOR,
    PROJECT_ID_HEX_LENGTH,
    PROJECT_ID_PREFIX,
    ProjectInventoryRecord,
)


def _make_record(**overrides: object) -> ProjectInventoryRecord:
    """Create a baseline project inventory record for tests.

    :param overrides: Field overrides for the record constructor.
    :type overrides: object
    :return: Test record instance.
    :rtype: ProjectInventoryRecord
    """
    data: dict[str, object] = {
        "project_id": " proj-abc123 ",
        "project_name": " demo-project ",
        "project_type": " CLI Tool ",
        "primary_language": " Python ",
        "location": " /tmp/demo-project ",
        "github_url": " https://github.com/example/demo-project ",
        "status": " Active ",
        "keywords": [" python ", "cli", "python", "", "  ", "tool"],
        "purpose": " Test project purpose ",
        "repo_root": " /tmp/demo-project ",
        "is_repo_root": True,
        "parent_repo": " ",
        "detection_source": " python-markers ",
    }
    data.update(overrides)
    return ProjectInventoryRecord(**data)


def test_post_init_normalizes_string_fields_and_keywords() -> None:
    """Verify __post_init__ trims strings and normalizes keywords.

    :return: None
    :rtype: None
    """
    record = _make_record()

    assert record.project_id == "proj-abc123"
    assert record.project_name == "demo-project"
    assert record.project_type == "CLI Tool"
    assert record.primary_language == "Python"
    assert record.location == "/tmp/demo-project"
    assert record.github_url == "https://github.com/example/demo-project"
    assert record.status == "Active"
    assert record.purpose == "Test project purpose"
    assert record.repo_root == "/tmp/demo-project"
    assert record.parent_repo == ""
    assert record.detection_source == "python-markers"

    # Trimmed, deduplicated, sorted.
    assert record.keywords == ["cli", "python", "tool"]


def test_post_init_ignores_non_string_keywords() -> None:
    """Verify keyword normalization drops non-string values safely.

    :return: None
    :rtype: None
    """
    record = _make_record(
        keywords=["python", 123, None, "  cli  ", "", "python"]  # type: ignore[list-item]
    )

    assert record.keywords == ["cli", "python"]


def test_to_csv_row_returns_expected_mapping() -> None:
    """Verify to_csv_row returns CSV-compatible values.

    :return: None
    :rtype: None
    """
    record = _make_record(
        keywords=["zeta", "alpha", "alpha"],
        is_repo_root=False,
        parent_repo=" /tmp/monorepo ",
    )

    row = record.to_csv_row()

    assert row["project_id"] == "proj-abc123"
    assert row["project_name"] == "demo-project"
    assert row["project_type"] == "CLI Tool"
    assert row["primary_language"] == "Python"
    assert row["location"] == "/tmp/demo-project"
    assert row["github_url"] == "https://github.com/example/demo-project"
    assert row["status"] == "Active"
    assert row["keywords"] == f"alpha{KEYWORD_SEPARATOR}zeta"
    assert row["purpose"] == "Test project purpose"
    assert row["repo_root"] == "/tmp/demo-project"
    assert row["is_repo_root"] == "False"
    assert row["parent_repo"] == "/tmp/monorepo"
    assert row["detection_source"] == "python-markers"


def test_to_csv_row_handles_empty_keywords() -> None:
    """Verify to_csv_row emits an empty keyword string when no keywords exist.

    :return: None
    :rtype: None
    """
    record = _make_record(keywords=[])

    row = record.to_csv_row()

    assert row["keywords"] == ""


def test_make_project_id_is_deterministic_for_same_path(tmp_path: Path) -> None:
    """Verify make_project_id returns the same value for the same path.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    project_dir = tmp_path / "demo"
    project_dir.mkdir()

    first_id = ProjectInventoryRecord.make_project_id(project_dir)
    second_id = ProjectInventoryRecord.make_project_id(project_dir)

    assert first_id == second_id


def test_make_project_id_differs_for_different_paths(tmp_path: Path) -> None:
    """Verify make_project_id differs for different normalized paths.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    project_a = tmp_path / "alpha"
    project_b = tmp_path / "beta"
    project_a.mkdir()
    project_b.mkdir()

    id_a = ProjectInventoryRecord.make_project_id(project_a)
    id_b = ProjectInventoryRecord.make_project_id(project_b)

    assert id_a != id_b


def test_make_project_id_uses_expected_prefix_and_length(tmp_path: Path) -> None:
    """Verify project IDs use the configured prefix and hex length.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    project_dir = tmp_path / "demo"
    project_dir.mkdir()

    project_id = ProjectInventoryRecord.make_project_id(project_dir)

    assert project_id.startswith(PROJECT_ID_PREFIX)
    assert len(project_id) == len(PROJECT_ID_PREFIX) + PROJECT_ID_HEX_LENGTH


def test_make_project_id_normalizes_equivalent_paths(tmp_path: Path) -> None:
    """Verify equivalent paths resolve to the same project ID.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    project_dir = tmp_path / "demo"
    project_dir.mkdir()

    path_one = project_dir
    path_two = project_dir / "."

    id_one = ProjectInventoryRecord.make_project_id(path_one)
    id_two = ProjectInventoryRecord.make_project_id(path_two)

    assert id_one == id_two


def test_normalize_keywords_staticmethod_sorts_dedupes_and_trims() -> None:
    """Verify _normalize_keywords trims, deduplicates, and sorts values.

    :return: None
    :rtype: None
    """
    normalized = ProjectInventoryRecord._normalize_keywords(
        [" beta ", "alpha", "beta", " ", "", "gamma"]
    )

    assert normalized == ["alpha", "beta", "gamma"]


def test_normalize_keywords_returns_empty_list_for_empty_input() -> None:
    """Verify _normalize_keywords returns an empty list for empty input.

    :return: None
    :rtype: None
    """
    assert ProjectInventoryRecord._normalize_keywords([]) == []


def test_project_inventory_record_is_frozen() -> None:
    """Verify the dataclass is frozen after initialization.

    :return: None
    :rtype: None
    """
    record = _make_record()

    try:
        record.project_name = "changed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("Expected FrozenInstanceError when mutating frozen dataclass")