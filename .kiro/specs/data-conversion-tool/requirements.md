# Requirements Document

## Introduction

The Data Conversion Tool is a browser-based budget data conversion pipeline that transforms Excel budget files (wide format with month columns) into accounting package import formats. It runs entirely client-side via WebAssembly, using IronCalc for spreadsheet preview and DuckDB for the transformation logic. The tool supports multiple accounting packages (Twinfield, Exact, Afas) through a template registry, and processes one file at a time.

This tool (excel2budget) is one application module within a larger system. Other modules include update_forecast, reporting_actuals, and potentially others. Each module handles a specific conversion use case but shares a common Documentation Module that generates standardized documentation artifacts via a generic ApplicationContext interface.

## Glossary

- **Pipeline**: The end-to-end conversion orchestrator that coordinates Excel import, mapping extraction, DuckDB transformation, preview, and export
- **Excel_Importer**: The component that parses .xlsx files and extracts budget data and mapping configuration
- **Spreadsheet_Engine**: The IronCalc WASM component that renders spreadsheet previews for input and output data
- **DuckDB_Engine**: The DuckDB WASM component that executes SQL transformation queries
- **Template_Registry**: The component that stores and retrieves output template definitions for each accounting package
- **Format_Exporter**: The component that serializes transformed data into CSV or Excel format for download
- **MappingConfig**: Configuration extracted from the Excel file defining which columns are Entity, Account, DC, and which are month columns
- **OutputTemplate**: A predefined schema for a specific accounting package import format, defining column names, types, ordering, and source mappings
- **TabularData**: The internal data structure representing rows and columns with typed values
- **Unpivot**: The SQL transformation that converts wide-format month columns into long-format rows with Period and Value columns
- **DC_Flag**: A column value of "D" (Debet) or "C" (Credit) indicating how the budget value should be split
- **UserParams**: User-specified parameters per conversion run, including budgetcode and year
- **Budget_Sheet**: The named range or sheet in the Excel file containing the budget data table
- **ArchiMate_Diagram**: An application-layer architecture diagram following the ArchiMate standard, showing the systems involved in a specific conversion configuration, derived from a standard ArchiMate template
- **BPMN_Diagram**: A Business Process Model and Notation diagram showing the process flow for a specific conversion configuration, derived from a standard BPMN template
- **Control_Table**: A condensed reconciliation sheet showing that input totals (sum of budget values) equal output totals (sum of Debet and Credit), proving data integrity through the transformation
- **Configuration**: A specific combination of accounting package, template, mapping config, and user parameters that defines a complete conversion setup
- **Documentation_Module**: A separate module within the system responsible for generating all 7 documentation artifacts per conversion configuration: ArchiMate diagram, BPMN diagram, input description, output description, transform description, control table, and user instruction
- **Input_Description**: A document describing the source data structure, column definitions, and data characteristics for a specific conversion configuration
- **Output_Description**: A document describing the target output structure, column definitions, and accounting package requirements for a specific conversion configuration
- **Transform_Description**: A document describing the transformation logic applied, including the unpivot, DC split, column mapping, and any computed fields
- **User_Instruction**: A step-by-step guide for the end user explaining how to perform the budget conversion for a specific configuration
- **ApplicationContext**: A generic data structure that any application module populates with its domain-specific metadata (source/target systems, process steps, data descriptions, control totals, user instruction steps). The Documentation Module depends only on this structure, enabling reuse across all application modules

## Requirements

### Requirement 1: Excel File Import

**User Story:** As a budget analyst, I want to upload an Excel budget file, so that I can convert its data into an accounting package import format.

#### Acceptance Criteria

1. WHEN a user uploads a valid .xlsx file containing a Budget sheet, THE Excel_Importer SHALL parse the file and return a structured ExcelWorkbook representation
2. WHEN a user uploads a file that is not a valid .xlsx file, THE Excel_Importer SHALL return a ParseError describing the expected format versus the actual file
3. WHEN a user uploads a valid .xlsx file that does not contain a Budget sheet, THE Excel_Importer SHALL return a ParseError listing the available sheet names
4. WHEN the Excel_Importer successfully parses a file, THE Spreadsheet_Engine SHALL render the budget data in a spreadsheet grid for user review

### Requirement 2: Mapping Configuration Extraction

**User Story:** As a budget analyst, I want the tool to automatically extract column mapping configuration from my Excel file, so that I do not have to manually specify which columns are months, accounts, or entities.

#### Acceptance Criteria

