"""Native PPTX / PDF export. Both formats are drawn from the same layout scenes (services/deck), so the
preview, the PowerPoint file and the PDF cannot drift apart. There are no fixed slide templates here."""
import os

from services.deck.adapter import build_scenes
from services.deck.render_pdf import scenes_to_pdf
from services.deck.render_pptx import scenes_to_pptx


def export_pptx(presentation) -> bytes:
    animations = os.getenv("PPTX_ANIMATIONS", "1") != "0"
    return scenes_to_pptx(build_scenes(presentation), presentation.title or "Presentation", animations, owner_user_id=presentation.user_id)


def export_pdf(presentation) -> bytes:
    return scenes_to_pdf(build_scenes(presentation), presentation.title or "Presentation", owner_user_id=presentation.user_id)
