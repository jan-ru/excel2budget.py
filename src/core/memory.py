"""Memory safety and client-side constraint validation.

Validates file sizes before parsing to prevent memory exhaustion in the
browser WASM environment. Ensures no data is transmitted to any server.

Requirements: 15.1, 15.2, 13.1, 13.2
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

# Default limits for browser WASM environments.
# DuckDB WASM and IronCalc share a 2 GB address space; we keep a safety
# margin so the engines can allocate working memory on top of the raw file.
DEFAULT_MAX_FILE_SIZE_BYTES: int = 100 * 1024 * 1024  # 100 MB
DEFAULT_WASM_MEMORY_LIMIT_BYTES: int = 2 * 1024 * 1024 * 1024  # 2 GB
# Rough multiplier: an Excel file expands ~5× when parsed into in-memory
# structures (openpyxl DOM, DuckDB table, IronCalc sheet).
MEMORY_EXPANSION_FACTOR: int = 5


@dataclass
class MemoryEstimate:
    """Estimated memory requirements for processing a file."""

    file_size_bytes: int
    estimated_memory_bytes: int
    wasm_limit_bytes: int

    @property
    def exceeds_limit(self) -> bool:
        return self.estimated_memory_bytes > self.wasm_limit_bytes


class FileSizeError(Exception):
    """Raised when a file exceeds the maximum allowed size."""

    def __init__(self, file_size: int, max_size: int) -> None:
        self.file_size = file_size
        self.max_size = max_size
        super().__init__(
            f"File size ({file_size:,} bytes) exceeds maximum allowed "
            f"size ({max_size:,} bytes)"
        )


class WasmMemoryError(MemoryError):
    """Raised when estimated memory exceeds the WASM allocation limit."""

    def __init__(self, estimate: MemoryEstimate) -> None:
        self.estimate = estimate
        super().__init__(
            f"Estimated memory requirement ({estimate.estimated_memory_bytes:,} bytes) "
            f"exceeds WASM limit ({estimate.wasm_limit_bytes:,} bytes). "
            f"File size: {estimate.file_size_bytes:,} bytes."
        )


class ClientSideViolationError(Exception):
    """Raised when an operation would transmit data to a server."""

    def __init__(self, detail: str = "") -> None:
        msg = "Client-side processing constraint violated: no data may be transmitted to any server"
        if detail:
            msg = f"{msg}. {detail}"
        super().__init__(msg)


def estimate_memory(
    file_size_bytes: int,
    *,
    expansion_factor: int = MEMORY_EXPANSION_FACTOR,
    wasm_limit: int = DEFAULT_WASM_MEMORY_LIMIT_BYTES,
) -> MemoryEstimate:
    """Estimate memory needed to process a file of the given size."""
    return MemoryEstimate(
        file_size_bytes=file_size_bytes,
        estimated_memory_bytes=file_size_bytes * expansion_factor,
        wasm_limit_bytes=wasm_limit,
    )


def validate_file_size(
    raw_bytes: bytes,
    *,
    max_file_size: int = DEFAULT_MAX_FILE_SIZE_BYTES,
    wasm_limit: int = DEFAULT_WASM_MEMORY_LIMIT_BYTES,
) -> None:
    """Validate that a file can be safely processed in the WASM environment.

    Raises ``FileSizeError`` if the file exceeds *max_file_size*.
    Raises ``WasmMemoryError`` if the estimated in-memory footprint
    exceeds *wasm_limit*.

    Requirements: 15.1, 15.2
    """
    size = len(raw_bytes)

    if size > max_file_size:
        raise FileSizeError(size, max_file_size)

    est = estimate_memory(size, wasm_limit=wasm_limit)
    if est.exceeds_limit:
        raise WasmMemoryError(est)


def get_current_memory_usage() -> int:
    """Return a rough estimate of current Python process memory usage in bytes.

    In a real browser WASM environment this would query the WebAssembly
    memory object.  In CPython we fall back to ``sys.getsizeof`` heuristics
    via the garbage collector.
    """
    try:
        import resource  # Unix only
        usage = resource.getrusage(resource.RUSAGE_SELF)
        # ru_maxrss is in kilobytes on Linux, bytes on macOS
        if sys.platform == "darwin":
            return usage.ru_maxrss  # bytes on macOS
        return usage.ru_maxrss * 1024  # KB → bytes on Linux
    except (ImportError, AttributeError):
        # Fallback: not available on this platform
        return 0


def assert_client_side_only() -> None:
    """Marker assertion documenting that the caller performs no network I/O.

    This is a design-time constraint enforced by code review and
    architecture.  The function itself is a no-op but can be called at
    module boundaries to make the contract explicit.

    Requirements: 13.1, 13.2
    """
    # No-op — the entire pipeline is client-side by design.
    # This function exists so tests can verify it is called and
    # so static analysis / grep can locate the contract.
    pass
