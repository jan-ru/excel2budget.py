# Implementation Plan: UI5 Web Components Migration

## Overview

Migrate the Data Conversion Tool frontend from plain HTML elements with inline CSS to UI5 Web Components v2.7+. The migration follows a bottom-up order: shared components first, then screens, then the app shell. Each task builds on the previous, ensuring the app remains functional after each step.

## Tasks

- [x] 1. Migrate shared components (Phase 1)
  - [x] 1.1 Migrate error-banner.ts to ui5-message-strip
    - Add side-effect import for `@ui5/webcomponents/dist/MessageStrip.js`
    - Replace `document.createElement("div")` with `document.createElement("ui5-message-strip")`
    - Set `design="Negative"` and `role="alert"` on the message strip
    - Remove inline `style.cssText` from the message strip element
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 11.1_

  - [x] 1.2 Write property test for showError message strip rendering
    - **Property 3: showError renders a correct message strip**
    - **Validates: Requirements 3.1, 3.3**

  - [x] 1.3 Write property test for showError/clearError round trip
    - **Property 4: showError/clearError round trip**
    - **Validates: Requirements 3.2**

  - [x] 1.4 Migrate header.ts to use ui5-button
    - Add side-effect import for `@ui5/webcomponents/dist/Button.js`
    - Replace the plain `<button>` "Download as PDF" with `document.createElement("ui5-button")`
    - Set `design="Default"` on the PDF button
    - Remove inline `style.cssText` from the button element
    - Preserve existing click handler and PDF download behavior
    - _Requirements: 2.1, 2.2, 2.3, 11.1_

  - [x] 1.5 Migrate sheet-selector.ts to ui5-select, ui5-option, ui5-button
    - Add side-effect imports for `Select.js`, `Option.js`, `Button.js`
    - Replace `<select>` with `ui5-select` and `<option>` children with `ui5-option`
    - Replace Confirm `<button>` with `ui5-button` having `design="Emphasized"`
    - Replace Cancel `<button>` with `ui5-button` having `design="Transparent"`
    - Update `change` event handler to read `(e as CustomEvent).detail.selectedOption.value`
    - Remove inline `style.cssText` from all migrated elements
    - Keep layout styles on the container wrapper div
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 11.1_

  - [x] 1.6 Write property test for selector UI5 structure
    - **Property 5: Selector components render correct UI5 structure**
    - **Validates: Requirements 5.1, 5.2, 5.3, 6.1, 6.2, 6.3**

  - [x] 1.7 Write property test for selector enable-on-select
    - **Property 6: Selector enable-on-select**
    - **Validates: Requirements 5.4, 6.4**

  - [x] 1.8 Write property test for selector confirm callback
    - **Property 7: Selector confirm callback delivers selected value**
    - **Validates: Requirements 5.5, 6.5**

  - [x] 1.9 Migrate header-row-selector.ts to ui5-select, ui5-option, ui5-button
    - Add side-effect imports for `Select.js`, `Option.js`, `Button.js`
    - Replace `<select>` with `ui5-select` and `<option>` children with `ui5-option`
    - Replace Confirm `<button>` with `ui5-button` having `design="Emphasized"`
    - Replace Cancel `<button>` with `ui5-button` having `design="Transparent"`
    - Update `change` event handler to read `(e as CustomEvent).detail.selectedOption.value`
    - Remove inline `style.cssText` from all migrated elements
    - Keep layout styles on the container wrapper div
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 11.1_

