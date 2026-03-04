"""FFmpeg compositor for overlaying text on stock footage backgrounds.

Uses Pillow to render text as transparent PNG overlays, then FFmpeg's
overlay filter to composite them onto stock video. Includes production-quality
visual polish: Ken Burns zoom, color grading, and multi-clip jump cuts.
"""

from __future__ import annotations

import logging
import os
import subprocess
import uuid

from PIL import Image, ImageDraw, ImageFont

from asset_orchestrator.exceptions import CompositionError

logger = logging.getLogger(__name__)

# Video dimensions
WIDTH, HEIGHT = 1920, 1080


def _gradient_scrim(
    width: int = WIDTH,
    height: int = HEIGHT,
    *,
    direction: str = "bottom",
    opacity: int = 180,
) -> Image.Image:
    """Create a linear-gradient scrim (transparent → dark).

    Args:
        direction: Where the dark end sits — "bottom", "top", "center".
        opacity: Peak alpha at the dark end (0–255).

    Returns:
        RGBA Image with gradient transparency.
    """
    import numpy as np

    if direction == "center":
        cy = height / 2
        ys = np.abs(np.arange(height) - cy) / cy  # 0 at center, 1 at edges
        alpha_col = (opacity * (1.0 - ys ** 1.4)).clip(0, 255).astype(np.uint8)
    elif direction == "top":
        t = np.arange(height) / height
        alpha_col = (opacity * (1.0 - t ** 1.6)).clip(0, 255).astype(np.uint8)
    else:  # "bottom" (default)
        t = np.arange(height) / height
        alpha_col = (opacity * t ** 1.6).clip(0, 255).astype(np.uint8)

    # Build RGBA array: black with varying alpha
    arr = np.zeros((height, width, 4), dtype=np.uint8)
    arr[:, :, 3] = alpha_col[:, np.newaxis]  # broadcast alpha across width

    return Image.fromarray(arr, "RGBA")


