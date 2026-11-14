"""Composition tokens: how each design system *composes* a slide, beyond colours and fonts.

A design system here is a set of rules (where the title goes, what shape language cards use, how
images are treated, which ornament marks the slide, which transition plays). The layout solver reads
these rules, so two systems produce structurally different slides rather than recolours.
"""
from dataclasses import dataclass

from services.design_systems import get_design_system

SAFE_SANS = "Calibri"
SAFE_SERIF = "Georgia"
SAFE_MONO = "Consolas"


SERIF_NAMES = ("playfair", "georgia", "garamond", "didot", "times", "baskerville", "cormorant", "source serif", "merriweather",
               "lora", "libre baskerville", "crimson", "spectral", "bodoni", "charter")
MONO_NAMES = ("mono", "courier", "consolas", "jetbrains", "fira code", "menlo", "sf mono", "space mono", "ibm plex mono")


def pick_font(stack: str, role: str = "sans") -> str:
    """PowerPoint needs one installed family. Decide serif/sans/mono from the first family, then the generic."""
    fams = [f.strip().lower() for f in (stack or "").split(",") if f.strip()]
    if not fams:
        return SAFE_SANS
    first = fams[0]
    if any(k in first for k in MONO_NAMES):
        return SAFE_MONO
    if any(k in first for k in SERIF_NAMES):
        return SAFE_SERIF
    if first in ("serif",):
        return SAFE_SERIF
    if first in ("monospace",):
        return SAFE_MONO
    return SAFE_SANS


def font_kind(font: str):
    return True if font == SAFE_SERIF else ('mono' if font == SAFE_MONO else False)


@dataclass(frozen=True)
class Comp:
    title_place: str      # top | rail | center | band
    card_style: str       # filled | outline | underline | accent | glass
    ornament: str         # rule | block | stripe | dots | corner | none
    image_style: str      # framed | bleed | overlay
    title_max: int        # largest title size (pt)
    gap: float            # base spacing multiplier
    transition: str       # fade | push | wipe | none
    entrance: str         # fade | wipe
    uppercase_kicker: bool = True
    number_style: str = "solid"   # solid | outline | plain
    mirror: bool = False          # image/text sides flipped on odd slides


