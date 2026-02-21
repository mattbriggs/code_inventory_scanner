"""Filesystem scanner for repositories and nested projects."""

from __future__ import annotations

import configparser
import logging
from pathlib import Path
from typing import Final, Sequence

from code_inventory.detectors import DetectionResult, ProjectDetector
from code_inventory.models import ProjectInventoryRecord

_LOG = logging.getLogger(__name__)

IGNORED_DIR_NAMES: Final[set[str]] = {
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    ".git",
    ".idea",
    ".vscode",
    "dist",
    "build",
}

DEFAULT_STATUS: Final[str] = "Active"


class RepositoryScanner:
    """Scan folders for repositories and nested projects."""

    def __init__(self, detectors: Sequence[ProjectDetector]) -> None:
        """Initialize the scanner.

        :param detectors: Detector strategies used to classify project folders.
        :type detectors: Sequence[ProjectDetector]
        """
        self._detectors: list[ProjectDetector] = list(detectors)

    def scan(self, root_folder: Path) -> list[ProjectInventoryRecord]:
        """Scan a root folder and return inventory records.

        :param root_folder: Root folder to scan.
        :type root_folder: Path
        :return: Inventory records sorted by location.
        :rtype: list[ProjectInventoryRecord]
        """
        normalized_root = root_folder.expanduser().resolve()
        _LOG.info("Scanning root folder: %s", normalized_root)

        records: list[ProjectInventoryRecord] = []
        seen_paths: set[Path] = set()

        repo_roots = self._find_repo_roots(normalized_root)
        _LOG.info("Detected %d repository root(s)", len(repo_roots))

        for repo_root in repo_roots:
            _LOG.info("Processing repository root: %s", repo_root)
            github_url = self._extract_github_url(repo_root)

            repo_record = self._make_repo_root_record(repo_root, github_url)
            self._append_if_new(records, seen_paths, repo_record)

            nested_records = self._scan_nested_projects(repo_root, github_url)
            for nested_record in nested_records:
                self._append_if_new(records, seen_paths, nested_record)

        sorted_records = sorted(records, key=lambda item: item.location.lower())
        _LOG.info("Scan complete. Returning %d inventory record(s).", len(sorted_records))
        return sorted_records

    def _append_if_new(
        self,
        records: list[ProjectInventoryRecord],
        seen_paths: set[Path],
        record: ProjectInventoryRecord,
    ) -> None:
        """Append a record only if its location has not already been seen.

        :param records: Output record list.
        :type records: list[ProjectInventoryRecord]
        :param seen_paths: Set of normalized paths already recorded.
        :type seen_paths: set[Path]
        :param record: Candidate record to append.
        :type record: ProjectInventoryRecord
        :return: None
        :rtype: None
        """
        record_path = Path(record.location).expanduser().resolve()
        if record_path in seen_paths:
            _LOG.debug("Skipping duplicate record for path: %s", record_path)
            return

        records.append(record)
        seen_paths.add(record_path)
        _LOG.debug("Added inventory record for path: %s", record_path)

    def _find_repo_roots(self, root_folder: Path) -> list[Path]:
        """Find Git repository roots under a folder.

        A repository root is any folder containing a ``.git`` directory or file.

        :param root_folder: Root folder to inspect.
        :type root_folder: Path
        :return: Repository root paths.
        :rtype: list[Path]
        """
        repo_roots: list[Path] = []

        for folder in self._walk_dirs(root_folder):
            git_path = folder / ".git"
            if git_path.is_dir() or git_path.is_file():
                repo_roots.append(folder)
                _LOG.debug("Repository root detected: %s", folder)

        return repo_roots

    def _scan_nested_projects(
        self,
        repo_root: Path,
        github_url: str,
    ) -> list[ProjectInventoryRecord]:
        """Scan inside a repository for nested projects.

        :param repo_root: Repository root.
        :type repo_root: Path
        :param github_url: GitHub URL inferred from repo config.
        :type github_url: str
        :return: Nested project records.
        :rtype: list[ProjectInventoryRecord]
        """
        records: list[ProjectInventoryRecord] = []

        for folder in self._walk_dirs(repo_root):
            if folder == repo_root:
                continue

            detection = self._detect_project(folder)
            if detection is None:
                continue

            record = self._build_record(
                project_path=folder,
                repo_root=repo_root,
                parent_repo=repo_root,
                is_repo_root=False,
                github_url=github_url,
                detection=detection,
            )
            records.append(record)
            _LOG.debug(
                "Nested project detected: path=%s source=%s",
                folder,
                detection.detection_source,
            )

        return records

    def _detect_project(self, folder: Path) -> DetectionResult | None:
        """Run detector strategies against a folder.

        :param folder: Folder to inspect.
        :type folder: Path
        :return: Detection result if a detector matches; otherwise ``None``.
        :rtype: DetectionResult | None
        """
        for detector in self._detectors:
            try:
                result = detector.detect(folder)
            except OSError as exc:
                _LOG.debug(
                    "Detector '%s' failed on folder '%s': %s",
                    detector.__class__.__name__,
                    folder,
                    exc,
                )
                continue

            if result is not None:
                _LOG.debug(
                    "Detector '%s' matched folder '%s' with source '%s'",
                    detector.__class__.__name__,
                    folder,
                    result.detection_source,
                )
                return result

        return None

    def _make_repo_root_record(
        self,
        repo_root: Path,
        github_url: str,
    ) -> ProjectInventoryRecord:
        """Create the repository-root inventory record.

        If the repo root also contains known project markers, the record is
        classified by those markers. Otherwise it is recorded as a generic
        repository.

        :param repo_root: Repository root path.
        :type repo_root: Path
        :param github_url: GitHub URL inferred from Git config.
        :type github_url: str
        :return: Inventory record for the repository root.
        :rtype: ProjectInventoryRecord
        """
        detection = self._detect_project(repo_root)
        if detection is None:
            detection = DetectionResult(
                project_type="Repository",
                primary_language="Unknown",
                keywords=["git", "repository"],
                detection_source="repo-root",
            )

        return self._build_record(
            project_path=repo_root,
            repo_root=repo_root,
            parent_repo=None,
            is_repo_root=True,
            github_url=github_url,
            detection=detection,
        )

    def _build_record(
        self,
        project_path: Path,
        repo_root: Path,
        parent_repo: Path | None,
        is_repo_root: bool,
        github_url: str,
        detection: DetectionResult,
    ) -> ProjectInventoryRecord:
        """Create a project inventory record.

        :param project_path: Detected project path.
        :type project_path: Path
        :param repo_root: Repository root path.
        :type repo_root: Path
        :param parent_repo: Parent repo path for nested projects, or ``None``.
        :type parent_repo: Path | None
        :param is_repo_root: Whether the record represents the repo root.
        :type is_repo_root: bool
        :param github_url: GitHub URL.
        :type github_url: str
        :param detection: Detection result.
        :type detection: DetectionResult
        :return: Inventory record.
        :rtype: ProjectInventoryRecord
        """
        normalized_project_path = project_path.expanduser().resolve()
        normalized_repo_root = repo_root.expanduser().resolve()

        keywords = list(detection.keywords)
        keywords.append("repo-root" if is_repo_root else "nested-project")

        parent_repo_value = ""
        if parent_repo is not None:
            parent_repo_value = str(parent_repo.expanduser().resolve())

        record = ProjectInventoryRecord(
            project_id=ProjectInventoryRecord.make_project_id(normalized_project_path),
            project_name=normalized_project_path.name,
            project_type=detection.project_type,
            primary_language=detection.primary_language,
            location=str(normalized_project_path),
            github_url=github_url,
            status=DEFAULT_STATUS,
            keywords=keywords,
            purpose="",
            repo_root=str(normalized_repo_root),
            is_repo_root=is_repo_root,
            parent_repo=parent_repo_value,
            detection_source=detection.detection_source,
        )

        _LOG.debug(
            "Built record: name=%s path=%s repo_root=%s is_repo_root=%s",
            record.project_name,
            record.location,
            record.repo_root,
            record.is_repo_root,
        )
        return record

    def _walk_dirs(self, root_folder: Path) -> list[Path]:
        """Walk directories recursively while pruning ignored folders.

        This method returns a deterministic, sorted list of directories and
        excludes known cache/build directories.

        :param root_folder: Root folder to walk.
        :type root_folder: Path
        :return: List of directories, including the root folder when valid.
        :rtype: list[Path]
        """
        normalized_root = root_folder.expanduser().resolve()
        output: list[Path] = []

        if not normalized_root.exists():
            _LOG.warning("Walk requested for non-existent folder: %s", normalized_root)
            return output

        if not normalized_root.is_dir():
            _LOG.warning("Walk requested for non-directory path: %s", normalized_root)
            return output

        output.append(normalized_root)

        try:
            for path in sorted(normalized_root.rglob("*")):
                if not path.is_dir():
                    continue
                if self._should_ignore_dir(path):
                    continue
                output.append(path)
        except OSError as exc:
            _LOG.warning("Error while traversing '%s': %s", normalized_root, exc)

        return output

    def _should_ignore_dir(self, path: Path) -> bool:
        """Return whether a directory should be ignored during traversal.

        :param path: Directory path to evaluate.
        :type path: Path
        :return: ``True`` if the directory should be ignored; otherwise ``False``.
        :rtype: bool
        """
        return any(part in IGNORED_DIR_NAMES for part in path.parts)

    def _extract_github_url(self, repo_root: Path) -> str:
        """Extract the primary remote URL from Git config when available.

        This reads ``.git/config`` for standard repositories. For worktrees or
        submodules where ``.git`` is a file, no config is read and an empty
        string is returned.

        :param repo_root: Repository root path.
        :type repo_root: Path
        :return: Normalized remote URL or an empty string.
        :rtype: str
        """
        git_path = repo_root / ".git"
        config_path: Path | None = None

        if git_path.is_dir():
            config_path = git_path / "config"
        elif git_path.is_file():
            _LOG.debug(
                "Skipping git remote extraction for git-file repo layout: %s",
                repo_root,
            )
            return ""

        if config_path is None or not config_path.exists():
            _LOG.debug("No git config found for repository: %s", repo_root)
            return ""

        parser = configparser.ConfigParser()
        try:
            parser.read(config_path, encoding="utf-8")
        except (configparser.Error, OSError) as exc:
            _LOG.debug("Failed to parse git config for '%s': %s", repo_root, exc)
            return ""

        for section in parser.sections():
            if not section.startswith("remote "):
                continue

            url = parser.get(section, "url", fallback="").strip()
            if url:
                normalized_url = self._normalize_remote_url(url)
                _LOG.debug(
                    "Extracted remote URL for '%s': raw=%s normalized=%s",
                    repo_root,
                    url,
                    normalized_url,
                )
                return normalized_url

        _LOG.debug("No remote URL found in git config for repository: %s", repo_root)
        return ""

    @staticmethod
    def _normalize_remote_url(url: str) -> str:
        """Normalize common remote URL formats into HTTPS when possible.

        Currently normalizes common GitHub SSH/HTTPS forms and strips the
        trailing ``.git`` suffix.

        :param url: Raw remote URL.
        :type url: str
        :return: Normalized URL.
        :rtype: str
        """
        normalized = url.strip()

        if normalized.startswith("git@github.com:"):
            repo = normalized.split("git@github.com:", maxsplit=1)[1]
            if repo.endswith(".git"):
                repo = repo[:-4]
            return f"https://github.com/{repo}"

        if normalized.startswith("https://github.com/") and normalized.endswith(".git"):
            return normalized[:-4]

        return normalized