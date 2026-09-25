"""Fundraising Strategy PDF — approved minimal professional document design (thin border, no logo)."""
from io import BytesIO

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer

V1_SECTIONS = [
    ("executive_summary", "Executive Summary"), ("fundraising_goal", "Fundraising Goal"),
    ("fundraising_audiences", "Ideal Funding Audiences"), ("where_to_find", "Where To Find Potential Funders"),
    ("attraction", "Attraction Strategy"), ("fundraising_process", "Fundraising Process"),
    ("technology", "Technology We Need To Execute"), ("fundraising_team", "The Fundraising Team We Need"),
    ("materials", "Fundraising Materials We Need"), ("execution_budget", "Execution Budget"), ("execution_timeline", "Execution Timeline"),
    ("additional_board_ideas", "Additional Board Ideas"), ("next_step", "Next Step"),
]
V2_SECTIONS = [
    ("executive_summary", "Executive Summary"), ("fundraising_goal", "Fundraising Goal"),
    ("fundraising_audiences", "Ideal Funding Audiences"), ("where_to_find", "Where To Find Potential Funders"),
    ("attraction", "Attraction Strategy"), ("fundraising_process", "Fundraising Process"),
    ("board_fundraising_process", "Board Fundraising Process"), ("team_roles", "Team, Roles & Responsibilities"),
    ("execution_resources", "Technology, Materials, Resources & Content"), ("execution_budget", "Lean Execution Budget"), ("execution_timeline", "Execution Timeline"),
    ("board_priorities", "Board Priorities"), ("additional_board_ideas", "Additional Board Ideas"),
    ("next_step", "Next Step"),
]
V3_SECTIONS = [
    ("fundraising_audiences", "Who We Will Raise Money From"),
    ("where_to_find", "Where We Will Find Them"),
    ("attraction", "How We Will Attract Their Attention"),
    ("fundraising_process", "How We Will Raise Money From Them"),
]
V1_STAGES = {
    "fundraising_process": [("know", "KNOW"), ("like", "LIKE"), ("trust", "TRUST"), ("ask", "ASK"),
                            ("follow_up", "FOLLOW UP"), ("steward", "STEWARD")],
    "execution_timeline": [("set_up", "SET UP"), ("launch", "LAUNCH"), ("execute", "EXECUTE"),
                           ("review_and_improve", "REVIEW AND IMPROVE")],
}
PROCESS_STAGES = [("know", "KNOW"), ("like", "LIKE"), ("trust", "TRUST"), ("ask", "ASK"),
                  ("follow_up", "FOLLOW UP"), ("steward", "STEWARD")]
AUDIENCE_LABELS = [("individuals", "Individuals"), ("businesses", "Businesses"), ("grantors", "Grantors")]
V2_TIMELINE = [("phase_1_build_the_system", "PHASE 1: BUILD THE SYSTEM"),
               ("phase_2_build_know_like_trust", "PHASE 2: BUILD KNOW, LIKE AND TRUST"),
               ("phase_3_ask_campaign", "PHASE 3: ASK CAMPAIGN"),
               ("follow_up_and_steward", "FOLLOW UP AND STEWARD"),
               ("business_timeline", "BUSINESS TIMELINE"),
               ("grantor_timeline", "GRANTOR TIMELINE")]
V2_RESOURCES = [("people", "People"), ("technology", "Technology"), ("materials", "Materials"),
                ("resources", "Resources"), ("content", "Content")]


