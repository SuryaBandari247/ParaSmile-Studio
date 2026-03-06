"""Documentary palette — shared visual constants for all effect templates.

Based on TradingView Lightweight Charts dark theme color system.
Source: https://tradingview.github.io/lightweight-charts/docs/api/

Calm Capitalist house style: dark background (#131722), TradingView blue primary,
Inter font, editorial layout. Designed for YouTube 1080p readability.

Change colors/sizes here and every effect template picks them up.
"""

# ── Font ──
FONT = "Inter"

# ── Background ──
BG = "#131722"          # TradingView dark theme background

# ── Text hierarchy ──
TXT_PRI = "#D1D4DC"     # title — TradingView dark theme textColor
TXT_SEC = "#B2B5BE"     # subtitle — lighter muted
TXT_MUT = "#787B86"     # axis labels — TradingView scale text muted

# ── Axes & grid ──
AX_COL = "#363A45"      # axis lines — TradingView dark scale line
GRD_COL = "#2B2B43"     # grid lines — TradingView dark separator
GRD_OPACITY = 0.6

# ── Primary line ──
LINE_COL = "#2962FF"    # TradingView signature blue
LINE_WIDTH = 6

# ── Accents (use sparingly) ──
ACCENT_POS = "#26A69A"  # TradingView candle up — teal
ACCENT_NEG = "#EF5350"  # TradingView candle down — red

# ── Area fill ──
AREA_TOP = "#2962FF"    # area gradient top (use with ~0.28 opacity)
AREA_BOT = "#2962FF"    # area gradient bottom (use with ~0.00 opacity)

# ── Shock / event markers ──
SMK_TEXT = "#FF9800"     # shock marker text — amber (pops on dark bg)
SMK_BORDER = "#FF9800"  # shock marker border — amber

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
        # ── TradingView dark palette (auto-injected) ──
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
