"""Unit tests for the Capital Flow effect."""

from __future__ import annotations

import ast

import pytest

from effects_catalog.templates.capital_flow import (
    compute_arrow_width,
    generate,
)


class TestComputeArrowWidth:
    def test_max_flow_gets_full_width(self):
        assert abs(compute_arrow_width(100, 100, 2.0) - 2.0) < 0.01

    def test_half_flow_gets_half_width(self):
        assert abs(compute_arrow_width(50, 100, 2.0) - 1.0) < 0.01

    def test_zero_max_returns_base(self):
        assert abs(compute_arrow_width(50, 0, 2.0) - 2.0) < 0.01

    def test_zero_flow(self):
        assert abs(compute_arrow_width(0, 100, 2.0)) < 0.01

    def test_custom_base_width(self):
        assert abs(compute_arrow_width(100, 100, 5.0) - 5.0) < 0.01


class TestGenerate:
    def _make_instruction(self, **overrides):
        data = {
            "flows": [
                {"from_entity": "US Equities", "to_entity": "EU Bonds", "flow_amount": 12.5, "flow_color": "#58a6ff"},
                {"from_entity": "EU Bonds", "to_entity": "EM Debt", "flow_amount": 5.2, "flow_color": "#f0883e"},
                {"from_entity": "EM Debt", "to_entity": "US Equities", "flow_amount": 3.1, "flow_color": "#3fb950"},
            ],
            "layout": "circular",
            "arrow_base_width": 2,
            "flow_label_format": "${:.1f}B",
            "animation_duration": 4.0,
        }
        data.update(overrides)
        return {"data": data, "title": "Capital Flows"}

    def test_generates_valid_python(self):
        ast.parse(generate(self._make_instruction()))

    def test_contains_scene_class(self):
        assert "CapitalFlowScene" in generate(self._make_instruction())

    def test_entity_names_in_output(self):
        code = generate(self._make_instruction())
        assert "US Equities" in code
        assert "EU Bonds" in code
        assert "EM Debt" in code

    def test_arrow_in_output(self):
        code = generate(self._make_instruction())
        assert "Arrow" in code

    def test_circular_layout(self):
        code = generate(self._make_instruction(layout="circular"))
        ast.parse(code)
        assert "circular" in code

    def test_horizontal_layout(self):
        code = generate(self._make_instruction(layout="horizontal"))
        ast.parse(code)
        assert "horizontal" in code

    def test_empty_flows_valid_python(self):
        code = generate(self._make_instruction(flows=[]))
        ast.parse(code)
        assert "No flows" in code

    def test_empty_data_valid_python(self):
        code = generate({"data": {}})
        ast.parse(code)

    def test_flow_labels(self):
        code = generate(self._make_instruction())
        assert "flow_label_format" in code

    def test_sequential_flow_reveal(self):
        code = generate(self._make_instruction())
        assert "Create" in code

    def test_single_flow(self):
        code = generate(self._make_instruction(flows=[
            {"from_entity": "A", "to_entity": "B", "flow_amount": 10.0}
        ]))
        ast.parse(code)

    def test_custom_animation_duration(self):
        code = generate(self._make_instruction(animation_duration=8.0))
        ast.parse(code)
        assert "8.0" in code

    def test_rounded_rectangle_entities(self):
        code = generate(self._make_instruction())
        assert "RoundedRectangle" in code
