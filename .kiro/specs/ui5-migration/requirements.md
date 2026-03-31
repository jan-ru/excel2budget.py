# Requirements Document

## Introduction

Migrate the Data Conversion Tool frontend from plain HTML elements with inline CSS styles to UI5 Web Components (v2.7+). The migration replaces all interactive elements (buttons, inputs, selects, file uploaders) and structural patterns (navigation, error banners, dialogs) with their UI5 equivalents while preserving all existing functionality and test coverage. The migration proceeds screen by screen to allow incremental validation.

## Glossary

- **App_Shell**: The top-level application layout in `app.ts` that contains the header, navigation, error container, and content area.
- **Navigation_Bar**: The screen-switching navigation element in the App_Shell, currently a plain `<nav>` with `<button>` elements.
- **Tab_Container**: A `ui5-tabcontainer` element that replaces the Navigation_Bar for screen switching.
- **Screen**: One of the six application views: Upload, Preview, Configuration, Transform, Output, Documentation.
- **Error_Banner**: The reusable error display component in `error-banner.ts`.
- **Message_Strip**: A `ui5-message-strip` element that replaces the Error_Banner.
- **Sheet_Selector**: The reusable sheet selection dropdown component in `sheet-selector.ts`.
- **Header_Row_Selector**: The reusable header row selection dropdown component in `header-row-selector.ts`.
- **Header_Component**: The application header bar component in `header.ts` with title, date, and PDF download action.
- **UI5_Button**: A `ui5-button` custom element replacing plain `<button>` elements.
- **UI5_Select**: A `ui5-select` custom element with `ui5-option` children replacing plain `<select>` elements.
- **UI5_Input**: A `ui5-input` custom element replacing plain `<input type="text">` and `<input type="number">` elements.
- **UI5_File_Uploader**: A `ui5-file-uploader` custom element replacing plain `<input type="file">` elements.
- **Value_State**: A UI5 attribute (`value-state`) used on input components to indicate validation status: `"None"`, `"Positive"`, `"Critical"`, `"Negative"`, `"Information"`.
- **Design_Variant**: A UI5 attribute (`design`) used on buttons to indicate visual intent: `"Default"`, `"Emphasized"`, `"Positive"`, `"Negative"`, `"Transparent"`.

## Requirements

### Requirement 1: App Shell Navigation Migration

**User Story:** As a user, I want the screen navigation to use a UI5 tab container, so that the navigation has a consistent enterprise look and feel with proper tab semantics.

#### Acceptance Criteria

1. WHEN the App_Shell mounts, THE Tab_Container SHALL render one `ui5-tab` element for each of the six screens with the corresponding screen label as the tab text.
2. WHEN a user selects a tab in the Tab_Container, THE App_Shell SHALL navigate to the corresponding Screen and render the screen content in the content area.
3. WHILE a Screen is active, THE Tab_Container SHALL visually indicate the active tab using the built-in UI5 selected-tab styling.
4. THE App_Shell SHALL import `@ui5/webcomponents/dist/TabContainer.js` and `@ui5/webcomponents/dist/Tab.js` as side-effect modules before creating Tab_Container elements.
5. THE App_Shell SHALL remove all inline CSS styles from the navigation element and rely on UI5 built-in styling for the Tab_Container.

### Requirement 2: Header Component Migration

**User Story:** As a user, I want the application header to use UI5 buttons, so that the header actions are visually consistent with the rest of the migrated UI.

#### Acceptance Criteria

1. THE Header_Component SHALL replace the plain `<button>` "Download as PDF" element with a UI5_Button having `design` set to `"Default"`.
2. WHEN the user clicks the PDF UI5_Button, THE Header_Component SHALL invoke the PDF download function with the current screen PDF options, preserving existing behavior.
3. THE Header_Component SHALL import `@ui5/webcomponents/dist/Button.js` as a side-effect module before creating UI5_Button elements.

### Requirement 3: Error Banner Migration

**User Story:** As a user, I want error messages displayed as UI5 message strips, so that error feedback follows the enterprise design system and supports value-state semantics.

#### Acceptance Criteria

1. WHEN `showError` is called, THE Message_Strip SHALL render inside the given container with `design` set to `"Negative"` and display the error message text.
2. WHEN `clearError` is called, THE Error_Banner module SHALL remove the Message_Strip from the container.
3. THE Message_Strip SHALL have the `role="alert"` attribute for accessibility.
4. THE Error_Banner module SHALL import `@ui5/webcomponents/dist/MessageStrip.js` as a side-effect module before creating Message_Strip elements.

