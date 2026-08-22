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
from board_content_topics import BOARD_CONTENT_TOPICS
from resend_service import create_segment_broadcast, upsert_contact

logger = logging.getLogger(__name__)

CATEGORIES = {
    "recruitment": {"name": "Board Recruitment", "day": 0, "cta_label": "Ready to Recruit Your Board?", "cta_button": "See How We Can Help You Recruit", "cta_url": "/recruit"},
    "reactivation": {"name": "Board Reactivation", "day": 2, "cta_label": "Ready to Reactivate Your Board?", "cta_button": "See How We Can Help You Reactivate", "cta_url": "/reactivate"},
    "fundraising_activation": {"name": "Board Fundraising Activation", "day": 4, "cta_label": "Ready to Activate Your Board Around Fundraising?", "cta_button": "See How We Can Help You Activate Your Board", "cta_url": "/activate"},
    "transformation": {"name": "Complete Board Transformation", "day": 5, "cta_label": "Ready to Transform Your Board?", "cta_button": "Start Your Complete Board Transformation", "cta_url": "/board-transformation"},
}
BANNED_PHRASES = ["in today's fast-paced world", "in the ever-evolving landscape", "it's important to note", "let's dive in", "game changer", "unlock the power", "navigate the complexities", "revolutionize", "game-changer"]

SEGMENT_NAMES = {
    "recruitment": "Nonprofit Board Builder — Recruitment Leads",
    "reactivation": "Nonprofit Board Builder — Reactivation Leads",
    "fundraising_activation": "Nonprofit Board Builder — Fundraising Activation Leads",
}

