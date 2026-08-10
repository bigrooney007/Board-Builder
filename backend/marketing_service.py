"""Phase 4: automatic blog publishing + weekly lead nurture. Fixed email templates, deterministic rotation."""
import asyncio
import html
import json
import logging
import os
import re
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import resend
from emergentintegrations.llm.chat import LlmChat, UserMessage

from ai_service import parse_json_response
from resend_service import create_segment_broadcast, upsert_contact

logger = logging.getLogger(__name__)

CATEGORIES = {
    "recruitment": {"name": "Board Recruitment", "day": 0, "cta_label": "Ready to Recruit Your Board?", "cta_button": "See How We Can Help You Recruit", "cta_url": "/recruit"},
    "reactivation": {"name": "Board Reactivation", "day": 2, "cta_label": "Ready to Reactivate Your Board?", "cta_button": "See How We Can Help You Reactivate", "cta_url": "/reactivate"},
    "fundraising_activation": {"name": "Board Fundraising Activation", "day": 4, "cta_label": "Ready to Activate Your Board Around Fundraising?", "cta_button": "See How We Can Help You Activate Your Board", "cta_url": "/activate"},
}
BANNED_PHRASES = ["in today's fast-paced world", "in the ever-evolving landscape", "it's important to note", "let's dive in", "game changer", "unlock the power", "navigate the complexities", "revolutionize", "game-changer"]

SEGMENT_NAMES = {
    "recruitment": "Nonprofit Board Builder — Recruitment Leads",
    "reactivation": "Nonprofit Board Builder — Reactivation Leads",
    "fundraising_activation": "Nonprofit Board Builder — Fundraising Activation Leads",
}