1. WHEN a valid ExcelWorkbook is provided, THE Excel_Importer SHALL extract a MappingConfig identifying the entityColumn, accountColumn, and dcColumn
2. WHEN a valid ExcelWorkbook is provided, THE Excel_Importer SHALL detect between 1 and 12 month columns, each with a unique periodNumber in the range 1 to 12
3. IF the Excel file does not contain recognizable mapping configuration, THEN THE Excel_Importer SHALL return a MappingError listing which required columns (Entity, Account, DC) could not be identified
4. IF the mapping configuration references month columns that do not exist in the budget data, THEN THE Excel_Importer SHALL return a MappingError listing available columns and expected month column names
5. WHEN a MappingConfig is extracted, THE Excel_Importer SHALL verify that all referenced column names exist in the budget data sheet

### Requirement 3: Template Selection

**User Story:** As a budget analyst, I want to select a target accounting package and template, so that the output matches the import format required by my accounting system.

#### Acceptance Criteria

1. THE Template_Registry SHALL provide a list of available accounting packages (Twinfield, Exact, Afas)
2. WHEN a user selects an accounting package, THE Template_Registry SHALL provide a list of available templates for that package
3. WHEN a user selects a valid package and template combination, THE Template_Registry SHALL return an OutputTemplate defining the target column schema, column ordering, data types, and source mappings
4. IF a user selects a package or template combination that does not exist, THEN THE Template_Registry SHALL return a TemplateError listing available packages and templates

### Requirement 4: User Parameter Specification

**User Story:** As a budget analyst, I want to specify conversion parameters like budgetcode and year, so that the output contains the correct fixed values for my accounting period.

#### Acceptance Criteria

1. WHEN a user provides UserParams containing a budgetcode and year, THE Pipeline SHALL use these values during the transformation
2. THE Pipeline SHALL require that budgetcode is a non-empty string
3. THE Pipeline SHALL require that year is a positive integer

### Requirement 5: Budget Data Transformation

**User Story:** As a budget analyst, I want the tool to transform my wide-format budget data into the long format required by my accounting package, so that I can import the data without manual restructuring.

#### Acceptance Criteria

1. WHEN the transformation is executed, THE DuckDB_Engine SHALL unpivot the month columns into rows, producing one output row per source row per month column
2. WHEN the source data contains R rows (after null-account filtering) and M month columns, THE Pipeline SHALL produce exactly R × M output rows
3. WHEN a source row has a DC_Flag value of "D", THE Pipeline SHALL set Debet to ROUND(Value, 4) and Credit to null for that output row
4. WHEN a source row has a DC_Flag value of "C", THE Pipeline SHALL set Credit to ROUND(ABS(Value), 4) and Debet to null for that output row
5. THE Pipeline SHALL ensure that for every output row with a non-null source Value, exactly one of Debet or Credit is non-null
6. WHEN the transformation is executed, THE Pipeline SHALL set the Periode value of each output row to the periodNumber (1 to 12) corresponding to the source month column
7. WHEN the transformation is executed, THE Pipeline SHALL set the Budgetcode of every output row to the user-specified budgetcode value
8. WHEN the transformation is executed, THE Pipeline SHALL set the Jaar of every output row to the user-specified year value
9. WHEN the source data contains rows with null Account values, THE Pipeline SHALL filter those rows out before the unpivot transformation
10. WHEN the transformation is executed, THE Pipeline SHALL produce output columns matching the selected OutputTemplate in name, order, and compatible data types

### Requirement 6: SQL Generation

**User Story:** As a budget analyst, I want the transformation to be driven by generated SQL, so that the conversion logic is transparent and auditable.

#### Acceptance Criteria

1. WHEN a MappingConfig, OutputTemplate, and UserParams are provided, THE Pipeline SHALL generate a syntactically valid DuckDB SQL string
2. THE Pipeline SHALL generate SQL that is SELECT-only, containing no DDL or DML statements
3. THE Pipeline SHALL generate SQL that references only the registered "budget" table
4. THE Pipeline SHALL use parameterized or validated identifiers to prevent SQL injection

### Requirement 7: Data Registration in DuckDB

**User Story:** As a budget analyst, I want my budget data to be loaded into DuckDB for transformation, so that the SQL engine can process it efficiently.

#### Acceptance Criteria

1. WHEN budget data is registered in DuckDB, THE DuckDB_Engine SHALL create a table with a schema matching the TabularData column definitions
2. WHEN budget data is registered in DuckDB, THE DuckDB_Engine SHALL insert exactly the same number of rows as the source TabularData
3. WHEN budget data is registered and immediately queried, THE DuckDB_Engine SHALL return data equivalent to the original TabularData (same schema, same values, same row count)
4. THE DuckDB_Engine SHALL validate that table names match the pattern [a-zA-Z_][a-zA-Z0-9_]*

