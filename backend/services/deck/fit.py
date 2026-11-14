"""Text measurement and fitting. Measures with a wide font (DejaVu) so text that fits here also fits in
Calibri/Arial/Georgia on the viewer's machine. Falls back to a conservative width estimate."""
import functools
import os

MIN = {"title": 32, "body": 18, "detail": 14, "caption": 12}

_FONT_FILES = {
    "sans": ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans.ttf"],
    "sansb": ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"],
    "serif": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", "/usr/share/fonts/dejavu/DejaVuSerif.ttf"],
    "serifb": ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSerif-Bold.ttf"],
}


@functools.lru_cache(maxsize=8)
def _font(kind: str):
    try:
        from PIL import ImageFont
        for path in _FONT_FILES[kind]:
            if os.path.exists(path):
                return ImageFont.truetype(path, 100)
    except Exception:
        pass
    return None


def text_width_in(text: str, size_pt: float, bold=False, serif=False) -> float:
    """serif: False (sans) | True (serif) | "mono" (monospace)."""
    if serif == "mono":
        return len(text) * size_pt * 0.62 / 72.0
    kind = ("serif" if serif else "sans") + ("b" if bold else "")
    f = _font(kind)
    if f is not None:
        w100 = f.getlength(text)           # width at 100 "px"; px==pt here
        # DejaVu is ~8% wider than Calibri/Arial: a safe overestimate
        return (w100 * size_pt / 100.0) / 72.0 * 0.97
    return len(text) * size_pt * (0.60 if bold else 0.55) / 72.0


def wrap(text: str, width_in: float, size_pt: float, bold=False, serif=False) -> list[str]:
    lines: list[str] = []
    for para in str(text).split("\n"):
        words, cur = para.split(), ""
        if not words:
            lines.append("")
            continue
        for w in words:
            trial = (cur + " " + w).strip()
            if text_width_in(trial, size_pt, bold, serif) <= width_in or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def height_in(n_lines: int, size_pt: float, spacing: float = 1.2) -> float:
    return n_lines * size_pt * spacing / 72.0


def fit(text: str, w: float, h: float, max_size: float, min_size: float, bold=False, serif=False, spacing=1.2):
    """Largest size in [min,max] whose wrapped text fits (w x h inches). Returns (size, lines, overflow)."""
    size = float(max_size)
    pad = 0.0
    while size >= min_size - 1e-6:
        lines = wrap(text, w - pad, size, bold, serif)
        if height_in(len(lines), size, spacing) <= h + 1e-6 and all(
                text_width_in(l, size, bold, serif) <= w + 1e-6 for l in lines):
            return size, lines, False
        size -= 1
    size = float(min_size)
    return size, wrap(text, w, size, bold, serif), True


def truncate_to_fit(text: str, w: float, h: float, size: float, bold=False, serif=False, spacing=1.2) -> str:
    """Last resort: cut at a word boundary so it fits at the minimum size (never shrink below minimum)."""
    words = text.split()
    while words:
        cand = " ".join(words)
        if height_in(len(wrap(cand, w, size, bold, serif)), size, spacing) <= h + 1e-6:
            return cand if len(words) == len(text.split()) else cand.rstrip(",;:- ") + "…"
        words.pop()
    return ""
