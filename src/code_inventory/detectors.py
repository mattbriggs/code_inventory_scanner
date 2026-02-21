"""Project detector strategies for classifying project folders."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, Sequence, runtime_checkable

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionResult:
    """Represents a successful project detection result.

    :param project_type: Classified project type (for example, ``CLI Tool``).
    :type project_type: str
    :param primary_language: Primary language associated with the project.
    :type primary_language: str
    :param keywords: Keywords describing the project and detection hints.
    :type keywords: list[str]
    :param detection_source: Identifier for the rule or detector that matched.
    :type detection_source: str
    """

    project_type: str
    primary_language: str
    keywords: list[str]
    detection_source: str


@runtime_checkable
class ProjectDetector(Protocol):
    """Protocol for project detector strategies."""

    def detect(self, folder: Path) -> DetectionResult | None:
        """Detect a project in a folder.

        :param folder: Folder to inspect.
        :type folder: Path
        :return: Detection result if matched; otherwise ``None``.
        :rtype: DetectionResult | None
        """
        ...


class PythonProjectDetector:
    """Detect Python projects using common marker files."""

    MARKERS: Final[tuple[str, ...]] = (
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
    )

    def detect(self, folder: Path) -> DetectionResult | None:
        """Detect Python project markers.

        :param folder: Folder to inspect.
        :type folder: Path
        :return: Detection result if Python markers are found; otherwise ``None``.
        :rtype: DetectionResult | None
        """
        found_markers = [marker for marker in self.MARKERS if (folder / marker).exists()]
        if not found_markers:
            return None

        has_src_layout = (folder / "src").is_dir()

        keywords = ["python"]
        if "pyproject.toml" in found_markers:
            keywords.append("pyproject")
        if "requirements.txt" in found_markers:
            keywords.append("requirements")
        if "setup.py" in found_markers:
            keywords.append("setuptools")
        if has_src_layout:
            keywords.append("src-layout")

        project_type = "CLI Tool" if has_src_layout else "Script"

        _LOG.debug(
            "Python project detected in '%s' using markers=%s",
            folder,
            found_markers,
        )

        return DetectionResult(
            project_type=project_type,
            primary_language="Python",
            keywords=keywords,
            detection_source="python-markers",
        )


class NodeProjectDetector:
    """Detect Node.js and JavaScript/TypeScript projects."""

    PACKAGE_JSON: Final[str] = "package.json"
    TSCONFIG_JSON: Final[str] = "tsconfig.json"

    def detect(self, folder: Path) -> DetectionResult | None:
        """Detect Node project markers.

        :param folder: Folder to inspect.
        :type folder: Path
        :return: Detection result if Node markers are found; otherwise ``None``.
        :rtype: DetectionResult | None
        """
        package_json_path = folder / self.PACKAGE_JSON
        if not package_json_path.exists():
            return None

        has_typescript = (folder / self.TSCONFIG_JSON).exists()

        keywords = ["node", "javascript"]
        if has_typescript:
            keywords.append("typescript")

        primary_language = "TypeScript" if has_typescript else "JavaScript"

        _LOG.debug(
            "Node project detected in '%s' (typescript=%s)",
            folder,
            has_typescript,
        )

        return DetectionResult(
            project_type="Web App",
            primary_language=primary_language,
            keywords=keywords,
            detection_source="node-markers",
        )


class GenericProjectDetector:
    """Detect common non-Python, non-Node projects via marker files."""

    #: Marker name -> (project_type, primary_language, keywords)
    MARKER_MAP: Final[dict[str, tuple[str, str, list[str]]]] = {
        "Cargo.toml": ("Library", "Rust", ["rust", "cargo"]),
        "go.mod": ("Library", "Go", ["go", "gomod"]),
        ".csproj": ("Library", "C#", ["dotnet", "csharp"]),
        "composer.json": ("Web App", "PHP", ["php", "composer"]),
    }

    def detect(self, folder: Path) -> DetectionResult | None:
        """Detect generic project markers.

        Supports both exact marker filenames (for example, ``Cargo.toml``)
        and suffix-based markers (for example, ``.csproj``).

        :param folder: Folder to inspect.
        :type folder: Path
        :return: Detection result if a known marker is found; otherwise ``None``.
        :rtype: DetectionResult | None
        """
        for marker, (project_type, language, keywords) in self.MARKER_MAP.items():
            if marker.startswith("."):
                if self._contains_file_with_suffix(folder, marker):
                    _LOG.debug(
                        "Generic project detected in '%s' by suffix marker '%s'",
                        folder,
                        marker,
                    )
                    return DetectionResult(
                        project_type=project_type,
                        primary_language=language,
                        keywords=list(keywords),
                        detection_source=f"generic-marker:{marker}",
                    )
                continue

            if (folder / marker).exists():
                _LOG.debug(
                    "Generic project detected in '%s' by marker '%s'",
                    folder,
                    marker,
                )
                return DetectionResult(
                    project_type=project_type,
                    primary_language=language,
                    keywords=list(keywords),
                    detection_source=f"generic-marker:{marker}",
                )

        return None

    @staticmethod
    def _contains_file_with_suffix(folder: Path, suffix: str) -> bool:
        """Return whether a folder contains any file with the given suffix.

        :param folder: Folder to inspect.
        :type folder: Path
        :param suffix: File suffix to match, including leading dot.
        :type suffix: str
        :return: ``True`` if a matching file exists; otherwise ``False``.
        :rtype: bool
        """
        try:
            for item in folder.iterdir():
                if item.is_file() and item.suffix == suffix:
                    return True
        except OSError as exc:
            _LOG.debug("Unable to inspect folder '%s' for suffix '%s': %s", folder, suffix, exc)
            return False

        return False


class DetectorFactory:
    """Factory for detector strategy instances."""

    @staticmethod
    def build() -> list[ProjectDetector]:
        """Create detector strategies in priority order.

        Detector order matters. More specific detectors should run before more
        generic detectors so the classification does not get flattened into a
        vague fallback result.

        :return: Detector instances in evaluation order.
        :rtype: list[ProjectDetector]
        """
        detectors: list[ProjectDetector] = [
            PythonProjectDetector(),
            NodeProjectDetector(),
            GenericProjectDetector(),
        ]
        _LOG.debug(
            "Built detector pipeline: %s",
            [detector.__class__.__name__ for detector in detectors],
        )
        return detectors