"""Unit tests for the inventory service layer."""

from __future__ import annotations

from pathlib import Path

import pytest

from code_inventory.service import InventoryService


class _FakeScanner:
    """Fake repository scanner for service tests."""

    def __init__(self, records: list[object] | None = None) -> None:
        """Initialize the fake scanner.

        :param records: Records to return from ``scan``.
        :type records: list[object] | None
        """
        self.records = records if records is not None else []
        self.calls: list[Path] = []

    def scan(self, input_folder: Path) -> list[object]:
        """Return predefined records and capture the call.

        :param input_folder: Input folder passed by the service.
        :type input_folder: Path
        :return: Fake records.
        :rtype: list[object]
        """
        self.calls.append(input_folder)
        return self.records


class _FakeWriter:
    """Fake CSV writer for service tests."""

    def __init__(self) -> None:
        """Initialize fake writer call capture."""
        self.calls: list[tuple[Path, list[object]]] = []

    def write(self, output_csv: Path, records: list[object]) -> None:
        """Capture write calls.

        :param output_csv: Output CSV path.
        :type output_csv: Path
        :param records: Records passed by the service.
        :type records: list[object]
        :return: None
        :rtype: None
        """
        self.calls.append((output_csv, records))


def test_init_uses_injected_dependencies() -> None:
    """Verify injected scanner and writer are used as-is.

    :return: None
    :rtype: None
    """
    scanner = _FakeScanner()
    writer = _FakeWriter()

    service = InventoryService(scanner=scanner, writer=writer)

    assert service._scanner is scanner  # noqa: SLF001
    assert service._writer is writer  # noqa: SLF001


def test_run_happy_path_calls_scanner_and_writer_with_resolved_paths(tmp_path: Path) -> None:
    """Verify run() validates paths, scans, writes CSV, and returns record count.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "workspace"
    input_dir.mkdir()

    output_csv = tmp_path / "out" / "inventory.csv"

    fake_records = [{"project_name": "alpha"}, {"project_name": "beta"}]
    scanner = _FakeScanner(records=fake_records)
    writer = _FakeWriter()

    service = InventoryService(scanner=scanner, writer=writer)

    count = service.run(input_folder=input_dir, output_csv=output_csv)

    assert count == 2
    assert scanner.calls == [input_dir.resolve()]
    assert len(writer.calls) == 1

    called_output, called_records = writer.calls[0]
    assert called_output == output_csv.resolve()
    assert called_records == fake_records


def test_run_raises_file_not_found_for_missing_input(tmp_path: Path) -> None:
    """Verify run() raises FileNotFoundError for missing input folder.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    missing_input = tmp_path / "missing"
    output_csv = tmp_path / "inventory.csv"

    service = InventoryService(scanner=_FakeScanner(), writer=_FakeWriter())

    with pytest.raises(FileNotFoundError, match="Input folder does not exist"):
        service.run(input_folder=missing_input, output_csv=output_csv)


def test_run_raises_not_a_directory_for_input_file(tmp_path: Path) -> None:
    """Verify run() raises NotADirectoryError when input path is a file.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_file = tmp_path / "not_a_folder.txt"
    input_file.write_text("x", encoding="utf-8")

    output_csv = tmp_path / "inventory.csv"
    service = InventoryService(scanner=_FakeScanner(), writer=_FakeWriter())

    with pytest.raises(NotADirectoryError, match="Input path is not a directory"):
        service.run(input_folder=input_file, output_csv=output_csv)


def test_run_raises_permission_error_when_input_not_readable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify run() raises PermissionError when input folder is unreadable.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "workspace"
    input_dir.mkdir()

    output_csv = tmp_path / "inventory.csv"
    service = InventoryService(scanner=_FakeScanner(), writer=_FakeWriter())

    monkeypatch.setattr(service, "_is_readable_dir", lambda path: False)

    with pytest.raises(PermissionError, match="Input folder is not readable"):
        service.run(input_folder=input_dir, output_csv=output_csv)


def test_run_raises_not_a_directory_when_output_parent_is_file(tmp_path: Path) -> None:
    """Verify run() raises NotADirectoryError if output parent exists as a file.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "workspace"
    input_dir.mkdir()

    fake_parent = tmp_path / "not_a_dir"
    fake_parent.write_text("x", encoding="utf-8")

    output_csv = fake_parent / "inventory.csv"
    service = InventoryService(scanner=_FakeScanner(), writer=_FakeWriter())

    with pytest.raises(NotADirectoryError, match="Output parent path is not a directory"):
        service.run(input_folder=input_dir, output_csv=output_csv)


