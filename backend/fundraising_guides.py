"""Editable copies of the two public fundraising guides, with fixed page addresses."""
from copy import deepcopy
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

DEFAULTS = json.loads((Path(__file__).parent / "fundraising_guides.json").read_text())
PUBLISHED_AT = "2026-10-06T10:53:37Z"
START_PATH = "/board-fundraising/start"
CTA = "Answer the 5 fundraising questions and get my board fundraising"
Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=3000)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
OptionalText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=3000)]


class GuideStep(BaseModel):
    id: Literal["before", "during", "after"]
    label: ShortText
    navLabel: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    title: ShortText
    paragraphs: list[Text] = Field(min_length=1, max_length=15)
    questions: list[Text] = Field(default_factory=list, max_length=10)
    afterQuestions: OptionalText = ""


class GuideEdit(BaseModel):
    title: ShortText
    headline: ShortText
    headlineAccent: Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)] = ""
    topic: ShortText
    excerpt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=250)]
    image_alt: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
    intro: list[Text] = Field(min_length=1, max_length=15)
    takeaway: Text
    steps: list[GuideStep] = Field(min_length=3, max_length=3)
    closingTitle: ShortText
    closing: Text
    offerNote: Text
    cardLabel: ShortText
    visualTitle: ShortText
    visualItems: list[ShortText] = Field(min_length=3, max_length=3)
    visualEyebrow: ShortText = "Your next board meeting"
    visualFootnote: ShortText = "A strategy your board can act on"
    ctaButton: ShortText = CTA

    @model_validator(mode="after")
    def ordered_steps(self):
        if [step.id for step in self.steps] != ["before", "during", "after"]:
            raise ValueError("Keep the three guide sections in their existing order.")
        return self


def default_guide(slug):
    original = next((guide for guide in DEFAULTS if guide["slug"] == slug), None)
    if not original:
        return None
    return {**deepcopy(original), **GuideEdit.model_validate(original).model_dump(), "published_at": PUBLISHED_AT}


async def get_guide(db, slug):
    guide = default_guide(slug)
    if not guide:
        return None
    saved = await db.marketing_settings.find_one({"key": "fundraising_guide:" + slug}, {"_id": 0})
    if saved:
        guide.update(GuideEdit.model_validate({**guide, **saved.get("content", {})}).model_dump())
        guide["edited_at"] = saved["edited_at"]
    return guide


async def list_guides(db):
    guides = [await get_guide(db, guide["slug"]) for guide in DEFAULTS]
    for guide in guides:
        related = next(item for item in guides if item["slug"] != guide["slug"])
        guide["relatedGuide"] = {"slug": related["slug"], "title": related["title"]}
    return guides


def guide_post(guide, origin):
    blocks = [*guide["intro"], guide["takeaway"]]
    for step in guide["steps"]:
        blocks.extend(["## " + step["label"] + ": " + step["title"], *step["paragraphs"],
                       *step.get("questions", []), step.get("afterQuestions", "")])
    blocks.extend(["## " + guide["closingTitle"], guide["closing"], guide["offerNote"]])
    return {**guide, "body": "\n\n".join(block for block in blocks if block),
            "category": guide["topic"], "image_url": origin + "/social/" + guide["image"],
            "cta_url": START_PATH, "cta_button": guide["ctaButton"]}
