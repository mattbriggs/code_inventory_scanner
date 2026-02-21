"""CSV writer for project inventory records."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Final, Sequence

from code_inventory.models import ProjectInventoryRecord

_LOG = logging.getLogger(__name__)


class CsvInventoryWriter:
    """Write project inventory records to a CSV file."""

    FIELDNAMES: Final[list[str]] = [
        "project_id",
        "project_name",
        "project_type",
        "primary_language",
        "location",
        "github_url",
        "status",
        "keywords",
        "purpose",
        "repo_root",
        "is_repo_root",
        "parent_repo",
        "detection_source",
    ]

    def write(
        self,
        output_file: Path,
        records: Sequence[ProjectInventoryRecord],
    ) -> None:
        """Write inventory records to a CSV file.

        The output directory is created automatically if it does not exist.

        :param output_file: Path to the CSV output file.
        :type output_file: Path
        :param records: Inventory records to write.
        :type records: Sequence[ProjectInventoryRecord]
        :return: None
        :rtype: None
        :raises ValueError: If ``output_file`` is empty or invalid.
        :raises OSError: If the file cannot be written.
        """
        self._validate_output_path(output_file)
        self._ensure_output_directory(output_file)

        record_count = len(records)
        _LOG.info("Writing %d inventory record(s) to CSV: %s", record_count, output_file)

        with output_file.open(
            mode="w",
            newline="",
            encoding="utf-8",
        ) as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=self.FIELDNAMES,
                extrasaction="ignore",
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writeheader()

            for index, record in enumerate(records, start=1):
                row = record.to_csv_row()
                writer.writerow(row)
                _LOG.debug(
                    "Wrote CSV row %d/%d for project: %s",
                    index,
                    record_count,
                    row.get("project_name", "<unknown>"),
                )

        _LOG.info("CSV write complete: %s", output_file)

    def _validate_output_path(self, output_file: Path) -> None:
        """Validate the output CSV path.

        :param output_file: Path to validate.
        :type output_file: Path
        :return: None
        :rtype: None
        :raises ValueError: If the path is invalid for CSV output.
        """
        if not str(output_file).strip():
            raise ValueError("Output file path cannot be empty.")

        if output_file.name in {"", ".", ".."}:
            raise ValueError(f"Invalid output file path: {output_file}")

        if output_file.suffix.lower() != ".csv":
            _LOG.warning(
                "Output file does not use .csv extension: %s",
                output_file,
            )

    def _ensure_output_directory(self, output_file: Path) -> None:
        """Create the output directory if needed.

        :param output_file: Output file path whose parent directory is required.
        :type output_file: Path
        :return: None
        :rtype: None
        :raises OSError: If the directory cannot be created.
        """
        parent_dir = output_file.parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        _LOG.debug("Ensured output directory exists: %s", parent_dir)