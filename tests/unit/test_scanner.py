"""Unit tests for filesystem repository scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_inventory.detectors import DetectionResult, ProjectDetector
from code_inventory.scanner import DEFAULT_STATUS, RepositoryScanner


class _StubDetector:
    """Simple detector stub for scanner tests."""

    def __init__(self, mapping: dict[Path, DetectionResult]) -> None:
        """Initialize the stub detector with path-result mappings.

        :param mapping: Mapping of folder path to detection result.
        :type mapping: dict[Path, DetectionResult]
        """
        self._mapping = {path.resolve(): result for path, result in mapping.items()}

    def detect(self, folder: Path) -> DetectionResult | None:
        """Return the mapped result for a folder, if any.

        :param folder: Folder path to inspect.
        :type folder: Path
        :return: Detection result or None.
        :rtype: DetectionResult | None
        """
        return self._mapping.get(folder.resolve())


class _RaisingDetector:
    """Detector stub that raises OSError for all folders."""

    def detect(self, folder: Path) -> DetectionResult | None:
        """Raise an OSError to simulate detector failure.

        :param folder: Folder path.
        :type folder: Path
        :return: Never returns.
        :rtype: DetectionResult | None
        :raises OSError: Always.
        """
        _ = folder
        raise OSError("simulated detector failure")


def _make_detection(
    project_type: str = "CLI Tool",
    language: str = "Python",
    keywords: list[str] | None = None,
    source: str = "python-markers",
) -> DetectionResult:
    """Create a DetectionResult for tests.

    :param project_type: Project type.
    :type project_type: str
    :param language: Primary language.
    :type language: str
    :param keywords: Keyword list.
    :type keywords: list[str] | None
    :param source: Detection source.
    :type source: str
    :return: Detection result.
    :rtype: DetectionResult
    """
    return DetectionResult(
        project_type=project_type,
        primary_language=language,
        keywords=keywords or ["python"],
        detection_source=source,
    )


def test_walk_dirs_includes_root_and_skips_ignored_dirs(tmp_path: Path) -> None:
    """Verify _walk_dirs returns root and excludes ignored directories.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    root = tmp_path / "root"
    root.mkdir()

    keep_dir = root / "src"
    keep_dir.mkdir()

    ignored_dir = root / "node_modules"
    ignored_dir.mkdir()

    nested_ignored = root / "pkg" / "__pycache__"
    nested_ignored.mkdir(parents=True)

    scanner = RepositoryScanner(detectors=[])
    walked = scanner._walk_dirs(root)

    walked_set = {p.resolve() for p in walked}

    assert root.resolve() in walked_set
    assert keep_dir.resolve() in walked_set
    assert ignored_dir.resolve() not in walked_set
    assert nested_ignored.resolve() not in walked_set


def test_walk_dirs_returns_empty_for_missing_path(tmp_path: Path) -> None:
    """Verify _walk_dirs returns empty list for non-existent path.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    missing = tmp_path / "does-not-exist"
    scanner = RepositoryScanner(detectors=[])

    assert scanner._walk_dirs(missing) == []


def test_walk_dirs_returns_empty_for_file_path(tmp_path: Path) -> None:
    """Verify _walk_dirs returns empty list for a file path.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    file_path = tmp_path / "file.txt"
    file_path.write_text("x", encoding="utf-8")

    scanner = RepositoryScanner(detectors=[])

    assert scanner._walk_dirs(file_path) == []


def test_find_repo_roots_detects_git_dir_and_git_file(tmp_path: Path) -> None:
    """Verify _find_repo_roots detects both .git directory and file layouts.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    root = tmp_path / "repos"
    root.mkdir()

    repo_a = root / "repo-a"
    (repo_a / ".git").mkdir(parents=True)

    repo_b = root / "repo-b"
    repo_b.mkdir()
    (repo_b / ".git").write_text("gitdir: /some/worktree/path\n", encoding="utf-8")

    non_repo = root / "not-a-repo"
    non_repo.mkdir()

    scanner = RepositoryScanner(detectors=[])
    repo_roots = scanner._find_repo_roots(root)

    resolved = {p.resolve() for p in repo_roots}
    assert repo_a.resolve() in resolved
    assert repo_b.resolve() in resolved
    assert non_repo.resolve() not in resolved


def test_detect_project_uses_first_matching_detector_and_skips_oserror(tmp_path: Path) -> None:
    """Verify _detect_project skips OSError detectors and returns first match.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    folder = tmp_path / "proj"
    folder.mkdir()

    expected = _make_detection(project_type="Script", source="stub-detector")
    matching_detector = _StubDetector({folder: expected})

    scanner = RepositoryScanner(detectors=[_RaisingDetector(), matching_detector])

    result = scanner._detect_project(folder)

    assert result == expected


