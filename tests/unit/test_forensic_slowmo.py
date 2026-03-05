"""Unit tests for Forensic SlowMo (jump-cut vs travel zoom modes)."""

import ast

from effects_catalog.templates.forensic_zoom import generate


class TestForensicSlowMo:
    def _make_instruction(self, **overrides):
        data = {
            "dates": [f"2024-{m:02d}-01" for m in range(1, 13)],
            "values": [100 + i * 5 for i in range(12)],
            "focus_date": "2024-06-01",
            "focus_window_days": 30,
            "glow_color": "#FFD700",
            "blur_opacity": 0.15,
        }
        data.update(overrides)
        return {"data": data, "title": "Forensic Test"}

    def test_jump_cut_generates_valid_python(self):
        code = generate(self._make_instruction(zoom_mode="jump_cut"))
        ast.parse(code)

    def test_travel_generates_valid_python(self):
        code = generate(self._make_instruction(zoom_mode="travel"))
        ast.parse(code)

    def test_jump_cut_has_instant_transition(self):
        code = generate(self._make_instruction(zoom_mode="jump_cut"))
        # jump_cut uses direct set() instead of animate
        assert "frame.set(" in code

    def test_travel_has_animated_transition(self):
        code = generate(self._make_instruction(zoom_mode="travel"))
        assert "frame.animate" in code

    def test_wide_hold_parameter(self):
        code = generate(self._make_instruction(zoom_mode="jump_cut", wide_hold=2.0))
        assert "2.0" in code

    def test_default_zoom_mode_is_jump_cut(self):
        code = generate(self._make_instruction())
        assert "jump_cut" in code

    def test_glow_rectangle_present(self):
        code = generate(self._make_instruction(zoom_mode="jump_cut"))
        assert "SurroundingRectangle" in code

    def test_indicate_present(self):
        code = generate(self._make_instruction())
        assert "Indicate" in code