NURTURE_TEMPLATES = {
    "recruitment": [
        {"subject": "Your Board Recruitment Should Start With What Your Organization Needs", "headline": "Stop Recruiting Whoever Happens to Be Available", "paragraphs": ["The goal is not simply to add more names to your board.", "You need people who strengthen the areas your organization is currently missing, whether that is fundraising, finance, corporate relationships, governance, marketing or professional connections.", "The right recruitment process starts with what the organization needs, then builds the campaign around finding people who can provide it.", "You already told us about the board you want to build."], "cta": "See How We Can Help You Recruit", "url": "/recruit/options"},
        {"subject": "The Right Professionals Need a Reason to Join Your Board", "headline": "A Board Vacancy Is Not a Compelling Opportunity", "paragraphs": ["Strong professionals are not looking for another meeting to attend.", "They want to understand the mission, what the organization is trying to accomplish and the meaningful role they will play in helping make it happen.", "Your recruitment campaign should make that clear before you ever ask someone to apply.", "We can help you build and launch the complete process."], "cta": "See Your Board Recruitment Options", "url": "/recruit/options"},
        {"subject": "Finding Applicants Is Only the Beginning", "headline": "You Still Have to Know Who Belongs on the Board", "paragraphs": ["A strong résumé does not automatically make someone the right board member.", "You still need to understand their commitment, professional strengths, fundraising willingness, relationships and ability to take responsibility.", "That is why recruitment must include a real application, structured interviews, references and thoughtful selection.", "We can help you execute the process from recruitment through onboarding."], "cta": "Choose How You Want to Recruit", "url": "/recruit/options"},
        {"subject": "Do Not Lose Good Board Members After You Recruit Them", "headline": "Recruitment Does Not End When Someone Says Yes", "paragraphs": ["New board members need to understand the organization, what the board expects from them and what responsibility they are agreeing to take.", "Without a proper onboarding process, even strong recruits can quickly become inactive board members.", "Your recruitment process should finish by preparing each person to contribute."], "cta": "Start Your Board Recruitment Process", "url": "/recruit/options"},
    ],
    "reactivation": [
        {"subject": "Your Inactive Board Members May Need a Decision, Not Another Reminder", "headline": "Give Them a Clear Opportunity to Recommit", "paragraphs": ["Repeated reminders rarely reactivate an inactive board.", "Each person needs a clear opportunity to decide whether they are still willing and able to serve, understand what the organization now requires and commit to meaningful responsibility.", "Those who cannot continue should have a respectful way to step down.", "That is the beginning of board reactivation."], "cta": "See How We Can Help You Reactivate", "url": "/reactivate/options"},
        {"subject": "Attendance Is Not the Same as Engagement", "headline": "Board Members Need Something to Own", "paragraphs": ["A person can attend every board meeting and still contribute very little.", "Real engagement begins when board members understand the organization's priorities and accept clear responsibilities connected to their strengths.", "Your board does not simply need more meetings.", "It needs clarity, ownership and accountability."], "cta": "See Your Board Reactivation Options", "url": "/reactivate/options"},
        {"subject": "Some Board Members Should Be Allowed to Step Down", "headline": "Reactivation Is Not About Pressuring Everyone to Stay", "paragraphs": ["Not every inactive board member needs to be persuaded to continue.", "People's circumstances change. Some no longer have the time, interest or ability to give the organization what board service requires.", "A good reactivation process lets committed people step up while giving others a respectful way to step down without unnecessarily damaging relationships."], "cta": "Start Your Board Reactivation Process", "url": "/reactivate/options"},
        {"subject": "Your Board Needs to Know Where the Organization Is Going", "headline": "People Execute What They Help Plan", "paragraphs": ["It is difficult to hold board members responsible for priorities they never helped understand or shape.", "One of the strongest ways to reactivate a board is to involve members in the direction of the organization, then turn that direction into individual responsibilities.", "That moves the board from observation into ownership."], "cta": "See How We Can Help", "url": "/reactivate/options"},
    ],
    "fundraising_activation": [
        {"subject": "“Help Us Fundraise” Is Not a Board Responsibility", "headline": "Give Every Board Member Something Specific to Do", "paragraphs": ["Board members struggle with fundraising when the expectation is simply to “help raise money.”", "One person may be good at corporate introductions. Another may know donors. Someone else may help with grants, events, sponsorship or community relationships.", "The goal is to give each person a fundraising responsibility they can actually execute."], "cta": "See How We Can Help You Activate Your Board", "url": "/activate/options"},
        {"subject": "Your Board Members Do Not Have to Become Professional Fundraisers", "headline": "Start With What They Already Know and Who They Already Know", "paragraphs": ["Board fundraising becomes easier when people are asked to contribute through their strengths.", "Their professional relationships, business connections, community credibility, technical skills and personal networks can all become part of the organization's fundraising system.", "The first step is turning those strengths into clear responsibilities."], "cta": "See Your Fundraising Activation Options", "url": "/activate/options"},
        {"subject": "A Fundraising Strategy Nobody Owns Will Sit on a Shelf", "headline": "Your Board Needs to Help Execute the Plan", "paragraphs": ["A written fundraising strategy is useful only when people know which parts they are responsible for carrying forward.", "The board should understand the strategy, help shape the execution and leave with clear assignments.", "That is how fundraising moves from ideas into consistent action."], "cta": "Activate Your Board Around Fundraising", "url": "/activate/options"},
        {"subject": "Build the Fundraising System Around the Board", "headline": "Strategy, People, Materials and Execution Have to Work Together", "paragraphs": ["Board fundraising does not succeed because people are told to ask for money.", "The organization needs a strategy, a team, the right materials and a consistent execution process.", "Then every board member needs to understand where they fit inside that system.", "That is what turns a board into a fundraising asset."], "cta": "See How We Can Help", "url": "/activate/options"},
    ],
}


def now_tz(env_key="BLOG_TIMEZONE"):
    return datetime.now(ZoneInfo(os.environ.get(env_key, "America/New_York")))


def slugify_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:80]