def test_make_repo_root_record_falls_back_to_generic_repository(tmp_path: Path) -> None:
    """Verify repo-root fallback record is used when no detector matches.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").mkdir()

    scanner = RepositoryScanner(detectors=[])
    record = scanner._make_repo_root_record(repo_root, github_url="")

    assert record.project_name == "repo"
    assert record.project_type == "Repository"
    assert record.primary_language == "Unknown"
    assert record.status == DEFAULT_STATUS
    assert record.is_repo_root is True
    assert record.parent_repo == ""
    assert record.repo_root == str(repo_root.resolve())
    assert "git" in record.keywords
    assert "repository" in record.keywords
    assert "repo-root" in record.keywords
    assert record.detection_source == "repo-root"


def test_build_record_sets_repo_and_parent_relationships(tmp_path: Path) -> None:
    """Verify _build_record populates repo linkage and nested flags.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    repo_root = tmp_path / "repo"
    nested = repo_root / "packages" / "app"
    nested.mkdir(parents=True)

    scanner = RepositoryScanner(detectors=[])
    detection = _make_detection(
        project_type="Web App",
        language="TypeScript",
        keywords=["node", "typescript"],
        source="node-markers",
    )

    record = scanner._build_record(
        project_path=nested,
        repo_root=repo_root,
        parent_repo=repo_root,
        is_repo_root=False,
        github_url="https://github.com/example/repo",
        detection=detection,
    )

    assert record.project_name == "app"
    assert record.project_type == "Web App"
    assert record.primary_language == "TypeScript"
    assert record.location == str(nested.resolve())
    assert record.repo_root == str(repo_root.resolve())
    assert record.parent_repo == str(repo_root.resolve())
    assert record.is_repo_root is False
    assert record.status == DEFAULT_STATUS
    assert record.github_url == "https://github.com/example/repo"
    assert "nested-project" in record.keywords
    assert "repo-root" not in record.keywords
    assert record.detection_source == "node-markers"


def test_append_if_new_deduplicates_by_normalized_record_location(tmp_path: Path) -> None:
    """Verify _append_if_new skips duplicate locations.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    project_dir = tmp_path / "repo"
    project_dir.mkdir()

    scanner = RepositoryScanner(detectors=[])
    records = []
    seen_paths: set[Path] = set()

    detection = _make_detection()

    record_a = scanner._build_record(
        project_path=project_dir,
        repo_root=project_dir,
        parent_repo=None,
        is_repo_root=True,
        github_url="",
        detection=detection,
    )
    # Same normalized path, but reconstructed independently.
    record_b = scanner._build_record(
        project_path=project_dir / ".",
        repo_root=project_dir,
        parent_repo=None,
        is_repo_root=True,
        github_url="",
        detection=detection,
    )

    scanner._append_if_new(records, seen_paths, record_a)
    scanner._append_if_new(records, seen_paths, record_b)

    assert len(records) == 1


def test_scan_nested_projects_detects_children_and_skips_repo_root(tmp_path: Path) -> None:
    """Verify _scan_nested_projects returns only nested matches.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    repo_root = tmp_path / "repo"
    (repo_root / ".git").mkdir(parents=True)

    nested_match = repo_root / "tools" / "cli"
    nested_match.mkdir(parents=True)

    nested_non_match = repo_root / "docs"
    nested_non_match.mkdir()

    # Also make repo root look like a project, to ensure _scan_nested_projects skips root itself.
    root_detection = _make_detection(project_type="Script", source="root-marker")
    nested_detection = _make_detection(project_type="CLI Tool", source="nested-marker")

    detector = _StubDetector(
        {
            repo_root: root_detection,
            nested_match: nested_detection,
        }
    )
    scanner = RepositoryScanner(detectors=[detector])

    nested_records = scanner._scan_nested_projects(
        repo_root=repo_root,
        github_url="https://github.com/example/repo",
    )

    assert len(nested_records) == 1
    rec = nested_records[0]
    assert rec.location == str(nested_match.resolve())
    assert rec.parent_repo == str(repo_root.resolve())
    assert rec.repo_root == str(repo_root.resolve())
    assert rec.is_repo_root is False
    assert rec.detection_source == "nested-marker"


def test_extract_github_url_from_git_config_ssh_is_normalized(tmp_path: Path) -> None:
    """Verify SSH GitHub remotes are normalized to HTTPS.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    repo_root = tmp_path / "repo"
    git_dir = repo_root / ".git"
    git_dir.mkdir(parents=True)

    config_text = """
[core]
    repositoryformatversion = 0
