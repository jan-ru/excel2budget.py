---
inclusion: manual
---

# UI5 Web Components — Usage Policy

This project uses [UI5 Web Components](https://github.com/SAP/ui5-webcomponents) v2.7+ for the frontend UI layer. UI5 Web Components are enterprise-grade custom HTML elements that implement SAP Fiori design guidelines and work with any framework — or no framework at all, which is our case.

## Installed Packages

- `@ui5/webcomponents` (^2.7.0) — Main components: buttons, inputs, selects, dialogs, tables, etc.
- `@ui5/webcomponents-fiori` (^2.7.0) — Fiori-specific components: shell bar, side navigation, wizard, etc.

## Architecture Context

The frontend is plain TypeScript + Vite — no React, no Angular, no Vue. Components are used as native custom HTML elements created via `document.createElement()` or HTML string templates. This is the simplest integration path for UI5 Web Components.

## How to Use Components

### Importing

Each component must be imported by its side-effect module before use. The import registers the custom element globally.

```typescript
// Import the component (registers the custom element)
import "@ui5/webcomponents/dist/Button.js";
import "@ui5/webcomponents/dist/Input.js";
import "@ui5/webcomponents/dist/Select.js";
import "@ui5/webcomponents/dist/Dialog.js";

// Fiori components
import "@ui5/webcomponents-fiori/dist/ShellBar.js";
```

### Creating Elements

Since we use plain TypeScript (no JSX), create elements via the DOM API:

```typescript
import "@ui5/webcomponents/dist/Button.js";

const btn = document.createElement("ui5-button");
btn.textContent = "Submit";
btn.setAttribute("design", "Emphasized");
btn.addEventListener("click", () => handleSubmit());
container.appendChild(btn);
```

### Event Handling

UI5 Web Components use custom events (not standard DOM events). Always use `addEventListener` with the UI5 event name:

```typescript
import "@ui5/webcomponents/dist/Select.js";

const select = document.createElement("ui5-select");
// UI5 uses "change" event, not "input"
select.addEventListener("change", (e: Event) => {
  const detail = (e as CustomEvent).detail;
  // handle selection
});
```

### Slots

Some components use named slots for child content:

```typescript
import "@ui5/webcomponents/dist/Card.js";
import "@ui5/webcomponents/dist/CardHeader.js";

const card = document.createElement("ui5-card");
const header = document.createElement("ui5-card-header");
header.setAttribute("title-text", "Budget Summary");
header.slot = "header";
card.appendChild(header);
```

## Component Selection Guide

Use these UI5 components instead of plain HTML equivalents:

| Plain HTML | UI5 Replacement | Tag | Import |
|---|---|---|---|
| `<button>` | Button | `ui5-button` | `Button.js` |
| `<input>` | Input | `ui5-input` | `Input.js` |
| `<select>` | Select | `ui5-select` | `Select.js` |
| `<textarea>` | TextArea | `ui5-textarea` | `TextArea.js` |
| `<table>` | Table | `ui5-table` | `Table.js` (fiori) |
| `<dialog>` | Dialog | `ui5-dialog` | `Dialog.js` |
| `<label>` | Label | `ui5-label` | `Label.js` |
| `<a>` | Link | `ui5-link` | `Link.js` |
| `<input type="file">` | FileUploader | `ui5-file-uploader` | `FileUploader.js` |
| `<input type="checkbox">` | CheckBox | `ui5-checkbox` | `CheckBox.js` |
| `<progress>` | ProgressIndicator | `ui5-progress-indicator` | `ProgressIndicator.js` |
| alert/toast | Toast | `ui5-toast` | `Toast.js` |
| alert banner | MessageStrip | `ui5-message-strip` | `MessageStrip.js` |
| tab navigation | TabContainer | `ui5-tabcontainer` | `TabContainer.js` |

### Fiori Components (from `@ui5/webcomponents-fiori`)

| Use Case | Component | Tag |
|---|---|---|
| App header bar | ShellBar | `ui5-shellbar` |
| Side navigation | SideNavigation | `ui5-side-navigation` |
| Step-by-step wizard | Wizard | `ui5-wizard` |
| Page layout | Page | `ui5-page` |
| Upload collection | UploadCollection | `ui5-upload-collection` |

## Rules

1. Always import the component module before creating the element. The import is a side effect that registers the custom element.
2. Use `ui5-*` elements for all interactive UI — do not mix plain HTML buttons/inputs with UI5 equivalents in the same screen.
3. Use the `design` attribute for button variants: `"Default"`, `"Emphasized"`, `"Positive"`, `"Negative"`, `"Transparent"`.
4. Use `value-state` for input validation feedback: `"None"`, `"Positive"`, `"Critical"`, `"Negative"`, `"Information"`.
5. Do not use inline CSS for component styling — UI5 components are styled via CSS custom properties (e.g., `--sapButton_BorderRadius`). Use the SAP theming variables.
6. For forms, use `ui5-label` with the `for` attribute pointing to the input's `id` for accessibility.
7. Use `ui5-dialog` and `ui5-popover` instead of custom modal implementations.
8. Use `ui5-message-strip` for inline notifications and `ui5-toast` for transient messages.
9. When using `ui5-select`, child options must be `ui5-option` elements (not plain `<option>`).
10. When using `ui5-list`, items must be `ui5-li` (standard), `ui5-li-custom` (custom), or `ui5-li-group` (group header).

## Current State

The UI5 packages are installed but the current UI (`frontend/src/ui/`) uses plain HTML elements with inline styles. The migration to UI5 Web Components is planned. When migrating screens:

- Start with the app shell (`app.ts`) — replace the nav bar with `ui5-tabcontainer`
- Replace buttons, selects, and inputs in each screen one at a time
- Replace the error banner with `ui5-message-strip`
- Replace the file upload with `ui5-file-uploader`

## Resources

- [GitHub Repository](https://github.com/SAP/ui5-webcomponents)
- [NPM: @ui5/webcomponents](https://www.npmjs.com/package/@ui5/webcomponents)
- [NPM: @ui5/webcomponents-fiori](https://www.npmjs.com/package/@ui5/webcomponents-fiori)
