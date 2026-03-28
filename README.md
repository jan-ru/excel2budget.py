# Data Conversion Tool

A browser-based data conversion platform that transforms financial data between source formats and accounting package import formats. Runs entirely client-side via WebAssembly using [IronCalc](https://www.ironcalc.com/) for spreadsheet rendering and [DuckDB WASM](https://duckdb.org/docs/api/wasm/overview) for SQL-driven transformations.

## Overview

This tool is part of a larger system of application modules, each handling a specific conversion use case:

| Module | Purpose |
|---|---|
| **excel2budget** | Convert Excel budget files (wide month columns) into accounting package budget import formats |
| **update_forecast** | Update forecast data in accounting packages *(planned)* |
| **reporting_actuals** | Report actuals data from accounting packages *(planned)* |

All modules share a common **Documentation Module** that generates standardized documentation artifacts via a generic `ApplicationContext` interface.

### Supported Accounting Packages

- Twinfield
- Exact
- Afas

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Browser UI                        │
├──────────────┬──────────────┬───────────────────────┤
│  IronCalc    │  Pipeline    │  Documentation Module  │
│  WASM        │  Orchestrator│  (7 artifacts)         │
│  (preview)   │              │                        │
├──────────────┼──────────────┤  - ArchiMate diagram   │
│  Excel       │  DuckDB WASM │  - BPMN diagram        │
│  Importer    │  (transform) │  - Input description   │
├──────────────┼──────────────┤  - Output description  │
│  Template    │  Format      │  - Transform description│
│  Registry    │  Exporter    │  - Control table       │
│              │              │  - User instruction    │
└──────────────┴──────────────┴───────────────────────┘
```

## Project Structure

```
data-conversion-tool/
├── src/
│   ├── core/                  # Shared types, TabularData, ApplicationContext
│   ├── modules/
│   │   └── excel2budget/      # Budget conversion pipeline
│   ├── documentation/         # Documentation Module (7 artifacts)
│   ├── engine/
│   │   ├── ironcalc/          # IronCalc WASM integration
│   │   └── duckdb/            # DuckDB WASM integration
│   ├── templates/             # Output templates per accounting package
│   │   ├── twinfield/
│   │   ├── exact/
│   │   └── afas/
│   ├── export/                # CSV/Excel/PDF exporters
│   └── ui/                    # Browser UI components
├── tests/
│   ├── unit/
│   ├── property/              # Property-based tests (fast-check)
│   └── integration/
├── docs/                      # Additional documentation
│   ├── archimate-template/    # Standard ArchiMate template
│   └── bpmn-template/         # Standard BPMN template
├── .kiro/
│   └── specs/                 # Spec-driven development artifacts
│       └── data-conversion-tool/
├── existing_m_code.md         # Reference Power Query M code
├── .gitignore
├── LICENSE.md
└── README.md
```

## Key Concepts

### Excel as Data + Config
The Excel budget file serves a dual purpose: it contains both the budget data and the column mapping configuration. IronCalc reads the file, extracts the mapping (which columns are Entity, Account, DC, months), and presents the data for review.

### DuckDB SQL Transformation
DuckDB WASM handles the heavy transformation: UNPIVOT of month columns into rows, Debet/Credit splitting based on the DC flag, column renaming, type casting, and rounding — all via generated SQL.

### Documentation Module
A reusable, application-agnostic module that generates 7 documentation artifacts per conversion configuration via a generic `ApplicationContext`. Each application module populates the context with its own domain metadata.

### Control Table
Every conversion produces a reconciliation sheet proving input totals equal output totals, ensuring no data is lost or corrupted.

## Development

*Setup instructions will be added as implementation progresses.*

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.
