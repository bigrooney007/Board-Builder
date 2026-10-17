"""Render the organization's board appointment letter as a real letterhead PDF."""
import base64
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from document_renderer import brand_color


def render_appointment_letter(*, organization: str, recipient: str, body: str, branding: dict) -> bytes:
    branding = branding or {}
    accent = colors.HexColor(brand_color(branding))
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=LETTER, leftMargin=25 * mm, rightMargin=25 * mm,
                            topMargin=48 * mm, bottomMargin=25 * mm, title=f"Board appointment letter for {recipient}")
    logo = branding.get("logo_data", "")

    def letterhead(canvas, document):
        canvas.saveState()
        y = LETTER[1] - 20 * mm
        if logo.startswith("data:image"):
            try:
                from reportlab.lib.utils import ImageReader
                raw = base64.b64decode(logo.split(",", 1)[1])
                image = ImageReader(BytesIO(raw))
                width, height = image.getSize()
                display_height = 16 * mm
                canvas.drawImage(image, 25 * mm, y - display_height, width=min(40 * mm, display_height * width / height),
                                 height=display_height, preserveAspectRatio=True, mask="auto")
            except Exception:
                pass
        canvas.setFillColor(colors.HexColor("#111827"))
        canvas.setFont("Helvetica-Bold", 13)
        canvas.drawRightString(LETTER[0] - 25 * mm, y - 6 * mm, organization[:55])
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1.8)
        canvas.line(25 * mm, LETTER[1] - 42 * mm, LETTER[0] - 25 * mm, LETTER[1] - 42 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#475569"))
        canvas.drawString(25 * mm, 16 * mm, organization[:75])
        canvas.drawRightString(LETTER[0] - 25 * mm, 16 * mm, f"Page {document.page}")
        canvas.restoreState()

    normal = ParagraphStyle("letterBody", fontName="Helvetica", fontSize=11, leading=17,
                            textColor=colors.HexColor("#111827"), spaceAfter=11)
    heading = ParagraphStyle("letterHeading", parent=normal, fontName="Helvetica-Bold", fontSize=13,
                             leading=19, textColor=accent, spaceBefore=6, spaceAfter=15)
    story = []
    for line in body.splitlines():
        cleaned = line.strip()
        if not cleaned:
            if story:
                story.append(Spacer(1, 4 * mm))
            continue
        style = heading if cleaned.startswith("RE:") else normal
        story.append(Paragraph(escape(cleaned), style))
    if not story:
        story.append(Paragraph("Board appointment", heading))
    doc.build(story, onFirstPage=letterhead, onLaterPages=letterhead)
    return output.getvalue()
