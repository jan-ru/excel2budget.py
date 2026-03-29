/**
 * Type generation script for the Data Conversion Tool frontend.
 *
 * Fetches the OpenAPI spec from the backend and generates TypeScript types
 * using openapi-typescript. This is a more configurable alternative to the
 * `npm run generate-types` CLI command.
 *
 * Usage:
 *   npx tsx scripts/generate-types.ts
 *
 * Environment variables:
 *   OPENAPI_URL - URL of the OpenAPI spec (default: http://localhost:8000/openapi.json)
 *   OUTPUT_PATH - Output file path (default: src/types/api.d.ts)
 *
 * Validates: Requirements 3.1, 3.2, 3.4
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import openapiTS, { astToString } from "openapi-typescript";

const OPENAPI_URL =
  process.env.OPENAPI_URL ?? "http://localhost:8000/openapi.json";
const OUTPUT_PATH = process.env.OUTPUT_PATH ?? "src/types/api.d.ts";

const HEADER = `/**
 * AUTO-GENERATED — DO NOT EDIT
 *
 * TypeScript types generated from the backend OpenAPI spec.
 * Re-generate with: npm run generate-types
 * Or: npx tsx scripts/generate-types.ts
 *
 * Source: ${OPENAPI_URL}
 * Generated: ${new Date().toISOString()}
 */

`;

async function main(): Promise<void> {
  console.log(`Fetching OpenAPI spec from ${OPENAPI_URL} ...`);

  let ast;
  try {
    ast = await openapiTS(new URL(OPENAPI_URL));
  } catch (err: unknown) {
    const message =
      err instanceof Error ? err.message : String(err);

    if (
      message.includes("ECONNREFUSED") ||
      message.includes("fetch failed")
    ) {
      console.error(
        `Error: Could not connect to ${OPENAPI_URL}\n` +
          "Make sure the backend is running (e.g. uvicorn backend.app.main:app)."
      );
      process.exit(1);
    }

    console.error(`Error fetching OpenAPI spec: ${message}`);
    process.exit(1);
  }

  const contents = HEADER + astToString(ast);

  // Resolve output path relative to the frontend project root
  const __dirname = path.dirname(fileURLToPath(import.meta.url));
  const projectRoot = path.resolve(__dirname, "..");
  const outputFile = path.resolve(projectRoot, OUTPUT_PATH);

  // Ensure the output directory exists
  const outputDir = path.dirname(outputFile);
  fs.mkdirSync(outputDir, { recursive: true });

  fs.writeFileSync(outputFile, contents, "utf-8");
  console.log(`Types written to ${path.relative(projectRoot, outputFile)}`);
}

main();