[remote "origin"]
    url = git@github.com:example-org/demo-repo.git
    fetch = +refs/heads/*:refs/remotes/origin/*
"""
    (git_dir / "config").write_text(config_text.strip(), encoding="utf-8")

    scanner = RepositoryScanner(detectors=[])

    url = scanner._extract_github_url(repo_root)

    assert url == "https://github.com/example-org/demo-repo"


def test_extract_github_url_from_git_config_https_strips_dot_git(tmp_path: Path) -> None:
    """Verify HTTPS GitHub remotes have trailing .git removed.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    repo_root = tmp_path / "repo"
    git_dir = repo_root / ".git"
    git_dir.mkdir(parents=True)

    (git_dir / "config").write_text(
        '[remote "origin"]\nurl = https://github.com/example-org/demo-repo.git\n',
        encoding="utf-8",
    )

    scanner = RepositoryScanner(detectors=[])

    url = scanner._extract_github_url(repo_root)

    assert url == "https://github.com/example-org/demo-repo"


def test_extract_github_url_returns_empty_for_git_file_layout(tmp_path: Path) -> None:
    """Verify git-file repository layout returns empty URL.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / ".git").write_text("gitdir: /worktree/path\n", encoding="utf-8")

    scanner = RepositoryScanner(detectors=[])

    assert scanner._extract_github_url(repo_root) == ""


def test_extract_github_url_returns_empty_when_no_config_or_no_remote(tmp_path: Path) -> None:
    """Verify missing config or missing remote URL returns empty string.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    scanner = RepositoryScanner(detectors=[])

    repo_no_config = tmp_path / "repo1"
    (repo_no_config / ".git").mkdir(parents=True)
    assert scanner._extract_github_url(repo_no_config) == ""

    repo_no_remote = tmp_path / "repo2"
    git_dir = repo_no_remote / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "config").write_text("[core]\nrepositoryformatversion = 0\n", encoding="utf-8")
    assert scanner._extract_github_url(repo_no_remote) == ""


def test_normalize_remote_url_handles_known_formats() -> None:
    """Verify _normalize_remote_url normalizes expected GitHub URL formats.

    :return: None
    :rtype: None
    """
    scanner = RepositoryScanner(detectors=[])

    assert (
        scanner._normalize_remote_url("git@github.com:org/repo.git")
        == "https://github.com/org/repo"
    )
    assert (
        scanner._normalize_remote_url("https://github.com/org/repo.git")
        == "https://github.com/org/repo"
    )
    assert scanner._normalize_remote_url(" https://github.com/org/repo ") == (
        "https://github.com/org/repo"
    )
    assert scanner._normalize_remote_url("https://gitlab.com/org/repo.git") == (
        "https://gitlab.com/org/repo.git"
    )


def test_scan_end_to_end_returns_repo_root_and_nested_project(tmp_path: Path) -> None:
    """Verify scan() returns repo root and nested project records sorted by location.

    :param tmp_path: Temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    root = tmp_path / "workspace"
    repo_root = root / "repo"
    nested_project = repo_root / "packages" / "tool"

    (repo_root / ".git").mkdir(parents=True)
    nested_project.mkdir(parents=True)

    # Add git config so github_url gets populated.
    (repo_root / ".git" / "config").write_text(
        '[remote "origin"]\nurl = git@github.com:example/repo.git\n',
        encoding="utf-8",
    )

    repo_detection = _make_detection(
        project_type="Repository App",
        language="Python",
        keywords=["python", "pyproject"],
        source="repo-detect",
    )
    nested_detection = _make_detection(
        project_type="CLI Tool",
        language="Python",
        keywords=["python", "src-layout"],
        source="nested-detect",
    )

    detector = _StubDetector(
        {
            repo_root: repo_detection,
            nested_project: nested_detection,
        }
    )
    scanner = RepositoryScanner(detectors=[detector])

    records = scanner.scan(root)

    assert len(records) == 2

    # Sorted by location
    assert records[0].location <= records[1].location

    repo_record = next(r for r in records if r.is_repo_root)
    nested_record = next(r for r in records if not r.is_repo_root)

    assert repo_record.location == str(repo_root.resolve())
    assert repo_record.parent_repo == ""
    assert repo_record.repo_root == str(repo_root.resolve())
    assert repo_record.github_url == "https://github.com/example/repo"
    assert "repo-root" in repo_record.keywords
    assert repo_record.detection_source == "repo-detect"

    assert nested_record.location == str(nested_project.resolve())
    assert nested_record.parent_repo == str(repo_root.resolve())
    assert nested_record.repo_root == str(repo_root.resolve())
    assert nested_record.github_url == "https://github.com/example/repo"
    assert "nested-project" in nested_record.keywords
    assert nested_record.detection_source == "nested-detect"