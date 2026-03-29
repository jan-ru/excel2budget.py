"""Unit tests for src/core/memory — file size validation and memory safety.

Requirements: 15.1, 15.2, 13.1, 13.2
"""

import pytest

from src.core.memory import (
    DEFAULT_MAX_FILE_SIZE_BYTES,
    DEFAULT_WASM_MEMORY_LIMIT_BYTES,
    MEMORY_EXPANSION_FACTOR,
    ClientSideViolationError,
    FileSizeError,
    MemoryEstimate,
    WasmMemoryError,
    assert_client_side_only,
    estimate_memory,
    get_current_memory_usage,
    validate_file_size,
)


# --- estimate_memory ---

class TestEstimateMemory:
    def test_basic_estimate(self):
        est = estimate_memory(1_000_000)
        assert est.file_size_bytes == 1_000_000
        assert est.estimated_memory_bytes == 1_000_000 * MEMORY_EXPANSION_FACTOR
        assert est.wasm_limit_bytes == DEFAULT_WASM_MEMORY_LIMIT_BYTES

    def test_custom_expansion_factor(self):
        est = estimate_memory(100, expansion_factor=10)
        assert est.estimated_memory_bytes == 1_000

    def test_exceeds_limit(self):
        est = estimate_memory(1_000, wasm_limit=100)
        assert est.exceeds_limit is True

    def test_within_limit(self):
        est = estimate_memory(10, wasm_limit=1_000_000)
        assert est.exceeds_limit is False

    def test_zero_size(self):
        est = estimate_memory(0)
        assert est.estimated_memory_bytes == 0
        assert est.exceeds_limit is False


# --- validate_file_size ---

class TestValidateFileSize:
    def test_small_file_passes(self):
        data = b"x" * 100
        validate_file_size(data)  # should not raise

    def test_empty_file_passes(self):
        validate_file_size(b"")  # should not raise

    def test_file_exceeds_max_size(self):
        max_size = 1_000
        data = b"x" * 1_001
        with pytest.raises(FileSizeError) as exc_info:
            validate_file_size(data, max_file_size=max_size)
        assert exc_info.value.file_size == 1_001
        assert exc_info.value.max_size == max_size

    def test_file_exceeds_wasm_memory(self):
        # 100 bytes × 5 expansion = 500 estimated, limit = 400
        data = b"x" * 100
        with pytest.raises(WasmMemoryError) as exc_info:
            validate_file_size(data, max_file_size=10_000, wasm_limit=400)
        assert exc_info.value.estimate.file_size_bytes == 100
        assert exc_info.value.estimate.exceeds_limit is True

    def test_file_at_exact_max_size_passes(self):
        data = b"x" * 1_000
        validate_file_size(data, max_file_size=1_000, wasm_limit=10_000_000)

    def test_file_one_byte_over_max_size_fails(self):
        data = b"x" * 1_001
        with pytest.raises(FileSizeError):
            validate_file_size(data, max_file_size=1_000)


# --- WasmMemoryError message ---

class TestWasmMemoryError:
    def test_message_contains_sizes(self):
        est = MemoryEstimate(
            file_size_bytes=200,
            estimated_memory_bytes=1_000,
            wasm_limit_bytes=500,
        )
        err = WasmMemoryError(est)
        msg = str(err)
        assert "1,000" in msg
        assert "500" in msg
        assert "200" in msg


# --- FileSizeError message ---

class TestFileSizeError:
    def test_message_contains_sizes(self):
        err = FileSizeError(5_000, 1_000)
        msg = str(err)
        assert "5,000" in msg
        assert "1,000" in msg


# --- ClientSideViolationError ---

class TestClientSideViolationError:
    def test_default_message(self):
        err = ClientSideViolationError()
        assert "no data may be transmitted" in str(err)

    def test_custom_detail(self):
        err = ClientSideViolationError("attempted HTTP POST")
        assert "attempted HTTP POST" in str(err)


# --- assert_client_side_only ---

class TestAssertClientSideOnly:
    def test_does_not_raise(self):
        assert_client_side_only()  # no-op, should succeed


# --- get_current_memory_usage ---

class TestGetCurrentMemoryUsage:
    def test_returns_non_negative(self):
        usage = get_current_memory_usage()
        assert usage >= 0


# --- Integration: pipeline import_budget_file with memory validation ---

class TestPipelineMemoryIntegration:
    def test_oversized_file_returns_error_string(self):
        """import_budget_file should reject files exceeding the size limit."""
        from unittest.mock import patch

        from src.core.memory import FileSizeError
        from src.modules.excel2budget.pipeline import import_budget_file

        def _reject(raw_bytes, **kwargs):
            raise FileSizeError(len(raw_bytes), 10)

        with patch("src.core.memory.validate_file_size", side_effect=_reject):
            result = import_budget_file(b"x" * 100)
        assert isinstance(result, str)
        assert "exceeds" in result.lower()

    def test_wasm_memory_exceeded_returns_error_string(self):
        """import_budget_file should reject files that would blow WASM memory."""
        from unittest.mock import patch

        from src.core.memory import MemoryEstimate, WasmMemoryError
        from src.modules.excel2budget.pipeline import import_budget_file

        est = MemoryEstimate(file_size_bytes=100, estimated_memory_bytes=500, wasm_limit_bytes=10)

        def _reject(raw_bytes, **kwargs):
            raise WasmMemoryError(est)

        with patch("src.core.memory.validate_file_size", side_effect=_reject):
            result = import_budget_file(b"x" * 100)
        assert isinstance(result, str)
        assert "memory" in result.lower()
