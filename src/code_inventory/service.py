"""Application service that coordinates scanning and export."""

from __future__ import annotations

import logging
from pathlib import Path

from code_inventory.csv_writer import CsvInventoryWriter
from code_inventory.detectors import DetectorFactory
from code_inventory.scanner import RepositoryScanner

_LOG = logging.getLogger(__name__)


class InventoryService:
    """Coordinate repository scanning and CSV export."""

    def __init__(
        self,
        scanner: RepositoryScanner | None = None,
        writer: CsvInventoryWriter | None = None,
    ) -> None:
        """Initialize the service.

        Dependency injection is supported so tests can provide fakes or mocks.

        :param scanner: Optional repository scanner instance.
        :type scanner: RepositoryScanner | None
        :param writer: Optional CSV writer instance.
        :type writer: CsvInventoryWriter | None
        """
        self._scanner = scanner if scanner is not None else RepositoryScanner(
            detectors=DetectorFactory.build()
        )
        self._writer = writer if writer is not None else CsvInventoryWriter()

    def run(self, input_folder: Path, output_csv: Path) -> int:
        """Execute the inventory scan and write CSV output.

        :param input_folder: Folder to scan.
        :type input_folder: Path
        :param output_csv: Output CSV file path.
        :type output_csv: Path
        :return: Number of records written.
        :rtype: int
        :raises FileNotFoundError: If the input folder does not exist.
        :raises NotADirectoryError: If the input path is not a directory.
        :raises PermissionError: If the input folder is not readable.
        :raises OSError: If output cannot be written.
        """
        normalized_input = input_folder.expanduser().resolve()
        normalized_output = output_csv.expanduser().resolve()

        self._validate_input_folder(normalized_input)
        self._validate_output_path(normalized_output)

        _LOG.info("Starting inventory scan for: %s", normalized_input)
        _LOG.debug("Output CSV path resolved to: %s", normalized_output)

        records = self._scanner.scan(normalized_input)
        record_count = len(records)

        _LOG.info("Detected %d project record(s)", record_count)

        self._writer.write(normalized_output, records)

        _LOG.info("Inventory CSV written successfully: %s", normalized_output)
        return record_count

    def _validate_input_folder(self, input_folder: Path) -> None:
        """Validate the input folder path.

        :param input_folder: Input folder to validate.
        :type input_folder: Path
        :return: None
        :rtype: None
        :raises FileNotFoundError: If the input folder does not exist.
        :raises NotADirectoryError: If the input path is not a directory.
        :raises PermissionError: If the input folder is not readable.
        """
        if not input_folder.exists():
            raise FileNotFoundError(f"Input folder does not exist: {input_folder}")

        if not input_folder.is_dir():
            raise NotADirectoryError(f"Input path is not a directory: {input_folder}")

        if not self._is_readable_dir(input_folder):
            raise PermissionError(f"Input folder is not readable: {input_folder}")

    def _validate_output_path(self, output_csv: Path) -> None:
        """Validate the output CSV path.

        This validates the parent directory when it already exists. Directory
        creation itself is handled by the writer.

        :param output_csv: Output CSV path to validate.
        :type output_csv: Path
        :return: None
        :rtype: None
        :raises NotADirectoryError: If the output parent exists but is not a directory.
        :raises PermissionError: If the output parent exists but is not writable.
        """
        parent_dir = output_csv.parent

        if parent_dir.exists() and not parent_dir.is_dir():
            raise NotADirectoryError(
                f"Output parent path is not a directory: {parent_dir}"
            )

        if parent_dir.exists() and not self._is_writable_dir(parent_dir):
            raise PermissionError(f"Output directory is not writable: {parent_dir}")

    @staticmethod
    def _is_readable_dir(path: Path) -> bool:
        """Return whether a directory is readable.

        :param path: Directory path to check.
        :type path: Path
        :return: ``True`` if readable; otherwise ``False``.
        :rtype: bool
        """
        try:
            next(path.iterdir(), None)
            return True
        except OSError:
            return False

    @staticmethod
    def _is_writable_dir(path: Path) -> bool:
        """Return whether a directory is writable.

        :param path: Directory path to check.
        :type path: Path
        :return: ``True`` if writable; otherwise ``False``.
        :rtype: bool
        """
        try:
            test_file = path / ".code_inventory_write_test.tmp"
            test_file.touch(exist_ok=False)
            test_file.unlink()
            return True
        except OSError:
            return False