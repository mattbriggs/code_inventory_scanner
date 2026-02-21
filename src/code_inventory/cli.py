"""CLI entry point for the code inventory scanner."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from code_inventory.logging_config import configure_logging
from code_inventory.service import InventoryService

_LOG = logging.getLogger(__name__)

EXIT_SUCCESS = 0
EXIT_UNEXPECTED_ERROR = 1
EXIT_INPUT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser.

    :return: Configured argument parser for the code inventory CLI.
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        prog="code-inventory",
        description=(
            "Scan a folder for code repositories and nested projects, "
            "then export a CSV inventory."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        metavar="FOLDER",
        help="Input folder to scan recursively.",
    )
    parser.add_argument(
        "--output",
        required=True,
        metavar="CSV_FILE",
        help="Output CSV file path.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser


def _resolve_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    """Resolve CLI path arguments into absolute paths.

    :param args: Parsed CLI arguments namespace.
    :type args: argparse.Namespace
    :return: Tuple of (input_path, output_path).
    :rtype: tuple[pathlib.Path, pathlib.Path]
    """
    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    return input_path, output_path


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI workflow.

    This function parses arguments, configures logging, runs the inventory
    service, and returns a process exit code.

    :param argv: Optional CLI arguments for testing or programmatic execution.
    :type argv: Sequence[str] | None
    :return: Process exit code.
    :rtype: int
    """
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    configure_logging(verbose=args.verbose)
    input_path, output_path = _resolve_paths(args)

    _LOG.debug("CLI arguments parsed successfully.")
    _LOG.debug("Resolved input path: %s", input_path)
    _LOG.debug("Resolved output path: %s", output_path)

    try:
        _LOG.info("Starting code inventory scan.")
        service = InventoryService()
        record_count = service.run(input_folder=input_path, output_csv=output_path)
    except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
        _LOG.error("Input/output validation error: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except Exception as exc:  # pragma: no cover
        _LOG.exception("Unexpected error while running inventory scan: %s", exc)
        print("Error: unexpected failure during inventory scan.", file=sys.stderr)
        return EXIT_UNEXPECTED_ERROR

    _LOG.info("Inventory scan completed successfully. Records written: %d", record_count)
    print(f"Wrote {record_count} record(s) to {output_path}")
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())