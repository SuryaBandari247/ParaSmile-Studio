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
        camera_shake: bool — enable subtle handheld drift (default True)
    """
    data = instruction.get("data", {})
    pdf_path = data.get("pdf_path", "")
    page_number = data.get("page_number", 1)
    highlights = data.get("highlights", [])
    title = instruction.get("title", "")
    camera_shake = data.get("camera_shake", True)

    J = json.dumps
    cam_shake_py = "True" if camera_shake else "False"

    return _build_scene_code(J, pdf_path, page_number, highlights, title, cam_shake_py)


def _build_scene_code(J, pdf_path, page_number, highlights, title, cam_shake_py):
    """Build the full Manim scene code string."""
    return f'''from manim import *
import subprocess
import numpy as np

FONT = "Inter"
import tempfile
from pathlib import Path

class {SCENE_CLASS}(MovingCameraScene):
    """Cinematic forensic investigation of a PDF report page.

    Modern dark gradient background, borderless soft-glow highlights,
    3D perspective, handheld drift, scanner sweep.
    """

    def construct(self):
        self.camera.background_color = "#080C14"
        self.camera.frame.save_state()

        pdf_path = {J(pdf_path)}
        page_number = {J(page_number)}
        highlights = {J(highlights)}
        title = {J(title)}
        camera_shake = {cam_shake_py}

        # Convert PDF page to image
        img_path = self._pdf_to_image(pdf_path, page_number)
        if img_path is None:
            error = Text("PDF conversion failed", font=FONT, font_size=28, color="#EF4444")
            self.play(FadeIn(error))
            self.wait(3)
            return

        # ══ BACKGROUND — clean dark with single subtle center glow ══
        bg_glow = Circle(radius=4.5, color="#0F1B2D", fill_opacity=0.2, stroke_width=0)
        bg_glow.move_to(ORIGIN).set_z_index(-19)
        self.add(bg_glow)

        # ══ PDF PAGE WITH 3D PERSPECTIVE ══
        page_img = ImageMobject(str(img_path))
        page_img.height = 6.5
        page_img.move_to(ORIGIN)

        # Single soft shadow
        shadow = RoundedRectangle(
            corner_radius=0.06,
            width=page_img.width + 0.3, height=page_img.height + 0.3,
            color="#000000", fill_opacity=0.4, stroke_width=0,
        )
        shadow.move_to(page_img.get_center() + DOWN * 0.06 + RIGHT * 0.06)
        shadow.set_z_index(-5)

        # 3D perspective tilt
        page_group = Group(shadow, page_img)
        page_group.rotate(8 * DEGREES, axis=RIGHT)
        page_group.rotate(3 * DEGREES, axis=UP)

        # ══ VIGNETTE — just 4 thin edge darkeners, very subtle ══
        vignette = VGroup()
        for thickness, edge_dir, op in [
            (1.2, UP, 0.6), (0.8, DOWN, 0.4),
            (1.5, LEFT, 0.5), (1.5, RIGHT, 0.5),
        ]:
            if edge_dir[1] != 0:
                bar = Rectangle(width=16, height=thickness, color="#080C14",
                                fill_opacity=op, stroke_width=0)
            else:
                bar = Rectangle(width=thickness, height=10, color="#080C14",
                                fill_opacity=op, stroke_width=0)
            bar.to_edge(edge_dir, buff=0).set_z_index(50)
            vignette.add(bar)

        # ══ TITLE ══
        if title:
            title_text = Text(title, font=FONT, font_size=44, color="#F8FAFC", weight=BOLD)
            title_text.to_edge(UP, buff=0.3).to_edge(LEFT, buff=0.55)
            title_text.set_z_index(100)
            if title_text.width > 12:
                title_text.scale_to_fit_width(12)
            self.play(FadeIn(title_text), run_time=0.3)

        # ══ ENTRANCE ══
        page_group.shift(DOWN * 1.5)
        page_group.set_opacity(0)
        self.add(page_group)
        self.play(
            page_group.animate.shift(UP * 1.5).set_opacity(1),
            FadeIn(vignette),
            run_time=0.8,
            rate_func=smooth,
        )
        self.wait(0.3)

        # ══ HANDHELD CAMERA DRIFT ══
        if camera_shake:
            _t = [0.0]
            _orig = self.camera.frame.get_center().copy()
            def _drift(mob, dt):
                _t[0] += dt
                dx = 0.015 * np.sin(_t[0] * 0.7)
                dy = 0.010 * np.cos(_t[0] * 0.5)
                mob.move_to(_orig + np.array([dx, dy, 0]))
            self.camera.frame.add_updater(_drift)

        # ══ SEQUENTIAL FORENSIC HIGHLIGHTS ══
        all_highlights = VGroup()
        for i, hl in enumerate(highlights):
            bbox = hl.get("bbox", {{}})
            style = hl.get("style", "rectangle")
            color = hl.get("color", "#FF453A")
            opacity = hl.get("opacity", 0.3)
            label = hl.get("label", "")
            zoom_level = hl.get("zoom_level", 4.0)

            if not bbox:
                continue

            x = bbox.get("x", 0.5)
            y = bbox.get("y", 0.5)
            w = bbox.get("width", 0.2)
            h = bbox.get("height", 0.05)

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
            hl_center = np.array([cx, cy, 0])

            # ── Highlight — NO borders, soft gradient fill only ──
            if style == "underline":
                # Soft glowing underline — no hard stroke
                highlight = Line(
                    [cx - rect_w / 2, cy - rect_h / 2, 0],
                    [cx + rect_w / 2, cy - rect_h / 2, 0],
                    color=color, stroke_width=3, stroke_opacity=0.8,
                )
                highlight.set_z_index(60)
                # Underline glow
                ul_glow = Line(
                    [cx - rect_w / 2, cy - rect_h / 2, 0],
                    [cx + rect_w / 2, cy - rect_h / 2, 0],
                    color=color, stroke_width=10, stroke_opacity=0.15,
                )
                ul_glow.set_z_index(59)
            elif style == "margin_annotation":
                highlight = Line(
                    [img_left - 0.15, cy + rect_h / 2, 0],
                    [img_left - 0.15, cy - rect_h / 2, 0],
                    color=color, stroke_width=5, stroke_opacity=0.8,
                )
                highlight.set_z_index(60)
                ul_glow = Line(
                    [img_left - 0.15, cy + rect_h / 2, 0],
                    [img_left - 0.15, cy - rect_h / 2, 0],
                    color=color, stroke_width=14, stroke_opacity=0.12,
                )
                ul_glow.set_z_index(59)
            else:
                # Borderless rectangle — soft fill with NO stroke
                highlight = RoundedRectangle(
                    corner_radius=0.03,
                    width=rect_w, height=rect_h,
                    color=color, fill_opacity=opacity,
                    stroke_width=0,
                )
                highlight.move_to(hl_center)
                highlight.set_z_index(60)
                ul_glow = None

            # ── Multi-layer bloom glow (no borders) ──
            glow_layers = VGroup()
            for gw_extra, go in [(0.30, 0.04), (0.18, 0.08), (0.08, 0.14)]:
                gl = RoundedRectangle(
                    corner_radius=0.05,
                    width=rect_w + gw_extra, height=rect_h + gw_extra,
                    color=color, fill_opacity=go, stroke_width=0,
                )
                gl.move_to(hl_center)
                glow_layers.add(gl)
            glow_layers.set_z_index(55)

            # ── Scanner sweep line ──
            scan_line = Line(
                [cx - rect_w / 2, cy - rect_h / 2, 0],
                [cx - rect_w / 2, cy + rect_h / 2, 0],
                color=WHITE, stroke_width=1.5, stroke_opacity=0.6,
            )
            scan_line.set_z_index(65)

            # ── Tight forensic zoom ──
            zoom_width = max(rect_w * zoom_level, 4.5)

            if camera_shake:
                self.camera.frame.remove_updater(_drift)

            anims = [
                FadeIn(glow_layers),
                Create(highlight),
                scan_line.animate.shift(RIGHT * rect_w),
                self.camera.frame.animate.set(width=zoom_width).move_to(hl_center),
            ]
            if ul_glow is not None:
                anims.insert(0, FadeIn(ul_glow))

            self.play(*anims, run_time=1.0, rate_func=smooth)

            # Soft pulse
            self.play(
                Indicate(highlight, scale_factor=1.04, color=color),
                run_time=0.4,
            )

            # ── Label — modern pill style, no hard border ──
            if label:
                label_text = Text(
                    label, font=FONT, font_size=13, color="#E2E8F0",
                    weight=BOLD,
                )
                label_bg = RoundedRectangle(
                    corner_radius=0.06,
                    width=label_text.width + 0.24,
                    height=label_text.height + 0.14,
                    color=color, fill_opacity=0.12,
                    stroke_width=0,
                )
                # Subtle glow behind pill
                label_glow = RoundedRectangle(
                    corner_radius=0.08,
                    width=label_text.width + 0.4,
                    height=label_text.height + 0.26,
                    color=color, fill_opacity=0.05,
                    stroke_width=0,
                )
                label_group = VGroup(label_glow, label_bg, label_text)
                label_text.move_to(label_bg.get_center())
                label_glow.move_to(label_bg.get_center())
                label_group.next_to(highlight, DOWN, buff=0.10)
                label_group.set_z_index(70)
                self.play(FadeIn(label_group, shift=UP * 0.04), run_time=0.3)

            self.play(FadeOut(scan_line), run_time=0.2)
            self.wait(1.2)

            all_highlights.add(highlight, glow_layers)
            if ul_glow is not None:
                all_highlights.add(ul_glow)

            # ── Pull back before next ──
            if i < len(highlights) - 1:
                if camera_shake:
                    _orig = self.camera.frame.get_center().copy()
                    self.camera.frame.add_updater(_drift)
                self.play(Restore(self.camera.frame), run_time=0.5)
                self.wait(0.3)
                if camera_shake:
                    self.camera.frame.remove_updater(_drift)

        # ══ FINAL ══
        if camera_shake:
            try:
                self.camera.frame.remove_updater(_drift)
            except Exception:
                pass

        self.wait(1.5)
        self.play(Restore(self.camera.frame), run_time=0.6)
        self.wait(1.5)
        self.play(*[FadeOut(m) for m in self.mobjects], run_time=0.6)

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
            candidates = list(Path(tmp).glob("page-*.png"))
            return str(candidates[0]) if candidates else None
        except Exception:
            return None
'''
