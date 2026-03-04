"""
Visual instruction validator for the Script Converter.

Validates VisualInstruction dicts against the Asset Orchestrator's expected
schemas, catching rendering failures early before they reach downstream.

Requirements: 3.3, 3.4, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from script_generator.models import VideoScript


class Validator:
    """Validates visual instructions against the Asset Orchestrator schema."""

    VALID_TYPES = {"bar_chart", "line_chart", "pie_chart", "code_snippet", "text_overlay"}

    def validate_script(self, script: VideoScript) -> list[str]:
        """
        Validate all scene blocks in a VideoScript.

        Returns a list of violation strings. An empty list means the script
        is valid.
        """
        violations: list[str] = []
        for scene in script.scenes:
            violations.extend(self.validate_instruction(scene.visual_instruction))
        return violations

    def validate_instruction(self, instruction: dict) -> list[str]:
        """
        Validate a single visual instruction dict against its type schema.

        Per-type checks:
        - bar_chart/line_chart: data has labels (list[str]) and values
          (list[number]) of equal length.
        - pie_chart: same as above, but all values must be positive (> 0).
        - code_snippet: data has code (non-empty str) and language (str).
        - text_overlay: data has text (non-empty str).
        - Unknown type: returns a violation identifying the invalid type.
        """
        violations: list[str] = []
        vis_type = instruction.get("type")

        if vis_type not in self.VALID_TYPES:
            violations.append(f"Unknown visual instruction type: {vis_type!r}")
            return violations

        data = instruction.get("data", {})

        if vis_type in ("bar_chart", "line_chart", "pie_chart"):
            violations.extend(self._validate_chart(data, vis_type))
        elif vis_type == "code_snippet":
            violations.extend(self._validate_code_snippet(data))
        elif vis_type == "text_overlay":
            violations.extend(self._validate_text_overlay(data))

        return violations

    def _validate_chart(self, data: dict, vis_type: str) -> list[str]:
        """Validate chart-type instructions (bar_chart, line_chart, pie_chart)."""
        violations: list[str] = []

        labels = data.get("labels")
        values = data.get("values")

        if not isinstance(labels, list):
            violations.append(f"{vis_type}: 'labels' must be a list of strings")
        elif not all(isinstance(l, str) for l in labels):
            violations.append(f"{vis_type}: 'labels' must be a list of strings")

        if not isinstance(values, list):
            violations.append(f"{vis_type}: 'values' must be a list of numbers")
        elif not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
            violations.append(f"{vis_type}: 'values' must be a list of numbers")

        if isinstance(labels, list) and isinstance(values, list):
            if len(labels) != len(values):
                violations.append(
                    f"{vis_type}: 'labels' length ({len(labels)}) must equal "
                    f"'values' length ({len(values)})"
                )

        if vis_type == "pie_chart" and isinstance(values, list):
            if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in values):
                if not all(v > 0 for v in values):
                    violations.append(f"pie_chart: all values must be positive (> 0)")

        return violations

    def _validate_code_snippet(self, data: dict) -> list[str]:
        """Validate code_snippet instructions."""
        violations: list[str] = []

        code = data.get("code")
        if not isinstance(code, str) or not code:
            violations.append("code_snippet: 'code' must be a non-empty string")

        language = data.get("language")
        if not isinstance(language, str):
            violations.append("code_snippet: 'language' must be a string")

        return violations

    def _validate_text_overlay(self, data: dict) -> list[str]:
        """Validate text_overlay instructions."""
        violations: list[str] = []

        text = data.get("text")
        if not isinstance(text, str) or not text:
            violations.append("text_overlay: 'text' must be a non-empty string")

        return violations