### Requirement 4: Upload Screen Migration

**User Story:** As a user, I want the file upload screen to use UI5 form components, so that the upload interaction is consistent with the enterprise design system.

#### Acceptance Criteria

1. THE Upload Screen SHALL replace the plain `<input type="file">` element with a UI5_File_Uploader that accepts `.xlsx` files.
2. WHEN a file is selected via the UI5_File_Uploader, THE Upload Screen SHALL trigger the import pipeline with the selected file, preserving existing import logic.
3. THE Upload Screen SHALL import `@ui5/webcomponents/dist/FileUploader.js` as a side-effect module before creating UI5_File_Uploader elements.

### Requirement 5: Sheet Selector Component Migration

**User Story:** As a user, I want the sheet selection dropdown to use UI5 select and button components, so that the sheet picker is visually consistent with the migrated UI.

#### Acceptance Criteria

1. THE Sheet_Selector SHALL replace the plain `<select>` element with a UI5_Select containing `ui5-option` children for each sheet name.
2. THE Sheet_Selector SHALL replace the plain "Confirm" `<button>` with a UI5_Button having `design` set to `"Emphasized"`.
3. THE Sheet_Selector SHALL replace the plain "Cancel" `<button>` with a UI5_Button having `design` set to `"Transparent"`.
4. WHEN a sheet is selected in the UI5_Select, THE Sheet_Selector SHALL enable the Confirm UI5_Button.
5. WHEN the Confirm UI5_Button is clicked with a valid selection, THE Sheet_Selector SHALL invoke the `onConfirm` callback with the selected sheet name.
6. WHEN the Cancel UI5_Button is clicked, THE Sheet_Selector SHALL invoke the `onCancel` callback.
7. THE Sheet_Selector SHALL import `@ui5/webcomponents/dist/Select.js`, `@ui5/webcomponents/dist/Option.js`, and `@ui5/webcomponents/dist/Button.js` as side-effect modules.

### Requirement 6: Header Row Selector Component Migration

**User Story:** As a user, I want the header row selection dropdown to use UI5 select and button components, so that the header row picker is visually consistent with the migrated UI.

#### Acceptance Criteria

1. THE Header_Row_Selector SHALL replace the plain `<select>` element with a UI5_Select containing `ui5-option` children for each candidate row.
2. THE Header_Row_Selector SHALL replace the plain "Confirm" `<button>` with a UI5_Button having `design` set to `"Emphasized"`.
3. THE Header_Row_Selector SHALL replace the plain "Cancel" `<button>` with a UI5_Button having `design` set to `"Transparent"`.
4. WHEN a row is selected in the UI5_Select, THE Header_Row_Selector SHALL enable the Confirm UI5_Button.
5. WHEN the Confirm UI5_Button is clicked with a valid selection, THE Header_Row_Selector SHALL invoke the `onConfirm` callback with the selected row index.
6. WHEN the Cancel UI5_Button is clicked, THE Header_Row_Selector SHALL invoke the `onCancel` callback.
7. THE Header_Row_Selector SHALL import `@ui5/webcomponents/dist/Select.js`, `@ui5/webcomponents/dist/Option.js`, and `@ui5/webcomponents/dist/Button.js` as side-effect modules.

### Requirement 7: Configuration Screen Migration

**User Story:** As a user, I want the configuration form to use UI5 form components with validation feedback, so that the form inputs follow the enterprise design system and provide clear validation states.

#### Acceptance Criteria

1. THE Configuration Screen SHALL replace the plain Package `<select>` with a UI5_Select containing `ui5-option` children for each package.
2. THE Configuration Screen SHALL replace the plain Template `<select>` with a UI5_Select containing `ui5-option` children for each template.
3. THE Configuration Screen SHALL replace the plain Budgetcode `<input>` with a UI5_Input.
4. THE Configuration Screen SHALL replace the plain Year `<input type="number">` with a UI5_Input having `type` set to `"Number"`.
5. THE Configuration Screen SHALL replace the plain "Apply Configuration" `<button>` with a UI5_Button having `design` set to `"Emphasized"`.
6. IF the user clicks Apply without selecting a package or template, THEN THE Configuration Screen SHALL set the Value_State of the corresponding UI5_Select to `"Negative"`.
7. IF the user clicks Apply without entering a budgetcode, THEN THE Configuration Screen SHALL set the Value_State of the Budgetcode UI5_Input to `"Negative"`.
8. IF the user clicks Apply with an invalid year, THEN THE Configuration Screen SHALL set the Value_State of the Year UI5_Input to `"Negative"`.
9. THE Configuration Screen SHALL import `@ui5/webcomponents/dist/Select.js`, `@ui5/webcomponents/dist/Option.js`, `@ui5/webcomponents/dist/Input.js`, `@ui5/webcomponents/dist/Label.js`, and `@ui5/webcomponents/dist/Button.js` as side-effect modules.
10. THE Configuration Screen SHALL use `ui5-label` elements with the `for` attribute pointing to the corresponding input `id` for accessibility.

