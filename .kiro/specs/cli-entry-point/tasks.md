# Implementation Plan: CLI Entry Point

## Overview

Add a CLI entry point to the Data Conversion Tool using Python's `argparse`. The implementation creates `src/cli.py` (argument parsing + orchestration), `src/__main__.py` (package entry point), and `main.py` (root shim). No new dependencies are required.

## Tasks

- [x] 1. Create CLI argument parser and entry-point shims
  - [x] 1.1 Create `src/cli.py` with `build_parser()` function
    - Define all arguments: positional (`input_file`, `package`, `template`), required named (`--budgetcode`, `--year`), optional (`--output`, `--format`, `--verbose`, `--quiet`, `--list-packages`, `--list-templates`, `--version`)
    - Add mutually exclusive group for `--verbose` and `--quiet`
    - Subclass `ArgumentParser` to override `error()` so argument errors exit with code 1 instead of argparse's default code 2
    - Set `--format` default to `"csv"` and `--output` default to `None`
    - Wire `--version` to read version from `pyproject.toml` or a constant
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

  - [x] 1.2 Create `src/__main__.py` and `main.py` entry-point shims
    - `src/__main__.py`: import and call `main()` from `src.cli`
    - `main.py` at project root: import and call `main()` from `src.cli`
    - _Requirements: 1.1_

  - [x] 1.3 Write property test for argument parsing round-trip
    - **Property 1: Argument parsing round-trip**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4**

- [-] 2. Implement `run()` orchestration — early-exit commands and input validation
  - [x] 2.1 Implement `--list-packages` and `--list-templates` early-exit paths in `run()`
    - Call `listPackages()` / `listTemplates()` from `src/templates/registry.py`
    - Print results to stdout and return exit code 0
    - _Requirements: 3.4, 3.5_

  - [x] 2.2 Implement input file reading and parsing in `run()`
    - Read file bytes from disk; catch `FileNotFoundError` and `PermissionError` → exit 1
    - Call `parseExcelFile()` from importer; check for `ParseError` → exit 1
    - Call `extractBudgetData()` from importer; check for `ParseError` → exit 1
    - Call `extractMappingConfig()` from importer; check for `MappingError` → exit 1
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.3 Implement template lookup in `run()`
    - Call `getTemplate()` from registry; catch `TemplateError` → exit 1
    - Include `available_packages` / `available_templates` from the exception in the error message
    - _Requirements: 3.1, 3.2, 3.3_

  - [x] 2.4 Write property test for non-existent file paths
    - **Property 2: Non-existent file paths produce exit code 1**
    - **Validates: Requirements 2.2, 6.2**

  - [x] 2.5 Write property test for invalid file bytes
    - **Property 3: Invalid file bytes produce exit code 1**
    - **Validates: Requirements 2.3, 6.2**

  - [x] 2.6 Write property test for invalid registry lookups
    - **Property 4: Invalid registry lookups list available alternatives**
    - **Validates: Requirements 3.2, 3.3, 6.2**

- [x] 3. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement `run()` orchestration — transformation and export
  - [x] 4.1 Implement transformation execution in `run()`
    - Build `UserParams` from `--budgetcode` and `--year`
    - Call `run_budget_transformation()` with budget data, mapping config, template, and user params
    - Check for `TransformError` → exit 2 with error message to stderr
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 4.2 Implement export and output writing in `run()`
    - Map `--format` string to `FileFormat` enum (case-insensitive)
    - Call `export_data()` with transformed data, file format, and template
    - If `--output` provided: write bytes to that path
    - If no `--output` and CSV: write to stdout
    - If no `--output` and Excel: derive default filename from input filename
    - Catch `IOError`/`OSError` on write → exit 2
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [x] 4.3 Implement `main()` function
    - Call `build_parser()`, parse `sys.argv`, call `run()`, call `sys.exit()` with return code
    - _Requirements: 1.1_

  - [x] 4.4 Write property test for transformation errors
    - **Property 5: Transformation errors produce exit code 2 with stderr output**
    - **Validates: Requirements 4.2, 6.3, 6.4**

  - [x] 4.5 Write property test for format argument mapping
    - **Property 8: Format argument maps to correct FileFormat**
    - **Validates: Requirements 5.3, 5.4**

- [x] 5. Implement verbose/quiet modes and stderr output control
  - [x] 5.1 Add verbose/quiet log helper and wire into `run()`
    - Create a closure or helper that prints to stderr based on verbosity level
    - In verbose mode: print progress messages at each pipeline stage (file loading, mapping extraction, template selection, transformation, export)
    - In default mode: print a summary line on success (input rows, output rows, output path)
    - In quiet mode: suppress all non-error stderr output
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 5.2 Write property test for stdout cleanliness on file output
    - **Property 6: Stdout cleanliness on file output**
    - **Validates: Requirements 6.5**

  - [x] 5.3 Write property test for quiet mode
    - **Property 7: Quiet mode suppresses non-error stderr**
    - **Validates: Requirements 7.2**

- [x] 6. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Write unit tests for specific examples and integration
  - [ ]* 7.1 Write unit tests in `tests/test_cli.py`
    - `--help` produces usage text mentioning all arguments (Req 1.5)
    - `--version` prints the version string (Req 1.6)
    - `--list-packages` prints all package names (Req 3.4)
    - `--list-templates <package>` prints template names (Req 3.5)
    - CSV output to stdout when no output path given (Req 5.2)
    - Excel output to default filename when no output path given (Req 5.2)
    - Output written to specified file path (Req 5.1)
    - Write failure produces exit code 2 (Req 5.5)
    - `--verbose` prints stage progress messages (Req 7.1)
    - Default mode prints summary line (Req 7.3)
    - _Requirements: 1.5, 1.6, 3.4, 3.5, 5.1, 5.2, 5.5, 7.1, 7.3_

- [ ] 8. Final checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use the Hypothesis library (already in the project)
- The CLI reuses all existing pipeline, importer, and registry modules — no new business logic
- All error messages go to stderr; only export data goes to stdout
