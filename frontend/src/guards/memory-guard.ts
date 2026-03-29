/**
 * Memory safety and client-side constraint validation.
 *
 * Validates file sizes before parsing to prevent memory exhaustion in the
 * browser WASM environment.
 *
 * Requirements: 12.1, 12.2, 12.3
 */

/** Default limits for browser WASM environments. */
export const DEFAULT_MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024; // 100 MB
export const DEFAULT_WASM_MEMORY_LIMIT_BYTES = 2 * 1024 * 1024 * 1024; // 2 GB
/** Rough multiplier: Excel file expands ~5× when parsed into in-memory structures. */
export const MEMORY_EXPANSION_FACTOR = 5;

export interface MemoryGuardConfig {
  maxFileSizeBytes?: number;
  wasmMemoryLimitBytes?: number;
  expansionFactor?: number;
}

export interface MemoryEstimate {
  fileSizeBytes: number;
  estimatedMemoryBytes: number;
  wasmLimitBytes: number;
  exceedsLimit: boolean;
}

export class FileSizeError extends Error {
  constructor(
    public readonly fileSize: number,
    public readonly maxSize: number,
  ) {
    super(
      `File size (${fileSize.toLocaleString()} bytes) exceeds maximum allowed size (${maxSize.toLocaleString()} bytes)`,
    );
    this.name = "FileSizeError";
  }
}

export class WasmMemoryError extends Error {
  constructor(public readonly estimate: MemoryEstimate) {
    super(
      `Estimated memory requirement (${estimate.estimatedMemoryBytes.toLocaleString()} bytes) ` +
        `exceeds WASM limit (${estimate.wasmLimitBytes.toLocaleString()} bytes). ` +
        `File size: ${estimate.fileSizeBytes.toLocaleString()} bytes.`,
    );
    this.name = "WasmMemoryError";
  }
}

export function estimateMemory(
  fileSizeBytes: number,
  expansionFactor: number = MEMORY_EXPANSION_FACTOR,
  wasmLimit: number = DEFAULT_WASM_MEMORY_LIMIT_BYTES,
): MemoryEstimate {
  const estimatedMemoryBytes = fileSizeBytes * expansionFactor;
  return {
    fileSizeBytes,
    estimatedMemoryBytes,
    wasmLimitBytes: wasmLimit,
    exceedsLimit: estimatedMemoryBytes > wasmLimit,
  };
}

/**
 * Validate that a file can be safely processed in the WASM environment.
 *
 * @throws {FileSizeError} if the file exceeds maxFileSizeBytes
 * @throws {WasmMemoryError} if the estimated in-memory footprint exceeds the WASM limit
 */
export function validateFileSize(
  fileSizeBytes: number,
  config: MemoryGuardConfig = {},
): void {
  const maxFileSize =
    config.maxFileSizeBytes ?? DEFAULT_MAX_FILE_SIZE_BYTES;
  const wasmLimit =
    config.wasmMemoryLimitBytes ?? DEFAULT_WASM_MEMORY_LIMIT_BYTES;
  const expansionFactor =
    config.expansionFactor ?? MEMORY_EXPANSION_FACTOR;

  if (fileSizeBytes > maxFileSize) {
    throw new FileSizeError(fileSizeBytes, maxFileSize);
  }

  const estimate = estimateMemory(fileSizeBytes, expansionFactor, wasmLimit);
  if (estimate.exceedsLimit) {
    throw new WasmMemoryError(estimate);
  }
}
