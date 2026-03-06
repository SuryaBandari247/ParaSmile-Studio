"""Chart Templates — reusable Scene subclasses for technical data visualizations.

All templates use a consistent dark-background colour scheme suitable for
video production: dark gray background, white text, accent colours for data.
"""

from __future__ import annotations

from asset_orchestrator.scene_registry import BaseScene

# -- Colour constants -------------------------------------------------------

BACKGROUND_COLOR = "#FFFFFF"
TEXT_COLOR = "#191919"
ACCENT_COLORS = [
    "#2962FF",  # deep blue (primary)
    "#26A69A",  # emerald
    "#F59E0B",  # amber
    "#EF5350",  # red
    "#8B5CF6",  # violet
    "#06B6D4",  # cyan
    "#F97316",  # orange
    "#EC4899",  # pink
    "#787B86",  # gray
    "#14B8A6",  # teal
    "#84CC16",  # lime
]

MAX_TITLE_LENGTH = 60
MAX_CATEGORIES = 10


def _truncate_title(title: str) -> str:
    """Truncate *title* to at most 60 characters, appending '...' if needed."""
    if len(title) > MAX_TITLE_LENGTH:
        return title[:MAX_TITLE_LENGTH] + "..."
    return title


def _group_categories(labels: list, values: list) -> tuple[list, list]:
    """Group the smallest categories into 'Other' when there are more than 10.

    Returns the (labels, values) pair — unchanged when ≤ 10 categories,
    otherwise the top 10 by value plus an 'Other' bucket.
    """
    if len(labels) <= MAX_CATEGORIES:
        return list(labels), list(values)

    paired = sorted(zip(values, labels), reverse=True)
    top = paired[:MAX_CATEGORIES]
    rest = paired[MAX_CATEGORIES:]

    new_labels = [label for _, label in top]
    new_values = [value for value, _ in top]

    other_sum = sum(value for value, _ in rest)
    new_labels.append("Other")
    new_values.append(other_sum)

    return new_labels, new_values


class BarChartScene(BaseScene):
    """Scene for bar-chart animations.

    Attributes set after ``construct()``:
        processed_title: Title after truncation.
        processed_data: ``{"labels": [...], "values": [...]}`` after grouping.
        background_color: Background colour applied.
        text_color: Text colour applied.
        bar_colors: Per-bar accent colours.
        axes_config: Dict describing the axes layout.
        bars: List of dicts describing each bar (label, value, color, value_label).
    """

    def __init__(self, title: str = "", data: dict | None = None, style: dict | None = None):
        super().__init__(title=title, data=data, style=style)
        # Attributes populated by construct()
        self.processed_title: str | None = None
        self.processed_data: dict | None = None
        self.background_color: str | None = None
        self.text_color: str | None = None
        self.bar_colors: list[str] = []
        self.axes_config: dict | None = None
        self.bars: list[dict] = []

    def construct(self) -> None:
        """Prepare the bar-chart animation data structures.

        Since we subclass ``BaseScene`` (not real Manim), this method stores
        what *would* be rendered as instance attributes so the logic can be
        verified in tests without a Manim installation.
        """
        # -- Title truncation ------------------------------------------------
        self.processed_title = _truncate_title(self.title)

        # -- Category grouping -----------------------------------------------
        raw_labels = self.data.get("labels", [])
        raw_values = self.data.get("values", [])
        grouped_labels, grouped_values = _group_categories(raw_labels, raw_values)
        self.processed_data = {"labels": grouped_labels, "values": grouped_values}

        # -- Colour scheme ---------------------------------------------------
        self.background_color = BACKGROUND_COLOR
        self.text_color = TEXT_COLOR

        # -- Axes configuration ----------------------------------------------
        max_val = max(grouped_values) if grouped_values else 0
        self.axes_config = {
            "x_labels": grouped_labels,
            "y_range": [0, max_val],
            "label_color": TEXT_COLOR,
        }

        # -- Bars with accent colours and value labels -----------------------
        self.bar_colors = []
        self.bars = []
        for idx, (label, value) in enumerate(zip(grouped_labels, grouped_values)):
            color = ACCENT_COLORS[idx % len(ACCENT_COLORS)]
            self.bar_colors.append(color)
            self.bars.append({
                "label": label,
                "value": value,
                "color": color,
                "value_label": str(value),
            })


