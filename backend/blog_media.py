"""Article-specific, branded 1200x630 PNG covers. No paid image calls or uploads."""
from functools import lru_cache
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
from blog_content import BLOG_CATEGORIES, LEGACY_BLOG_CATEGORIES

ORIGIN = "https://nonprofitboardbuilder.com"
FONT = Path(__file__).parent / "assets/fonts/BoardBuilderSans-Bold.ttf"


def cover_copy(post):
    category = {**LEGACY_BLOG_CATEGORIES, **BLOG_CATEGORIES}.get(post.get("category_key"), {})
    return (post.get("graphic_headline") or post.get("title") or post.get("topic_title") or "Build the board your mission needs",
            post.get("graphic_subtitle") or "Practical insight for your next step.",
            category.get("name", post.get("category", "Board Leadership")), category.get("accent", "#818cf8"))


def image_version(post):
    return sha256(("blog-cover-v1|" + "|".join(cover_copy(post))).encode()).hexdigest()[:16]


def present_post(post, public=False):
    result = {key: value for key, value in post.items() if key != "_id"}
    config = {**LEGACY_BLOG_CATEGORIES, **BLOG_CATEGORIES}.get(post.get("category_key"))
    if config:
        result.update({"category": config["name"], **{key: config[key] for key in ["cta_label", "cta_button", "cta_url"]}})
    published = post.get("publication_status") == "Published"
    path = f"/api/blog/images/{post['slug']}.png" if published else f"/api/admin/blog/posts/{post['blog_post_id']}/image"
    result.update({"image_url": f"{ORIGIN}{path}?v={image_version(post)}", "image_path": f"{path}?v={image_version(post)}",
                   "image_alt": f"{cover_copy(post)[0]} | Nonprofit Board Builder", "image_width": 1200, "image_height": 630})
    if public:
        fields = {"blog_post_id", "title", "slug", "category", "category_key", "excerpt", "body", "published_at", "edited_at", "updated_at",
                  "cta_label", "cta_button", "cta_url", "image_url", "image_path", "image_alt", "image_width", "image_height"}
        return {key: value for key, value in result.items() if key in fields}
    from blog_service import generation_is_active
    result["can_regenerate"] = not published and not generation_is_active(post)
    result["generation_interrupted"] = post.get("publication_status") == "Generating" and not generation_is_active(post)
    result.pop("generation_token", None)
    return result


def wrapped(draw, text, font, width):
    # Splits overlong words as well as wrapping ordinary English titles.
    words = re.sub(r"\s+", " ", text).strip().split()
    lines, line = [], ""
    for word in words:
        if draw.textlength((line + " " + word).strip(), font=font) <= width:
            line = (line + " " + word).strip()
            continue
        if line:
            lines.append(line)
        line = ""
        for char in word:
            if line and draw.textlength(line + char, font=font) > width:
                lines.append(line)
                line = ""
            line += char
    if line:
        lines.append(line)
    return lines


def fit(draw, text, width, height, maximum, minimum):
    for size in range(maximum, minimum - 1, -2):
        font = ImageFont.truetype(str(FONT), size)
        lines = wrapped(draw, text, font, width)
        if len(lines) * (size + 10) <= height:
            return font, lines, size + 10
    raise ValueError("Shorten the graphic headline or subtitle to fit the cover.")


@lru_cache(maxsize=128)
def render_cover(headline, subtitle, category, accent):
    canvas = Image.new("RGB", (1200, 630), "#10132d")
    draw = ImageDraw.Draw(canvas)
    draw.ellipse((840, -260, 1390, 290), fill="#20204d")
    draw.ellipse((1010, -60, 1310, 240), outline=accent, width=3)
    draw.rounded_rectangle((54, 44, 62, 92), radius=4, fill=accent)
    small = ImageFont.truetype(str(FONT), 22)
    label = ImageFont.truetype(str(FONT), 23)
    draw.text((80, 43), "NONPROFIT", font=small, fill="#ffffff")
    draw.text((80, 71), "BOARD BUILDER", font=small, fill="#ffffff")
    draw.text((1050, 55), "INSIGHTS", font=ImageFont.truetype(str(FONT), 15), fill=accent)
    draw.text((58, 142), category.upper(), font=label, fill=accent)
    font, lines, step = fit(draw, headline, 1070, 258, 70, 28)
    for index, line in enumerate(lines):
        draw.text((54, 192 + index * step), line, font=font, fill="#ffffff")
    font, lines, step = fit(draw, subtitle, 1050, 84, 27, 18)
    for index, line in enumerate(lines):
        draw.text((58, 464 + index * step), line, font=font, fill="#c7c9ed")
    draw.line((58, 566, 1142, 566), fill="#3b3e64", width=2)
    footer = ImageFont.truetype(str(FONT), 18)
    draw.text((58, 587), "Rooney Akpesiri", font=footer, fill="#ffffff")
    draw.text((812, 587), "nonprofitboardbuilder.com", font=footer, fill=accent)
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()


def cover_png(post):
    return render_cover(*cover_copy(post))
