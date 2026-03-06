"""Render CALM CAPITALIST intro — dark glassmorphism reveal.

Dark editorial background (Slate-900) with frosted-glass text that
materialises through animated light. The glass has real depth:
  - Subtle animated aurora/gradient field behind text (gives glass
    something to refract)
  - Frosted glass fill with inner blur
  - Embossed edges with specular highlights
  - Sweeping light bar across the glass
  - Soft outer glow bloom

Frames → ffmpeg → 1080p/30fps MP4, ~5 seconds.

Usage:
    venv/bin/python scripts/render_calm_capitalist_intro.py
"""

import os
import shutil
import subprocess
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Config ──
W, H = 1920, 1080
FPS = 30
DURATION = 4.0
TOTAL_FRAMES = int(FPS * DURATION)
FONT_PATH = os.path.expanduser("~/Library/Fonts/Montserrat-Bold.ttf")
OUT_DIR = "output/renders/intro"
FRAMES_DIR = f"{OUT_DIR}/frames"

# ── Palette (pure black + white) ──
BG_COLOR = (0, 0, 0)           # pure black
GLASS_BASE = (20, 20, 25)      # near-black glass fill
GLASS_EDGE_HI = (200, 200, 210)  # bright highlight edge
GLASS_EDGE_SH = (0, 0, 0)     # shadow edge
ACCENT_BLUE = (41, 98, 255)    # #2962FF subtle aurora accent
ACCENT_TEAL = (38, 166, 154)   # #26A69A subtle aurora accent
TEXT_WHITE = (255, 255, 255)    # pure white


