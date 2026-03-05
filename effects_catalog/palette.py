"""Documentary palette — shared visual constants for all effect templates.

Calm Capitalist house style: white background, deep blue primary,
Inter font, editorial layout. Designed for YouTube 1080p readability.

Change colors/sizes here and every effect template picks them up.
"""

# ── Font ──
FONT = "Inter"

# ── Background ──
BG = "#FFFFFF"

# ── Text hierarchy ──
TXT_PRI = "#111827"   # title — near black
TXT_SEC = "#374151"   # subtitle — slate gray
TXT_MUT = "#6B7280"   # axis labels, muted text

# ── Axes & grid ──
AX_COL = "#9CA3AF"    # axis lines — mid gray
GRD_COL = "#E5E7EB"   # grid lines — soft neutral
GRD_OPACITY = 0.6

# ── Primary line ──
LINE_COL = "#2563EB"   # deep blue — authoritative
LINE_WIDTH = 6

# ── Accents (use sparingly) ──
ACCENT_POS = "#10B981"  # emerald — positive
ACCENT_NEG = "#EF4444"  # red — negative

# ── Shock / event markers ──
SMK_TEXT = "#C2410C"    # shock marker text — dark orange
SMK_BORDER = "#F97316"  # shock marker border — orange highlight

# ── Font sizes (YouTube-optimized) ──
FS_TITLE = 44
FS_SUBTITLE = 22
FS_ANNOTATION = 18
FS_AXIS = 16
FS_BADGE = 18
FS_SOURCE = 14
FS_LABEL = 14          # small labels (regime zones, etc.)

# ── Layout ──
TITLE_BUFF_TOP = 0.3
TITLE_BUFF_LEFT = 0.55
CHART_SHIFT = "DOWN * 0.55 + RIGHT * 0.15"

# ── Multi-series palette (for charts with multiple lines) ──
SERIES_COLORS = [
    "#2563EB",  # deep blue
    "#10B981",  # emerald
    "#F59E0B",  # amber
    "#EF4444",  # red
    "#8B5CF6",  # violet
    "#06B6D4",  # cyan
    "#F97316",  # orange
    "#EC4899",  # pink
]


def manim_palette_block() -> str:
    """Return a block of Python code that injects palette constants into a Manim scene.

    Templates embed this at the top of construct() so every scene has
    the same visual language without importing at render time.
    """
    return f'''
        # ── Documentary palette (auto-injected) ──
        FONT = "{FONT}"
        BG = "{BG}"
        TP = "{TXT_PRI}"
        TS = "{TXT_SEC}"
        TM = "{TXT_MUT}"
        AC = "{AX_COL}"
        GC = "{GRD_COL}"
        GC_OP = {GRD_OPACITY}
        LC = "{LINE_COL}"
        LW = {LINE_WIDTH}
        AP = "{ACCENT_POS}"
        AN = "{ACCENT_NEG}"
        SMT = "{SMK_TEXT}"
        SMB = "{SMK_BORDER}"
'''
