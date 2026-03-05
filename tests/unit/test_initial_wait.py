"""Unit tests for InitialWait integration in the codegen pacing system."""

from asset_orchestrator.manim_codegen import _inject_pacing


class TestInitialWaitInjection:
    def test_initial_wait_injected_after_first_play(self):
        code = '''class TestScene(Scene):
    def construct(self):
        self.play(FadeIn(text))
        self.play(Create(line))'''
        instruction = {"_initial_wait": 1.5}
        result = _inject_pacing(code, instruction)
        assert "self.wait(1.5)  # initial_wait" in result
        # Should appear after first play, before second
        lines = result.split("\n")
        play_idx = next(i for i, l in enumerate(lines) if "FadeIn" in l)
        wait_idx = next(i for i, l in enumerate(lines) if "initial_wait" in l)
        play2_idx = next(i for i, l in enumerate(lines) if "Create" in l)
        assert play_idx < wait_idx < play2_idx

    def test_zero_initial_wait_no_injection(self):
        code = '''class TestScene(Scene):
    def construct(self):
        self.play(FadeIn(text))'''
        instruction = {"_initial_wait": 0}
        result = _inject_pacing(code, instruction)
        assert "initial_wait" not in result

    def test_no_initial_wait_key_no_injection(self):
        code = '''class TestScene(Scene):
    def construct(self):
        self.play(FadeIn(text))'''
        result = _inject_pacing(code, {})
        assert result == code

    def test_sync_waits_appended(self):
        code = '''class TestScene(Scene):
    def construct(self):
        self.play(FadeIn(text))'''
        instruction = {"_sync_waits": {"line_start": 1.5, "event_reveal": 3.0}}
        result = _inject_pacing(code, instruction)
        assert "sync_point: line_start @ 1.50s" in result
        assert "sync_point: event_reveal @ 3.00s" in result

    def test_both_initial_wait_and_sync(self):
        code = '''class TestScene(Scene):
    def construct(self):
        self.play(FadeIn(text))'''
        instruction = {"_initial_wait": 1.5, "_sync_waits": {"drop": 2.0}}
        result = _inject_pacing(code, instruction)
        assert "self.wait(1.5)" in result
        assert "sync_point: drop" in result
