"""Unit tests for project detector strategies."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_inventory.detectors import (
    DetectionResult,
    DetectorFactory,
    GenericProjectDetector,
    NodeProjectDetector,
    ProjectDetector,
    PythonProjectDetector,
)


def test_detection_result_dataclass_fields() -> None:
    """Verify DetectionResult stores expected values.

    :return: None
    :rtype: None
    """
    result = DetectionResult(
        project_type="CLI Tool",
        primary_language="Python",
        keywords=["python", "pyproject"],
        detection_source="python-markers",
    )

    assert result.project_type == "CLI Tool"
    assert result.primary_language == "Python"
    assert result.keywords == ["python", "pyproject"]
    assert result.detection_source == "python-markers"


def test_python_detector_returns_none_when_no_markers(tmp_path: Path) -> None:
    """Verify Python detector returns None without marker files.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    detector = PythonProjectDetector()

    result = detector.detect(tmp_path)

    assert result is None


def test_python_detector_detects_script_without_src_layout(tmp_path: Path) -> None:
    """Verify Python detector classifies non-src project as Script.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("pytest\n", encoding="utf-8")

    detector = PythonProjectDetector()
    result = detector.detect(tmp_path)

    assert result is not None
    assert result.project_type == "Script"
    assert result.primary_language == "Python"
    assert result.detection_source == "python-markers"
    assert "python" in result.keywords
    assert "pyproject" in result.keywords
    assert "requirements" in result.keywords
    assert "src-layout" not in result.keywords


def test_python_detector_detects_cli_tool_with_src_layout(tmp_path: Path) -> None:
    """Verify Python detector classifies src-layout project as CLI Tool.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    (tmp_path / "setup.py").write_text("from setuptools import setup\n", encoding="utf-8")
    (tmp_path / "src").mkdir()

    detector = PythonProjectDetector()
    result = detector.detect(tmp_path)

    assert result is not None
    assert result.project_type == "CLI Tool"
    assert result.primary_language == "Python"
    assert result.detection_source == "python-markers"
    assert "python" in result.keywords
    assert "setuptools" in result.keywords
    assert "src-layout" in result.keywords


def test_node_detector_returns_none_without_package_json(tmp_path: Path) -> None:
    """Verify Node detector returns None when package.json is missing.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    detector = NodeProjectDetector()

    result = detector.detect(tmp_path)

    assert result is None


def test_node_detector_detects_javascript_project(tmp_path: Path) -> None:
    """Verify Node detector identifies JavaScript project.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    (tmp_path / "package.json").write_text('{"name": "demo"}\n', encoding="utf-8")

    detector = NodeProjectDetector()
    result = detector.detect(tmp_path)

    assert result is not None
    assert result.project_type == "Web App"
    assert result.primary_language == "JavaScript"
    assert result.detection_source == "node-markers"
    assert "node" in result.keywords
    assert "javascript" in result.keywords
    assert "typescript" not in result.keywords


def test_node_detector_detects_typescript_project(tmp_path: Path) -> None:
    """Verify Node detector identifies TypeScript project.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    (tmp_path / "package.json").write_text('{"name": "demo"}\n', encoding="utf-8")
    (tmp_path / "tsconfig.json").write_text('{"compilerOptions": {}}\n', encoding="utf-8")

    detector = NodeProjectDetector()
    result = detector.detect(tmp_path)

    assert result is not None
    assert result.project_type == "Web App"
    assert result.primary_language == "TypeScript"
    assert result.detection_source == "node-markers"
    assert "node" in result.keywords
    assert "javascript" in result.keywords
    assert "typescript" in result.keywords


def test_generic_detector_detects_exact_marker_rust(tmp_path: Path) -> None:
    """Verify generic detector identifies Rust projects via Cargo.toml.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    (tmp_path / "Cargo.toml").write_text("[package]\nname='demo'\n", encoding="utf-8")

    detector = GenericProjectDetector()
    result = detector.detect(tmp_path)

    assert result is not None
    assert result.project_type == "Library"
    assert result.primary_language == "Rust"
    assert result.keywords == ["rust", "cargo"]
    assert result.detection_source == "generic-marker:Cargo.toml"


def test_generic_detector_detects_suffix_marker_csproj(tmp_path: Path) -> None:
    """Verify generic detector identifies .NET projects via .csproj suffix.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    (tmp_path / "DemoApp.csproj").write_text("<Project></Project>\n", encoding="utf-8")

    detector = GenericProjectDetector()
    result = detector.detect(tmp_path)

    assert result is not None
    assert result.project_type == "Library"
    assert result.primary_language == "C#"
    assert result.keywords == ["dotnet", "csharp"]
    assert result.detection_source == "generic-marker:.csproj"


def test_generic_detector_returns_none_when_no_markers(tmp_path: Path) -> None:
    """Verify generic detector returns None without known markers.

    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    detector = GenericProjectDetector()

    result = detector.detect(tmp_path)

    assert result is None


def test_generic_suffix_helper_handles_oserror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify suffix helper returns False when folder iteration fails.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Temporary folder fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    original_iterdir = Path.iterdir

    def fake_iterdir(self: Path):  # noqa: ANN001
        """Raise OSError for the target path only."""
        if self == tmp_path:
            raise OSError("Permission denied")
        return original_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)

    assert GenericProjectDetector._contains_file_with_suffix(tmp_path, ".csproj") is False


def test_detector_factory_build_returns_ordered_detectors() -> None:
    """Verify factory returns detectors in the expected priority order.

    :return: None
    :rtype: None
    """
    detectors = DetectorFactory.build()

    assert len(detectors) == 3
    assert isinstance(detectors[0], PythonProjectDetector)
    assert isinstance(detectors[1], NodeProjectDetector)
    assert isinstance(detectors[2], GenericProjectDetector)


def test_detector_factory_outputs_protocol_compatible_detectors() -> None:
    """Verify factory detectors conform to ProjectDetector protocol.

    :return: None
    :rtype: None
    """
    detectors = DetectorFactory.build()

    for detector in detectors:
        assert isinstance(detector, ProjectDetector)