- [x] 2. Checkpoint — Shared components migrated
  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Migrate screens (Phase 2)
  - [x] 3.1 Migrate upload.ts to use ui5-file-uploader
    - Add side-effect import for `@ui5/webcomponents/dist/FileUploader.js`
    - Replace `<input type="file">` with `document.createElement("ui5-file-uploader")`
    - Set `accept=".xlsx"` on the file uploader
    - Update `change` event handler to read files from `(e as CustomEvent).detail.files`
    - Remove inline `style.cssText` from the file uploader element
    - Verify integration with already-migrated sheet-selector and header-row-selector
    - _Requirements: 4.1, 4.2, 4.3, 11.1, 13.1_

  - [x] 3.2 Migrate configuration.ts to ui5-select, ui5-input, ui5-label, ui5-button
    - Add side-effect imports for `Select.js`, `Option.js`, `Input.js`, `Label.js`, `Button.js`
    - Replace Package `<select>` with `ui5-select` + `ui5-option` children
    - Replace Template `<select>` with `ui5-select` + `ui5-option` children
    - Replace Budgetcode `<input>` with `ui5-input`
    - Replace Year `<input type="number">` with `ui5-input` having `type="Number"`
    - Replace Apply `<button>` with `ui5-button` having `design="Emphasized"`
    - Replace `<label>` elements with `ui5-label` elements with `for` attribute pointing to input `id`
    - Add validation: set `value-state="Negative"` on invalid fields when Apply is clicked
    - Update `change` event handlers for `ui5-select` to use `CustomEvent.detail.selectedOption`
    - Remove inline `style.cssText` from all migrated elements; keep layout styles on wrapper
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 11.1, 13.2_

  - [x] 3.3 Write property test for configuration select options
    - **Property 8: Configuration select options match data**
    - **Validates: Requirements 7.1, 7.2**

  - [x] 3.4 Write property test for configuration validation value-state
    - **Property 9: Configuration validation sets Negative value-state**
    - **Validates: Requirements 7.6, 7.7, 7.8**

  - [x] 3.5 Write property test for label-for-input accessibility
    - **Property 10: Label-for-input accessibility pairing**
    - **Validates: Requirements 7.10**

  - [x] 3.6 Migrate transform.ts to use ui5-button
    - Add side-effect import for `@ui5/webcomponents/dist/Button.js`
    - Replace "Run Transformation" `<button>` with `ui5-button` having `design="Emphasized"`
    - Set `disabled` attribute on the button while transformation is in progress
    - Re-enable button on failure; navigate to Output on success
    - Remove inline `style.cssText` from the button element
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 11.1, 13.3_

  - [x] 3.7 Migrate output.ts to use ui5-button
    - Add side-effect import for `@ui5/webcomponents/dist/Button.js`
    - Replace "Export CSV", "Export Excel", "Export PDF" `<button>` elements with `ui5-button` having `design="Default"`
    - Preserve existing export click handlers
    - Remove inline `style.cssText` from the button elements
    - _Requirements: 9.1, 9.2, 9.3, 11.1, 13.4_

  - [x] 3.8 Migrate preview.ts — minimal changes
    - No interactive elements to replace (display-only screen)
    - Verify it works with the migrated error-banner component
    - _Requirements: 13.1_

  - [x] 3.9 Migrate documentation.ts — minimal changes
    - Preserve existing `<details>`/`<summary>` pattern for collapsible sections
    - Verify it works with the migrated error-banner component
    - _Requirements: 10.1, 10.2, 13.5_

- [x] 4. Checkpoint — All screens migrated
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Migrate app shell (Phase 3)
  - [x] 5.1 Migrate app.ts navigation to ui5-tabcontainer
    - Add side-effect imports for `@ui5/webcomponents/dist/TabContainer.js` and `@ui5/webcomponents/dist/Tab.js`
    - Replace the `<nav>` element with `ui5-tabcontainer`
    - Replace each navigation `<button>` with a `ui5-tab` element with the screen label as tab text
    - Listen for `tab-select` event on the tabcontainer to navigate: read `(e as CustomEvent).detail.tab`
    - Use `ui5-tab` `selected` attribute to indicate the active tab
    - Remove all inline `style.cssText` from navigation elements
    - Remove the `updateNavHighlight` function (UI5 handles active tab styling)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 11.1, 13.6_

  - [x] 5.2 Write unit tests for app shell tab navigation
    - Verify 6 tabs render with correct labels
    - Verify tab selection triggers navigation to the correct screen
    - _Requirements: 1.1, 1.2, 1.3_

- [x] 6. Cross-cutting verification
  - [x] 6.1 Write property test for side-effect import discipline
    - **Property 1: Side-effect import discipline**
    - Parse all source files in `frontend/src/ui/` for `document.createElement("ui5-*")` calls
    - Verify each file contains the corresponding side-effect import
    - **Validates: Requirements 1.4, 2.3, 3.4, 4.3, 5.7, 6.7, 7.9, 8.5, 9.3, 12.1, 12.2**

  - [x] 6.2 Write property test for no inline styles on UI5 elements
    - **Property 2: No inline styles on UI5 elements**
    - **Validates: Requirements 1.5, 11.1**

- [x] 7. Final checkpoint — Full migration complete
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The bottom-up migration order (components → screens → app shell) ensures dependencies are migrated before consumers
- Property tests use fast-check and run via `vitest --run`
- No public TypeScript interfaces change — only internal DOM construction code is modified
