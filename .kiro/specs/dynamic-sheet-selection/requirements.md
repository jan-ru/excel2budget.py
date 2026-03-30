# Requirements Document

## Introduction

The Excel_Importer currently hardcodes "Budget" as the target sheet name when extracting data from uploaded .xlsx files. This specification adds dynamic sheet selection: when the workbook contains a "Budget" sheet, the importer uses it automatically (preserving backward compatibility). When no "Budget" sheet exists, the application presents the user with a dropdown of available sheet names so the user can pick the correct one, or cancel to return to the initial upload state.

## Glossary

- **Excel_Importer**: The frontend module (`frontend/src/import/excel-importer.ts`) that parses .xlsx files client-side using SheetJS and extracts budget data and column mapping configuration
- **Pipeline_Orchestrator**: The frontend module (`frontend/src/pipeline/orchestrator.ts`) that coordinates the client-side data flow: import → validate → transform → preview → export
- **Upload_Screen**: The frontend UI screen (`frontend/src/ui/screens/upload.ts`) where the user selects and uploads an .xlsx file
- **Sheet_Selector**: A new UI component that displays a dropdown of available sheet names and allows the user to select one or cancel
- **Workbook**: A parsed SheetJS workbook object containing one or more named sheets
- **Sheet_Name_List**: The ordered array of sheet names available in a parsed Workbook (from `workbook.SheetNames`)

## Requirements

### Requirement 1: Automatic Budget Sheet Detection

**User Story:** As a user, I want the importer to automatically use the "Budget" sheet when it exists, so that my existing workflow is unchanged.

#### Acceptance Criteria

1. WHEN a Workbook contains a sheet named "Budget", THE Excel_Importer SHALL extract data from the "Budget" sheet without prompting the user for sheet selection
2. WHEN a Workbook contains a sheet named "Budget", THE Pipeline_Orchestrator SHALL proceed with the import pipeline using the "Budget" sheet data

### Requirement 2: Sheet Name Extraction

**User Story:** As a user, I want the application to read all available sheet names from my uploaded file, so that I can choose the correct one when "Budget" is not present.

#### Acceptance Criteria

1. WHEN a Workbook does not contain a sheet named "Budget", THE Excel_Importer SHALL return the Sheet_Name_List to the caller
2. THE Excel_Importer SHALL preserve the original order of sheet names as they appear in the Workbook
3. THE Sheet_Name_List SHALL contain all sheet names present in the Workbook without filtering or modification

### Requirement 3: Sheet Selection UI

**User Story:** As a user, I want to see a dropdown of available sheets when "Budget" is not found, so that I can pick the sheet that contains my budget data.

#### Acceptance Criteria

1. WHEN the Excel_Importer reports that no "Budget" sheet exists, THE Upload_Screen SHALL display the Sheet_Selector component
2. THE Sheet_Selector SHALL render a dropdown (`<select>` or ui5-select) populated with all entries from the Sheet_Name_List
3. THE Sheet_Selector SHALL display a "Confirm" action that submits the selected sheet name
4. THE Sheet_Selector SHALL display a "Cancel" action that aborts the sheet selection
5. THE Sheet_Selector SHALL disable the "Confirm" action until the user selects a sheet name from the dropdown

### Requirement 4: Import with User-Selected Sheet

**User Story:** As a user, I want the import to proceed with the sheet I selected, so that I can work with budget data that is not on a sheet named "Budget".

#### Acceptance Criteria

1. WHEN the user confirms a sheet selection, THE Pipeline_Orchestrator SHALL call the Excel_Importer with the user-selected sheet name
2. WHEN the user confirms a sheet selection, THE Excel_Importer SHALL extract budget data and column mapping configuration from the user-selected sheet
3. IF the user-selected sheet is empty, THEN THE Excel_Importer SHALL return a descriptive error indicating the sheet contains no data

### Requirement 5: Cancel Returns to Initial State

**User Story:** As a user, I want to cancel the sheet selection and go back to the upload state, so that I can upload a different file instead.

#### Acceptance Criteria

1. WHEN the user activates the "Cancel" action on the Sheet_Selector, THE Upload_Screen SHALL hide the Sheet_Selector component
2. WHEN the user activates the "Cancel" action on the Sheet_Selector, THE Upload_Screen SHALL reset to the initial file upload state (file input cleared, no status messages)
3. WHEN the user activates the "Cancel" action on the Sheet_Selector, THE Pipeline_Orchestrator SHALL discard the parsed Workbook from memory

### Requirement 6: Error Handling for Sheet Selection Flow

**User Story:** As a user, I want clear error messages during the sheet selection flow, so that I know what went wrong.

#### Acceptance Criteria

1. IF the uploaded file contains zero sheets, THEN THE Excel_Importer SHALL return a descriptive error indicating the workbook is empty
2. IF data extraction from the user-selected sheet fails, THEN THE Upload_Screen SHALL display the error and return to the sheet selection state so the user can pick a different sheet or cancel
