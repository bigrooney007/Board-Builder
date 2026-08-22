"""Global Document Design Standard — single reusable PDF renderer for every generated document."""
import base64
import re
from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import BaseDocTemplate, Frame, Image, NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer

ARTIFACT_LINE = re.compile(r"^(sections?|version\s*\d+)\s*:?\s*$", re.I)
TITLE_PREFIX = re.compile(r"^title\s*:\s*", re.I)
CONTENT_PREFIX = re.compile(r"^content\s*:\s*", re.I)
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def _logo_dominant_color(logo_data: str) -> str:
    try:
        from PIL import Image as PILImage
        raw = base64.b64decode(logo_data.split(",", 1)[1])
        img = PILImage.open(BytesIO(raw)).convert("RGBA").resize((40, 40))
        best, best_score = None, -1
        for r, g, b, a in img.getdata():
            if a < 200:
                continue
            brightness = (r + g + b) / 3
            if brightness > 235 or brightness < 15:
                continue
            saturation = max(r, g, b) - min(r, g, b)
            if saturation > best_score:
                best_score, best = saturation, (r, g, b)
        if best:
            return "#{:02x}{:02x}{:02x}".format(*best)
    except Exception:
        pass
    return ""


def brand_color(branding: dict) -> str:
    branding = branding or {}
    primary = (branding.get("primary_color") or "").strip()
    if HEX_COLOR.match(primary):
        return primary
    logo = branding.get("logo_data", "")
    if logo.startswith("data:image"):
        derived = _logo_dominant_color(logo)
        if derived:
            return derived
    return "#000000"


def clean_document_lines(text: str, title: str) -> list:
    """Convert structured AI output into finished document blocks: (kind, text)."""
    blocks = []
    for raw in (text or "").split("\n"):
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped:
            blocks.append(("blank", ""))
            continue
        if ARTIFACT_LINE.match(stripped):
            continue
        if TITLE_PREFIX.match(stripped):
            heading = TITLE_PREFIX.sub("", stripped).strip()
            if heading:
                blocks.append(("heading", heading))
            continue
        if CONTENT_PREFIX.match(stripped):
            body = CONTENT_PREFIX.sub("", stripped).strip()
            if body:
                blocks.append(("body", body))
            continue
        if stripped.startswith("- ") or stripped.startswith("• "):
            blocks.append(("bullet", stripped[2:].strip()))
            continue
        if stripped == stripped.upper() and 2 < len(stripped) < 90 and any(c.isalpha() for c in stripped):
            if stripped.upper() != (title or "").upper():
                blocks.append(("heading", stripped))
            continue
        blocks.append(("body", stripped))
    return blocks


def render_document_pdf(*, title: str, org_name: str = "", body_text: str = "", branding: dict = None,
                        created_by: dict = None, prepared_for: str = "") -> bytes:
    """One consistent professional document format for every generated document."""
    branding = branding or {}
    color = brand_color(branding)
    accent = HexColor(color)
    buffer = BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=LETTER, leftMargin=24 * mm, rightMargin=24 * mm,
                          topMargin=24 * mm, bottomMargin=26 * mm, title=title)

    def border(canvas):
        canvas.setStrokeColor(accent)
        canvas.setLineWidth(1.1)
        canvas.rect(14 * mm, 14 * mm, LETTER[0] - 28 * mm, LETTER[1] - 28 * mm)

    def cover_page(canvas, _doc):
        canvas.saveState()
        border(canvas)
        canvas.restoreState()

    def content_page(canvas, _doc):
        canvas.saveState()
        border(canvas)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(HexColor("#444444"))
        if org_name:
            canvas.drawString(doc.leftMargin, 17.5 * mm, org_name)
        canvas.drawRightString(doc.leftMargin + doc.width, 17.5 * mm, f"Page {canvas.getPageNumber() - 1}")
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
    doc.addPageTemplates([
        PageTemplate(id="cover", frames=[frame], onPage=cover_page),
        PageTemplate(id="content", frames=[frame], onPage=content_page),
    ])

    cover_title = ParagraphStyle("cover_title", fontName="Helvetica-Bold", fontSize=26, leading=32,
                                 alignment=1, textColor=HexColor("#000000"), spaceAfter=14)
    cover_org = ParagraphStyle("cover_org", fontName="Helvetica-Bold", fontSize=14, leading=20,
                               alignment=1, textColor=accent, spaceAfter=8)
    cover_meta = ParagraphStyle("cover_meta", fontName="Helvetica", fontSize=12, leading=18,
                                alignment=1, textColor=HexColor("#333333"), spaceAfter=4)
    heading = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=14, leading=22, textColor=accent,
                             spaceBefore=16, spaceAfter=8, keepWithNext=1)
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=12, leading=24,
                          textColor=HexColor("#000000"), spaceAfter=10)
    bullet = ParagraphStyle("bullet", parent=body, leftIndent=14, spaceAfter=6)

    esc = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;")
    story = [Spacer(1, 60 * mm)]
    logo = branding.get("logo_data", "")
    if logo.startswith("data:image"):
        try:
            image_bytes = base64.b64decode(logo.split(",", 1)[1])
            img = Image(BytesIO(image_bytes))
            ratio = img.imageWidth / max(img.imageHeight, 1)
            img.drawHeight = 26 * mm
            img.drawWidth = min(26 * mm * ratio, 80 * mm)
            img.hAlign = "CENTER"
            story = [Spacer(1, 44 * mm), img, Spacer(1, 12 * mm)]
        except Exception:
            pass
    story.append(Paragraph(esc(title), cover_title))
    if org_name:
        story.append(Paragraph(esc(org_name), cover_org))
    if prepared_for:
        story.append(Paragraph(f"Prepared for {esc(prepared_for)}", cover_meta))
    story.append(Paragraph(datetime.now(timezone.utc).strftime("%B %d, %Y"), cover_meta))
    if created_by and created_by.get("name"):
        cover_created = f"Created By: {created_by['name']}"
        if created_by.get("title"):
            cover_created += f" — {created_by['title']}"
        story.append(Paragraph(esc(cover_created), cover_meta))
    story.extend([NextPageTemplate("content"), PageBreak()])

    for kind, text in clean_document_lines(body_text, title):
        if kind == "heading":
            story.append(Paragraph(esc(text), heading))
        elif kind == "bullet":
            story.append(Paragraph(f"• {esc(text)}", bullet))
        elif kind == "body":
            story.append(Paragraph(esc(text), body))

    if created_by and (created_by.get("name") or created_by.get("organization")):
        story.append(Paragraph("Created By", heading))
        for key in ("name", "title", "organization"):
            if created_by.get(key):
                story.append(Paragraph(esc(created_by[key]), body))

    doc.build(story)
    return buffer.getvalue()


def clean_document_text(text: str, title: str = "") -> str:
    """Finished-document text: structural artifacts removed, headings/bullets normalized."""
    out = []
    for kind, value in clean_document_lines(text, title):
        if kind == "blank":
            out.append("")
        elif kind == "heading":
            out.append(value if value == value.upper() else value.upper())
        elif kind == "bullet":
            out.append(f"- {value}")
        else:
            out.append(value)
    return "\n".join(out)


async def material_created_by(db, user_id: str) -> dict:
    member = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1}) or {}
    profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data.founder_title": 1}) or {}
    org = (await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1}) or {}).get("organization_name", "")
    return {
        "name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
        "title": (profile.get("data", {}) or {}).get("founder_title", "") or "Founder",
        "organization": org,
    }