### Requirement 8: Transform Screen Migration

**User Story:** As a user, I want the transform screen to use UI5 buttons, so that the transformation action is visually consistent with the migrated UI.

#### Acceptance Criteria

1. THE Transform Screen SHALL replace the plain "Run Transformation" `<button>` with a UI5_Button having `design` set to `"Emphasized"`.
2. WHILE the transformation is in progress, THE UI5_Button SHALL be disabled.
3. WHEN the transformation completes successfully, THE Transform Screen SHALL navigate to the Output Screen after a brief delay, preserving existing behavior.
4. IF the transformation fails, THEN THE Transform Screen SHALL display the error via the Message_Strip and re-enable the UI5_Button.
5. THE Transform Screen SHALL import `@ui5/webcomponents/dist/Button.js` as a side-effect module.

### Requirement 9: Output Screen Migration

**User Story:** As a user, I want the output screen export buttons to use UI5 buttons, so that the export actions are visually consistent with the migrated UI.

#### Acceptance Criteria

1. THE Output Screen SHALL replace the plain "Export CSV", "Export Excel", and "Export PDF" `<button>` elements with UI5_Button elements having `design` set to `"Default"`.
2. WHEN a user clicks an export UI5_Button, THE Output Screen SHALL trigger the corresponding export function (CSV, Excel, or PDF), preserving existing behavior.
3. THE Output Screen SHALL import `@ui5/webcomponents/dist/Button.js` as a side-effect module.

### Requirement 10: Documentation Screen Migration

**User Story:** As a user, I want the documentation screen to use UI5 components where applicable, so that the documentation view is consistent with the migrated UI.

#### Acceptance Criteria

1. THE Documentation Screen SHALL use UI5 components for any interactive elements present on the screen.
2. THE Documentation Screen SHALL preserve the existing `<details>`/`<summary>` pattern for collapsible documentation sections, as UI5 does not provide a direct equivalent for disclosure widgets.

### Requirement 11: Inline Style Removal

**User Story:** As a developer, I want all inline CSS styles removed from migrated components, so that the UI relies on UI5 built-in theming and SAP CSS custom properties for consistent styling.

#### Acceptance Criteria

1. THE migrated components SHALL remove inline `style.cssText` assignments from elements that have been replaced by UI5 Web Components.
2. WHERE layout styling is needed for non-UI5 container elements (e.g., flex wrappers, spacing divs), THE Screen SHALL use CSS classes or minimal inline styles limited to layout properties (`display`, `gap`, `margin`, `padding`, `max-width`).
3. THE migrated components SHALL rely on UI5 `design`, `value-state`, and CSS custom properties (e.g., `--sapButton_BorderRadius`) for visual styling of UI5 elements.

### Requirement 12: Side-Effect Import Discipline

**User Story:** As a developer, I want each file that creates UI5 elements to import the corresponding UI5 module, so that custom elements are registered before use and the application does not throw undefined-element errors.

#### Acceptance Criteria

1. FOR ALL files that create a `ui5-*` element via `document.createElement`, THE file SHALL contain a top-level side-effect import for the corresponding UI5 component module.
2. IF a file creates multiple distinct UI5 element types, THEN THE file SHALL contain one side-effect import per UI5 component type used.

### Requirement 13: Functional Preservation

**User Story:** As a user, I want all existing application functionality to work identically after the migration, so that the UI5 migration is purely visual with no behavioral regressions.

#### Acceptance Criteria

1. THE migrated Upload Screen SHALL support file selection, sheet selection, header row selection, progress summary display, and navigation to Preview on success.
2. THE migrated Configuration Screen SHALL support package loading, template loading, parameter input, validation, and navigation to Transform on success.
3. THE migrated Transform Screen SHALL support triggering transformation, displaying progress, showing errors, and navigation to Output on success.
4. THE migrated Output Screen SHALL support CSV export, Excel export, PDF export, and spreadsheet preview rendering.
5. THE migrated Documentation Screen SHALL support documentation generation and display of all seven documentation artifacts.
6. THE migrated App_Shell SHALL support screen navigation via tabs and PDF download via the header button.
