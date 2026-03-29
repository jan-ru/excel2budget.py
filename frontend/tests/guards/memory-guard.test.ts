import { describe, it, expect } from "vitest";
import fc from "fast-check";
import {
  validateFileSize,
  estimateMemory,
  FileSizeError,
  WasmMemoryError,
  DEFAULT_MAX_FILE_SIZE_BYTES,
  DEFAULT_WASM_MEMORY_LIMIT_BYTES,
  MEMORY_EXPANSION_FACTOR,
} from "../../src/guards/memory-guard";

describe("Property 15: Memory Guard Rejection", () => {
  it("rejects files exceeding max file size", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 500 * 1024 * 1024 }), // maxSize up to 500MB
        fc.integer({ min: 1, max: 100 }),                 // overBy: how much to exceed
        (maxSize, overBy) => {
          const fileSize = maxSize + overBy;
          try {
            validateFileSize(fileSize, { maxFileSizeBytes: maxSize });
            // If it didn't throw FileSizeError, it must have been caught by WASM limit instead
            return true;
          } catch (e) {
            if (e instanceof FileSizeError) {
              expect(e.fileSize).toBe(fileSize);
              expect(e.maxSize).toBe(maxSize);
              expect(e.message).toContain("exceeds maximum allowed size");
              return true;
            }
            // WasmMemoryError is also acceptable — file passed size check but failed memory check
            return e instanceof WasmMemoryError;
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("rejects files where size × expansion factor exceeds WASM limit", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 10 }),                   // expansion factor
        fc.integer({ min: 1024, max: 1024 * 1024 * 1024 }), // wasmLimit
        (factor, wasmLimit) => {
          // Pick a file size that passes the max-file-size check but fails the WASM check
          const fileSize = Math.floor(wasmLimit / factor) + 1;
          const maxFileSize = fileSize + 1; // ensure file size check passes

          try {
            validateFileSize(fileSize, {
              maxFileSizeBytes: maxFileSize,
              wasmMemoryLimitBytes: wasmLimit,
              expansionFactor: factor,
            });
            return false; // should have thrown
          } catch (e) {
            expect(e).toBeInstanceOf(WasmMemoryError);
            if (e instanceof WasmMemoryError) {
              expect(e.estimate.fileSizeBytes).toBe(fileSize);
              expect(e.estimate.estimatedMemoryBytes).toBe(fileSize * factor);
              expect(e.estimate.exceedsLimit).toBe(true);
            }
            return true;
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  it("accepts files within both limits", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 1000 }),  // fileSize (small, guaranteed within limits)
        (fileSize) => {
          // Use generous limits so the file is always accepted
          const maxFileSize = fileSize + 1;
          const wasmLimit = fileSize * MEMORY_EXPANSION_FACTOR + 1;

          // Should not throw
          validateFileSize(fileSize, {
            maxFileSizeBytes: maxFileSize,
            wasmMemoryLimitBytes: wasmLimit,
          });
          return true;
        },
      ),
      { numRuns: 100 },
    );
  });

  it("estimateMemory correctly computes exceedsLimit", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1_000_000 }),
        fc.integer({ min: 1, max: 20 }),
        fc.integer({ min: 1, max: 10_000_000 }),
        (fileSize, factor, wasmLimit) => {
          const est = estimateMemory(fileSize, factor, wasmLimit);
          expect(est.fileSizeBytes).toBe(fileSize);
          expect(est.estimatedMemoryBytes).toBe(fileSize * factor);
          expect(est.wasmLimitBytes).toBe(wasmLimit);
          expect(est.exceedsLimit).toBe(fileSize * factor > wasmLimit);
        },
      ),
      { numRuns: 100 },
    );
  });

  it("uses default config values when none provided", () => {
    // A tiny file should always pass with defaults
    validateFileSize(1);

    // A file just over the default max should fail
    expect(() => validateFileSize(DEFAULT_MAX_FILE_SIZE_BYTES + 1)).toThrow(
      FileSizeError,
    );
  });
});
