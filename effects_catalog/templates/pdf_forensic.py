"""PDF Forensic Effect — animate highlights on actual company PDF reports.

Converts a PDF page to a high-res image, then uses Manim to animate
highlight rectangles, camera zooms, and sequential reveals on the source
document. Replaces generic stock footage with credible source material.
"""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)

# Manim scene class name for this effect
SCENE_CLASS = "PDFForensicScene"


class PDFForensicError(Exception):
    """Base error for PDF Forensic effect."""


class InvalidPDFPathError(PDFForensicError):
    """Raised when the PDF file path is invalid or not found."""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"PDF file not found: {path}")


class PageRangeError(PDFForensicError):
    """Raised when the page number is out of range."""

    def __init__(self, page: int, max_pages: int):
        self.page = page
        self.max_pages = max_pages
        super().__init__(
            f"Page {page} out of range. PDF has {max_pages} page(s) (valid: 1–{max_pages})"
        )


class TextNotFoundError(PDFForensicError):
    """Raised when a text search string is not found on the page."""

    def __init__(self, text: str, page: int):
        self.text = text
        self.page = page
        super().__init__(f"Text '{text}' not found on page {page}")


def validate_instruction(data: dict) -> None:
    """Validate PDF forensic instruction data. Raises on invalid input."""
    pdf_path = data.get("pdf_path", "")
    page_number = data.get("page_number", 1)
    highlights = data.get("highlights", [])

    if not pdf_path:
        raise InvalidPDFPathError("")

    if not os.path.isfile(pdf_path):
        raise InvalidPDFPathError(pdf_path)

    # Check page count using pdfinfo if available
    try:
        import subprocess
        result = subprocess.run(
            ["pdfinfo", pdf_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("Pages:"):
                    max_pages = int(line.split(":")[1].strip())
                    if page_number < 1 or page_number > max_pages:
                        raise PageRangeError(page_number, max_pages)
                    break
    except FileNotFoundError:
        # pdfinfo not installed — skip page count validation
        logger.debug("pdfinfo not available, skipping page count validation")
    except PDFForensicError:
        raise
    except Exception as exc:
        logger.debug("pdfinfo check failed: %s", exc)

    if page_number < 1:
        raise PageRangeError(page_number, 0)

    # Validate text_search highlights can be resolved
    for hl in highlights:
        text_search = hl.get("text_search")
        if text_search and not hl.get("bbox"):
            # Try to resolve text to bbox using pdftotext
            bbox = _resolve_text_search(pdf_path, page_number, text_search)
            if bbox is None:
                raise TextNotFoundError(text_search, page_number)
            hl["bbox"] = bbox


def _resolve_text_search(pdf_path: str, page: int, text: str) -> dict | None:
    """Attempt to find text on a PDF page and return approximate bbox.

    Uses pdftotext with -bbox-layout to get word positions.
    Returns None if text not found.
    """
    try:
        import subprocess
        import xml.etree.ElementTree as ET

        result = subprocess.run(
            ["pdftotext", "-bbox-layout",
             "-f", str(page), "-l", str(page),
             pdf_path, "-"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            return None

        # Parse the XHTML output to find word positions
        # pdftotext -bbox-layout outputs XHTML with word elements
        content = result.stdout
        search_lower = text.lower()

        # Simple approach: find the text in the raw output and estimate position
        # For production, use proper XML parsing with namespace handling
        try:
            root = ET.fromstring(content)
            ns = {"xhtml": "http://www.w3.org/1999/xhtml"}
            pages = root.findall(".//xhtml:page", ns)
            if not pages:
                return None

            page_el = pages[0]
            page_w = float(page_el.get("width", "612"))
            page_h = float(page_el.get("height", "792"))

            words = page_el.findall(".//xhtml:word", ns)
            # Build text from words and find match
            for i, word in enumerate(words):
                word_text = (word.text or "").strip()
                if search_lower in word_text.lower():
                    x = float(word.get("xMin", "0"))
                    y = float(word.get("yMin", "0"))
                    x_max = float(word.get("xMax", "0"))
                    y_max = float(word.get("yMax", "0"))
                    return {
                        "x": x / page_w,
                        "y": y / page_h,
                        "width": (x_max - x) / page_w,
                        "height": (y_max - y) / page_h,
                    }
        except ET.ParseError:
            pass

        return None
    except FileNotFoundError:
        logger.debug("pdftotext not available for text search")
        return None
    except Exception as exc:
        logger.debug("Text search failed: %s", exc)
        return None


def generate(instruction: dict) -> str:
    """Generate a Manim Python file for the PDF Forensic effect.

    Expected instruction.data keys:
        pdf_path: str — path to the PDF file
        page_number: int — 1-indexed page number
        highlights: list[dict] — each with bbox or text_search, style, color, opacity
    """
    data = instruction.get("data", {})
    pdf_path = data.get("pdf_path", "")
    page_number = data.get("page_number", 1)
    highlights = data.get("highlights", [])
    title = instruction.get("title", "")

    return f'''from manim import *
import subprocess

FONT = "Inter"
import tempfile
from pathlib import Path

class {SCENE_CLASS}(MovingCameraScene):
    """Animate highlights on a PDF report page."""

    def construct(self):
        self.camera.background_color = "#FFFFFF"
        self.camera.frame.save_state()

        pdf_path = {json.dumps(pdf_path)}
        page_number = {json.dumps(page_number)}
        highlights = {json.dumps(highlights)}
        title = {json.dumps(title)}

        # Convert PDF page to image using pdftoppm (poppler)
        img_path = self._pdf_to_image(pdf_path, page_number)
        if img_path is None:
            error = Text("PDF conversion failed", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(error))
            self.wait(3)
            return

        # Display the PDF page
        page_img = ImageMobject(str(img_path))
        page_img.height = 6.5
        page_img.move_to(ORIGIN)

        if title:
            title_text = Text(title, font=FONT, font_size=44, color="#111827", weight=BOLD)
            title_text.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            if title_text.width > 12:
                title_text.scale_to_fit_width(12)
            self.play(FadeIn(title_text), run_time=0.3)

        self.play(FadeIn(page_img, scale=0.95), run_time=0.6)
        self.wait(0.5)

        # Sequential highlight animation
        for i, hl in enumerate(highlights):
            bbox = hl.get("bbox", {{}})
            style = hl.get("style", "rectangle")
            color = hl.get("color", "#FF453A")
            opacity = hl.get("opacity", 0.3)

            if not bbox:
                continue

            # Convert relative bbox (0-1) to page coordinates
            x = bbox.get("x", 0.5)
            y = bbox.get("y", 0.5)
            w = bbox.get("width", 0.2)
            h = bbox.get("height", 0.05)

            # Map to Manim coordinates relative to the image
            img_left = page_img.get_left()[0]
            img_right = page_img.get_right()[0]
            img_top = page_img.get_top()[1]
            img_bottom = page_img.get_bottom()[1]

            img_w = img_right - img_left
            img_h = img_top - img_bottom

            cx = img_left + (x + w / 2) * img_w
            cy = img_top - (y + h / 2) * img_h
            rect_w = w * img_w
            rect_h = h * img_h

            if style == "underline":
                highlight = Line(
                    [cx - rect_w / 2, cy - rect_h / 2, 0],
                    [cx + rect_w / 2, cy - rect_h / 2, 0],
                    color=color, stroke_width=4,
                )
            elif style == "margin_annotation":
                highlight = Line(
                    [img_left - 0.15, cy + rect_h / 2, 0],
                    [img_left - 0.15, cy - rect_h / 2, 0],
                    color=color, stroke_width=6,
                )
            else:  # rectangle
                highlight = Rectangle(
                    width=rect_w, height=rect_h,
                    color=color, fill_opacity=opacity,
                    stroke_width=2, stroke_color=color,
                )
                highlight.move_to([cx, cy, 0])

            # Camera zoom into the highlight region
            zoom_target = [cx, cy, 0]
            self.play(
                Create(highlight),
                self.camera.frame.animate.set(width=max(rect_w * 4, 5)).move_to(zoom_target),
                run_time=0.6,
            )
            self.play(Indicate(highlight, scale_factor=1.05, color=color), run_time=0.4)
            self.wait(1.0)

            # Pull back before next highlight
            if i < len(highlights) - 1:
                self.play(Restore(self.camera.frame), run_time=0.4)
                self.wait(0.3)

        # Final hold and fade
        self.wait(2)
        self.play(Restore(self.camera.frame), run_time=0.4)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)

    @staticmethod
    def _pdf_to_image(pdf_path: str, page_number: int) -> str | None:
        """Convert a PDF page to PNG using pdftoppm. Returns path or None."""
        try:
            tmp = tempfile.mkdtemp(prefix="pdf_forensic_")
            out_prefix = f"{{tmp}}/page"
            subprocess.run(
                ["pdftoppm", "-png", "-r", "300",
                 "-f", str(page_number), "-l", str(page_number),
                 pdf_path, out_prefix],
                check=True, capture_output=True, timeout=30,
            )
            # pdftoppm outputs page-01.png, page-1.png, etc.
            candidates = list(Path(tmp).glob("page-*.png"))
            return str(candidates[0]) if candidates else None
        except Exception:
            return None
'''
