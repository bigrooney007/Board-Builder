"""RSS 2.0 for published articles. Stable article URLs are the item identifiers."""
from datetime import datetime, timezone
from email.utils import format_datetime
from hashlib import sha256
from html import escape
import re
from urllib.parse import quote
import xml.etree.ElementTree as ET

from blog_media import ORIGIN

FEED_PATH = "/api/blog/feed.xml"
CONTENT = "http://purl.org/rss/1.0/modules/content/"
MEDIA = "http://search.yahoo.com/mrss/"
ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("content", CONTENT)
ET.register_namespace("media", MEDIA)
ET.register_namespace("atom", ATOM)


def clean(value):
    # XML 1.0 excludes control characters even when HTML-escaped.
    return re.sub(r"[^\x09\x0a\x0d\x20-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]", "", str(value or ""))


def timestamp(value):
    try:
        instant = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return instant.replace(tzinfo=timezone.utc) if not instant.tzinfo else instant.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return datetime(1970, 1, 1, tzinfo=timezone.utc)


def article_html(post):
    image = post.get("image_url", "")
    parts = [f'<p><img src="{escape(image, quote=True)}" alt="{escape(clean(post.get("image_alt")), quote=True)}" /></p>'] if image else []
    for block in re.split(r"\n{2,}|\n(?=## )", post.get("body") or ""):
        text = block.strip()
        if text:
            tag = "h2" if text.startswith("## ") else "p"
            parts.append(f"<{tag}>{escape(clean(text[3:] if tag == 'h2' else text))}</{tag}>")
    cta = post.get("cta_url", "")
    if re.fullmatch(r"/(?!/)[a-z0-9/-]*", cta):
        parts.append(f'<p><a href="{ORIGIN}{cta}">{escape(clean(post.get("cta_button", "Get started")))}</a></p>')
    return "".join(parts)


def render_feed(posts):
    root = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(root, "channel")
    for tag, text in [("title", "Nonprofit Board Builder Insights"), ("link", ORIGIN + "/blog"),
                      ("description", "Practical insights for nonprofit founders, executive directors and board members."),
                      ("language", "en-us"), ("ttl", "15")]:
        ET.SubElement(channel, tag).text = text
    ET.SubElement(channel, f"{{{ATOM}}}link", {"href": ORIGIN + FEED_PATH, "rel": "self", "type": "application/rss+xml"})
    published = sorted((post for post in posts if post.get("slug") and post.get("title")),
                       key=lambda post: timestamp(post.get("published_at")), reverse=True)[:50]
    latest = max((timestamp(post.get("edited_at") or post.get("updated_at") or post.get("published_at")) for post in published),
                 default=timestamp(None))
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(latest, usegmt=True)
    for post in published:
        item = ET.SubElement(channel, "item")
        url = ORIGIN + "/blog/" + quote(post["slug"], safe="")
        for tag, text in [("title", post["title"]), ("link", url), ("description", post.get("excerpt", "")),
                          ("category", post.get("category", "")),
                          ("pubDate", format_datetime(timestamp(post.get("published_at")), usegmt=True))]:
            ET.SubElement(item, tag).text = clean(text)
        ET.SubElement(item, "guid", {"isPermaLink": "true"}).text = url
        ET.SubElement(item, f"{{{CONTENT}}}encoded").text = article_html(post)
        if post.get("image_url"):
            ET.SubElement(item, f"{{{MEDIA}}}content", {"url": post["image_url"], "medium": "image", "type": "image/png"})
    xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return xml, '"' + sha256(xml).hexdigest() + '"'
