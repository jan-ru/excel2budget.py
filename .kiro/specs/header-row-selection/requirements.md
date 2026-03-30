# Requirements Document

## Introduction

The Excel_Importer currently hardcodes `raw[0]` (the first row of the sheet) as the header row when extracting budget data and column mapping configuration. This works when the required columns (Entity, Account, DC) appear in row 1, but fails silently or errors out when headers are on a different row (e.g., the sheet has a title row, metadata rows, or blank rows above the actual headers).

This specification adds header row detection and selection to the import flow. When the required columns are found in row 1, the import proceeds automatically. When they are not found, the application scans subsequent rows and either auto-selects the correct header row or prompts the user to specify which row contains the headers. The Upload_Screen progressively displays resolved import variables (filename, sheet name, header row) as each step completes.

This feature builds on top of the existing dynamic sheet selection feature (`.kiro/specs/dynamic-sheet-selection/`).

## Glossary

- **Excel_Importer**: The frontend module (`frontend/src/import/excel-importer.ts`) that parses .xlsx files client-side using SheetJS and extracts budget data and column mapping configuration
- **Pipeline_Orchestrator**: The frontend module (`frontend/src/pipeline/orchestrator.ts`) that coordinates the client-side data flow: import → validate → transform → preview → export
- **Upload_Screen**: The frontend UI screen (`frontend/src/ui/screens/upload.ts`) where the user selects and uploads an .xlsx file and resolves import parameters
- **Header_Row_Selector**: A new UI component that displays a dropdown of candidate row numbers and allows the user to select which row contains the column headers
- **Required_Columns**: The set of column names that must be present in the header row for a valid budget import: Entity, Account, DC
- **Header_Row_Index**: A zero-based integer index identifying which row of the sheet's raw data array contains the column headers
- **Progress_Summary**: A UI section on the Upload_Screen that displays the resolved import variables (filename, sheet name, header row) as each step completes
- **Sheet_Raw_Data**: The two-dimensional array of cell values returned by SheetJS `sheet_to_json` with `header: 1` for a given sheet

## Requirements

### Requirement 1: Automatic Header Row Detection

**User Story:** As a user, I want the importer to automatically detect the header row when the required columns are in row 1, so that my existing workflow is unchanged.

#### Acceptance Criteria

1. WHEN the first row of the Sheet_Raw_Data contains all Required_Columns (Entity, Account, DC), THE Excel_Importer SHALL use row index 0 as the Header_Row_Index without prompting the user
2. WHEN the first row contains all Required_Columns, THE Pipeline_Orchestrator SHALL proceed with data extraction using Header_Row_Index 0

### Requirement 2: Header Row Scanning

**User Story:** As a user, I want the importer to scan the sheet for the header row when it is not in row 1, so that the correct row can be identified automatically or I can be prompted to select it.

#### Acceptance Criteria

1. WHEN the first row of the Sheet_Raw_Data does not contain all Required_Columns, THE Excel_Importer SHALL scan rows 0 through 19 (the first 20 rows) for a row containing all Required_Columns
2. WHEN exactly one row within the scanned range contains all Required_Columns, THE Excel_Importer SHALL return that row's index as the detected Header_Row_Index
3. WHEN multiple rows within the scanned range contain all Required_Columns, THE Excel_Importer SHALL return the list of candidate row indices to the caller
4. WHEN no row within the scanned range contains all Required_Columns, THE Excel_Importer SHALL return an empty list of candidate row indices to the caller
5. THE Excel_Importer SHALL perform Required_Columns matching using the same case-insensitive logic used for column detection in extractMappingConfig

### Requirement 3: Header Row Selection UI

**User Story:** As a user, I want to see a dropdown of candidate rows when the header row cannot be auto-detected, so that I can pick the correct one.

#### Acceptance Criteria

1. WHEN the Excel_Importer returns zero or multiple candidate header rows, THE Upload_Screen SHALL display the Header_Row_Selector component
2. THE Header_Row_Selector SHALL render a dropdown populated with candidate row numbers (displayed as 1-based row numbers for user readability) and a preview of each row's first three cell values
3. WHEN no candidate rows are found, THE Header_Row_Selector SHALL allow the user to select any row from 1 to 20 (displayed as 1-based) from the Sheet_Raw_Data
4. THE Header_Row_Selector SHALL display a "Confirm" action that submits the selected Header_Row_Index
5. THE Header_Row_Selector SHALL display a "Cancel" action that aborts the import and returns to the initial upload state
6. THE Header_Row_Selector SHALL disable the "Confirm" action until the user selects a row from the dropdown

### Requirement 4: Import with User-Selected Header Row

**User Story:** As a user, I want the import to use the header row I selected, so that data extraction starts from the correct row.

#### Acceptance Criteria

1. WHEN the user confirms a header row selection, THE Pipeline_Orchestrator SHALL call the Excel_Importer with the user-selected Header_Row_Index
2. WHEN a Header_Row_Index is provided, THE Excel_Importer SHALL use the specified row as the column header source and treat all subsequent rows as data rows
3. WHEN a Header_Row_Index is provided, THE Excel_Importer SHALL ignore all rows above the Header_Row_Index (treating them as non-data preamble)
4. IF the user-selected header row does not contain all Required_Columns, THEN THE Excel_Importer SHALL return a MappingError listing the missing columns

### Requirement 5: Progressive Import Summary Display

**User Story:** As a user, I want to see the resolved import variables (filename, sheet name, header row) appear progressively on the upload screen, so that I have clear visibility into the import state.

#### Acceptance Criteria

1. WHEN a file is selected, THE Upload_Screen SHALL display the filename in the Progress_Summary
2. WHEN a sheet is resolved (either automatically as "Budget" or via user selection), THE Upload_Screen SHALL display the sheet name in the Progress_Summary
3. WHEN a header row is resolved (either automatically as row 1 or via user selection), THE Upload_Screen SHALL display the header row number (1-based) in the Progress_Summary
4. THE Upload_Screen SHALL display each Progress_Summary item only after the corresponding step completes successfully
5. WHEN the user cancels or resets the import, THE Upload_Screen SHALL clear all Progress_Summary items

### Requirement 6: Backward Compatibility with Existing Flow

**User Story:** As a user with files that have headers in row 1, I want the import to work exactly as before, so that the new feature does not disrupt my workflow.

#### Acceptance Criteria

1. WHEN a Workbook contains a "Budget" sheet with Required_Columns in row 1, THE Pipeline_Orchestrator SHALL complete the import without prompting for sheet selection or header row selection
2. WHEN a Workbook requires sheet selection but the selected sheet has Required_Columns in row 1, THE Pipeline_Orchestrator SHALL complete the import after sheet selection without prompting for header row selection

### Requirement 7: Error Handling for Header Row Selection Flow

**User Story:** As a user, I want clear error messages during the header row selection flow, so that I know what went wrong.

#### Acceptance Criteria

1. IF the user-selected header row produces a MappingError, THEN THE Upload_Screen SHALL display the error and return to the Header_Row_Selector so the user can pick a different row or cancel
2. IF the sheet contains fewer rows than the scanned range (20 rows), THEN THE Excel_Importer SHALL scan only the available rows without error
3. WHEN the user activates the "Cancel" action on the Header_Row_Selector, THE Pipeline_Orchestrator SHALL discard the pending import state and THE Upload_Screen SHALL reset to the initial file upload state