def _item_text(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return " — ".join(str(item.get(k, "")).strip() for k in ("title", "explanation", "focus") if str(item.get(k, "")).strip())
    return str(item)


def section_blocks(key: str, data, schema_version: int) -> list:
    """Return list of (kind, text) blocks: kind in {sub, body, bullet}."""
    blocks = []
    if data in (None, "", [], {}):
        return blocks
    if key in {"executive_summary", "next_step"}:
        for line in str(data).split("\n"):
            if line.strip():
                blocks.append(("body", line.strip()))
        return blocks
    if key == "fundraising_goal":
        for label, field in (("Goal", "amount"), ("Deadline", "deadline"), ("Purpose", "purpose")):
            if data.get(field):
                blocks.append(("body", f"<b>{label}:</b> {data[field]}"))
        if data.get("summary"):
            blocks.append(("body", data["summary"]))
        return blocks
    if key == "fundraising_audiences" and schema_version >= 2:
        for field, label in AUDIENCE_LABELS:
            items = data.get(field) or []
            if items:
                blocks.append(("sub", label.upper()))
                for item in items:
                    blocks.append(("bullet", _item_text(item)))
        return blocks
    if key == "fundraising_process" and schema_version >= 2:
        for field, label in AUDIENCE_LABELS:
            process = data.get(field) or {}
            if any((process.get(stage) or []) for stage, _ in PROCESS_STAGES) or process.get("how_this_process_works"):
                blocks.append(("sub", f"{label.upper()} FUNDRAISING PROCESS"))
                if process.get("how_this_process_works"):
                    blocks.append(("sub", "HOW THIS PROCESS WORKS"))
                    blocks.append(("body", str(process["how_this_process_works"])))
                for stage, stage_label in PROCESS_STAGES:
                    items = process.get(stage) or []
                    if items:
                        blocks.append(("sub", stage_label))
                        for item in items:
                            blocks.append(("bullet", _item_text(item)))
        return blocks
    if key == "board_fundraising_process":
        for stage, stage_label in PROCESS_STAGES:
            items = data.get(stage) or []
            if items:
                blocks.append(("sub", stage_label))
                for item in items:
                    blocks.append(("bullet", _item_text(item)))
        return blocks
    if key == "team_roles":
        for row in data if isinstance(data, list) else []:
            role = str(row.get("role", "")).strip()
            assigned = str(row.get("assigned", "")).strip() or "ROLE / CAPACITY NEEDED"
            blocks.append(("sub", role))
            blocks.append(("body", f"Assigned: {assigned}"))
            if row.get("responsibility"):
                blocks.append(("body", str(row["responsibility"])))
        return blocks
    if key == "execution_resources":
        for field, label in V2_RESOURCES:
            items = data.get(field) or []
            if items:
                blocks.append(("sub", label.upper()))
                for item in items:
                    blocks.append(("bullet", _item_text(item)))
        return blocks
    if key == "execution_budget":
        required = data.get("required_now") or []
        if required:
            blocks.append(("sub", "REQUIRED NOW"))
            for item in required:
                text = str(item.get("item", "")).strip()
                if item.get("why_needed"):
                    text += f" — {item['why_needed']}"
                if item.get("lowest_cost_approach"):
                    text += f" — Lean approach: {item['lowest_cost_approach']}"
                text += f" — Cost: {item.get('cost') or 'PRICE TO CONFIRM'}"
                blocks.append(("bullet", text))
        later = data.get("later_or_optional") or []
        if later:
            blocks.append(("sub", "LATER / OPTIONAL"))
            for item in later:
                text = str(item.get("item", "")).strip()
                if item.get("why_later"):
                    text += f" — {item['why_later']}"
                if item.get("lowest_cost_approach"):
                    text += f" — Lean approach: {item['lowest_cost_approach']}"
                text += f" — Cost: {item.get('cost') or 'PRICE TO CONFIRM'}"
                blocks.append(("bullet", text))
        reductions = data.get("cost_reduction_options") or []
        if reductions:
            blocks.append(("sub", "WAYS TO REDUCE THE COST"))
            for item in reductions:
                blocks.append(("bullet", _item_text(item)))
        if data.get("budget_summary"):
            blocks.append(("body", str(data["budget_summary"])))
        return blocks
    if key == "execution_timeline" and schema_version >= 2:
        for field, label in V2_TIMELINE:
            items = data.get(field) or []
            if items:
                blocks.append(("sub", label))
                for item in items:
                    blocks.append(("bullet", _item_text(item)))
        return blocks
    if key in {"board_priorities"} or (key == "additional_board_ideas" and isinstance(data, list)):
        for group in data if isinstance(data, list) else []:
            items = group.get("items") or []
            if items:
                blocks.append(("sub", str(group.get("area", "")).upper()))
                for item in items:
                    blocks.append(("bullet", _item_text(item)))
        return blocks
    if key in V1_STAGES:
        for stage, label in V1_STAGES[key]:
            items = data.get(stage) or []
            if items:
                blocks.append(("sub", label))
                for item in items:
                    blocks.append(("bullet", _item_text(item)))
        return blocks
    if key == "additional_board_ideas" and isinstance(data, dict):
        for area_key, items in data.items():
            if items:
                blocks.append(("sub", area_key.replace("_", " ").upper()))
                for item in items:
                    blocks.append(("bullet", _item_text(item)))
        return blocks
    if isinstance(data, dict):
        for item in data.get("priorities") or []:
            blocks.append(("bullet", _item_text(item)))
        extra = data.get("additional_ideas") or []
        if extra:
            blocks.append(("sub", "ADDITIONAL IDEAS TO CONSIDER"))
            for item in extra:
                blocks.append(("bullet", _item_text(item)))
    return blocks


class _StrategyDoc(BaseDocTemplate):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.toc_pages = {}

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name == "section_title":
            self.toc_pages[flowable.getPlainText()] = self.page


def build_strategy_pdf(strategy: dict, org_name: str) -> bytes:
    schema_version = int(strategy.get("schema_version") or 1)
    sections = V3_SECTIONS if schema_version >= 3 else V2_SECTIONS if schema_version >= 2 else V1_SECTIONS
    data = strategy.get("data") or {}
    edits = strategy.get("section_edits") or {}
    prepared_by = strategy.get("prepared_by") or (
        f"The Board of {org_name}" if strategy.get("mode") == "final" else org_name)

    black = HexColor("#111111")
    grey = HexColor("#555555")
    title_style = ParagraphStyle("cover_title", fontName="Helvetica-Bold", fontSize=30, leading=38, alignment=1, textColor=black, spaceAfter=16)
    org_style = ParagraphStyle("cover_org", fontName="Helvetica-Bold", fontSize=16, leading=22, alignment=1, textColor=black, spaceAfter=10)
    meta_style = ParagraphStyle("cover_meta", fontName="Helvetica", fontSize=12, leading=18, alignment=1, textColor=grey, spaceAfter=4)
    toc_title = ParagraphStyle("toc_title", fontName="Helvetica-Bold", fontSize=20, leading=26, textColor=black, spaceAfter=18)
    toc_row = ParagraphStyle("toc_row", fontName="Helvetica", fontSize=12, leading=24, textColor=black)
    section_title = ParagraphStyle("section_title", fontName="Helvetica-Bold", fontSize=17, leading=24, textColor=black, spaceAfter=12, keepWithNext=1)
    sub_style = ParagraphStyle("sub", fontName="Helvetica-Bold", fontSize=11.5, leading=17, textColor=black, spaceBefore=12, spaceAfter=5, keepWithNext=1)
    body_style = ParagraphStyle("body", fontName="Helvetica", fontSize=10.5, leading=17, textColor=HexColor("#222222"), spaceAfter=7)
    bullet_style = ParagraphStyle("bullet", parent=body_style, leftIndent=13, spaceAfter=5)
    empty_style = ParagraphStyle("empty", parent=body_style, textColor=grey)

    esc = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;")

    def build(toc_pages: dict) -> bytes:
        buffer = BytesIO()
        doc = _StrategyDoc(buffer, pagesize=LETTER, leftMargin=24 * mm, rightMargin=24 * mm,
                           topMargin=26 * mm, bottomMargin=26 * mm, title="Fundraising Strategy")

        def border(canvas):
            canvas.setStrokeColor(HexColor("#111111"))
            canvas.setLineWidth(0.8)
            canvas.rect(14 * mm, 14 * mm, LETTER[0] - 28 * mm, LETTER[1] - 28 * mm)

        def on_page(canvas, _doc):
            canvas.saveState()
            border(canvas)
            if canvas.getPageNumber() > 1:
                canvas.setFont("Helvetica", 9)
                canvas.setFillColor(HexColor("#555555"))
                if org_name:
                    canvas.drawString(doc.leftMargin, 17 * mm, org_name)
                canvas.drawRightString(doc.leftMargin + doc.width, 17 * mm, f"Page {canvas.getPageNumber()}")
            canvas.restoreState()

        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="body")
        doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=on_page)])

        story = [Spacer(1, 70 * mm), Paragraph("FUNDRAISING STRATEGY", title_style)]
        if org_name:
            story.append(Paragraph(esc(org_name), org_style))
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph("Prepared By:", meta_style))
        story.append(Paragraph(esc(prepared_by), meta_style))
        story.append(PageBreak())

        story.append(Paragraph("FUNDRAISING STRATEGY", toc_title))
        for _, title in sections:
            page = toc_pages.get(title)
            suffix = f" — Page {page}" if page else ""
            story.append(Paragraph(f"{esc(title)}{esc(suffix)}", toc_row))
        story.append(PageBreak())

        for index, (key, title) in enumerate(sections):
            joined_with_previous = schema_version >= 1 and key == "fundraising_goal"
            if index > 0 and not joined_with_previous:
                story.append(PageBreak())
            story.append(Paragraph(esc(title), section_title))
            if edits.get(key):
                for line in str(edits[key]).split("\n"):
                    if line.strip():
                        story.append(Paragraph(esc(line.strip()), body_style))
                continue
            blocks = section_blocks(key, data.get(key), schema_version)
            if not blocks:
                story.append(Paragraph("No information was provided for this section.", empty_style))
                continue
            for kind, text in blocks:
                if kind == "sub":
                    story.append(Paragraph(esc(text), sub_style))
                elif kind == "bullet":
                    story.append(Paragraph(f"• {esc(text)}", bullet_style))
                else:
                    story.append(Paragraph(text if text.startswith("<b>") else esc(text), body_style))

        doc.build(story)
        return buffer.getvalue(), doc.toc_pages

    _, toc_pages = build({})
    pdf_bytes, _ = build(toc_pages)
    return pdf_bytes
