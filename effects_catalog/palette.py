"""Documentary palette — shared visual constants for all effect templates.

D3 narrative chart style — Slate-900 dark editorial background with
TradingView signature blue primary line. Designed for YouTube 1080p readability.

Change colors/sizes here and every effect template picks them up.
"""

# ── Font ──
FONT = "Inter"

# ── Background ──
BG = "#0F172A"          # Slate-900 dark editorial background

# ── Text hierarchy ──
TXT_PRI = "#F8FAFC"     # title — bright white
TXT_SEC = "#94A3B8"     # subtitle — slate-400
TXT_MUT = "#64748B"     # axis labels, source — slate-500

# ── Axes & grid ──
AX_COL = "#334155"      # axis lines — slate-700
GRD_COL = "#1E293B"     # grid lines — slate-800
GRD_OPACITY = 0.6

# ── Primary line ──
LINE_COL = "#2962FF"    # TradingView signature blue
LINE_WIDTH = 6

# ── Accents (use sparingly) ──
ACCENT_POS = "#10B981"  # emerald-500 (up/positive)
ACCENT_NEG = "#EF4444"  # red-500 (down/negative)

# ── Area fill ──
AREA_TOP = "#2962FF"    # area gradient top (use with ~0.28 opacity)
AREA_BOT = "#2962FF"    # area gradient bottom (use with ~0.00 opacity)

# ── Shock / event markers ──
SMK_TEXT = "#EF4444"     # red for shock labels
SMK_BORDER = "#EF4444"  # red border

# ── Font sizes (YouTube-optimized) ──
FS_TITLE = 44
FS_SUBTITLE = 22
FS_ANNOTATION = 18
FS_AXIS = 16
FS_BADGE = 18
FS_SOURCE = 14
FS_LABEL = 14           # small labels (regime zones, etc.)

# ── Layout ──
TITLE_BUFF_TOP = 0.3
TITLE_BUFF_LEFT = 0.55
CHART_SHIFT = "DOWN * 0.55 + RIGHT * 0.15"

# ── Multi-series palette (TradingView-inspired, bright on dark) ──
SERIES_COLORS = [
    "#2962FF",  # TradingView blue
    "#26A69A",  # teal (up)
    "#FF9800",  # orange
    "#EF5350",  # red (down)
    "#AB47BC",  # purple
    "#26C6DA",  # cyan
    "#FF7043",  # deep orange
    "#EC407A",  # pink
]


def manim_palette_block() -> str:
    """Return a block of Python code that injects palette constants into a Manim scene."""
    return f'''
        # ── D3 narrative dark palette (auto-injected) ──
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
