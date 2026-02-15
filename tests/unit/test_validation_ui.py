"""Unit tests for validation UI components.

Tests for context cycling dot indicator (Story 5.6, AC1)
and ReviewScreen display behaviour.
"""

from __future__ import annotations

import pytest

from gdpr_pseudonymizer.validation.ui import generate_context_dots


class TestGenerateContextDots:
    """Tests for the generate_context_dots helper function."""

    # --- Edge case: single context (no dots) ---

    def test_single_context_returns_empty(self) -> None:
        assert generate_context_dots(1, 1) == ""

    def test_zero_total_returns_empty(self) -> None:
        assert generate_context_dots(1, 0) == ""

    # --- Standard format (2-10 contexts) ---

    def test_two_contexts_first_active(self) -> None:
        assert generate_context_dots(1, 2) == "● ○"

    def test_two_contexts_second_active(self) -> None:
        assert generate_context_dots(2, 2) == "○ ●"

    def test_three_contexts_first_active(self) -> None:
        assert generate_context_dots(1, 3) == "● ○ ○"

    def test_three_contexts_second_active(self) -> None:
        assert generate_context_dots(2, 3) == "○ ● ○"

    def test_three_contexts_third_active(self) -> None:
        assert generate_context_dots(3, 3) == "○ ○ ●"

    def test_five_contexts_middle_active(self) -> None:
        assert generate_context_dots(3, 5) == "○ ○ ● ○ ○"

    def test_ten_contexts_last_active(self) -> None:
        result = generate_context_dots(10, 10)
        dots = result.split(" ")
        assert len(dots) == 10
        assert dots[9] == "●"
        assert dots.count("●") == 1

    def test_ten_contexts_first_active(self) -> None:
        result = generate_context_dots(1, 10)
        dots = result.split(" ")
        assert len(dots) == 10
        assert dots[0] == "●"
        assert dots.count("●") == 1

    # --- Truncated format (>10 contexts) ---

    def test_fifteen_contexts_first_active(self) -> None:
        result = generate_context_dots(1, 15)
        assert "●" in result
        assert "…" in result
        assert result.count("●") == 1

    def test_fifteen_contexts_second_active(self) -> None:
        result = generate_context_dots(2, 15)
        assert "●" in result
        assert "…" in result

    def test_fifteen_contexts_third_active(self) -> None:
        result = generate_context_dots(3, 15)
        # 3 is in the visible_start range [1,2,3]
        assert "●" in result
        assert "…" in result

    def test_fifteen_contexts_middle_active(self) -> None:
        """Middle position (not in first 3 or last 2) shows ○ ○ … ● … ○ ○."""
        result = generate_context_dots(7, 15)
        assert "●" in result
        assert "…" in result
        assert result.count("●") == 1

    def test_fifteen_contexts_penultimate_active(self) -> None:
        result = generate_context_dots(14, 15)
        # 14 is in visible_end [14, 15]
        assert "●" in result
        assert "…" in result

    def test_fifteen_contexts_last_active(self) -> None:
        result = generate_context_dots(15, 15)
        assert "●" in result
        assert "…" in result

    def test_eleven_contexts_middle_active(self) -> None:
        """Boundary: 11 contexts, position 6 is in middle."""
        result = generate_context_dots(6, 11)
        assert "●" in result
        assert "…" in result
        assert result.count("●") == 1

    def test_truncated_format_limited_length(self) -> None:
        """Truncated format should never exceed ~7 tokens (dots + ellipsis)."""
        result = generate_context_dots(50, 100)
        tokens = result.split(" ")
        # Middle format: ○ ○ … ● … ○ ○ = 7 tokens
        assert len(tokens) <= 7

    # --- Verify only one active dot ---

    @pytest.mark.parametrize("total", [2, 5, 10])
    def test_exactly_one_active_dot_standard(self, total: int) -> None:
        for idx in range(1, total + 1):
            result = generate_context_dots(idx, total)
            assert result.count("●") == 1

    @pytest.mark.parametrize("idx", [1, 3, 7, 14, 15])
    def test_exactly_one_active_dot_truncated(self, idx: int) -> None:
        result = generate_context_dots(idx, 15)
        assert result.count("●") == 1
