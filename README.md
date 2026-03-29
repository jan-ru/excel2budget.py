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

- Twinfield (full budget template)
- Exact (stub template)
- Afas (stub template)

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
│   ├── core/                  # Shared types, validation, memory safety
│   │   ├── types.py           # All dataclasses, enums, type aliases
│   │   ├── validation.py      # TabularData, MappingConfig, UserParams validation
│   │   └── memory.py          # File size limits, WASM memory checks
│   ├── modules/
│   │   └── excel2budget/      # Budget conversion pipeline
│   │       ├── importer.py    # Excel .xlsx parsing, mapping extraction
│   │       ├── sql_generator.py # DuckDB SQL generation (UNPIVOT + DC split)
│   │       ├── pipeline.py    # End-to-end orchestrator
│   │       └── context_builder.py # ApplicationContext builder for docs
│   ├── documentation/         # Documentation Module (7 artifacts)
│   │   ├── module.py          # Orchestrator producing DocumentationPack
│   │   ├── diagram_generator.py # ArchiMate + BPMN SVG generation
│   │   ├── control_table.py   # Reconciliation totals
│   │   ├── description_generator.py # Input/output/transform descriptions
│   │   └── user_instruction.py # Step-by-step user guide
│   ├── engine/
│   │   ├── ironcalc/          # IronCalc WASM integration + XSS sanitizer
│   │   └── duckdb/            # DuckDB WASM engine wrapper
│   ├── templates/             # Output templates per accounting package
│   │   ├── registry.py        # Template lookup and validation
│   │   ├── twinfield/budget.py # 13-column Twinfield budget schema
│   │   ├── exact/budget.py    # Exact stub
│   │   └── afas/budget.py     # Afas stub
│   ├── export/                # CSV/Excel/PDF exporters
│   │   ├── exporter.py        # CSV + Excel serialization
│   │   └── pdf_exporter.py    # Screen-to-PDF via fpdf2
│   └── ui/
│       └── app.py             # State-machine UI shell
├── tests/
│   ├── property/              # Property-based tests (Hypothesis)
│   └── unit/                  # Unit tests
├── .kiro/
│   └── specs/                 # Spec-driven development artifacts
│       └── data-conversion-tool/
├── existing_m_code.md         # Reference Power Query M code
├── pyproject.toml
└── README.md
```

## Key Concepts

### Excel as Data + Config
The Excel budget file serves a dual purpose: it contains both the budget data and the column mapping configuration. The importer reads the file, extracts the mapping (which columns are Entity, Account, DC, months), and presents the data for review.

### DuckDB SQL Transformation
DuckDB handles the heavy transformation: UNPIVOT of month columns into rows, Debet/Credit splitting based on the DC flag, column renaming, type casting, and rounding — all via generated SQL that is SELECT-only and injection-safe.

### Documentation Module
A reusable, application-agnostic module that generates 7 documentation artifacts per conversion configuration via a generic `ApplicationContext`. Each application module populates the context with its own domain metadata.

### Control Table
Every conversion produces a reconciliation sheet proving input totals equal output totals, ensuring no data is lost or corrupted.

### Client-Side Only
All processing happens in the browser. No budget data is ever transmitted to a server. File size and WASM memory limits are validated before parsing.

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) (recommended) or pip

### Setup

```bash
# Clone the repository
git clone https://github.com/jan-ru/excel2budget.git
cd excel2budget

# Create virtual environment and install dependencies
uv venv
uv sync

# Or with pip
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Dependencies

Runtime:
- `openpyxl` — Excel file parsing and writing
- `fpdf2` — PDF generation
- `duckdb` — In-process SQL engine
- `ironcalc` — Spreadsheet engine (optional, for preview)

Testing:
- `pytest` — Test runner
- `hypothesis` — Property-based testing

### Running Tests

```bash
# Run all tests
.venv/bin/python -m pytest

# Run with verbose output
.venv/bin/python -m pytest -v

# Run only property-based tests
.venv/bin/python -m pytest tests/property/

# Run only unit tests
.venv/bin/python -m pytest tests/unit/
```

All 159 tests should pass. The test suite includes:
- Property-based tests validating correctness properties (unpivot row counts, DC split, SQL safety, round-trip fidelity, XSS sanitization, etc.)
- Unit tests for Excel importing and memory safety

### Code Coverage

```bash
# Run tests with coverage report
.venv/bin/python -m pytest --cov=src --cov-report=term-missing -q
```

| Module | Stmts | Miss | Cover |
|---|---|---|---|
| src/core/memory.py | 49 | 3 | 94% |
| src/core/types.py | 241 | 0 | 100% |
| src/core/validation.py | 46 | 0 | 100% |
| src/documentation/control_table.py | 9 | 2 | 78% |
| src/documentation/description_generator.py | 57 | 0 | 100% |
| src/documentation/diagram_generator.py | 48 | 7 | 85% |
| src/documentation/module.py | 21 | 0 | 100% |
| src/documentation/user_instruction.py | 23 | 0 | 100% |
| src/engine/duckdb/engine.py | 77 | 8 | 90% |
| src/engine/ironcalc/engine.py | 185 | 156 | 16% |
| src/engine/ironcalc/sanitizer.py | 25 | 0 | 100% |
| src/export/exporter.py | 41 | 5 | 88% |
| src/export/pdf_exporter.py | 36 | 0 | 100% |
| src/modules/excel2budget/context_builder.py | 78 | 10 | 87% |
| src/modules/excel2budget/importer.py | 111 | 4 | 96% |
| src/modules/excel2budget/pipeline.py | 100 | 20 | 80% |
| src/modules/excel2budget/sql_generator.py | 56 | 5 | 91% |
| src/templates/registry.py | 34 | 10 | 71% |
| src/ui/app.py | 201 | 22 | 89% |
| **TOTAL** | **1444** | **252** | **83%** |

Note: `src/engine/ironcalc/engine.py` has low coverage (16%) because IronCalc WASM requires a native binary that is not exercised in the pure-Python test environment. The sanitizer and all other modules are well covered.

## License

This project is licensed under the MIT License. See [LICENSE.md](LICENSE.md) for details.
