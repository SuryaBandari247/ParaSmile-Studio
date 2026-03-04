"""Renderer module — invokes Manim to render scenes to MP4 files.

Generates real Manim scene code via manim_codegen, writes it to a temp
file, and invokes `manim render` as a subprocess.
"""

from __future__ import annotations

import logging
import os
import re
import subprocess
import tempfile
import time

from asset_orchestrator.config import RenderConfig
from asset_orchestrator.exceptions import RenderError
from asset_orchestrator.manim_codegen import generate_scene_code, get_scene_class_name

logger = logging.getLogger(__name__)


class Renderer:
    """Renders Manim Scenes to MP4 files."""

    def __init__(self, config: RenderConfig) -> None:
        self.config = config

    def render(self, scene, instruction: dict) -> str:
        """Render a Visual_Instruction to MP4 via Manim.

        Generates real Manim code with data baked in, writes to a temp file,
        runs `manim render`, and returns the absolute path of the MP4.

        Args:
            scene: Configured scene instance (used for compatibility, data
                   comes from instruction).
            instruction: Visual_Instruction dict.

        Returns:
            Absolute file path of the rendered MP4.

        Raises:
            RenderError: If Manim rendering fails.
        """
        output_dir = os.path.abspath(self.config.output_dir)
        os.makedirs(output_dir, exist_ok=True)

        sanitized = self.sanitize_filename(instruction.get("title", "untitled"))
        inst_type = instruction.get("type", "scene")
        output_filename = f"{inst_type}_{sanitized}.{self.config.output_format}"
        class_name = get_scene_class_name(instruction)

        # Generate real Manim code with data embedded
        manim_code = generate_scene_code(instruction)

        tmp_file = None
        try:
            tmp_file = tempfile.NamedTemporaryFile(
                suffix=".py", prefix="manim_scene_", delete=False, mode="w"
            )
            tmp_file.write(manim_code)
            tmp_file.flush()
            tmp_file.close()

            cmd = [
                "manim", "render",
                "-qh",
                "--fps", str(self.config.fps),
                "-r", f"{self.config.width},{self.config.height}",
                "-o", output_filename,
                "--media_dir", output_dir,
                tmp_file.name,
                class_name,
            ]

            logger.info("Render start: type=%s, title=%s", inst_type, sanitized)
            start = time.time()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            elapsed_ms = (time.time() - start) * 1000

            if result.returncode != 0:
                logger.error(
                    "Render failed: type=%s, title=%s, elapsed=%.1fms, stderr=%s",
                    inst_type, sanitized, elapsed_ms,
                    result.stderr[:500] if result.stderr else result.stdout[:500],
                )
                raise RenderError(
                    error_output=result.stderr or result.stdout,
                    instruction=instruction,
                )

            logger.info(
                "Render complete: type=%s, title=%s, elapsed=%.1fms",
                inst_type, sanitized, elapsed_ms,
            )

            # Manim places output under media_dir/videos/<temp_name>/<resolution>/
            rendered_path = self._find_rendered_file(output_dir, output_filename)
            if rendered_path:
                return os.path.abspath(rendered_path)

            # Fallback path — should not normally be reached
            fallback = os.path.join(output_dir, output_filename)
            if os.path.isfile(fallback):
                return os.path.abspath(fallback)

            raise RenderError(
                error_output=f"Rendered file not found. Expected: {output_filename} under {output_dir}",
                instruction=instruction,
            )

        except RenderError:
            raise
        except Exception as exc:
            raise RenderError(
                error_output=str(exc),
                instruction=instruction,
            ) from exc
        finally:
            if tmp_file and os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

    @staticmethod
    def sanitize_filename(title: str) -> str:
        """Replace non-alphanumeric characters with underscores."""
        return re.sub(r"[^a-zA-Z0-9]", "_", title)

    @staticmethod
    def _find_rendered_file(root_dir: str, filename: str) -> str | None:
        """Walk *root_dir* looking for *filename* and return its path, or None."""
        for dirpath, _, filenames in os.walk(root_dir):
            if filename in filenames:
                return os.path.join(dirpath, filename)
        return None