COMP = {
    "linear_dark":          Comp("top", "outline", "block", "framed", 46, 1.0, "fade", "fade", True, "solid"),
    "stripe_scale":         Comp("top", "filled", "rule", "framed", 44, 1.0, "fade", "wipe", True, "solid"),
    "pitch_deck":           Comp("top", "filled", "block", "overlay", 48, 1.0, "push", "fade", True, "solid"),
    "pitch_venture":        Comp("top", "filled", "block", "overlay", 48, 1.0, "push", "fade", True, "solid"),
    "deeptech_emerald":     Comp("top", "filled", "dots", "framed", 44, 1.0, "fade", "wipe", True, "solid"),
    "swiss_minimal":        Comp("rail", "underline", "rule", "framed", 40, 1.0, "fade", "wipe", True, "plain"),
    "swiss_bauhaus":        Comp("rail", "underline", "rule", "framed", 40, 1.0, "fade", "wipe", True, "plain"),
    "apple_keynote":        Comp("center", "glass", "none", "overlay", 54, 1.15, "fade", "fade", False, "outline"),
    "editorial_magazine":   Comp("top", "underline", "rule", "framed", 44, 1.0, "fade", "fade", False, "plain", True),
    "editorial_monocle":    Comp("top", "underline", "rule", "framed", 44, 1.0, "fade", "fade", False, "plain", True),
    "brutalist":            Comp("band", "outline", "block", "framed", 44, 0.9, "none", "wipe", True, "solid"),
    "brutalist_raw":        Comp("band", "outline", "block", "framed", 44, 0.9, "none", "wipe", True, "solid"),
    "japanese_minimalism":  Comp("rail", "underline", "stripe", "framed", 36, 1.3, "fade", "fade", False, "plain"),
    "startup_pitch":        Comp("top", "filled", "block", "overlay", 48, 1.0, "push", "fade", True, "solid"),
    "financial_analyst":    Comp("band", "filled", "none", "framed", 36, 0.9, "fade", "wipe", True, "solid"),
    "academic_research":    Comp("top", "outline", "rule", "framed", 38, 0.95, "fade", "fade", False, "plain"),
    "architecture_portfolio": Comp("rail", "outline", "stripe", "bleed", 42, 1.1, "wipe", "wipe", True, "outline"),
    "creative_agency":      Comp("top", "accent", "corner", "bleed", 52, 1.0, "push", "wipe", True, "solid", True),
    "cybersecurity":        Comp("band", "outline", "dots", "overlay", 38, 0.9, "wipe", "wipe", True, "outline"),
    "cyber_terminal":       Comp("band", "outline", "dots", "overlay", 38, 0.9, "wipe", "wipe", True, "outline"),
    "futuristic_ai":        Comp("center", "glass", "dots", "overlay", 48, 1.1, "fade", "fade", True, "outline"),
    "luxury_brand":         Comp("center", "outline", "rule", "bleed", 46, 1.25, "fade", "fade", True, "plain"),
    "luxury_maison":        Comp("center", "outline", "rule", "bleed", 46, 1.25, "fade", "fade", True, "plain"),
    "education_modern":     Comp("top", "accent", "block", "framed", 44, 1.0, "push", "fade", False, "solid", True),
    "documentary_storytelling": Comp("rail", "glass", "none", "bleed", 46, 1.1, "fade", "fade", False, "outline"),
    "corporate_premium":    Comp("band", "filled", "stripe", "framed", 38, 1.0, "fade", "fade", True, "solid"),
    "data_storytelling":    Comp("top", "filled", "rule", "framed", 40, 0.95, "fade", "wipe", True, "solid"),
    "dark_technology":      Comp("top", "glass", "dots", "overlay", 44, 1.0, "wipe", "wipe", True, "outline"),
    "nordic_frost":         Comp("rail", "underline", "rule", "framed", 40, 1.05, "fade", "wipe", True, "plain"),
    "tokyo_neon":           Comp("top", "outline", "dots", "overlay", 46, 1.0, "wipe", "wipe", True, "outline"),
    "california_warmth":    Comp("top", "filled", "block", "framed", 48, 1.1, "push", "fade", True, "solid"),
    "monochrome_monument":  Comp("band", "outline", "block", "framed", 48, 0.9, "none", "wipe", True, "solid"),
}


def _hex(h: str) -> str:
    return (h or "#000000").lstrip("#").upper()[:6]


def _mix(a: str, b: str, t: float) -> str:
    a, b = _hex(a), _hex(b)
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


@dataclass
class Theme:
    id: str
    dark: bool
    bg: str
    card: str
    title: str
    body: str
    muted: str
    accent: str
    accent2: str
    on_accent: str
    border: str
    font_title: str
    font_body: str
    radius: float          # inches
    comp: Comp
    palette: list

    @property
    def title_serif(self):
        return font_kind(self.font_title)


def resolve_theme(theme_name) -> Theme:
    ds = get_design_system(theme_name)
    comp = COMP.get(ds.id) or COMP["swiss_minimal"]
    bg, title, body = _hex(ds.background_hex), _hex(ds.title_hex), _hex(ds.body_hex)
    accent, accent2 = _hex(ds.accent_hex), _hex(ds.accent_secondary_hex)
    # on-accent text: pick black or white by luminance
    r, g, b = (int(accent[i:i + 2], 16) for i in (0, 2, 4))
    on_accent = "111111" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "FFFFFF"
    muted = _mix(body, bg, 0.25)
    # accent2 can be near-bg in some systems; guarantee a distinguishable second colour
    if _mix(accent2, bg, 0) == bg or abs(sum(int(accent2[i:i + 2], 16) for i in (0, 2, 4)) - sum(int(bg[i:i + 2], 16) for i in (0, 2, 4))) < 90:
        accent2 = _mix(accent, title, 0.5)
    palette = [accent, accent2, _mix(accent, title, 0.35), _mix(accent2, bg, 0.35), _mix(accent, bg, 0.5), _mix(accent2, title, 0.6)]
    return Theme(ds.id, ds.dark_mode, bg, _hex(ds.card_bg_hex), title, body, muted, accent, accent2, on_accent,
                 _hex(ds.border_hex), pick_font(ds.font_title), pick_font(ds.font_body), ds.card_radius / 100.0, comp, palette)
