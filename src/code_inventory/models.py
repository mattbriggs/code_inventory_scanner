"""Data models for code inventory records."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

_LOG = logging.getLogger(__name__)

KEYWORD_SEPARATOR: Final[str] = ";"
PROJECT_ID_PREFIX: Final[str] = "proj-"
PROJECT_ID_HEX_LENGTH: Final[int] = 10


@dataclass(frozen=True)
class ProjectInventoryRecord:
    """Represent a single inventory row for a detected project.

    :param project_id: Stable identifier for the project record.
    :type project_id: str
    :param project_name: Human-readable project name.
    :type project_name: str
    :param project_type: Project classification (for example, ``CLI Tool``).
    :type project_type: str
    :param primary_language: Primary implementation language.
    :type primary_language: str
    :param location: Filesystem path for the project.
    :type location: str
    :param github_url: GitHub URL if available.
    :type github_url: str
    :param status: Project lifecycle status (for example, ``Active``).
    :type status: str
    :param keywords: Keyword tags describing the project.
    :type keywords: list[str]
    :param purpose: Short project description or purpose statement.
    :type purpose: str
    :param repo_root: Repository root path associated with the project.
    :type repo_root: str
    :param is_repo_root: Whether this record represents the repository root.
    :type is_repo_root: bool
    :param parent_repo: Parent repository path for nested projects.
    :type parent_repo: str
    :param detection_source: Detector/rule that classified the project.
    :type detection_source: str
    """

    project_id: str
    project_name: str
    project_type: str
    primary_language: str
    location: str
    github_url: str
    status: str
    keywords: list[str] = field(default_factory=list)
    purpose: str = ""
    repo_root: str = ""
    is_repo_root: bool = False
    parent_repo: str = ""
    detection_source: str = ""

    def __post_init__(self) -> None:
        """Normalize fields after initialization.

        This method trims whitespace from string fields and normalizes keywords
        to a deduplicated, sorted list while preserving a frozen dataclass.

        :return: None
        :rtype: None
        """
        normalized_keywords = self._normalize_keywords(self.keywords)

        object.__setattr__(self, "project_id", self.project_id.strip())
        object.__setattr__(self, "project_name", self.project_name.strip())
        object.__setattr__(self, "project_type", self.project_type.strip())
        object.__setattr__(self, "primary_language", self.primary_language.strip())
        object.__setattr__(self, "location", self.location.strip())
        object.__setattr__(self, "github_url", self.github_url.strip())
        object.__setattr__(self, "status", self.status.strip())
        object.__setattr__(self, "purpose", self.purpose.strip())
        object.__setattr__(self, "repo_root", self.repo_root.strip())
        object.__setattr__(self, "parent_repo", self.parent_repo.strip())
        object.__setattr__(self, "detection_source", self.detection_source.strip())
        object.__setattr__(self, "keywords", normalized_keywords)

    def to_csv_row(self) -> dict[str, str]:
        """Convert the record into a CSV-compatible dictionary.

        :return: CSV row mapping for ``csv.DictWriter``.
        :rtype: dict[str, str]
        """
        row = {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_type": self.project_type,
            "primary_language": self.primary_language,
            "location": self.location,
            "github_url": self.github_url,
            "status": self.status,
            "keywords": KEYWORD_SEPARATOR.join(self.keywords),
            "purpose": self.purpose,
            "repo_root": self.repo_root,
            "is_repo_root": str(self.is_repo_root),
            "parent_repo": self.parent_repo,
            "detection_source": self.detection_source,
        }
        _LOG.debug("Converted project record to CSV row: %s", self.project_name)
        return row

    @classmethod
    def make_project_id(cls, base_path: Path) -> str:
        """Create a stable project ID from a filesystem path.

        This ID is deterministic across runs for the same normalized path. It
        avoids Python's built-in ``hash()`` randomization behavior.

        :param base_path: Path for the detected project.
        :type base_path: Path
        :return: Stable project identifier.
        :rtype: str
        """
        normalized_path = str(base_path.expanduser().resolve()).replace("\\", "/")
        digest = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()
        project_id = f"{PROJECT_ID_PREFIX}{digest[:PROJECT_ID_HEX_LENGTH]}"

        _LOG.debug(
            "Generated project ID '%s' for path '%s'",
            project_id,
            normalized_path,
        )
        return project_id

    @staticmethod
    def _normalize_keywords(keywords: list[str]) -> list[str]:
        """Normalize keyword values for consistent storage and CSV export.

        Normalization trims whitespace, removes empty values, de-duplicates,
        and sorts alphabetically for stable output.

        :param keywords: Raw keyword list.
        :type keywords: list[str]
        :return: Normalized keyword list.
        :rtype: list[str]
        """
        cleaned = {
            keyword.strip()
            for keyword in keywords
            if isinstance(keyword, str) and keyword.strip()
        }
        return sorted(cleaned)