async def send_owner_alert(subject: str, rows: list) -> None:
    try:
        resend.api_key = os.environ["RESEND_API_KEY"]
        table = "".join(f"<tr><td style='padding:7px;border-bottom:1px solid #ddd;font-weight:bold;'>{html.escape(str(k))}</td><td style='padding:7px;border-bottom:1px solid #ddd;'>{html.escape(str(v))}</td></tr>" for k, v in rows)
        await resend.Emails.send_async({"from": os.environ["NONPROFIT_SENDER"], "to": [os.environ["OWNER_NOTIFICATION_EMAIL"]], "subject": subject, "html": f"<table style='border-collapse:collapse;font-family:Arial;'>{table}</table>"})
    except Exception as exc:
        logger.error("Owner alert failed: %s", exc)


# ---------------- BLOG ----------------
BLOG_SYSTEM = (
    "You are Rooney Akpesiri, the Nonprofit Board Builder. You write for nonprofit founders and Executive Directors in American English. "
    "You help nonprofits reactivate their present board, recruit the board members they are missing, and activate their board to raise money. "
    "You sound like someone who has actually worked with nonprofit founders and boards. Every article makes ONE clear point about ONE specific problem. "
    "Get to the problem within the first two or three sentences. Never open with broad industry commentary, generic nonprofit observations, long context sections or motivational filler. "
    "Open with a real, recognizable situation, for example: a founder carrying the organization alone, seven board members but only two doing anything, board members attending meetings but taking no responsibility, a founder who recruited friends because they needed names on the board, board members told to fundraise without knowing what that means. Use situations, never fabricated named client stories. "
    "Explain what is actually going wrong and the perspective the leader needs, then show what changes when the issue is handled properly. Provide useful insight without teaching every execution step; do not write step-by-step numbered guides unless the topic strictly requires it. "
    "STRICT RULES: never use an em dash character. Use normal paragraph structure, not choppy one-sentence-paragraph AI style. No generic filler. No fake quotations, statistics, research, "
    "case studies, client stories, testimonials or platform claims. Never use phrases like 'In today's fast-paced world', 'In the ever-evolving landscape', "
    "'It's important to note', 'Let's dive in', 'Game changer', 'Unlock the power', 'Navigate the complexities', 'Revolutionize'. "
    "Respond ONLY with one valid JSON object, no markdown fences."
)


