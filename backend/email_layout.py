"""Shared email layout. Content and links precede the sender's closing signature."""
from html import escape


def split_signature(text, signature=None):
    # Older queued deliveries contain the complete text without a separate
    # signature field. Recognize their original defaults without changing them.
    candidates = [signature] if signature else [
        "Rooney A.\nThe Nonprofit Board Builder",
        "Rooney Akpesiri\nNonprofit Board Builder",
    ]
    for closing in candidates:
        if text == closing:
            return "", closing
        if closing and text.endswith("\n\n" + closing):
            return text[:-(len(closing) + 2)], closing
    return text, ""


def email_html(text, link, *, cta_label, signature=None, secondary_links=None, preview_text=""):
    body, closing = split_signature(text, signature)
    parts = [
        "<span style='display:none;max-height:0;overflow:hidden'>" + escape(preview_text) + "</span>",
        "<div style='max-width:640px;margin:auto;font-family:Arial;line-height:1.6;text-align:left'>",
    ]
    if body:
        parts.append("<p>" + escape(body).replace("\n", "<br>") + "</p>")
    parts.append("<p><a href='" + escape(link, quote=True) + "'>" + escape(cta_label) + "</a></p>")
    for item in secondary_links or []:
        if str(item.get("url", "")).startswith("https://"):
            parts.append("<p><a href='" + escape(item["url"], quote=True) + "'>" + escape(item["label"]) + "</a></p>")
    if closing:
        parts.append("<p>" + escape(closing).replace("\n", "<br>") + "</p>")
    return "".join(parts) + "</div>"