### Requirement 8: Output Preview

**User Story:** As a budget analyst, I want to preview the transformed data before exporting, so that I can verify the conversion is correct.

#### Acceptance Criteria

1. WHEN the transformation completes successfully, THE Spreadsheet_Engine SHALL render the transformed data in a spreadsheet grid for user review
2. WHEN the transformation fails, THE Pipeline SHALL return a TransformResult.Error containing the error message and SQL state code

### Requirement 9: Data Export

**User Story:** As a budget analyst, I want to export the transformed data as CSV or Excel, so that I can import it into my accounting package.

#### Acceptance Criteria

1. WHEN a user requests export in CSV format, THE Format_Exporter SHALL serialize the transformed TabularData into a valid CSV file
2. WHEN a user requests export in Excel format, THE Format_Exporter SHALL serialize the transformed TabularData into a valid .xlsx file
3. WHEN exporting data, THE Format_Exporter SHALL preserve the column ordering defined by the OutputTemplate
4. WHEN exporting data, THE Format_Exporter SHALL produce output with the same row count as the transformed TabularData
5. WHEN export completes, THE Format_Exporter SHALL provide a downloadable blob to the user

### Requirement 10: Source Data Integrity

**User Story:** As a budget analyst, I want assurance that the original data is not modified during conversion, so that I can re-run the transformation or use the source data for other purposes.

#### Acceptance Criteria

1. WHEN the transformation is executed, THE Pipeline SHALL leave the original budget table in DuckDB unmodified
2. WHEN the transformation is executed, THE Pipeline SHALL leave the source spreadsheet data in the Spreadsheet_Engine unmodified

### Requirement 11: Transformation Determinism

**User Story:** As a budget analyst, I want the same inputs to always produce the same output, so that I can trust the conversion results are reproducible.

#### Acceptance Criteria

1. WHEN the same input data, MappingConfig, OutputTemplate, and UserParams are provided, THE Pipeline SHALL produce identical output on every execution

### Requirement 12: TabularData Validation

**User Story:** As a developer, I want the internal data structures to be validated, so that data integrity is maintained throughout the pipeline.

#### Acceptance Criteria

1. THE Pipeline SHALL ensure that every Row in a TabularData instance has exactly the same number of values as there are columns
2. THE Pipeline SHALL ensure that column names within a TabularData instance are unique
3. THE Pipeline SHALL ensure that the rowCount field equals the actual number of rows

### Requirement 13: Client-Side Processing

**User Story:** As a budget analyst, I want all data processing to happen in my browser, so that sensitive budget data never leaves my machine.

#### Acceptance Criteria

1. THE Pipeline SHALL execute all data parsing, transformation, and export operations client-side using WebAssembly
2. THE Pipeline SHALL transmit no budget data to any server

### Requirement 14: Error Handling for Invalid DC Values

**User Story:** As a budget analyst, I want clear error messages when my data contains invalid DC flag values, so that I can fix the source data.

#### Acceptance Criteria

1. IF the DC column contains values other than "D" or "C", THEN THE Pipeline SHALL return a TransformResult.Error listing the invalid values and their row positions

### Requirement 15: Memory Safety

**User Story:** As a budget analyst, I want the tool to handle large files gracefully, so that my browser does not crash during conversion.

#### Acceptance Criteria

1. IF the data size exceeds the browser WASM memory allocation, THEN THE Pipeline SHALL raise a MemoryError with current usage and estimated requirement
2. THE Pipeline SHALL validate file sizes before parsing to prevent memory exhaustion

### Requirement 16: Content Security

**User Story:** As a developer, I want cell values to be sanitized before rendering, so that malicious content in Excel files cannot execute scripts in the browser.

#### Acceptance Criteria

1. WHEN rendering cell values in the Spreadsheet_Engine, THE Pipeline SHALL sanitize all values to prevent cross-site scripting (XSS)

### Requirement 17: Documentation Module

**User Story:** As a budget analyst, I want a dedicated documentation module that generates a complete set of documentation artifacts for each conversion configuration, so that I have full traceability, audit support, and user guidance.

The Documentation Module is a separate module within the system, though integral to the overall pipeline. It produces 7 artifacts per configuration, all viewable in the UI and downloadable as PDF (see Requirement 22).

#### Acceptance Criteria

**17.1 ArchiMate Diagram**
1. WHEN a conversion configuration is defined, THE Documentation_Module SHALL generate an ArchiMate application-layer diagram showing the systems involved in that configuration
2. THE ArchiMate diagram SHALL be derived from a standard ArchiMate template provided to the tool
3. THE ArchiMate diagram SHALL show at minimum: the source system (Excel), the conversion tool, and the target accounting package (e.g., Twinfield, Exact, Afas)