def make_two_line_mask(line1: str, line2: str, font_size: int, gap: int = 30) -> Image.Image:
    """Render two centered lines as a white-on-black alpha mask."""
    font = ImageFont.truetype(FONT_PATH, font_size)
    tmp = Image.new("L", (1, 1), 0)
    d = ImageDraw.Draw(tmp)

    b1 = d.textbbox((0, 0), line1, font=font)
    b2 = d.textbbox((0, 0), line2, font=font)
    tw1, th1 = b1[2] - b1[0], b1[3] - b1[1]
    tw2, th2 = b2[2] - b2[0], b2[3] - b2[1]

    total_h = th1 + gap + th2
    y_start = (H - total_h) // 2

    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    draw.text(((W - tw1) // 2 - b1[0], y_start - b1[1]), line1, fill=255, font=font)
    draw.text(((W - tw2) // 2 - b2[0], y_start + th1 + gap - b2[1]), line2, fill=255, font=font)
    return mask


def make_aurora_field(time_s: float, intensity: float) -> Image.Image:
    """Generate a subtle animated color field — gives the glass something to refract.

    Two soft blobs of blue/teal drift slowly. This is what makes the glass
    look alive rather than flat.
    """
    field = Image.new("RGB", (W, H), BG_COLOR)
    if intensity <= 0:
        return field

    arr = np.array(field, dtype=np.float32)

    # Coordinate grids (normalised 0-1)
    ys = np.linspace(0, 1, H)[:, None]
    xs = np.linspace(0, 1, W)[None, :]

    # Blob 1: blue, drifts right-to-left
    cx1 = 0.5 + 0.15 * math.sin(time_s * 0.4)
    cy1 = 0.45 + 0.05 * math.cos(time_s * 0.3)
    d1 = ((xs - cx1) ** 2) / 0.08 + ((ys - cy1) ** 2) / 0.06
    blob1 = np.exp(-d1) * intensity

    # Blob 2: teal, drifts opposite
    cx2 = 0.5 - 0.12 * math.cos(time_s * 0.35)
    cy2 = 0.55 + 0.04 * math.sin(time_s * 0.45)
    d2 = ((xs - cx2) ** 2) / 0.06 + ((ys - cy2) ** 2) / 0.08
    blob2 = np.exp(-d2) * intensity * 0.7

    # Apply color — very subtle on black, just enough to give glass something
    arr[:, :, 0] += blob1 * ACCENT_BLUE[0] * 0.15
    arr[:, :, 1] += blob1 * ACCENT_BLUE[1] * 0.15
    arr[:, :, 2] += blob1 * ACCENT_BLUE[2] * 0.15

    arr[:, :, 0] += blob2 * ACCENT_TEAL[0] * 0.12
    arr[:, :, 1] += blob2 * ACCENT_TEAL[1] * 0.12
    arr[:, :, 2] += blob2 * ACCENT_TEAL[2] * 0.12

    arr = np.clip(arr, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def create_glass_frame(
    text_mask: Image.Image,
    bg: Image.Image,
    reveal: float,
    sweep_x: float | None,
    glow_strength: float,
) -> Image.Image:
    """Render one frame of the dark glassmorphism effect."""
    frame = bg.copy().convert("RGBA")
    mask_arr = np.array(text_mask).astype(np.float32) / 255.0

    if reveal <= 0:
        return frame.convert("RGB")

    # Scale mask by reveal progress
    revealed_mask = text_mask.point(lambda p: int(p * reveal))
    rmask_arr = mask_arr * reveal

    # ── 1. Frosted glass body ──
    # Sample the background behind the text, blur it (frosted glass refraction)
    frost_src = bg.copy().filter(ImageFilter.GaussianBlur(radius=20))
    # Brighten the frosted area significantly — text should read as white
    frost_arr = np.array(frost_src, dtype=np.float32)
    frost_arr = frost_arr * 2.5 + 180
    frost_arr = np.clip(frost_arr, 0, 255).astype(np.uint8)
    frost_src = Image.fromarray(frost_arr)

    glass_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    frost_rgba = frost_src.convert("RGBA")
    # Set alpha from text mask
    frost_alpha = (rmask_arr * 200).clip(0, 255).astype(np.uint8)  # ~78% opacity
    r, g, b, _ = frost_rgba.split()
    frost_rgba = Image.merge("RGBA", (r, g, b, Image.fromarray(frost_alpha)))
    frame = Image.alpha_composite(frame, frost_rgba)

    # ── 2. Glass tint overlay (push toward white) ──
    tint_layer = Image.new("RGBA", (W, H), (220, 225, 235, 0))
    tint_alpha = (rmask_arr * 60).clip(0, 255).astype(np.uint8)
    tint_layer.putalpha(Image.fromarray(tint_alpha))
    frame = Image.alpha_composite(frame, tint_layer)

    # ── 3. Embossed edges ──
    if reveal > 0.15:
        bevel = min(1.0, (reveal - 0.15) / 0.4)

        # Top-left highlight
        hl_shifted = Image.new("L", (W, H), 0)
        hl_shifted.paste(text_mask, (-2, -2))
        hl_edge = np.clip(
            np.array(text_mask, dtype=np.int16) - np.array(hl_shifted, dtype=np.int16),
            0, 255,
        ).astype(np.uint8)
        hl_edge = Image.fromarray(hl_edge).filter(ImageFilter.GaussianBlur(1.5))
        hl_layer = Image.new("RGBA", (W, H), (*GLASS_EDGE_HI, 0))
        hl_a = (np.array(hl_edge, dtype=np.float32) * bevel * 0.7).clip(0, 255).astype(np.uint8)
        hl_layer.putalpha(Image.fromarray(hl_a))
        frame = Image.alpha_composite(frame, hl_layer)

        # Bottom-right shadow
        sh_shifted = Image.new("L", (W, H), 0)
        sh_shifted.paste(text_mask, (2, 2))
        sh_edge = np.clip(
            np.array(text_mask, dtype=np.int16) - np.array(sh_shifted, dtype=np.int16),
            0, 255,
        ).astype(np.uint8)
        sh_edge = Image.fromarray(sh_edge).filter(ImageFilter.GaussianBlur(1.5))
        sh_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sh_a = (np.array(sh_edge, dtype=np.float32) * bevel * 0.5).clip(0, 255).astype(np.uint8)
        sh_layer.putalpha(Image.fromarray(sh_a))
        frame = Image.alpha_composite(frame, sh_layer)

    # ── 4. Inner noise texture (frosted glass grain) ──
    if reveal > 0.25:
        frost_t = min(1.0, (reveal - 0.25) / 0.4)
        noise = np.random.RandomState(42).randint(0, 20, (H, W), dtype=np.uint8)
        noise = Image.fromarray(noise).filter(ImageFilter.GaussianBlur(1.5))
        noise_layer = Image.new("RGBA", (W, H), (200, 210, 230, 0))
        n_a = (np.array(noise, dtype=np.float32) * rmask_arr * frost_t * 0.4).clip(0, 255).astype(np.uint8)
        noise_layer.putalpha(Image.fromarray(n_a))
        frame = Image.alpha_composite(frame, noise_layer)

    # ── 5. Specular sweep ──
    if sweep_x is not None:
        sweep_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        bar_w = 160
        xs = np.arange(W, dtype=np.float32)
        dist = np.abs(xs - sweep_x) / (bar_w / 2)
        intensity = np.exp(-3.0 * dist * dist)
        # Build full-frame sweep
        sweep_band = np.zeros((H, W, 4), dtype=np.uint8)
        alpha_row = (intensity * 160 * reveal).clip(0, 255).astype(np.uint8)
        for c in range(3):
            sweep_band[:, :, c] = 255
        sweep_band[:, :, 3] = alpha_row[None, :]
        # Mask to text
        sweep_band[:, :, 3] = (sweep_band[:, :, 3].astype(np.float32) * rmask_arr).astype(np.uint8)
        sweep_layer = Image.fromarray(sweep_band)
        frame = Image.alpha_composite(frame, sweep_layer)

    # ── 6. Outer glow bloom ──
    if glow_strength > 0:
        glow_mask = text_mask.filter(ImageFilter.GaussianBlur(radius=25))
        glow_arr = np.array(glow_mask, dtype=np.float32) - np.array(text_mask, dtype=np.float32) * 0.5
        glow_arr = np.clip(glow_arr, 0, 255)
        # Blue-tinted glow
        glow_layer = Image.new("RGBA", (W, H), (ACCENT_BLUE[0], ACCENT_BLUE[1], min(255, ACCENT_BLUE[2] + 40), 0))
        g_a = (glow_arr * glow_strength * 0.2).clip(0, 255).astype(np.uint8)
        glow_layer.putalpha(Image.fromarray(g_a))
        frame = Image.alpha_composite(frame, glow_layer)

    # ── 7. Thin bright edge line (glass rim catch) ──
    if reveal > 0.6:
        rim_t = min(1.0, (reveal - 0.6) / 0.3)
        dilated = text_mask.filter(ImageFilter.MaxFilter(3))
        rim = np.clip(
            np.array(dilated, dtype=np.int16) - np.array(text_mask, dtype=np.int16),
            0, 255,
        ).astype(np.uint8)
        rim = Image.fromarray(rim).filter(ImageFilter.GaussianBlur(0.8))
        rim_layer = Image.new("RGBA", (W, H), (*TEXT_WHITE, 0))
        r_a = (np.array(rim, dtype=np.float32) * rim_t * 0.25).clip(0, 255).astype(np.uint8)
        rim_layer.putalpha(Image.fromarray(r_a))
        frame = Image.alpha_composite(frame, rim_layer)

    return frame.convert("RGB")


def ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


def ease_in_out_sine(t: float) -> float:
    return -(math.cos(math.pi * t) - 1) / 2


def ease_out_expo(t: float) -> float:
    return 1.0 if t >= 1.0 else 1.0 - 2.0 ** (-10.0 * t)


def render_all_frames():
    """Generate all frames for the intro animation.

    Timeline (4s total):
      0.0–0.4s   Dark BG fades in, aurora begins
      0.4–1.7s   Glass text materialises (reveal 0→1)
      1.7–2.8s   Specular sweep crosses left→right
      2.8–4.0s   Hold with glow pulse
    """
    os.makedirs(FRAMES_DIR, exist_ok=True)

    for f in os.listdir(FRAMES_DIR):
        if f.endswith(".png"):
            os.remove(os.path.join(FRAMES_DIR, f))

    text_mask = make_two_line_mask("CALM", "CAPITALIST", font_size=150, gap=45)

    print(f"Rendering {TOTAL_FRAMES} frames at {W}x{H} @ {FPS}fps...")

    for i in range(TOTAL_FRAMES):
        time_s = i / FPS

        # ── Aurora intensity (background light field) ──
        if time_s < 0.4:
            aurora_i = ease_out_cubic(time_s / 0.4) * 0.6
        elif time_s < 1.7:
            aurora_i = 0.6 + ease_out_cubic((time_s - 0.4) / 1.3) * 0.4
        else:
            aurora_i = 1.0

        bg = make_aurora_field(time_s, aurora_i)

        # ── Reveal progress ──
        if time_s < 0.4:
            reveal = 0.0
        elif time_s < 1.7:
            reveal = ease_out_expo((time_s - 0.4) / 1.3)
        else:
            reveal = 1.0

        # ── Specular sweep (slower, softer) ──
        sweep_x = None
        if 1.7 <= time_s <= 3.3:
            sweep_t = (time_s - 1.7) / 1.6
            sweep_x = -150 + ease_in_out_sine(sweep_t) * (W + 300)

        # ── Glow bloom ──
        if time_s < 1.5:
            glow = 0.0
        elif time_s < 2.8:
            glow = ease_out_cubic((time_s - 1.5) / 1.3) * 0.8
        else:
            pulse = 0.5 + 0.15 * math.sin((time_s - 2.8) * 2.5)
            glow = 0.8 * pulse + 0.4

        frame = create_glass_frame(text_mask, bg, reveal, sweep_x, glow)
        frame.save(os.path.join(FRAMES_DIR, f"frame_{i:04d}.png"))

        if (i + 1) % 30 == 0 or i == TOTAL_FRAMES - 1:
            print(f"  Frame {i + 1}/{TOTAL_FRAMES}")

    print("All frames rendered.")


def stitch_video():
    """Combine frames into MP4 using ffmpeg."""
    output_path = os.path.join(OUT_DIR, "calm_capitalist_intro.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(FRAMES_DIR, "frame_%04d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "18",
        "-preset", "slow",
        "-movflags", "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    print(f"\n✅ Intro rendered: {output_path}")

    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", output_path],
        capture_output=True, text=True,
    )
    print(f"   Duration: {result.stdout.strip()}s")
    print(f"   Resolution: {W}x{H} @ {FPS}fps")


if __name__ == "__main__":
    media_dir = os.path.join(OUT_DIR, "media")
    if os.path.exists(media_dir):
        shutil.rmtree(media_dir)

    render_all_frames()
    stitch_video()

    shutil.rmtree(FRAMES_DIR)
    print("   Frames cleaned up.")
