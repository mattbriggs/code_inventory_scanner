# Logging Config Module

Module: `code_inventory.logging_config`

This module provides centralized logging configuration for the application.

## Purpose

- Configure root logger behavior for CLI runs
- Provide consistent formatting
- Support INFO vs DEBUG output
- Avoid duplicate handlers when called multiple times

This is especially useful for CLI tools and tests, where logging may be configured more than once.

## Public API

### `configure_logging(verbose: bool = False, stream: TextIO | None = None) -> None`

Configures application logging.

## Parameters

- `verbose`: if `True`, use `DEBUG`; otherwise `INFO`
- `stream`: optional output stream (defaults to `sys.stderr`)

## Behavior

- sets root logger level
- clears existing handlers
- adds a single `StreamHandler`
- applies consistent formatter and date format

## Internal helpers

### `_clear_handlers(logger: logging.Logger) -> None`

Removes and closes all handlers attached to a logger.

This prevents duplicate log output in repeated CLI/test runs.

## Log format

The module uses a standard log format:

- timestamp
- level
- logger name
- message

Example output:

```text
2026-02-21 10:42:15 INFO [code_inventory.service] Starting inventory scan for: /Volumes/Matt_files/Git
```

## Logging configuration flow

```mermaid
flowchart TD
    A[configure_logging(verbose, stream)] --> B[Determine level]
    B --> C[Get root logger]
    C --> D[Clear existing handlers]
    D --> E[Create StreamHandler]
    E --> F[Set formatter]
    F --> G[Attach handler]
```

## Design notes

Centralized logging configuration keeps formatting and behavior consistent across modules.

Without this, each module tends to improvise, and then your logs look like five tools arguing in a hallway.