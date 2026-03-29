# Requirements Document

## Introduction

This feature adds a command-line interface (CLI) entry point to the Data Conversion Tool. The project currently has no executable entry point — it can only be used programmatically or via tests. The CLI will allow users to perform the full budget conversion workflow from the terminal: load an Excel budget file, select an accounting package and template, provide user parameters, run the transformation, and export the result to CSV or Excel.

## Glossary

- **CLI**: The command-line interface program that serves as the entry point to the Data Conversion Tool
- **Budget_File**: An Excel (.xlsx) file containing budget data in wide format with month columns (e.g., "jan-26", "feb-26")
- **Accounting_Package**: A target accounting system (Twinfield, Exact, or Afas) that defines the output format
- **Template**: A named output schema within an Accounting_Package (currently "budget" for all packages)
- **Budgetcode**: A user-supplied string identifier for the budget conversion run
- **Year**: A user-supplied integer representing the budget year
- **Mapping_Config**: Column mapping configuration automatically extracted from the Budget_File header row
- **Export_Format**: The output file format, either CSV or EXCEL
- **Pipeline**: The existing budget transformation pipeline (`src/modules/excel2budget/pipeline.py`)

## Requirements

### Requirement 1: CLI Invocation

**User Story:** As a developer, I want to run the budget conversion from the command line, so that I can automate conversions without a UI.

#### Acceptance Criteria

1. THE CLI SHALL accept the following required arguments: input file path, accounting package name, and template name
2. THE CLI SHALL accept the following required arguments: budgetcode (string) and year (integer)
3. THE CLI SHALL accept an optional argument for the output file path
4. THE CLI SHALL accept an optional argument for the export format, defaulting to CSV
5. WHEN the CLI is invoked with `--help`, THE CLI SHALL display usage information describing all arguments and their expected values
6. WHEN the CLI is invoked with `--version`, THE CLI SHALL display the tool version from the project metadata

### Requirement 2: Input File Loading

**User Story:** As a developer, I want the CLI to load and parse my Excel budget file, so that I can convert it without manual steps.

#### Acceptance Criteria

1. WHEN a valid Excel file path is provided, THE CLI SHALL read the file and pass its bytes to the Pipeline import function
2. IF the input file path does not exist, THEN THE CLI SHALL print an error message stating the file was not found and exit with a non-zero exit code
3. IF the input file is not a valid .xlsx file, THEN THE CLI SHALL print the parse error message from the Pipeline and exit with a non-zero exit code
4. WHEN the Budget_File is successfully parsed, THE CLI SHALL automatically extract the Mapping_Config from the file header row

### Requirement 3: Template Selection

**User Story:** As a developer, I want to specify the target accounting package and template, so that the output matches my accounting system's import format.

#### Acceptance Criteria

1. WHEN a valid Accounting_Package and Template name are provided, THE CLI SHALL retrieve the corresponding output template from the template registry
2. IF the specified Accounting_Package does not exist, THEN THE CLI SHALL print an error message listing the available packages and exit with a non-zero exit code
3. IF the specified Template does not exist for the given Accounting_Package, THEN THE CLI SHALL print an error message listing the available templates for that package and exit with a non-zero exit code
4. WHEN the CLI is invoked with `--list-packages`, THE CLI SHALL print all available Accounting_Package names and exit with a zero exit code
5. WHEN the CLI is invoked with `--list-templates` and a package name, THE CLI SHALL print all available Template names for that package and exit with a zero exit code

### Requirement 4: Transformation Execution

**User Story:** As a developer, I want the CLI to run the budget transformation, so that I get the converted output data.

#### Acceptance Criteria

1. WHEN all inputs are valid (Budget_File, Mapping_Config, Template, budgetcode, year), THE CLI SHALL invoke the Pipeline transformation function
2. IF the transformation returns an error, THEN THE CLI SHALL print the error message to stderr and exit with a non-zero exit code
3. WHEN the transformation succeeds, THE CLI SHALL proceed to export the result

### Requirement 5: Output Export

**User Story:** As a developer, I want the CLI to write the converted data to a file, so that I can import it into my accounting system.

#### Acceptance Criteria

1. WHEN an output file path is provided, THE CLI SHALL write the exported data to that path
2. WHEN no output file path is provided, THE CLI SHALL write the exported data to stdout (for CSV) or to a default filename derived from the input filename (for Excel)
3. WHEN the export format is CSV, THE CLI SHALL export the transformed data as CSV
4. WHEN the export format is EXCEL, THE CLI SHALL export the transformed data as an Excel file
5. IF writing the output file fails, THEN THE CLI SHALL print an error message to stderr and exit with a non-zero exit code
6. WHEN the export completes successfully, THE CLI SHALL exit with a zero exit code

### Requirement 6: Exit Codes and Error Reporting

**User Story:** As a developer, I want consistent exit codes and error messages, so that I can use the CLI in scripts and automation pipelines.

#### Acceptance Criteria

1. THE CLI SHALL exit with code 0 on successful completion
2. THE CLI SHALL exit with code 1 on any user input error (missing file, invalid arguments, unknown package/template)
3. THE CLI SHALL exit with code 2 on any transformation or export error
4. THE CLI SHALL print all error messages to stderr
5. THE CLI SHALL print only the export output (or nothing, when writing to a file) to stdout

### Requirement 7: Verbose and Quiet Modes

**User Story:** As a developer, I want to control the amount of output from the CLI, so that I can debug issues or suppress noise in scripts.

#### Acceptance Criteria

1. WHEN the `--verbose` flag is provided, THE CLI SHALL print progress messages to stderr for each pipeline stage (file loading, mapping extraction, template selection, transformation, export)
2. WHEN the `--quiet` flag is provided, THE CLI SHALL suppress all non-error output to stderr
3. THE CLI SHALL default to printing a summary line to stderr on successful completion (input rows, output rows, output path)