**17.2 BPMN Process Flow Diagram**
1. WHEN a conversion configuration is defined, THE Documentation_Module SHALL generate a BPMN diagram showing the process flow for that configuration
2. THE BPMN diagram SHALL be derived from a standard BPMN template provided to the tool
3. THE BPMN diagram SHALL show the process steps: file upload, mapping extraction, parameter specification, transformation, review, and export

**17.3 Input Description**
1. WHEN a conversion configuration is defined, THE Documentation_Module SHALL generate an Input_Description document
2. THE Input_Description SHALL describe the source Excel file structure: sheet name, column names and types, which columns are Entity, Account, DC, and which are month columns
3. THE Input_Description SHALL include the MappingConfig details (column assignments, month-to-period mapping)

**17.4 Output Description**
1. WHEN a conversion configuration is defined, THE Documentation_Module SHALL generate an Output_Description document
2. THE Output_Description SHALL describe the target output structure: column names, data types, ordering, and which accounting package template it conforms to
3. THE Output_Description SHALL include any fixed values (Budgetcode, null placeholder columns) and their sources

**17.5 Transform Description**
1. WHEN a conversion configuration is defined, THE Documentation_Module SHALL generate a Transform_Description document
2. THE Transform_Description SHALL describe the transformation logic: unpivot operation, DC-based Debet/Credit split, column renaming, type casting, and rounding rules
3. THE Transform_Description SHALL include the generated SQL or a human-readable equivalent

**17.6 Control Table**
1. WHEN the transformation completes successfully, THE Documentation_Module SHALL generate a Control_Table output sheet
2. THE Control_Table SHALL display the sum of all source budget values (before transformation)
3. THE Control_Table SHALL display the sum of all Debet values and the sum of all Credit values in the output
4. THE Control_Table SHALL display a reconciliation check confirming that the sum of source values equals the sum of Debet plus the sum of Credit (or equivalent balance proof)
5. THE Control_Table SHALL display row counts for both input (after null-account filtering) and output

**17.7 User Instruction**
1. WHEN a conversion configuration is defined, THE Documentation_Module SHALL generate a User_Instruction document
2. THE User_Instruction SHALL provide step-by-step guidance for performing the budget conversion: uploading the file, verifying the mapping, setting parameters, running the transformation, reviewing the output, and exporting
3. THE User_Instruction SHALL be specific to the selected accounting package and template

**General Documentation Module Criteria**
1. ALL 7 documentation artifacts SHALL be viewable within the tool's UI
2. ALL 7 documentation artifacts SHALL be downloadable as PDF (see Requirement 20)
3. ALL 7 documentation artifacts SHALL include the configuration date and current date
4. THE Documentation_Module SHALL be architecturally separate from the conversion pipeline, communicating via a generic ApplicationContext interface that any application module (excel2budget, update_forecast, reporting_actuals, etc.) can populate

### Requirement 18: Date Display on All Screens

**User Story:** As a budget analyst, I want every screen in the tool to display the current date, so that I always know when I am viewing or working with the data.

#### Acceptance Criteria

1. EVERY screen rendered by the Pipeline SHALL display the current date in a visible location
2. THE date SHALL be formatted in a locale-appropriate format (e.g., DD-MM-YYYY or YYYY-MM-DD)

### Requirement 19: Date Stamping on Input and Output Data

**User Story:** As a budget analyst, I want all input and output data to carry a date stamp, so that I can trace when data was imported and when conversions were performed.

#### Acceptance Criteria

1. WHEN an Excel file is imported, THE Pipeline SHALL record the import date-time in the data metadata
2. WHEN a transformation is executed, THE Pipeline SHALL record the transformation date-time in the output data metadata
3. WHEN data is exported, THE Pipeline SHALL include the export date-time in the exported file metadata or as a header/footer
4. THE date stamps SHALL be in ISO 8601 format (YYYY-MM-DDTHH:MM:SS) for metadata and locale-appropriate format for display

### Requirement 20: PDF Download for All Screens

**User Story:** As a budget analyst, I want to download any screen as a PDF, so that I can archive, print, or share the conversion results and documentation.

#### Acceptance Criteria

1. EVERY screen rendered by the Pipeline SHALL provide a "Download as PDF" action
2. THE PDF export SHALL capture the full content of the screen, including spreadsheet data, diagrams (ArchiMate, BPMN), and the control table
3. THE PDF export SHALL include the date stamp (see Requirement 18) and any relevant metadata (configuration name, accounting package, template)
4. THE PDF export SHALL preserve the layout and formatting of the screen content
