# API Reference

This section documents the Python modules that make up the **Code Inventory Scanner**.

The codebase is organized into small modules with clear responsibilities:

- **CLI** for argument parsing and process exit behavior
- **Service** for orchestration
- **Scanner** for filesystem traversal and project detection
- **Detectors** for classification strategies
- **Models** for record structure and CSV conversion
- **CSV Writer** for output serialization
- **Logging Config** for centralized logging setup

## Module map

```mermaid
flowchart TD
    A[cli.py] --> B[service.py]
    B --> C[scanner.py]
    B --> D[csv_writer.py]
    C --> E[detectors.py]
    C --> F[models.py]
    D --> F
    A --> G[logging_config.py]
```

## Typical runtime flow

```mermaid
sequenceDiagram
    participant CLI as cli.main()
    participant Log as configure_logging()
    participant Service as InventoryService
    participant Scanner as RepositoryScanner
    participant Writer as CsvInventoryWriter

    CLI->>Log: configure_logging(verbose)
    CLI->>Service: run(input_folder, output_csv)
    Service->>Scanner: scan(input_folder)
    Scanner-->>Service: list[ProjectInventoryRecord]
    Service->>Writer: write(output_csv, records)
    Writer-->>Service: None
    Service-->>CLI: record_count
```

## Notes

- Paths are normalized before scanning and record creation.
- Project IDs are deterministic and derived from normalized paths.
- CSV output flattens `keywords` into a semicolon-separated string.
- Logging is centralized and supports `--verbose` (DEBUG mode).