class FFmpegCompositor:
    """Compose stock footage with text overlays using Pillow + FFmpeg overlay."""

    def __init__(self, output_dir: str = "output/composed_stock") -> None:
        self._output_dir = os.path.abspath(output_dir)
        os.makedirs(self._output_dir, exist_ok=True)

    # ── Visual Polish Filters ─────────────────────────────────────────

    # Available effects that users can toggle per scene
    AVAILABLE_EFFECTS: dict[str, dict] = {
        # Lighting group
        "vignette": {"label": "Vignette", "group": "Lighting", "filter": "vignette=PI/5"},
        "vignette_strong": {"label": "Vignette (Strong)", "group": "Lighting", "filter": "vignette=PI/4"},
        "brightness_boost": {"label": "Brightness Boost", "group": "Lighting", "filter": "eq=brightness=0.06"},
        "darken": {"label": "Darken", "group": "Lighting", "filter": "eq=brightness=-0.05"},
        # Color group
        "color_grade": {"label": "Color Grade", "group": "Color", "filter": "eq=contrast=1.08:saturation=0.92:brightness=0.02"},
        "desaturate": {"label": "Desaturate", "group": "Color", "filter": "eq=saturation=0.5"},
        "warm_tone": {"label": "Warm Tone", "group": "Color", "filter": "colorbalance=rs=0.1:gs=-0.05:bs=-0.1"},
        "cool_tone": {"label": "Cool Tone", "group": "Color", "filter": "colorbalance=rs=-0.1:gs=0.0:bs=0.1"},
        "high_contrast": {"label": "High Contrast", "group": "Color", "filter": "eq=contrast=1.3:saturation=1.1"},
        # Motion group
        "ken_burns": {"label": "Ken Burns Zoom", "group": "Motion", "filter": "__ken_burns__"},
        # Blur group
        "blur_edges": {"label": "Blur Edges", "group": "Blur", "filter": "gblur=sigma=2"},
        "sharpen": {"label": "Sharpen", "group": "Blur", "filter": "unsharp=5:5:1.0"},
    }

    @staticmethod
    def build_effects_filter(effects: list[str], duration: float = 8.0) -> str:
        """Build an FFmpeg filter string from a list of effect names.

        Returns a comma-separated filter chain, or empty string if no effects.
        """
        parts: list[str] = []
        for eff in effects:
            info = FFmpegCompositor.AVAILABLE_EFFECTS.get(eff)
            if not info:
                continue
            f = info["filter"]
            if f == "__ken_burns__":
                # Ken Burns needs duration-aware params
                frames = int(duration * 30)
                parts.append(
                    f"scale=2*iw:2*ih,"
                    f"zoompan=z='1+0.08*on/{max(frames, 1)}':"
                    f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                    f":d={frames}:s=1920x1080:fps=30"
                )
            else:
                parts.append(f)
        return ",".join(parts)

    @staticmethod
    def _polish_filter(duration: float, effects: list[str] | None = None) -> str:
        """Build FFmpeg filter chain for production-quality look.

        If effects list is provided, uses those. Otherwise applies default
        Ken Burns zoom + color grade.
        """
        if effects is not None:
            custom = FFmpegCompositor.build_effects_filter(effects, duration)
            if custom:
                return custom
            # Empty effects list = no polish at all
            return "null"

        # Default: Ken Burns + color grade (legacy behavior)
        frames = int(duration * 30)
        zoom = (
            f"scale=2*iw:2*ih,"
            f"zoompan=z='1+0.08*on/{max(frames, 1)}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1920x1080:fps=30"
        )
        color = "eq=contrast=1.08:saturation=0.92:brightness=0.02"
        return f"{zoom},{color}"

    # ── Multi-clip Jump Cut ───────────────────────────────────────────

    def concat_clips(
        self,
        clip_paths: list[str],
        duration: float,
        output_path: str | None = None,
        clip_durations: list[float] | None = None,
        clip_speeds: list[float] | None = None,
    ) -> str:
        """Concat multiple clips into a single video with jump cuts.

        If clip_durations is provided, each clip uses its specified duration.
        Otherwise each clip gets an equal share of the total duration.
        clip_speeds: per-clip playback speed multiplier (1.0 = normal, 2.0 = 2x fast, 0.5 = half speed).
        Applies visual polish to the final output.
        """
        output_path = output_path or self._gen_output_path("jumpcut")
        if not clip_paths:
            return self.generate_solid_background(duration=duration, output_path=output_path)

        if len(clip_paths) == 1:
            single_dur = clip_durations[0] if clip_durations else duration
            single_speed = clip_speeds[0] if clip_speeds else 1.0
            if single_speed != 1.0:
                return self._trim_speed_and_polish(clip_paths[0], single_dur, single_speed, output_path)
            return self._trim_and_polish(clip_paths[0], single_dur, output_path)

        temp_parts = []

        for i, clip in enumerate(clip_paths):
            if clip_durations and i < len(clip_durations):
                clip_dur = clip_durations[i]
            else:
                clip_dur = duration / len(clip_paths)
            speed = clip_speeds[i] if clip_speeds and i < len(clip_speeds) else 1.0

            part_path = self._gen_output_path(f"part{i}")

            # Build video filter: scale + optional speed change
            vf_parts = ["scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"]
            if speed != 1.0:
                # setpts=PTS/speed — speed>1 = faster, speed<1 = slower
                vf_parts.append(f"setpts=PTS/{speed:.2f}")
                # Trim output to exact target duration after speed change
                vf_parts.append(f"trim=duration={clip_dur:.2f}")
                vf_parts.append("setpts=PTS-STARTPTS")
                # Read more source frames to cover the sped-up output
                read_dur = clip_dur * speed
            else:
                read_dur = clip_dur

            cmd = [
                "ffmpeg", "-y", "-i", clip,
                "-t", f"{read_dur:.2f}",
                "-vf", ",".join(vf_parts),
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
                "-an", part_path,
            ]
            try:
                self._exec(cmd, part_path)
                temp_parts.append(part_path)
            except Exception:
                logger.warning("Failed to trim clip %d, skipping", i)

        if not temp_parts:
            return self.generate_solid_background(duration=duration, output_path=output_path)

        # Write concat list
        list_path = self._gen_output_path("list").replace(".mp4", ".txt")
        with open(list_path, "w") as f:
            for p in temp_parts:
                f.write(f"file '{p}'\n")

        # Concat + polish
        polish = f"eq=contrast=1.08:saturation=0.92:brightness=0.02"
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_path,
            "-vf", polish,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-t", f"{duration:.2f}",
            output_path,
        ]
        self._exec(cmd, output_path)

        # Cleanup temp files
        for p in temp_parts:
            try: os.unlink(p)
            except OSError: pass
        try: os.unlink(list_path)
        except OSError: pass

        return os.path.abspath(output_path)

    def _trim_and_polish(self, clip_path: str, duration: float, output_path: str) -> str:
        """Trim a single clip to duration with visual polish."""
        polish = self._polish_filter(duration)
        cmd = [
            "ffmpeg", "-y", "-i", clip_path,
            "-vf", polish,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-t", f"{duration:.2f}", "-an",
            output_path,
        ]
        self._exec(cmd, output_path)
        return os.path.abspath(output_path)
    def _trim_speed_and_polish(self, clip_path: str, duration: float, speed: float, output_path: str) -> str:
        """Trim a single clip with speed adjustment and visual polish."""
        read_dur = duration * speed
        vf = (
            f"scale=1920:1080:force_original_aspect_ratio=decrease,"
            f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
            f"setpts=PTS/{speed:.2f},"
            f"trim=duration={duration:.2f},setpts=PTS-STARTPTS,"
            f"eq=contrast=1.08:saturation=0.92:brightness=0.02"
        )
        cmd = [
            "ffmpeg", "-y", "-i", clip_path,
            "-t", f"{read_dur:.2f}",
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "30",
            "-an", output_path,
        ]
        self._exec(cmd, output_path)
        return os.path.abspath(output_path)

    # ── Text Overlay Compositions ─────────────────────────────────────

    def compose_text_overlay(
        self,
        video_path: str,
        heading: str = "",
        body: str = "",
        position: str = "center",
        duration: float | None = None,
        output_path: str | None = None,
        effects: list[str] | None = None,
    ) -> str:
        """Overlay heading + body text on stock footage with dark scrim.

        If both heading and body are empty, skip the overlay entirely and
        just apply effects (if any) or return the video as-is.
        """
        if not heading and not body:
            # No text — skip scrim overlay, just apply effects if any
            if effects:
                return self._apply_effects_only(video_path, duration, effects, output_path)
            # Still need to trim/scale to target duration even without text/effects
            if duration:
                return self._apply_effects_only(video_path, duration, [], output_path)
            return video_path

        output_path = output_path or self._gen_output_path("text")
        overlay_png = self._gen_output_path("overlay").replace(".mp4", ".png")

        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        # Gradient scrim — dark at text position, transparent elsewhere
        grad_dir = "bottom" if position in ("lower_third", "bottom") else "center"
        scrim = _gradient_scrim(direction=grad_dir, opacity=160)
        img = Image.alpha_composite(img, scrim)
        draw = ImageDraw.Draw(img)

        y_pos = self._position_to_y(position)

        if heading:
            font_h = self._get_font(54)
            lines_h = self._wrap_text(heading, font_h, WIDTH - 200)
            for line in lines_h:
                bbox = draw.textbbox((0, 0), line, font=font_h)
                tw = bbox[2] - bbox[0]
                x = (WIDTH - tw) // 2
                draw.text((x + 2, y_pos + 2), line, fill=(0, 0, 0, 200), font=font_h)
                draw.text((x, y_pos), line, fill=(255, 255, 255, 255), font=font_h)
                y_pos += 70

        if body:
            font_b = self._get_font(32)
            lines = self._wrap_text(body, font_b, WIDTH - 200)
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font_b)
                tw = bbox[2] - bbox[0]
                x = (WIDTH - tw) // 2
                draw.text((x + 2, y_pos + 2), line, fill=(0, 0, 0, 180), font=font_b)
                draw.text((x, y_pos), line, fill=(255, 255, 255, 230), font=font_b)
                y_pos += 42

        img.save(overlay_png)
        return self._overlay_on_video(video_path, overlay_png, duration, output_path, effects=effects)

    def compose_stat_overlay(
        self,
        video_path: str,
        value: str,
        label: str,
        subtitle: str = "",
        duration: float | None = None,
        output_path: str | None = None,
        effects: list[str] | None = None,
    ) -> str:
        """Overlay a large stat value + label centered on stock footage."""
        output_path = output_path or self._gen_output_path("stat")
        overlay_png = self._gen_output_path("overlay").replace(".mp4", ".png")

        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        scrim = _gradient_scrim(direction="center", opacity=170)
        img = Image.alpha_composite(img, scrim)
        draw = ImageDraw.Draw(img)

        # Big stat value
        font_val = self._get_font(80)
        bbox = draw.textbbox((0, 0), value, font=font_val)
        tw = bbox[2] - bbox[0]
        y = HEIGHT // 2 - 80
        x = (WIDTH - tw) // 2
        draw.text((x + 3, y + 3), value, fill=(0, 0, 0, 200), font=font_val)
        draw.text((x, y), value, fill=(255, 255, 255, 255), font=font_val)

        # Label
        font_lbl = self._get_font(36)
        bbox = draw.textbbox((0, 0), label, font=font_lbl)
        tw = bbox[2] - bbox[0]
        y += 100
        x = (WIDTH - tw) // 2
        draw.text((x + 2, y + 2), label, fill=(0, 0, 0, 180), font=font_lbl)
        draw.text((x, y), label, fill=(255, 255, 255, 230), font=font_lbl)

        if subtitle:
            font_sub = self._get_font(24)
            bbox = draw.textbbox((0, 0), subtitle, font=font_sub)
            tw = bbox[2] - bbox[0]
            y += 55
            x = (WIDTH - tw) // 2
            draw.text((x + 1, y + 1), subtitle, fill=(0, 0, 0, 150), font=font_sub)
            draw.text((x, y), subtitle, fill=(255, 255, 255, 180), font=font_sub)

        img.save(overlay_png)
        return self._overlay_on_video(video_path, overlay_png, duration, output_path, effects=effects)

    def compose_quote_overlay(
        self,
        video_path: str,
        quote: str,
        attribution: str = "",
        duration: float | None = None,
        output_path: str | None = None,
        effects: list[str] | None = None,
    ) -> str:
        """Overlay a styled quote with attribution on stock footage."""
        output_path = output_path or self._gen_output_path("quote")
        overlay_png = self._gen_output_path("overlay").replace(".mp4", ".png")

        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        scrim = _gradient_scrim(direction="center", opacity=160)
        img = Image.alpha_composite(img, scrim)
        draw = ImageDraw.Draw(img)

        # Opening quote mark
        font_q_mark = self._get_font(100)
        draw.text((150, HEIGHT // 2 - 160), "\u201C", fill=(233, 69, 96, 120), font=font_q_mark)

        # Quote text (wrapped)
        font_q = self._get_font(36)
        lines = self._wrap_text(quote, font_q, WIDTH - 400)
        y = HEIGHT // 2 - 60
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_q)
            tw = bbox[2] - bbox[0]
            x = (WIDTH - tw) // 2
            draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 180), font=font_q)
            draw.text((x, y), line, fill=(255, 255, 255, 255), font=font_q)
            y += 48

        if attribution:
            font_attr = self._get_font(24)
            attr_text = f"\u2014 {attribution}"
            bbox = draw.textbbox((0, 0), attr_text, font=font_attr)
            tw = bbox[2] - bbox[0]
            x = (WIDTH - tw) // 2
            y += 20
            draw.text((x, y), attr_text, fill=(255, 255, 255, 180), font=font_attr)

        img.save(overlay_png)
        return self._overlay_on_video(video_path, overlay_png, duration, output_path, effects=effects)

    def compose_social_card(
        self,
        video_path: str,
        platform: str = "reddit",
        username: str = "u/anonymous",
        post_title: str = "",
        body: str = "",
        upvotes: int = 0,
        comments: int = 0,
        subreddit: str = "",
        duration: float | None = None,
        output_path: str | None = None,
        effects: list[str] | None = None,
    ) -> str:
        """Render a social media card (Reddit/Twitter style) over stock footage."""
        output_path = output_path or self._gen_output_path("social")
        overlay_png = self._gen_output_path("overlay").replace(".mp4", ".png")

        img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        # Gradient scrim for card readability
        scrim = _gradient_scrim(direction="center", opacity=180)
        img = Image.alpha_composite(img, scrim)
        draw = ImageDraw.Draw(img)

        # Card dimensions
        card_w, card_h = 1200, 500
        card_x = (WIDTH - card_w) // 2
        card_y = (HEIGHT - card_h) // 2

        # Rounded card background
        card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card)
        card_draw.rounded_rectangle(
            [(0, 0), (card_w, card_h)],
            radius=20,
            fill=(26, 26, 46, 230),
            outline=(60, 60, 90, 200),
            width=2,
        )

        # Platform header
        font_sm = self._get_font(20)
        font_user = self._get_font(22)
        font_title = self._get_font(32)
        font_body = self._get_font(24)
        font_meta = self._get_font(18)

        y = 30
        if subreddit:
            card_draw.text((30, y), subreddit, fill=(100, 180, 255, 255), font=font_sm)
            y += 30
        card_draw.text((30, y), username, fill=(180, 180, 200, 255), font=font_user)
        y += 40

        # Post title
        if post_title:
            lines = self._wrap_text(post_title, font_title, card_w - 60)
            for line in lines[:4]:
                card_draw.text((30, y), line, fill=(255, 255, 255, 255), font=font_title)
                y += 42

        # Body text
        if body:
            y += 10
            lines = self._wrap_text(body, font_body, card_w - 60)
            for line in lines[:3]:
                card_draw.text((30, y), line, fill=(200, 200, 210, 230), font=font_body)
                y += 32

        # Upvotes / comments footer
        y = card_h - 50
        meta_parts = []
        if upvotes:
            meta_parts.append(f"▲ {upvotes:,}")
        if comments:
            meta_parts.append(f"💬 {comments:,}")
        meta_text = "   ".join(meta_parts)
        if meta_text:
            card_draw.text((30, y), meta_text, fill=(150, 150, 170, 200), font=font_meta)

        img.paste(card, (card_x, card_y), card)
        img.save(overlay_png)
        return self._overlay_on_video(video_path, overlay_png, duration, output_path, effects=effects)

    # ── Background Generators ─────────────────────────────────────────

    def generate_solid_background(
        self,
        duration: float = 8.0,
        color: str = "0x1a1a2e",
        output_path: str | None = None,
    ) -> str:
        """Generate a solid-color background video (fallback)."""
        output_path = output_path or self._gen_output_path("solid_bg")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"color=c={color}:s=1920x1080:r=30:d={duration}",
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            output_path,
        ]
        self._exec(cmd, output_path)
        return os.path.abspath(output_path)
    def image_to_video(
        self,
        image_path: str,
        duration: float = 8.0,
        output_path: str | None = None,
    ) -> str:
        """Convert a static image to a video with Ken Burns zoom effect.

        Scales the image up and applies a slow zoom-pan to create cinematic
        motion from a still photo. Used for Wikimedia Commons images.
        """
        output_path = output_path or self._gen_output_path("img_video")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        frames = int(duration * 30)
        # Ken Burns: slow zoom 1.0x → 1.10x, centered
        vf = (
            f"scale=3840:2160,"
            f"zoompan=z='1+0.10*on/{max(frames, 1)}':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
            f":d={frames}:s=1920x1080:fps=30,"
            f"eq=contrast=1.08:saturation=0.92:brightness=0.02"
        )

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-vf", vf,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", "30",
            "-t", str(duration),
            output_path,
        ]
        self._exec(cmd, output_path)
        return os.path.abspath(output_path)


    # ── Internal helpers ──────────────────────────────────────────────

    def _overlay_on_video(
        self,
        video_path: str,
        overlay_png: str,
        duration: float | None,
        output_path: str,
        effects: list[str] | None = None,
    ) -> str:
        """Overlay a PNG image on a video using FFmpeg overlay filter.

        Applies user-selected effects, or default color grade if none specified.
        """
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        dur = duration or 8.0

        # Build effects filter chain
        if effects is not None and len(effects) > 0:
            effects_str = self.build_effects_filter(effects, dur)
            if effects_str:
                vf = (
                    f"[0:v]scale=1920:1080[bg];"
                    f"[bg][1:v]overlay=0:0,"
                    f"{effects_str}"
                )
            else:
                vf = f"[0:v]scale=1920:1080[bg];[bg][1:v]overlay=0:0"
        elif effects is not None:
            # Empty list = no effects
            vf = f"[0:v]scale=1920:1080[bg];[bg][1:v]overlay=0:0"
        else:
            # None = default color grade
            vf = (
                f"[0:v]scale=1920:1080[bg];"
                f"[bg][1:v]overlay=0:0,"
                f"eq=contrast=1.08:saturation=0.92:brightness=0.02"
            )

        cmd = ["ffmpeg", "-y"]
        if duration:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", video_path]
        cmd += ["-i", overlay_png]
        cmd += ["-filter_complex", vf]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        cmd += ["-r", "30"]
        cmd += ["-t", str(dur)]
        cmd += [output_path]

        self._exec(cmd, output_path)

        try:
            os.unlink(overlay_png)
        except OSError:
            pass

        return os.path.abspath(output_path)
    def _apply_effects_only(
        self,
        video_path: str,
        duration: float | None,
        effects: list[str],
        output_path: str | None = None,
    ) -> str:
        """Apply effects to a video without any text overlay or scrim."""
        output_path = output_path or self._gen_output_path("fx")
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        dur = duration or 8.0

        effects_str = self.build_effects_filter(effects, dur)
        vf = f"scale=1920:1080"
        if effects_str:
            vf += f",{effects_str}"

        cmd = ["ffmpeg", "-y"]
        if duration:
            cmd += ["-stream_loop", "-1"]
        cmd += ["-i", video_path]
        cmd += ["-vf", vf]
        cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        cmd += ["-r", "30"]
        cmd += ["-t", str(dur)]
        cmd += [output_path]

        self._exec(cmd, output_path)
        return os.path.abspath(output_path)

    def _exec(self, cmd: list[str], output_path: str) -> None:
        """Execute an FFmpeg command."""
        logger.info("FFmpeg: %s", " ".join(cmd))
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as exc:
            raise CompositionError(
                error_output=exc.stderr or exc.stdout or str(exc),
                command=" ".join(cmd),
            ) from exc

    def _gen_output_path(self, prefix: str) -> str:
        uid = uuid.uuid4().hex[:8]
        return os.path.join(self._output_dir, f"{prefix}_{uid}.mp4")

    @staticmethod
    def _get_font(size: int) -> ImageFont.FreeTypeFont:
        """Get a font, trying system paths then falling back to default."""
        font_paths = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNSText.ttf",
            "/System/Library/Fonts/SFNS.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
        for fp in font_paths:
            if os.path.isfile(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    @staticmethod
    def _wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
        """Word-wrap text to fit within max_width pixels."""
        words = text.replace("\n", " ").split()
        lines: list[str] = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            bbox = font.getbbox(test)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]

    @staticmethod
    def _position_to_y(position: str) -> int:
        """Convert position name to pixel Y coordinate."""
        positions = {
            "top": int(HEIGHT * 0.15),
            "center": HEIGHT // 2 - 60,
            "bottom": int(HEIGHT * 0.72),
        }
        return positions.get(position, HEIGHT // 2 - 60)
