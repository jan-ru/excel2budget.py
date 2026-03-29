"""CLI entry point for the Data Conversion Tool.

Parses command-line arguments and orchestrates the budget conversion
pipeline: load Excel → extract data → select template → transform → export.

Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 6.1, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3
"""

from __future__ import annotations

import argparse
import os
import sys

from src.core.types import FileFormat, TransformError, UserParams
from src.modules.excel2budget.importer import (
    ParseError,
    MappingError,
    extractBudgetData,
    extractMappingConfig,
    parseExcelFile,
)
from src.modules.excel2budget.pipeline import export_data, run_budget_transformation
from src.templates.registry import (
    TemplateError,
    getTemplate,
    listPackages,
    listTemplates,
)

VERSION = "0.1.0"


class _CliArgumentParser(argparse.ArgumentParser):
    """ArgumentParser subclass that exits with code 1 on argument errors."""

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"Error: {message}\n")


def build_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser."""
    parser = _CliArgumentParser(
        prog="data-conversion-tool",
        description="Convert Excel budget files to accounting package formats.",
    )

    # Positional arguments
    parser.add_argument("input_file", help="Path to the .xlsx budget file")
    parser.add_argument("package", help="Accounting package name (e.g. twinfield, exact, afas)")
    parser.add_argument("template", help="Template name within the package (e.g. budget)")

    # Required named arguments
    parser.add_argument("--budgetcode", required=True, help="Budget code identifier")
    parser.add_argument("--year", type=int, required=True, help="Budget year")

    # Optional arguments
    parser.add_argument("-o", "--output", default=None, help="Output file path (default: stdout for CSV)")
    parser.add_argument("-f", "--format", default="csv", choices=["csv", "excel"],
                        help="Export format (default: csv)")

    # Mutually exclusive verbose/quiet
    verbosity = parser.add_mutually_exclusive_group()
    verbosity.add_argument("-v", "--verbose", action="store_true", help="Print progress messages to stderr")
    verbosity.add_argument("-q", "--quiet", action="store_true", help="Suppress all non-error output")

    # Listing commands
    parser.add_argument("--list-packages", action="store_true",
                        help="List available accounting packages and exit")
    parser.add_argument("--list-templates", metavar="PACKAGE",
                        help="List available templates for a package and exit")

    # Version
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    return parser


def run(args: argparse.Namespace) -> int:
    """Orchestrate the conversion pipeline. Returns exit code 0, 1, or 2."""

    # --- Log helper based on verbosity level ---
    def log(msg: str) -> None:
        """Print *msg* to stderr unless --quiet is active."""
        if not args.quiet:
            print(msg, file=sys.stderr)

    def log_verbose(msg: str) -> None:
        """Print *msg* to stderr only when --verbose is active."""
        if args.verbose:
            print(msg, file=sys.stderr)

    # --- Early-exit: listing commands ---
    if args.list_packages:
        for pkg in listPackages():
            print(pkg)
        return 0

    if args.list_templates is not None:
        try:
            for tpl in listTemplates(args.list_templates):
                print(tpl)
        except TemplateError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            if exc.available_packages:
                print(f"Available packages: {', '.join(exc.available_packages)}", file=sys.stderr)
            return 1
        return 0

    # --- Input file reading and parsing ---
    log_verbose(f"Loading file: {args.input_file}")
    try:
        raw_bytes = open(args.input_file, "rb").read()
    except FileNotFoundError:
        print(f"Error: file not found: {args.input_file}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"Error: permission denied: {args.input_file}", file=sys.stderr)
        return 1

    workbook = parseExcelFile(raw_bytes)
    if isinstance(workbook, ParseError):
        print(f"Error: {workbook.message}", file=sys.stderr)
        return 1

    log_verbose("Extracting budget data")
    budget_data = extractBudgetData(workbook)
    if isinstance(budget_data, ParseError):
        print(f"Error: {budget_data.message}", file=sys.stderr)
        return 1

    log_verbose("Extracting mapping configuration")
    mapping_config = extractMappingConfig(workbook)
    if isinstance(mapping_config, MappingError):
        print(f"Error: {mapping_config.message}", file=sys.stderr)
        return 1

    # --- Template lookup ---
    log_verbose(f"Selecting template: {args.package}/{args.template}")
    try:
        template = getTemplate(args.package, args.template)
    except TemplateError as exc:
        msg = f"Error: {exc}"
        if exc.available_packages:
            msg += f"\nAvailable packages: {', '.join(exc.available_packages)}"
        if exc.available_templates:
            msg += f"\nAvailable templates: {', '.join(exc.available_templates)}"
        print(msg, file=sys.stderr)
        return 1

    # --- Transformation ---
    log_verbose("Running transformation")
    user_params = UserParams(budgetcode=args.budgetcode, year=args.year)
    result = run_budget_transformation(budget_data, mapping_config, template, user_params)

    if isinstance(result, TransformError):
        print(f"Error: {result.message}", file=sys.stderr)
        return 2

    # --- Export ---
    log_verbose("Exporting data")
    file_format = FileFormat[args.format.upper()]
    output_bytes = export_data(result.data, file_format, template)

    input_rows = budget_data.rowCount if hasattr(budget_data, "rowCount") else len(getattr(budget_data, "rows", []))
    output_rows = result.data.rowCount if hasattr(result.data, "rowCount") else len(getattr(result.data, "rows", []))

    if args.output:
        output_path = args.output
        try:
            with open(args.output, "wb") as f:
                f.write(output_bytes)
        except (IOError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
    elif file_format == FileFormat.CSV:
        output_path = "stdout"
        sys.stdout.write(output_bytes.decode("utf-8"))
    else:
        # Excel with no --output: derive default filename from input
        base, _ = os.path.splitext(os.path.basename(args.input_file))
        default_name = f"{base}_output.xlsx"
        output_path = default_name
        try:
            with open(default_name, "wb") as f:
                f.write(output_bytes)
        except (IOError, OSError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    # Default summary line (suppressed in quiet mode)
    log(f"Converted {input_rows} rows → {output_rows} rows, output: {output_path}")

    return 0


def main() -> None:
    """Entry point: parse args, run pipeline, exit."""
    parser = build_parser()
    args = parser.parse_args()
    code = run(args)
    sys.exit(code)