async def claude_blog(category_key: str, recent_titles: list, correction: str = "", draft: dict = None) -> dict:
    config = CATEGORIES[category_key]
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
    chat = LlmChat(api_key=api_key, session_id=f"blog-{uuid.uuid4()}", system_message=BLOG_SYSTEM).with_model("anthropic", os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"))
    if correction and draft:
        prompt = f"Your previous {config['name']} article draft failed validation.\nFailures:\n{correction}\n\nPrevious draft JSON:\n{json.dumps(draft)}\n\nFix ONLY the validation failures. Keep the same topic unless the failure requires a new topic. Return JSON: {{\"title\": str, \"excerpt\": str (1-2 sentences), \"body\": str (350-550 words, absolute maximum 650, use lines starting with '## ' as subheadings only if they genuinely help, blank line between paragraphs)}}"
    else:
        prompt = (
            f"Write one new blog article in the category: {config['name']}.\n"
            f"Recent published titles in this category (choose a topic and angle that does NOT substantially repeat any of them):\n"
            + ("\n".join(f"- {title}" for title in recent_titles) if recent_titles else "- (none yet)")
            + "\n\nThe article must target 350 to 550 words and must never exceed 650 words. Do not pad the article to reach a minimum; if the point is made naturally in around 350 words, stop. "
            "Make one specific point well (for example 'Why Adding More People Will Not Fix an Inactive Board', not 'Everything You Need to Know About Building a Strong Board'). "
            "Use at most one or two short '## ' subheadings, and only if they genuinely help. End by making the next step clear and moving the reader toward the solution; never end with generic tips or 'hopefully this helps'. "
            "Do not write the CTA link or button; the application appends it. Vary the angle from the recent titles.\n"
            "Return JSON: {\"title\": str, \"excerpt\": str (1-2 sentences), \"body\": str (paragraphs separated by blank lines, subheadings as lines starting with '## ')}"
        )
    response = await chat.send_message(UserMessage(text=prompt))
    text = response if isinstance(response, str) else getattr(response, "text", str(response))
    return parse_json_response(text)


def validate_article(article: dict, category_key: str, recent_titles: list, existing_slugs: set) -> list:
    errors = []
    title = (article.get("title") or "").strip()
    excerpt = (article.get("excerpt") or "").strip()
    body = (article.get("body") or "").strip()
    if not title:
        errors.append("Title missing")
    if not excerpt:
        errors.append("Excerpt missing")
    if not body:
        errors.append("Article body empty")
    words = len(re.findall(r"\S+", body))
    if body and not 300 <= words <= 650:
        errors.append(f"Word count {words} outside the 350-550 target (absolute maximum 650)")
    blocks = [block.strip() for block in re.split(r"\n{2,}", body) if block.strip() and not block.strip().startswith("## ")]
    short_paragraphs = sum(1 for block in blocks if len(re.findall(r"\S+", block)) < 12)
    if blocks and short_paragraphs > 3:
        errors.append("Too many one-sentence paragraphs; use normal paragraph structure")
    full = f"{title}\n{excerpt}\n{body}"
    if "—" in full:
        errors.append("Contains em dash character")
    lowered = full.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            errors.append(f"Contains banned phrase: {phrase}")
    if re.search(r"\b\d{1,3}(\.\d+)?\s*%|\baccording to (a|the|recent) (study|survey|report|research)", lowered):
        errors.append("Contains unsupported statistics or research claims")
    if title and slugify_title(title) in existing_slugs:
        errors.append("Duplicate slug")
    normalized = re.sub(r"[^a-z0-9 ]", "", title.lower())
    for recent in recent_titles:
        if normalized and normalized == re.sub(r"[^a-z0-9 ]", "", recent.lower()):
            errors.append("Substantially duplicates a recent title")
    return errors


async def create_scheduled_blog_post(db, category_key: str, scheduled_date: str, publish_now: bool = False) -> dict:
    """Generate + validate + schedule one post. Unique key: category + scheduled_date."""
    config = CATEGORIES[category_key]
    ts = now_tz().isoformat()
    try:
        await db.blog_posts.insert_one({"blog_post_id": str(uuid.uuid4()), "category_key": category_key, "category": config["name"], "scheduled_date": scheduled_date, "publication_status": "Generating", "created_at": ts, "title": "", "slug": ""})
    except Exception:
        return {"skipped": True, "reason": "A post for this category and scheduled date already exists"}
    query = {"category_key": category_key, "scheduled_date": scheduled_date}
    recent = await db.blog_posts.find({"category_key": category_key, "publication_status": "Published"}, {"_id": 0, "title": 1}).sort("published_at", -1).to_list(12)
    recent_titles = [post["title"] for post in recent if post.get("title")]
    existing_slugs = {post["slug"] async for post in db.blog_posts.find({"slug": {"$ne": ""}}, {"_id": 0, "slug": 1})}
    try:
        article = await claude_blog(category_key, recent_titles)
        errors = validate_article(article, category_key, recent_titles, existing_slugs)
        if errors:
            article = await claude_blog(category_key, recent_titles, correction="\n".join(errors), draft=article)
            errors = validate_article(article, category_key, recent_titles, existing_slugs)
        if errors:
            await db.blog_posts.update_one(query, {"$set": {"publication_status": "Validation Failed", "generation_status": "Generated", "validation_status": "Failed", "title": article.get("title", ""), "error": "; ".join(errors)}})
            await send_owner_alert("Nonprofit Board Builder Blog Post Failed Validation", [("Category", config["name"]), ("Intended publication date", scheduled_date), ("Title", article.get("title", "")), ("Validation errors", "; ".join(errors))])
            return {"status": "Validation Failed", "errors": errors}
        slug = slugify_title(article["title"])
        update = {
            "title": article["title"].strip(), "slug": slug, "excerpt": article["excerpt"].strip(),
            "body": article["body"].strip(), "cta_label": config["cta_label"], "cta_button": config["cta_button"],
            "cta_url": config["cta_url"], "generation_status": "Generated", "validation_status": "Passed",
            "publication_status": "Published" if publish_now else "Pending Review", "error": "",
        }
        if publish_now:
            update["published_at"] = now_tz().isoformat()
        await db.blog_posts.update_one(query, {"$set": update})
        if not publish_now:
            await send_owner_alert("New Blog Draft Ready for Your Review", [("Category", config["name"]), ("Title", update["title"]), ("Scheduled date", scheduled_date), ("Review at", f"{os.environ.get('PUBLIC_ORIGIN', 'https://nonprofitboardbuilder.com')}/admin")])
        return {"status": update["publication_status"], "slug": slug, "title": update["title"]}
    except Exception as exc:
        await db.blog_posts.update_one(query, {"$set": {"publication_status": "Failed", "error": str(exc)[:500]}})
        await send_owner_alert("Nonprofit Board Builder Blog Automation Error", [("Category", config["name"]), ("Schedule", scheduled_date), ("Error", str(exc)[:500]), ("Generation occurred", "Attempted"), ("Validation occurred", "See error"), ("Published", "No")])
        return {"status": "Failed", "error": str(exc)[:300]}


async def regenerate_blog_post(db, post: dict) -> dict:
    """Replace an unpublished draft's content with a freshly generated article."""
    category_key = post["category_key"]
    query = {"blog_post_id": post["blog_post_id"]}
    await db.blog_posts.update_one(query, {"$set": {"publication_status": "Generating"}})
    recent = await db.blog_posts.find({"category_key": category_key, "publication_status": "Published"}, {"_id": 0, "title": 1}).sort("published_at", -1).to_list(12)
    recent_titles = [item["title"] for item in recent if item.get("title")]
    existing_slugs = {item["slug"] async for item in db.blog_posts.find({"slug": {"$ne": ""}, "blog_post_id": {"$ne": post["blog_post_id"]}}, {"_id": 0, "slug": 1})}
    try:
        article = await claude_blog(category_key, recent_titles)
        errors = validate_article(article, category_key, recent_titles, existing_slugs)
        if errors:
            article = await claude_blog(category_key, recent_titles, correction="\n".join(errors), draft=article)
            errors = validate_article(article, category_key, recent_titles, existing_slugs)
        if errors:
            await db.blog_posts.update_one(query, {"$set": {"publication_status": "Validation Failed", "error": "; ".join(errors)}})
            return {"status": "Validation Failed", "errors": errors}
        update = {"title": article["title"].strip(), "slug": slugify_title(article["title"]), "excerpt": article["excerpt"].strip(), "body": article["body"].strip(), "publication_status": "Pending Review", "error": "", "regenerated_at": now_tz().isoformat()}
        await db.blog_posts.update_one(query, {"$set": update})
        return {"status": "Pending Review"}
    except Exception as exc:
        await db.blog_posts.update_one(query, {"$set": {"publication_status": "Failed", "error": str(exc)[:500]}})
        return {"status": "Failed", "error": str(exc)[:300]}


# ---------------- NURTURE ----------------
async def get_nurture_segments(db) -> dict:
    settings = await db.marketing_settings.find_one({"key": "nurture_segments"}, {"_id": 0}) or {}
    ids = settings.get("ids", {})
    if all(ids.get(key) for key in SEGMENT_NAMES):
        return ids
    resend.api_key = os.environ["RESEND_API_KEY"]
    listing = await resend.Segments.list_async({"limit": 100})
    data = listing.get("data", listing) if isinstance(listing, dict) else listing
    existing = {item.get("name"): item.get("id") for item in (data or []) if isinstance(item, dict)}
    for key, name in SEGMENT_NAMES.items():
        if not ids.get(key):
            segment_id = existing.get(name)
            if not segment_id:
                created = await resend.Segments.create_async({"name": name})
                segment_id = created.get("id") if isinstance(created, dict) else getattr(created, "id", "")
            ids[key] = segment_id
    await db.marketing_settings.update_one({"key": "nurture_segments"}, {"$set": {"ids": ids}}, upsert=True)
    return ids


async def sync_lead_nurture(db, lead: dict) -> None:
    """Latest submission wins: one active nurture category per contact."""
    email = lead["email"].lower()
    source = lead["offer_source"]
    ts = now_tz().isoformat()
    await db.nurture_contacts.update_one(
        {"email": email},
        {"$set": {"active_offer_source": source, "name": lead.get("name", ""), "organization": lead.get("organization", ""), "updated_at": ts},
         "$setOnInsert": {"created_at": ts, "nurture_status": "lead"}},
        upsert=True)
    try:
        segments = await get_nurture_segments(db)
        contact_id = await upsert_contact(email=email, first_name=lead.get("name", ""), last_name="", properties={}, segment_id=segments[source], topic_id=os.environ["RESEND_BOARD_BUILDING_TOPIC_ID"])
        for key, segment_id in segments.items():
            if key != source and segment_id:
                try:
                    await resend.ContactSegments.remove_async({"segment_id": segment_id, "email": email})
                except Exception:
                    pass
        await db.nurture_contacts.update_one({"email": email}, {"$set": {"resend_contact_id": contact_id, "segment_sync_status": "Synced"}})
    except Exception as exc:
        await db.nurture_contacts.update_one({"email": email}, {"$set": {"segment_sync_status": "Failed", "segment_sync_error": str(exc)[:300]}})


async def stop_recruitment_nurture(db, email: str) -> None:
    email = email.lower()
    await db.nurture_contacts.update_one({"email": email}, {"$set": {"nurture_status": "customer", "active_offer_source": "", "updated_at": now_tz().isoformat()}}, upsert=True)
    try:
        segments = await get_nurture_segments(db)
        resend.api_key = os.environ["RESEND_API_KEY"]
        await resend.ContactSegments.remove_async({"segment_id": segments["recruitment"], "email": email})
    except Exception as exc:
        logger.warning("Recruitment nurture removal failed for %s: %s", email, exc)


def nurture_email_html(template: dict, origin: str) -> str:
    paragraphs = "".join(f"<p style='font-size:18px;line-height:1.6;color:#000;margin:0 0 16px;'>{html.escape(p)}</p>" for p in template["paragraphs"])
    return (
        f"<div style='background:#ffffff;padding:26px;font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:auto;'>"
        f"<h1 style='font-size:24px;color:#000;'>{html.escape(template['headline'])}</h1>{paragraphs}"
        f"<p><a href='{origin}{template['url']}' style='display:inline-block;background:#087e5b;color:#ffffff;padding:14px 24px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:17px;'>{html.escape(template['cta'])}</a></p>"
        f"<p style='font-size:12px;color:#667;margin-top:30px;'>Nonprofit Board Builder — {html.escape(os.environ.get('POSTAL_ADDRESS', ''))}<br/>"
        f"<a href='{{{{{{RESEND_UNSUBSCRIBE_URL}}}}}}'>Unsubscribe</a></p></div>"
    )


async def run_weekly_nurture(db, origin: str, test_only: bool, test_email: str = "") -> dict:
    """One Tuesday campaign per segment per ISO week. Failed sends never advance the rotation."""
    week = now_tz("LEAD_NURTURE_TIMEZONE").strftime("%G-W%V")
    results = {}
    for source, templates in NURTURE_TEMPLATES.items():
        key = {"segment": source, "scheduled_week": week}
        ts = now_tz().isoformat()
        try:
            await db.nurture_sends.insert_one({**key, "status": "Sending", "created_at": ts, "test_only": test_only})
        except Exception:
            results[source] = {"skipped": True, "reason": "Already sent this week (duplicate protection)"}
            continue
        rotation = await db.nurture_rotation.find_one({"segment": source}, {"_id": 0}) or {"last_sent": 0}
        index = rotation["last_sent"] % len(templates)
        template = templates[index]
        html_body = nurture_email_html(template, origin)
        try:
            if test_only:
                resend.api_key = os.environ["RESEND_API_KEY"]
                recipient = test_email or os.environ.get("OWNER_TEST_EMAIL") or os.environ["OWNER_NOTIFICATION_EMAIL"]
                response = await resend.Emails.send_async({"from": os.environ["NONPROFIT_SENDER"], "to": [recipient], "subject": f"[TEST] {template['subject']}", "html": html_body.replace("{{{RESEND_UNSUBSCRIBE_URL}}}", f"{origin}/privacy-policy")})
                broadcast_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", "")
            else:
                segments = await get_nurture_segments(db)
                broadcast_id = await create_segment_broadcast(segment_id=segments[source], sender=os.environ["NONPROFIT_SENDER"], subject=template["subject"], html_content=html_body, name=f"Nurture {source} {week}", send=True)
            await db.nurture_sends.update_one(key, {"$set": {"status": "Sent", "template": index + 1, "broadcast_id": broadcast_id or "", "sent_at": now_tz().isoformat()}})
            await db.nurture_rotation.update_one({"segment": source}, {"$set": {"last_sent": index + 1, "updated_at": now_tz().isoformat()}}, upsert=True)
            results[source] = {"sent": True, "template": index + 1, "subject": template["subject"], "cta_url": template["url"]}
        except Exception as exc:
            await db.nurture_sends.update_one(key, {"$set": {"status": "Failed", "template": index + 1, "error": str(exc)[:400]}})
            await send_owner_alert("Nonprofit Board Builder Lead Email Automation Error", [("Audience", SEGMENT_NAMES[source]), ("Template", index + 1), ("Intended date", week), ("Error", str(exc)[:400])])
            results[source] = {"sent": False, "error": str(exc)[:200]}
    return results


# ---------------- SCHEDULER ----------------
async def marketing_loop(db) -> None:
    origin = os.environ.get("PUBLIC_ORIGIN", "https://nonprofitboardbuilder.com")
    while True:
        try:
            if os.environ.get("BLOG_AUTOMATION_ENABLED", "false").lower() == "true":
                now = now_tz("BLOG_TIMEZONE")
                publish_time = os.environ.get("BLOG_PUBLISH_TIME", "08:00")
                for key, config in CATEGORIES.items():
                    if now.weekday() == config["day"] and now.strftime("%H:%M") >= publish_time:
                        await create_scheduled_blog_post(db, key, now.strftime("%Y-%m-%d"), publish_now=False)
            if os.environ.get("LEAD_NURTURE_ENABLED", "false").lower() == "true":
                now = now_tz("LEAD_NURTURE_TIMEZONE")
                day_name = os.environ.get("LEAD_NURTURE_DAY", "Tuesday")
                send_time = os.environ.get("LEAD_NURTURE_TIME", "07:00")
                if now.strftime("%A") == day_name and now.strftime("%H:%M") >= send_time:
                    await run_weekly_nurture(db, origin, test_only=False)
        except Exception as exc:
            logger.error("Marketing loop error: %s", exc)
        await asyncio.sleep(300)


def week_key() -> str:
    return now_tz("LEAD_NURTURE_TIMEZONE").strftime("%G-W%V")


def yesterday_scheduled(days: int = 1) -> str:
    return (now_tz() - timedelta(days=days)).strftime("%Y-%m-%d")
