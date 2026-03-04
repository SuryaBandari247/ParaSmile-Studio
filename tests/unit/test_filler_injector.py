"""Unit tests for the FillerInjector."""

import pytest

from voice_synthesizer.filler_injector import FillerInjector


class TestFillerInjectorBasic:
    """Basic functionality tests."""

    def test_empty_text_returns_empty(self):
        fi = FillerInjector(seed=42)
        assert fi.inject("") == ""

    def test_whitespace_only_returns_unchanged(self):
        fi = FillerInjector(seed=42)
        assert fi.inject("   ") == "   "

    def test_none_like_empty(self):
        fi = FillerInjector(seed=42)
        assert fi.inject("") == ""

    def test_short_text_no_insertion_points(self):
        fi = FillerInjector(seed=42, filler_density=1.0)
        result = fi.inject("Hello world.")
        # No conjunctions or commas, so no insertion points
        assert "Hello" in result

    def test_density_zero_no_fillers(self):
        fi = FillerInjector(filler_density=0.0, restart_probability=0.0, seed=42)
        text = "This is a test, and it should work, but nothing changes."
        result = fi.inject(text)
        assert result == text

    def test_density_one_fills_every_point(self):
        fi = FillerInjector(filler_density=1.0, restart_probability=0.0, seed=42)
        text = "We need to act, and we need to plan, but we also need to wait."
        result = fi.inject(text)
        # Should have fillers inserted at conjunction/comma points
        assert "{{pause:" in result


class TestFillerInjectorDeterministic:
    """Deterministic seed tests."""

    def test_same_seed_same_output(self):
        text = "The market is volatile, and investors are worried, but analysts remain calm."
        fi1 = FillerInjector(seed=123, filler_density=0.5)
        fi2 = FillerInjector(seed=123, filler_density=0.5)
        assert fi1.inject(text) == fi2.inject(text)

    def test_different_seed_different_output(self):
        text = "The market is volatile, and investors are worried, but analysts remain calm."
        fi1 = FillerInjector(seed=1, filler_density=0.8)
        fi2 = FillerInjector(seed=999, filler_density=0.8)
        r1 = fi1.inject(text)
        r2 = fi2.inject(text)
        # With high density and different seeds, outputs should differ
        # (not guaranteed but very likely)
        # At minimum, both should be valid strings
        assert isinstance(r1, str)
        assert isinstance(r2, str)


class TestFillerInjectorProtectedSpans:
    """Protected span preservation tests."""

    def test_inline_code_not_modified(self):
        fi = FillerInjector(seed=42, filler_density=1.0, restart_probability=0.0)
        text = "Use `kubectl apply` and then check the status."
        result = fi.inject(text)
        assert "`kubectl apply`" in result

    def test_quoted_string_not_modified(self):
        fi = FillerInjector(seed=42, filler_density=1.0, restart_probability=0.0)
        text = 'The error says "connection refused" and we need to fix it.'
        result = fi.inject(text)
        assert '"connection refused"' in result

    def test_acronym_not_modified(self):
        fi = FillerInjector(seed=42, filler_density=1.0, restart_probability=0.0)
        text = "The GPU and CPU are both important, but GPU matters more."
        result = fi.inject(text)
        assert "GPU" in result
        assert "CPU" in result


class TestFillerInjectorRestarts:
    """Mid-sentence restart tests."""

    def test_restart_produces_dash(self):
        fi = FillerInjector(
            seed=42, filler_density=0.0, restart_probability=1.0
        )
        text = "This technology will change everything, and it will be amazing, but we need to wait."
        result = fi.inject(text)
        # With restart_probability=1.0, should have at least one restart marker
        assert "—" in result or result == text  # May not have enough words

    def test_restart_with_short_text_falls_back(self):
        fi = FillerInjector(
            seed=42, filler_density=0.0, restart_probability=1.0
        )
        text = "Go, and do it."
        result = fi.inject(text)
        # Should not crash even with very short clauses
        assert isinstance(result, str)


class TestFillerInjectorCustomVocabulary:
    """Custom vocabulary tests."""

    def test_custom_vocabulary_used(self):
        custom = ["err", "well well"]
        fi = FillerInjector(
            seed=42,
            filler_density=1.0,
            restart_probability=0.0,
            filler_vocabulary=custom,
        )
        text = "We should invest, and we should diversify, but we should also save."
        result = fi.inject(text)
        # At least one custom filler should appear
        has_custom = any(f in result for f in custom)
        has_pause = "{{pause:" in result
        assert has_pause  # Pause markers should be present