class LineChartScene(BaseScene):
    """Scene for line-chart animations.

    Attributes set after ``construct()``:
        processed_title: Title after truncation.
        processed_data: ``{"labels": [...], "values": [...]}`` after grouping.
        background_color: Background colour applied.
        text_color: Text colour applied.
        points: List of dicts describing each data point (label, value, x, y, color).
        lines: List of dicts describing connecting line segments between points.
        axes_config: Dict describing the axes layout.
    """

    def __init__(self, title: str = "", data: dict | None = None, style: dict | None = None):
        super().__init__(title=title, data=data, style=style)
        # Attributes populated by construct()
        self.processed_title: str | None = None
        self.processed_data: dict | None = None
        self.background_color: str | None = None
        self.text_color: str | None = None
        self.points: list[dict] = []
        self.lines: list[dict] = []
        self.axes_config: dict | None = None

    def construct(self) -> None:
        """Prepare the line-chart animation data structures.

        Since we subclass ``BaseScene`` (not real Manim), this method stores
        what *would* be rendered as instance attributes so the logic can be
        verified in tests without a Manim installation.
        """
        # -- Title truncation ------------------------------------------------
        self.processed_title = _truncate_title(self.title)

        # -- Category grouping -----------------------------------------------
        raw_labels = self.data.get("labels", [])
        raw_values = self.data.get("values", [])
        grouped_labels, grouped_values = _group_categories(raw_labels, raw_values)
        self.processed_data = {"labels": grouped_labels, "values": grouped_values}

        # -- Colour scheme ---------------------------------------------------
        self.background_color = BACKGROUND_COLOR
        self.text_color = TEXT_COLOR

        # -- Axes configuration ----------------------------------------------
        max_val = max(grouped_values) if grouped_values else 0
        num_points = len(grouped_labels)
        self.axes_config = {
            "x_labels": grouped_labels,
            "x_range": [0, max(num_points - 1, 1)],
            "y_range": [0, max_val],
            "label_color": TEXT_COLOR,
        }

        # -- Data points with accent colours ---------------------------------
        self.points = []
        for idx, (label, value) in enumerate(zip(grouped_labels, grouped_values)):
            color = ACCENT_COLORS[idx % len(ACCENT_COLORS)]
            self.points.append({
                "label": label,
                "value": value,
                "x": idx,
                "y": value,
                "color": color,
            })

        # -- Connecting line segments ----------------------------------------
        self.lines = []
        for i in range(len(self.points) - 1):
            self.lines.append({
                "from_point": {"x": self.points[i]["x"], "y": self.points[i]["y"]},
                "to_point": {"x": self.points[i + 1]["x"], "y": self.points[i + 1]["y"]},
                "color": ACCENT_COLORS[0],
            })


class PieChartScene(BaseScene):
    """Scene for pie-chart animations.

    Attributes set after ``construct()``:
        processed_title: Title after truncation.
        processed_data: ``{"labels": [...], "values": [...]}`` after grouping.
        background_color: Background colour applied.
        text_color: Text colour applied.
        total_value: Sum of all values (used for percentage calculation).
        segments: List of dicts describing each pie segment
            (label, value, percentage, color).
    """

    def __init__(self, title: str = "", data: dict | None = None, style: dict | None = None):
        super().__init__(title=title, data=data, style=style)
        # Attributes populated by construct()
        self.processed_title: str | None = None
        self.processed_data: dict | None = None
        self.background_color: str | None = None
        self.text_color: str | None = None
        self.total_value: float = 0
        self.segments: list[dict] = []

    def construct(self) -> None:
        """Prepare the pie-chart animation data structures.

        Since we subclass ``BaseScene`` (not real Manim), this method stores
        what *would* be rendered as instance attributes so the logic can be
        verified in tests without a Manim installation.
        """
        # -- Title truncation ------------------------------------------------
        self.processed_title = _truncate_title(self.title)

        # -- Category grouping -----------------------------------------------
        raw_labels = self.data.get("labels", [])
        raw_values = self.data.get("values", [])
        grouped_labels, grouped_values = _group_categories(raw_labels, raw_values)
        self.processed_data = {"labels": grouped_labels, "values": grouped_values}

        # -- Colour scheme ---------------------------------------------------
        self.background_color = BACKGROUND_COLOR
        self.text_color = TEXT_COLOR

        # -- Percentage calculation and segment construction -----------------
        self.total_value = sum(grouped_values) if grouped_values else 0
        self.segments = []
        for idx, (label, value) in enumerate(zip(grouped_labels, grouped_values)):
            color = ACCENT_COLORS[idx % len(ACCENT_COLORS)]
            percentage = (value / self.total_value * 100) if self.total_value else 0
            self.segments.append({
                "label": label,
                "value": value,
                "percentage": percentage,
                "color": color,
            })
