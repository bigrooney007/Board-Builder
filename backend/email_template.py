"""Provider-independent shell shared by original and simplified emails."""
import html
import os


def wrap_email(title, body_html, separator=" — "):
    return f"<div style='max-width:640px;margin:auto;font-family:Arial,sans-serif;color:#111;line-height:1.6;'><h2 style='color:#083d2a;'>{html.escape(title)}</h2>{body_html}<p style='color:#667;font-size:12px;margin-top:28px;'>Nonprofit Board Builder{separator}{html.escape(os.environ.get('POSTAL_ADDRESS', ''))}</p></div>"