NURTURE_TEMPLATES = {
    "fundraising_activation": [
        {"subject": "Before You Decide What to Do With Your Board", "greeting": True,
         "paragraphs": [
             "You came to me because your Board is not carrying its share of the fundraising, and you are deciding what to do about it.",
             "Before you decide whether you want to activate your Board yourself or have me work through the process with you, I want you to know a little about the person behind the process.",
             "I started as a nonprofit founder many years ago, where I built my first Board.",
             "I made mistakes, damaged relationships, learned from the experience, rebuilt my board, and eventually developed a process that worked.",
             "Since then, I have served on nonprofit Boards, worked as a fundraising consultant, served as Vice President of a fundraising consulting firm working with nonprofits across the United States, trained hundreds of nonprofit founders and fundraisers, helped nonprofits strengthen their Boards, and contributed to raising more than $5 million.",
             "Today, I work with founders and executive directors so they do not have to carry fundraising alone while their Board sits on the sidelines.",
             "If you are still trying to decide how to move forward with your Board, start here.",
         ],
         "cta": "LEARN ABOUT ROONEY", "url": "/about-rooney",
         "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
        {"subject": "You Can Activate Your Board Yourself", "greeting": True,
         "paragraphs": [
             "You should not be the only person carrying the fundraising responsibility for your organization.",
             "I have created a way for you to lead your Board through the complete fundraising activation process yourself — and stop carrying fundraising alone.",
             "You will get your Board involved in building the fundraising plan, turn everyone's ideas into one fundraising strategy, bring the plan back to the Board for review, facilitate its adoption, establish clear responsibility and give participating members practical tools to begin taking action.",
             "People who plan together execute together. When your Board helps build the plan, they understand it, take ownership of it and help execute it.",
             "You are doing it yourself, but you are not doing it alone — you are following my process with the tools and support you need to execute it.",
             "The investment is $497, one time.",
             "Your investment is protected by our 100% money-back guarantee.",
             "If you are ready to stop carrying fundraising alone and start activating your Board, you can begin now.",
         ],
         "cta": "ACTIVATE MY BOARD MYSELF — $497", "url": "/activate-your-board-yourself",
         "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
        {"subject": "Want Me to Help You Activate Your Board?", "greeting": True,
         "paragraphs": [
             "You do not have to figure out how to turn your Board Members into fundraising participants alone.",
             "If you want someone who has done this before to work through the Board Fundraising Activation process with you, this is the option I created for you.",
             "We will get your Board involved in the fundraising planning, align everyone around one fundraising strategy, take the plan through Board review and adoption, establish clear responsibility, and equip your members to begin executing.",
             "The outcome is not a fundraising document. The outcome is a Board that understands the fundraising direction, helped shape it, knows what it is responsible for and is better equipped to help your organization raise money.",
             "The investment is $2,497.",
             "Your investment is protected by our 100% money-back guarantee.",
         ],
         "cta": "ACTIVATE MY BOARD WITH ROONEY — $2,497", "url": "/board-activation-proposal",
         "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
    ],
    "recruitment": [
        {"subject": "Before You Decide How to Build Your Board", "greeting": True,
         "paragraphs": [
             "You came to me because your nonprofit needs Board Members.",
             "Before you decide whether you want to recruit them yourself or have me work with you, I want you to know a little about the person behind the process.",
             "I started as a nonprofit founder many years ago, where I built my first Board.",
             "I made mistakes, damaged relationships, learned from the experience, rebuilt my Board, and eventually developed a process that worked.",
             "Since then, I have served on nonprofit Boards, worked as a fundraising consultant, served as Vice President of a fundraising consulting firm working with nonprofits across the United States, trained hundreds of nonprofit founders and fundraisers, helped nonprofits strengthen their Boards, and contributed to raising more than $5 million.",
             "Today, I work with founders and executive directors so they do not have to make the mistakes I made, damage relationships, or waste months trying to figure out how to build the Board their organization needs.",
             "If you are still trying to decide how to move forward with your Board, start here.",
         ],
         "cta": "MEET ROONEY & SEE HOW I CAN HELP", "url": "/about-rooney",
         "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
        {"subject": "You Can Build Your Board Yourself", "greeting": True,
         "paragraphs": [
             "If you want to recruit your Board yourself, you do not have to spend months figuring out what to do next.",
             "I have created a way for you to follow the same Board Recruitment process I use and actually build the Board your nonprofit needs.",
             "You will identify the types of Board Members your organization should be recruiting, launch your actual Recruitment campaign, put your opportunity in front of professionals, work through the applicants who respond, interview the people you want to consider, complete your references and due diligence, and properly bring the people you choose into your organization.",
             "You will have the Recruitment materials you need.",
             "Your organization will have its own Board Application.",
             "Your opportunity can also be shared with our existing Board Applicant Network of professionals interested in nonprofit Board service.",
             "And when you are finished, you will not only have worked toward building your Board — you will understand the Recruitment process well enough to use it again whenever your nonprofit needs another Board Member.",
             "You are doing it yourself, but you are not doing it alone.",
             "If you get stuck, need clarification, want something reviewed, or need help moving through a step, you can reach out to me for support.",
             "The investment is $297, one time.",
             "Your investment is protected by our 100% money-back guarantee.",
             "If you are ready to stop waiting for the right people to somehow find you and start building the Board your nonprofit needs, you can begin now.",
         ],
         "cta": "BUILD MY BOARD MYSELF — $297", "url": "/offer/recruitment",
         "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
        {"subject": "Want Me to Help You Build Your Board?", "greeting": True,
         "paragraphs": [
             "You do not have to build your Board alone.",
             "If your nonprofit needs stronger people around the table and you want someone who has done this before to work through the Recruitment with you, this is the option I created for you.",
             "We will work together to build the Board your organization needs.",
             "The goal is not to give you another plan and leave you to figure it out.",
             "The goal is to get your Recruitment moving, attract quality professionals, help you work through the people who respond, and properly bring the people you choose into your organization so you can begin building with them.",
             "You remain in control of who joins your Board.",
             "I bring the Recruitment process, experience, structure and support needed to help you get there.",
             "Your nonprofit should not have to keep struggling because you do not have the right people around the table.",
             "If you want me directly involved in helping you change that, come build your Board with me.",
             "The investment is $1,497.",
         ],
         "cta": "BUILD MY BOARD WITH ROONEY — $1,497", "url": "/offer/recruitment",
         "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
    ],
    "reactivation": [
        {"subject": "Before You Decide What to Do With Your Board", "greeting": True,
         "paragraphs": [
             "You came to me because your Board is not functioning the way your organization needs it to.",
             "Maybe people have stopped participating. Maybe they attend meetings but do not take responsibility. Maybe you are carrying most of the organization while also carrying Board Members who were supposed to help carry it with you.",
             "Before you decide how you want to deal with that, I want you to know a little about the person behind this process.",
             "I started as a nonprofit founder many years ago, where I built my first Board. I made mistakes, damaged relationships, learned from the experience, rebuilt my Board, and eventually developed a process that worked.",
             "Since then, I have served on nonprofit Boards, worked as a fundraising consultant, served as Vice President of a fundraising consulting firm working with nonprofits across the United States, trained hundreds of nonprofit founders and fundraisers, helped nonprofits strengthen their Boards, and contributed to raising more than $5 million.",
             "Today, I work with founders and executive directors so they can build Boards that actually help carry the mission.",
             "If you want to know more about me and how I work, start here.",
         ], "cta": "MEET ROONEY & SEE HOW I CAN HELP", "url": "/about-rooney", "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
        {"subject": "You Can Reactivate Your Board Yourself", "greeting": True,
         "paragraphs": [
             "You do not have to keep carrying dead weight on your Board.",
             "If your Board Members are disengaged, the answer is not simply to keep reminding them to attend meetings or asking them to become more active.",
             "You need clarity. Who is actually willing and able to continue serving? Who needs clearer responsibility? Who is prepared to stand up and take ownership? And who no longer has the capacity or willingness to carry Board responsibility?",
             "I have created a way for you to work through that process yourself.",
             "You will understand what caused the disengagement, give every current Board Member an opportunity to recommit, have the conversations that need to happen, and give the people who remain clear responsibility for helping move your organization forward.",
             "You will not have to walk blindly into those conversations. Each Board Member's own responses will help you understand where they are before you speak with them.",
             "And once you have agreed on how a continuing Board Member will contribute, you can create their individual Board Member Portfolio so they leave knowing what they own.",
             "You are doing the process yourself, but you are not doing it alone. If you get stuck, need clarification, want something reviewed or need help moving through a difficult step, you can reach out to me for support.",
             "The investment is $497, one time. Your investment is protected by our 100% money-back guarantee.",
             "If you are ready to stop carrying a Board that is not carrying the mission with you, start now.",
         ], "cta": "REACTIVATE MY BOARD MYSELF — $497", "url": "/reactivate-your-board-yourself", "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
        {"subject": "Want Me to Help You Reactivate Your Board?", "greeting": True,
         "paragraphs": [
             "You do not have to have the difficult conversations with your Board without a process or support.",
             "If you want me directly involved, we can work through the Reactivation process together.",
             "The goal is not to pressure disengaged Board Members into staying. The goal is to find out who is genuinely ready to stand up, what responsibility those people are prepared to carry, and how to deal respectfully with the people who are no longer willing or able to serve actively.",
             "We will work through your current Board and turn vague membership into clarity.",
             "Those who are ready to serve should know where they fit and what they own. Those who are no longer prepared to carry Board responsibility should not remain dead weight for the founder to carry indefinitely.",
             "Your Board should help carry the organization forward.",
             "If you want me to work through that process with you, come reactivate your Board with me.",
             "The investment is $1,997. Your investment is protected by our 100% money-back guarantee.",
         ], "cta": "REACTIVATE MY BOARD WITH ROONEY — $1,997", "url": "/board-reactivation-proposal", "closing": ["Rooney Akpesiri", "The Nonprofit Board Builder"]},
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


async def next_topic_for(db, category_key: str) -> dict:
    """Sequential per-category topic progression. Cycles back only after all 25 are published."""
    topics = BOARD_CONTENT_TOPICS[category_key]
    published = await db.blog_posts.count_documents(
        {"category_key": category_key, "topic_number": {"$gte": 1}, "publication_status": "Published"})
    index = published % len(topics)
    return {"topic_number": index + 1, "topic_title": topics[index], "published_in_category": published}


async def claude_blog(category_key: str, recent_titles: list, correction: str = "", draft: dict = None, topic_title: str = "") -> dict:
    config = CATEGORIES[category_key]
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
    chat = LlmChat(api_key=api_key, session_id=f"blog-{uuid.uuid4()}", system_message=BLOG_SYSTEM).with_model("anthropic", os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"))
    if correction and draft:
        prompt = f"Your previous {config['name']} article draft failed validation.\nFailures:\n{correction}\n\nPrevious draft JSON:\n{json.dumps(draft)}\n\nFix ONLY the validation failures. Keep the same topic{' and the exact title: ' + topic_title if topic_title else ' unless the failure requires a new topic'}. Return JSON: {{\"title\": str, \"excerpt\": str (1-2 sentences), \"body\": str (350-550 words, absolute maximum 650, use lines starting with '## ' as subheadings only if they genuinely help, blank line between paragraphs)}}"
    elif topic_title:
        prompt = (
            f"Write one blog article in the category: {config['name']}.\n"
            f"The article title MUST be EXACTLY: {topic_title}\n"
            "Do not change, shorten or rephrase the title.\n\n"
            "Follow this five-part structure in the body (do not label the parts, write them as flowing sections):\n"
            "1. THE PROBLEM: open with the specific problem this topic represents so the founder immediately recognizes their situation.\n"
            "2. WHAT IS REALLY HAPPENING: show the underlying limitation or reason the problem exists.\n"
            "3. ROONEY'S INSIGHT: give the founder a useful way to understand the problem that demonstrates real board-development expertise. Provide genuine insight, not a sales pitch.\n"
            "4. WHAT THE FOUNDER CAN DO: give a practical next step connected to the topic so the reader finishes knowing what needs to happen next.\n"
            "5. Do not write the CTA link or button; the application appends it. End by making the next step clear and moving the reader toward the solution.\n\n"
            "Use this board terminology consistently where relevant: Powerhouse Board, Board Recruitment, Board Reactivation, Board Fundraising Activation, Complete Board Transformation, board members, fundraising, professional expertise, relationships and networks, organizational capabilities, board responsibility, board accountability, mission, fund, grow and scale. Do not introduce competing terminology.\n\n"
            "The article must target 350 to 550 words and must never exceed 650 words. Use at most one or two short '## ' subheadings, and only if they genuinely help.\n"
            "Return JSON: {\"title\": str, \"excerpt\": str (1-2 sentences), \"body\": str (paragraphs separated by blank lines, subheadings as lines starting with '## ')}"
        )
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


async def generate_linkedin_snippet(db, post) -> str:
    """Three-paragraph LinkedIn post (problem / possibility / article-as-methodology) + article link."""
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
    chat = LlmChat(api_key=api_key, session_id=f"snippet-{uuid.uuid4()}", system_message=BLOG_SYSTEM).with_model("anthropic", os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6"))
    prompt = (
        "Write a ready-to-paste LinkedIn post promoting this published article.\n\n"
        f"Article title: {post['title']}\n"
        f"Category: {CATEGORIES[post['category_key']]['name']}\n"
        f"Article excerpt: {post.get('excerpt', '')}\n"
        f"Article body:\n{post.get('body', '')[:3500]}\n\n"
        "Structure — EXACTLY three paragraphs, EXACTLY two sentences each, separated by blank lines:\n"
        "Paragraph 1: two sentences that identify the problem and make the founder recognize their present situation.\n"
        "Paragraph 2: two sentences that help them see what becomes possible when the problem is addressed properly.\n"
        "Paragraph 3: two sentences positioning the article as the methodology and driving them to read it.\n\n"
        "Speak directly to nonprofit founders in Rooney's voice. No hashtags, no emojis, no links (the application appends the article link), no headings, no bullet points, no em dashes.\n"
        'Return JSON: {"snippet": str}'
    )
    response = await chat.send_message(UserMessage(text=prompt))
    data = parse_json_response(response)
    text = (data.get("snippet") or "").strip()
    if not text:
        raise ValueError("Empty LinkedIn snippet")
    origin = os.environ.get("PUBLIC_ORIGIN", "https://nonprofitboardbuilder.com").rstrip("/")
    snippet = f"{text}\n\nRead the full article: {origin}/blog/{post['slug']}"
    await db.blog_posts.update_one({"blog_post_id": post["blog_post_id"]}, {"$set": {"linkedin_snippet": snippet, "linkedin_snippet_generated_at": now_tz().isoformat()}})
    return snippet


async def create_scheduled_blog_post(db, category_key: str, scheduled_date: str, publish_now: bool = False) -> dict:
    """Generate + validate + schedule one post from the canonical topic library. Unique key: category + scheduled_date."""
    config = CATEGORIES[category_key]
    ts = now_tz().isoformat()
    topic = await next_topic_for(db, category_key)
    try:
        await db.blog_posts.insert_one({"blog_post_id": str(uuid.uuid4()), "category_key": category_key, "category": config["name"], "scheduled_date": scheduled_date, "publication_status": "Generating", "created_at": ts, "title": "", "slug": "", "topic_number": topic["topic_number"], "topic_title": topic["topic_title"]})
    except Exception:
        return {"skipped": True, "reason": "A post for this category and scheduled date already exists"}
    query = {"category_key": category_key, "scheduled_date": scheduled_date}
    recent = await db.blog_posts.find({"category_key": category_key, "publication_status": "Published"}, {"_id": 0, "title": 1}).sort("published_at", -1).to_list(12)
    recent_titles = [post["title"] for post in recent if post.get("title")]
    existing_slugs = {post["slug"] async for post in db.blog_posts.find({"slug": {"$ne": ""}}, {"_id": 0, "slug": 1})}
    try:
        article = await claude_blog(category_key, [], topic_title=topic["topic_title"])
        article["title"] = topic["topic_title"]
        errors = validate_article(article, category_key, [], set())
        if errors:
            article = await claude_blog(category_key, [], correction="\n".join(errors), draft=article, topic_title=topic["topic_title"])
            article["title"] = topic["topic_title"]
            errors = validate_article(article, category_key, [], set())
        if errors:
            await db.blog_posts.update_one(query, {"$set": {"publication_status": "Validation Failed", "generation_status": "Generated", "validation_status": "Failed", "title": article.get("title", ""), "error": "; ".join(errors)}})
            await send_owner_alert("Nonprofit Board Builder Blog Post Failed Validation", [("Category", config["name"]), ("Topic", f"{topic['topic_number']}. {topic['topic_title']}"), ("Intended publication date", scheduled_date), ("Validation errors", "; ".join(errors))])
            return {"status": "Validation Failed", "errors": errors}
        slug = slugify_title(article["title"])
        if slug in existing_slugs:
            slug = f"{slug}-{scheduled_date}"
        update = {
            "title": article["title"].strip(), "slug": slug, "excerpt": article["excerpt"].strip(),
            "body": article["body"].strip(), "cta_label": config["cta_label"], "cta_button": config["cta_button"],
            "cta_url": config["cta_url"], "generation_status": "Generated", "validation_status": "Passed",
            "publication_status": "Published" if publish_now else "Pending Review", "error": "",
        }
        if publish_now:
            update["published_at"] = now_tz().isoformat()
        await db.blog_posts.update_one(query, {"$set": update})
        if publish_now:
            try:
                post = await db.blog_posts.find_one(query, {"_id": 0})
                await generate_linkedin_snippet(db, post)
            except Exception as exc:
                logger.warning("LinkedIn snippet generation failed for %s: %s", slug, exc)
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
        topic_title = post.get("topic_title", "")
        article = await claude_blog(category_key, recent_titles, topic_title=topic_title)
        if topic_title:
            article["title"] = topic_title
        errors = validate_article(article, category_key, [] if topic_title else recent_titles, existing_slugs if not topic_title else set())
        if errors:
            article = await claude_blog(category_key, recent_titles, correction="\n".join(errors), draft=article, topic_title=topic_title)
            if topic_title:
                article["title"] = topic_title
            errors = validate_article(article, category_key, [] if topic_title else recent_titles, existing_slugs if not topic_title else set())
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
    if source not in NURTURE_TEMPLATES:
        return
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


RECRUITMENT_PURCHASE_SOURCES = {"direct_diy_board_recruitment_497", "direct_board_recruitment_project"}
REACTIVATION_PURCHASE_SOURCES = {"direct_diy_board_reactivation_497", "direct_board_reactivation_project"}
ACTIVATION_PURCHASE_SOURCES = {"direct_diy_board_activation_497", "direct_board_activation_project_2497"}


async def stop_activation_nurture(db, email: str) -> None:
    email = email.lower()
    await db.nurture_contacts.update_one({"email": email}, {"$set": {"nurture_status": "customer", "active_offer_source": "", "updated_at": now_tz().isoformat()}}, upsert=True)
    try:
        segments = await get_nurture_segments(db)
        resend.api_key = os.environ["RESEND_API_KEY"]
        await resend.ContactSegments.remove_async({"segment_id": segments["fundraising_activation"], "email": email})
    except Exception as exc:
        logger.warning("Activation nurture removal failed for %s: %s", email, exc)


async def stop_reactivation_nurture(db, email: str) -> None:
    email = email.lower()
    await db.nurture_contacts.update_one({"email": email}, {"$set": {"nurture_status": "customer", "active_offer_source": "", "updated_at": now_tz().isoformat()}}, upsert=True)
    try:
        segments = await get_nurture_segments(db)
        resend.api_key = os.environ["RESEND_API_KEY"]
        await resend.ContactSegments.remove_async({"segment_id": segments["reactivation"], "email": email})
    except Exception as exc:
        logger.warning("Reactivation nurture removal failed for %s: %s", email, exc)


async def stop_recruitment_nurture_for_purchase(db, transaction: dict, buyer_email: str = "") -> None:
    """Stop the matching prospect nurture the moment a purchase is verified paid. Idempotent; never raises."""
    try:
        source = (transaction or {}).get("purchase_source", "")
        if source not in RECRUITMENT_PURCHASE_SOURCES | REACTIVATION_PURCHASE_SOURCES | ACTIVATION_PURCHASE_SOURCES:
            return
        emails = {value.lower() for value in [buyer_email, (transaction or {}).get("customer_email", "")] if value}
        for email in emails:
            if source in RECRUITMENT_PURCHASE_SOURCES:
                await stop_recruitment_nurture(db, email)
            elif source in ACTIVATION_PURCHASE_SOURCES:
                await stop_activation_nurture(db, email)
            else:
                await stop_reactivation_nurture(db, email)
    except Exception as exc:
        logger.warning("Nurture stop after purchase failed (payment unaffected): %s", exc)


def enabled_nurture_sources() -> set:
    enabled = set()
    if os.environ.get("LEAD_NURTURE_ENABLED", "false").lower() == "true":
        enabled.update(NURTURE_TEMPLATES.keys())
    if os.environ.get("RECRUITMENT_LEAD_NURTURE_ENABLED", "false").lower() == "true":
        enabled.add("recruitment")
    if os.environ.get("REACTIVATION_LEAD_NURTURE_ENABLED", "false").lower() == "true":
        enabled.add("reactivation")
    if os.environ.get("ACTIVATION_LEAD_NURTURE_ENABLED", "false").lower() == "true":
        enabled.add("fundraising_activation")
    return enabled


def nurture_sender(source: str) -> str:
    base = os.environ["NONPROFIT_SENDER"]
    if source in {"recruitment", "reactivation", "fundraising_activation"}:
        address = base.split("<", 1)[1].rstrip(">").strip() if "<" in base else base
        return f"Rooney Akpesiri | The Nonprofit Board Builder <{address}>"
    return base


def nurture_email_html(template: dict, origin: str) -> str:
    parts = ["<div style='background:#ffffff;padding:26px;font-family:Arial,Helvetica,sans-serif;max-width:600px;margin:auto;'>"]
    if template.get("headline"):
        parts.append(f"<h1 style='font-size:24px;color:#000;'>{html.escape(template['headline'])}</h1>")
    if template.get("greeting"):
        parts.append("<p style='font-size:18px;line-height:1.6;color:#000;margin:0 0 16px;'>Hi {{{FIRST_NAME|there}}},</p>")
    parts.append("".join(f"<p style='font-size:18px;line-height:1.6;color:#000;margin:0 0 16px;'>{html.escape(p)}</p>" for p in template["paragraphs"]))
    parts.append(f"<p><a href='{origin}{template['url']}' style='display:inline-block;background:#087e5b;color:#ffffff;padding:14px 24px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:17px;'>{html.escape(template['cta'])}</a></p>")
    if template.get("closing"):
        closing = "<br/>".join(html.escape(line) for line in template["closing"])
        parts.append(f"<p style='font-size:18px;line-height:1.6;color:#000;margin:24px 0 0;'>{closing}</p>")
    parts.append(
        f"<p style='font-size:12px;color:#667;margin-top:30px;'>Nonprofit Board Builder — {html.escape(os.environ.get('POSTAL_ADDRESS', ''))}<br/>"
        f"<a href='{{{{{{RESEND_UNSUBSCRIBE_URL}}}}}}'>Unsubscribe</a></p></div>"
    )
    return "".join(parts)


async def run_weekly_nurture(db, origin: str, test_only: bool, test_email: str = "") -> dict:
    """One Tuesday campaign per segment per ISO week. Failed sends never advance the rotation."""
    week = now_tz("LEAD_NURTURE_TIMEZONE").strftime("%G-W%V")
    results = {}
    enabled = enabled_nurture_sources()
    for source, templates in NURTURE_TEMPLATES.items():
        if not test_only and source not in enabled:
            results[source] = {"skipped": True, "reason": "Nurture disabled for this audience"}
            continue
        if not test_only and os.environ.get("DB_NAME") == "test_database":
            results[source] = {"skipped": True, "reason": "Real nurture broadcasts are disabled in the preview environment"}
            continue
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
                preview_html = html_body.replace("{{{RESEND_UNSUBSCRIBE_URL}}}", f"{origin}/privacy-policy").replace("{{{FIRST_NAME|there}}}", "there")
                response = await resend.Emails.send_async({"from": nurture_sender(source), "to": [recipient], "subject": f"[TEST] {template['subject']}", "html": preview_html})
                broadcast_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", "")
            else:
                segments = await get_nurture_segments(db)
                broadcast_id = await create_segment_broadcast(segment_id=segments[source], sender=nurture_sender(source), subject=template["subject"], html_content=html_body, name=f"Nurture {source} {week}", send=True)
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
                        await create_scheduled_blog_post(db, key, now.strftime("%Y-%m-%d"), publish_now=True)
            if os.environ.get("LEAD_NURTURE_ENABLED", "false").lower() == "true" or enabled_nurture_sources():
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
