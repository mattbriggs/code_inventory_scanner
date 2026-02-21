"""Unit tests for the code inventory CLI module."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from code_inventory import cli


def test_build_parser_returns_argument_parser() -> None:
    """Verify the CLI parser is created correctly.

    :return: None
    :rtype: None
    """
    parser = cli.build_parser()

    assert isinstance(parser, argparse.ArgumentParser)


def test_build_parser_parses_required_arguments() -> None:
    """Verify required CLI arguments are parsed.

    :return: None
    :rtype: None
    """
    parser = cli.build_parser()

    args = parser.parse_args(["--input", "src", "--output", "out.csv"])

    assert args.input == "src"
    assert args.output == "out.csv"
    assert args.verbose is False


def test_build_parser_parses_verbose_flag() -> None:
    """Verify the optional verbose flag is parsed.

    :return: None
    :rtype: None
    """
    parser = cli.build_parser()

    args = parser.parse_args(["--input", "src", "--output", "out.csv", "--verbose"])

    assert args.verbose is True


def test_resolve_paths_returns_absolute_paths(tmp_path: Path) -> None:
    """Verify CLI path resolution returns resolved absolute paths.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "projects"
    output_file = tmp_path / "out" / "inventory.csv"
    input_dir.mkdir(parents=True, exist_ok=True)

    args = argparse.Namespace(input=str(input_dir), output=str(output_file))

    resolved_input, resolved_output = cli._resolve_paths(args)

    assert resolved_input == input_dir.resolve()
    assert resolved_output == output_file.resolve()


def test_main_success_returns_zero_and_prints_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify CLI success path configures logging and prints record count.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :param capsys: Pytest capture fixture.
    :type capsys: pytest.CaptureFixture[str]
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "repos"
    output_file = tmp_path / "inventory.csv"
    input_dir.mkdir(parents=True, exist_ok=True)

    captured: dict[str, object] = {}

    def fake_configure_logging(verbose: bool = False) -> None:
        """Capture logging configuration calls.

        :param verbose: Verbose flag value.
        :type verbose: bool
        :return: None
        :rtype: None
        """
        captured["verbose"] = verbose

    class FakeInventoryService:
        """Fake inventory service for CLI tests."""

        def run(self, input_folder: Path, output_csv: Path) -> int:
            """Return a fixed row count and capture arguments.

            :param input_folder: Input folder.
            :type input_folder: Path
            :param output_csv: Output CSV path.
            :type output_csv: Path
            :return: Fake record count.
            :rtype: int
            """
            captured["input_folder"] = input_folder
            captured["output_csv"] = output_csv
            return 7

    monkeypatch.setattr(cli, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(cli, "InventoryService", FakeInventoryService)

    exit_code = cli.main(
        ["--input", str(input_dir), "--output", str(output_file), "--verbose"]
    )

    std = capsys.readouterr()

    assert exit_code == cli.EXIT_SUCCESS
    assert captured["verbose"] is True
    assert captured["input_folder"] == input_dir.resolve()
    assert captured["output_csv"] == output_file.resolve()
    assert "Wrote 7 record(s) to" in std.out
    assert str(output_file.resolve()) in std.out
    assert std.err == ""


def test_main_validation_error_returns_input_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify validation-style exceptions return the input error exit code.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :param capsys: Pytest capture fixture.
    :type capsys: pytest.CaptureFixture[str]
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "repos"
    output_file = tmp_path / "inventory.csv"
    input_dir.mkdir(parents=True, exist_ok=True)

    def fake_configure_logging(verbose: bool = False) -> None:
        """No-op logging config for tests.

        :param verbose: Verbose flag value.
        :type verbose: bool
        :return: None
        :rtype: None
        """
        _ = verbose

    class FakeInventoryService:
        """Fake service that simulates a validation error."""

        def run(self, input_folder: Path, output_csv: Path) -> int:
            """Raise a validation error.

            :param input_folder: Input folder.
            :type input_folder: Path
            :param output_csv: Output CSV path.
            :type output_csv: Path
            :return: Never returns.
            :rtype: int
            :raises FileNotFoundError: Always.
            """
            _ = input_folder, output_csv
            raise FileNotFoundError("Input folder does not exist: /bad/path")

    monkeypatch.setattr(cli, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(cli, "InventoryService", FakeInventoryService)

    exit_code = cli.main(["--input", str(input_dir), "--output", str(output_file)])

    std = capsys.readouterr()

    assert exit_code == cli.EXIT_INPUT_ERROR
    assert "Error: Input folder does not exist: /bad/path" in std.err
    assert std.out == ""


def test_main_unexpected_error_returns_unexpected_error_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify unexpected exceptions return the unexpected error exit code.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :param capsys: Pytest capture fixture.
    :type capsys: pytest.CaptureFixture[str]
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "repos"
    output_file = tmp_path / "inventory.csv"
    input_dir.mkdir(parents=True, exist_ok=True)

    def fake_configure_logging(verbose: bool = False) -> None:
        """No-op logging config for tests.

        :param verbose: Verbose flag value.
        :type verbose: bool
        :return: None
        :rtype: None
        """
        _ = verbose

    class FakeInventoryService:
        """Fake service that raises an unexpected exception."""

        def run(self, input_folder: Path, output_csv: Path) -> int:
            """Raise a runtime error.

            :param input_folder: Input folder.
            :type input_folder: Path
            :param output_csv: Output CSV path.
            :type output_csv: Path
            :return: Never returns.
            :rtype: int
            :raises RuntimeError: Always.
            """
            _ = input_folder, output_csv
            raise RuntimeError("Boom")

    monkeypatch.setattr(cli, "configure_logging", fake_configure_logging)
    monkeypatch.setattr(cli, "InventoryService", FakeInventoryService)

    exit_code = cli.main(["--input", str(input_dir), "--output", str(output_file)])

    std = capsys.readouterr()

    assert exit_code == cli.EXIT_UNEXPECTED_ERROR
    assert "Error: unexpected failure during inventory scan." in std.err
    assert std.out == ""


def test_main_missing_required_args_raises_system_exit() -> None:
    """Verify argparse exits when required args are missing.

    :return: None
    :rtype: None
    """
    with pytest.raises(SystemExit) as exc_info:
        cli.main([])

    assert exc_info.value.code == 2