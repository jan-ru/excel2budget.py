/**
 * Data Conversion Tool — Frontend Entry Point
 *
 * Plain TypeScript + @ui5/webcomponents. No framework.
 * All data processing is ephemeral (in-memory only).
 */

import { mountApp } from "./ui/app";

const root = document.getElementById("app");
if (root) {
  mountApp(root);
}