def test_run_raises_permission_error_when_output_parent_not_writable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify run() raises PermissionError when output directory is not writable.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "workspace"
    input_dir.mkdir()

    output_parent = tmp_path / "out"
    output_parent.mkdir()
    output_csv = output_parent / "inventory.csv"

    service = InventoryService(scanner=_FakeScanner(), writer=_FakeWriter())
    monkeypatch.setattr(service, "_is_writable_dir", lambda path: False)

    with pytest.raises(PermissionError, match="Output directory is not writable"):
        service.run(input_folder=input_dir, output_csv=output_csv)


def test_validate_input_folder_accepts_valid_readable_directory(tmp_path: Path) -> None:
    """Verify _validate_input_folder succeeds for a valid readable directory.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "workspace"
    input_dir.mkdir()

    service = InventoryService(scanner=_FakeScanner(), writer=_FakeWriter())

    service._validate_input_folder(input_dir)


def test_validate_output_path_allows_nonexistent_parent(tmp_path: Path) -> None:
    """Verify _validate_output_path allows a missing parent directory.

    Writer is responsible for creating the directory later.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    output_csv = tmp_path / "new" / "nested" / "inventory.csv"
    service = InventoryService(scanner=_FakeScanner(), writer=_FakeWriter())

    service._validate_output_path(output_csv)


def test_is_readable_dir_returns_true_for_readable_directory(tmp_path: Path) -> None:
    """Verify _is_readable_dir returns True for normal directories.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "file.txt").write_text("hello", encoding="utf-8")

    assert InventoryService._is_readable_dir(folder) is True


def test_is_readable_dir_returns_false_when_iterdir_raises(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify _is_readable_dir returns False when directory iteration fails.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    folder = tmp_path / "folder"
    folder.mkdir()

    original_iterdir = Path.iterdir

    def fake_iterdir(self: Path):
        """Raise OSError for the target path only."""
        if self == folder:
            raise OSError("permission denied")
        return original_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)

    assert InventoryService._is_readable_dir(folder) is False


def test_is_writable_dir_returns_true_for_writable_directory(tmp_path: Path) -> None:
    """Verify _is_writable_dir returns True for writable directories.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    folder = tmp_path / "folder"
    folder.mkdir()

    assert InventoryService._is_writable_dir(folder) is True


def test_is_writable_dir_returns_false_when_touch_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Verify _is_writable_dir returns False when temp file creation fails.

    :param monkeypatch: Pytest monkeypatch fixture.
    :type monkeypatch: pytest.MonkeyPatch
    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    folder = tmp_path / "folder"
    folder.mkdir()

    original_touch = Path.touch

    def fake_touch(self: Path, *args: object, **kwargs: object) -> None:
        """Raise OSError for the service temp file only."""
        if self.name == ".code_inventory_write_test.tmp":
            raise OSError("read-only file system")
        original_touch(self, *args, **kwargs)

    monkeypatch.setattr(Path, "touch", fake_touch)

    assert InventoryService._is_writable_dir(folder) is False


def test_run_propagates_writer_oserror(
    tmp_path: Path,
) -> None:
    """Verify run() propagates writer OSError to caller.

    :param tmp_path: Pytest temporary directory fixture.
    :type tmp_path: Path
    :return: None
    :rtype: None
    """
    input_dir = tmp_path / "workspace"
    input_dir.mkdir()

    output_csv = tmp_path / "out" / "inventory.csv"

    scanner = _FakeScanner(records=[{"project": "x"}])

    class _FailingWriter(_FakeWriter):
        """Fake writer that raises OSError."""

        def write(self, output_csv: Path, records: list[object]) -> None:
            """Raise OSError during write.

            :param output_csv: Output path.
            :type output_csv: Path
            :param records: Records.
            :type records: list[object]
            :return: None
            :rtype: None
            :raises OSError: Always.
            """
            _ = output_csv, records
            raise OSError("disk full")

    service = InventoryService(scanner=scanner, writer=_FailingWriter())

    with pytest.raises(OSError, match="disk full"):
        service.run(input_folder=input_dir, output_csv=output_csv)