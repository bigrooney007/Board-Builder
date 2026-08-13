"""Server-side Claude generation service (Phase 3). All AI calls happen here only."""
import io
import json
import logging
import os
import re
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)

REVIEW_WARNING = "This document is generated as a working template. Review it against your bylaws, policies and applicable legal requirements before using it."

CAMPAIGN_STANDARD = (
    "You are acting as an experienced nonprofit board recruitment consultant preparing FINISHED recruitment materials for a real nonprofit — never a template for the founder to finish. "
    "Use ONLY verified information supplied in the context (organization, board, Module 1 priority profiles, recruitment logistics, live system links). "
    "Never invent programs, achievements, impact statistics, legal status, partnerships, board expectations, meeting schedules, candidate requirements, compensation or application deadlines. "
    "The supplied Board Application URL must appear naturally wherever an application call-to-action belongs (the platform substitutes [APPLICATION LINK] with the real URL). "
    "Never say the opportunity has been posted on an external platform. Never describe board service as paid employment unless the context explicitly says it is compensated. "
    "Adapt language to the actual board type — never describe an Advisory Board as having governing/fiduciary authority. "
    "Write like an experienced human nonprofit leader, not an AI assistant. Avoid 'exciting opportunity', 'calling all changemakers', hype, generic inspirational filler, emojis, fake quotes, invented urgency and hashtag walls. "
    "Each campaign resource serves a DIFFERENT channel — do not repeat the same opening, structure and language used by the other campaign materials. "
    "Recruitment materials should communicate meaningful contribution, not simply attending meetings. The finished resource must require no missing information from the founder."
)

# generation type registry: module, title, schema description (JSON the model must return)
GENERATION_TYPES = {
    "powerhouse_board_blueprint": {"module": 1, "title": "The Board Members Your Organization Needs", "per_application": False, "schema": {
        "recommended_count_statement": "string — ONLY when the customer said they are Not Sure how many board members to recruit: write 'Recommended Number of New Board Members: X' followed by one short sentence explaining the recommendation based on their current board size, active members, gaps, challenges and priorities. When the customer supplied an exact number, return an empty string.",
        "priority_roles": [{
            "role_name": "string — the Role / Expertise Area, e.g. 'Fundraising & Philanthropy' or 'Finance & Accounting'. NEVER invent formal board officer titles such as 'Chief Fundraising Board Officer' — name the expertise area itself.",
            "why_this_person_is_important": "string — exactly TWO concise organization-specific sentences explaining why this expertise is important to THIS nonprofit",
            "how_this_person_can_support": "string — exactly TWO concise organization-specific sentences explaining what this person could help strengthen, lead, open, build or contribute",
            "what_to_look_for": ["string — 3 to 5 concise qualities, experience areas, capabilities or useful relationships relevant to the role"],
        }],
        "internal_analysis": {"present_board_brings": "string — internal use only", "important_gaps": "string — internal use only", "board_needed": "string — internal use only"},
    }, "note": "CRITICAL COUNT RULE: the number of priority_roles MUST EXACTLY EQUAL the number of new board members the customer said they want to recruit (see the recruitment profile context — new_members_count). If they said 1, produce exactly 1. If they said 7, produce exactly 7. There is NO maximum. ONLY if the customer selected 'Not Sure' should you recommend an appropriate number yourself (state it in recommended_count_statement) and produce exactly that many profiles. A single candidate may satisfy more than one need — never claim the organization must recruit one completely separate person for every competency unless the supplied context specifically requires it."},
    "recruitment_strategy": {"module": 0, "title": "Board Recruitment Strategy", "per_application": False, "schema": {
        "executive_summary": "string — NO MORE than TWO short sentences stating the roles being recruited, the channels being used, and that recruitment begins immediately",
        "roles": [{"role_name": "string — a priority board role from Module 1, same order", "person_sought": "string — ONE short sentence describing the type of person being sought"}],
        "channels": [{"channel": "string — ONLY one of: 'Personal Network', 'Referral Network', 'Public Outreach'. Include ONLY channels the customer's intake answers make available. Never include a channel they said they cannot or do not want to use.", "approach": "string — a VERY BRIEF one-to-two sentence practical approach for this channel, mentioning the customer's actual selected outlets where relevant. Never multiple paragraphs."}],
        "selection_criteria": ["string — one concise quality applicants should demonstrate, adapted to the organization's selected board type (mission alignment, relevant skills for a priority role, willingness and capacity to serve, understanding of the board role, ability to contribute to the kind of board being built, participation in meetings and agreed responsibilities, professional conduct and credibility). Never numeric scores. Never statutory/legal requirements."],
    }, "note": "Keep every section concise and practical. No long consulting essays, no repetition of the full Module 1 analysis, no long channel instructions. The timeline and execution roadmap are added by the platform — do not write them."},
    "board_opportunity": {"module": 2, "title": "Board Opportunity", "per_application": False, "schema": {
        "title": "string — professional board opportunity title",
        "introduction": "string — 2 to 4 sentence organization/opportunity introduction",
        "about_the_organization": "string — the organization and its mission in natural prose",
        "who_we_are_looking_for": "string — the priority board roles from Module 1, concisely, in natural prose or a short list",
        "what_board_members_will_contribute": "string",
        "board_expectations": "string",
        "meeting_time_and_location": "string — meeting frequency, time commitment and location/geographic information as supplied",
        "how_to_apply": "string — must contain the exact application URL supplied in the context",
    }, "note": "Write as a real professional board opportunity announcement. Never print internal field labels such as 'Why Recruiting:' or 'Fundraising Contribution:'. Use only the priority roles identified in Module 1 — never invent 10-12 candidate profiles."},
    "application_questions": {"module": 2, "title": "Board Application — Organization-Specific Questions", "per_application": False, "schema": {
        "custom_questions": [{"label": "string — the question", "type": "one of: text, textarea, yes_no", "why": "string — why this question matters for this organization"}],
    }},
    "linkedin_post": {"module": 2, "title": "LinkedIn Recruitment Post", "per_application": False, "schema": {
        "post_text": "string — a complete LinkedIn feed post in the founder's voice, ready to publish, including the application link placeholder [APPLICATION LINK]. NOT a shortened copy of the Recruitment Job Post — it should sound like a person speaking to their professional network. OPENING: a strong natural observation, decision, milestone or invitation relevant to THIS organization (why they are intentionally building the board, the stage reached, why professional expertise matters to the mission — vary the approach). MIDDLE: briefly the organization, mission, what the board is being built to accomplish, and the most important expertise sought from the Module 1 priority profiles (do not overwhelm with an enormous skills list). BOARD CONTRIBUTION: members bring more than attendance — describe meaningful contribution based on actual expectations. CTA: direct invitation to apply with the application link. 150-300 words. Short paragraphs, mobile-readable. No emojis. Never clichés like 'Calling all changemakers!' or 'We're thrilled to announce!'.",
        "hashtags": ["string — OPTIONAL, no more than 3 highly relevant hashtags; return an empty list if hashtags add nothing"],
    }, "note": CAMPAIGN_STANDARD},
    "social_posts": {"module": 2, "title": "Social Media Recruitment Post", "per_application": False, "schema": {
        "post_text": "string — ONE concise board recruitment post suitable for Facebook, Instagram and similar general social channels, including the application link placeholder [APPLICATION LINK]. NOT a copy of the LinkedIn post: slightly more accessible and shareable while remaining professional. Structure: a strong opening; 2-5 short paragraphs; if useful a SHORT list of key expertise being recruited and why those people matter; direct invitation to apply. 100-220 words. Human, simple, mobile-readable, easy to share. Prefer no emojis. No unnecessary hashtags. Never sound like a commercial advertisement.",
    }, "note": CAMPAIGN_STANDARD},
    "recruitment_emails": {"module": 2, "title": "Recruitment Email", "per_application": False, "schema": {
        "subject": "string — ONE strong professional subject line, not ten alternatives",
        "body": "string — a finished professional email the founder can send to their network, supporters, colleagues and professional relationships inviting qualified people to consider the board opportunity, including the application link placeholder [APPLICATION LINK]. Use a natural GENERAL greeting such as 'Hello,' — never [First Name] and never fake personalization. Body: (1) briefly why the founder is reaching out; (2) the organization is recruiting/building its board; (3) the mission briefly; (4) the kinds of professional experience being sought; (5) what board members will help accomplish; (6) invite recipients whose experience aligns to apply; (7) make it natural to forward the opportunity to another suitable professional; (8) the application link; (9) sign with the actual founder/contact information supplied. Never claim the founder personally admires the recipient or that they were specially selected. 225-400 words. Warm, professional, personal without pretending intimacy.",
    }, "note": CAMPAIGN_STANDARD},
    "linkedin_launch_instructions": {"module": 2, "title": "LinkedIn Jobs Launch Guide", "per_application": False, "schema": {
        "steps": [{"title": "string", "instructions": "string — practical instructions covering where to post, how to structure the post, how to use the application link, how to ask others to share, how to contact potential prospects, how to follow up, how to maintain campaign activity. When discussing budget say: 'You can begin with a small controlled test budget, such as $20 where the option is available, and increase it only if you choose. LinkedIn's available posting and promotion options may vary.' NEVER state that LinkedIn charges $20 as a universal platform fact. Do not fabricate LinkedIn screenshots or exact current UI labels."}],
    }},
    "board_recruitment_job_post": {"module": 2, "title": "Recruitment Job Post", "per_application": False, "schema": {
        "title": "string — a professional opportunity title using the organization's actual board terminology, e.g. 'Founding Board Member | Help Shape [Mission Area]' or 'Board Member Opportunity | Help Build [Meaningful Outcome]'. No clickbait.",
        "post_body": "string — the organization's PRIMARY professional board recruitment opportunity, suitable for professional platforms such as LinkedIn Jobs, BoardSource, Idealist and VolunteerMatch (never claim it has already been published anywhere). Written for a professional who may never have heard of the nonprofit. Use these exact section headings in this order, each on its own line in UPPERCASE, omitting a section only when no supporting data exists: OPENING (2-4 strong sentences — why the organization is building/recruiting its board and the opportunity for capable professionals, specific to this organization); ABOUT THE ORGANIZATION (what it does, who it serves, its mission, relevant direction — concise and factual); THE OPPORTUNITY (what board service means within THIS organization — strategy, governance, expertise, relationships, partnerships, fundraising, growth, leadership, committee work only where supported); WHO WE ARE LOOKING FOR (translate the approved Module 1 priority profiles into outward-facing professional expertise — never paste internal phrases like 'Why this role is important'; where appropriate note that candidates bringing experience across several areas are welcome); BOARD MEMBER EXPECTATIONS (only actually-supported items); PRACTICAL DETAILS (only KNOWN meeting frequency, format, location, time commitment, term, deadline — omit unknown items entirely, never write 'Not provided'); CALL TO ACTION (a strong direct invitation containing the application link placeholder [APPLICATION LINK]). 450-750 words depending on available information. Professional, credible, specific, human, purpose-driven. Clearly represent the actual nature of the board opportunity; NEVER describe an unpaid nonprofit board role as salaried employment.",
    }, "note": CAMPAIGN_STANDARD},
    "personal_invitation_email": {"module": 2, "title": "Personal Invitation Email", "per_application": False, "schema": {
        "subject": "string", "body": "string — a warm personal email inviting someone the founder already knows to consider the board opportunity, includes the application link placeholder [APPLICATION LINK]",
    }},
    "personal_invitation_message": {"module": 2, "title": "Personal Invitation Message", "per_application": False, "schema": {
        "message": "string — a concise direct message version for LinkedIn, Facebook, text or another direct-message channel, includes the application link placeholder [APPLICATION LINK]",
    }},
    "referral_request_email": {"module": 2, "title": "Referral Recruitment Message", "per_application": False, "schema": {
        "message": "string — a finished referral message the founder can send to current board members, supporters, colleagues, partners, community leaders, friends and advisors asking them to help identify people who may be a good fit for the board, including the application link placeholder [APPLICATION LINK]. This asks for REFERRALS — never pressure the recipient to join the board themselves. Use a natural general greeting with no unresolved placeholder. Briefly explain the organization is intentionally recruiting new board members; the top categories of people/expertise needed; why those people would be useful; ask the recipient to think of strong matches in their network and to forward/share the application link directly. Sign with the actual founder/contact information supplied. 150-275 words. Personal, direct, easy to forward, relationship-preserving. Do not over-explain the entire organization.",
    }, "note": CAMPAIGN_STANDARD},
    "referral_request_message": {"module": 2, "title": "Referral Request Message", "per_application": False, "schema": {
        "message": "string — a concise direct-message version of the referral request for LinkedIn, text or other channels, includes the application link placeholder [APPLICATION LINK]",
    }},
    "general_interview_invitation": {"module": 3, "title": "General Interview Invitation", "per_application": False, "schema": {"subject": "string", "body": "string — general invitation to a board introductory/interview conversation, with [APPLICANT NAME] and scheduling placeholders"}},
    "general_interview_invitation_message": {"module": 3, "title": "Interview Invitation — Short Message", "per_application": False, "schema": {"message": "string — a concise direct-message version of the interview invitation for LinkedIn, text message, Facebook Messenger or another messaging channel. Includes [APPLICANT NAME], the organization name, thanks for their interest, the invitation to interview and a scheduling placeholder. NO email subject line. Keep it short — a few sentences, not another email."}},
    "general_rejection_email": {"module": 3, "title": "Application Rejection Email", "per_application": True, "schema": {"subject": "string", "body": "string — respectful, concise email for an applicant the organization has decided not to invite to interview"}},
    "conditional_offer": {"module": 4, "title": "Conditional Board Appointment Email", "per_application": True, "schema": {
        "subject": "string — exactly: Congratulations! Your Conditional Appointment as [the organization's actual board terminology, e.g. Board Member / Founding Board Member]",
        "body": "string — a candidate-specific conditional appointment email that feels PERSONALLY WRITTEN. Start 'Dear [actual candidate first name],'. OPENING: congratulate them and state clearly that following the interview process the organization is pleased to offer them a Conditional Appointment to the Board. WHY WE WANT YOU TO MOVE FORWARD: 1-2 candidate-specific paragraphs connecting their ACTUAL verified experience to the organization's actual priorities and Module 1 board needs — never invent experience, never generic 'we were impressed with your experience'. CONDITIONS: explain the appointment remains conditional on outstanding final requirements — include ONLY the requirements the supplied status context shows are actually outstanding (e.g. Reference Check, Background Check); if reference checking is complete do not claim it is outstanding; if background checking is not required omit it; explain that once the applicable requirements are completed and the organization confirms appointment they move into formal board service. YOUR NEXT STEP — BOARD ONBOARDING: invite them to the onboarding session and explain appropriate purposes (meet fellow board members and leadership, understand mission/direction, board responsibilities, how the board operates, fundraising/partnership expectations where applicable, how their particular expertise can contribute, ask questions). ONBOARDING DETAILS: use only the actual supplied date, time, timezone, format, meeting link and location — omit anything not supplied, no placeholders. DOCUMENTS AND FORMS: present the actual supplied links, clearly distinguishing items to REVIEW (Board Member Manual, Organizational Overview) from items to COMPLETE/SIGN (Board Member Profile Form, Board Member Agreement, Confidentiality Agreement, Conflict of Interest Disclosure) and ask them to review and complete the applicable forms before onboarding. CLOSING: warm organization-specific closing reinforcing why the organization looks forward to working with them; sign with actual founder/contact details. Use the words 'conditional appointment'; NEVER 'confidential board position'. Never make false statements about legal requirements."}},
    "after_interview_rejection": {"module": 4, "title": "After-Interview Rejection Email", "per_application": True, "schema": {"subject": "string", "body": "string — respectful, concise email for an applicant who was interviewed but will not move forward"}},
    "onboarding_script": {"module": 5, "title": "Board Member Onboarding Facilitator Guide", "per_application": False, "schema": {
        "session_purpose": "string — 1-2 short paragraphs explaining what the founder should accomplish during the onboarding session",
        "before_you_begin": ["string — short checklist of items that already exist and should be available (e.g. Board Member Manual, Organizational Overview, signed agreements, Board Member Profile status, meeting information) — do not create new resources"],
        "sections": [{"title": "string — use these exact section titles in order: 1. Welcome and Introductions; 2. Why This Organization Exists; 3. Where We Are Going; 4. The Role of the Board; 5. How We Will Work Together; 6. How Each Board Member Can Contribute; 7. Fundraising, Relationships and Ambassadorship; 8. Review the Board Documents; 9. Immediate Next Steps; 10. Questions and Discussion; 11. Closing",
                      "objective": "string — what this section accomplishes",
                      "talking_points": ["string — practical founder-facing talking points grounded in the actual organization/board context"],
                      "suggested_language": "string — short natural wording the founder can use (never a long speech); empty string where not useful",
                      "discussion_questions": ["string — questions to invite member input where appropriate (e.g. 'Based on what you know so far, where do you believe your experience could make the greatest contribution?'); empty list where not applicable"]}],
    }, "note": "You are an experienced nonprofit board-development consultant preparing a founder to PERSONALLY onboard newly recruited board members. This is a practical FACILITATOR GUIDE the founder follows during the meeting — NOT another Board Member Manual and NOT a generic article. Section 1: suggested time 10-15 minutes where appropriate, and if multiple members attend, invite each to briefly share their background, what interested them in the mission and what they hope to contribute. Section 4: adapt to the ACTUAL board type — never describe an Advisory Board as having governing authority, and never imply board members run day-to-day staff operations unless the working-board structure requires it. Section 6: use actual new-member expertise where supplied; suggest discussion questions, never make final role assignments. Section 7: fundraising can include introductions, opening doors, donor conversations, corporate partnerships, sponsorship, stewardship, events, grant relationships, sharing the mission, professional expertise, personal giving only where applicable — never tell every member they must personally ask for money unless that is actual policy. Section 8: explain what each supplied document is for and what remains outstanding — do not restate the documents. NEVER invent bylaws, committees, officer roles, voting rules, legal obligations, meeting schedules, donation requirements, strategic priorities, programs or statistics; omit or generalize what is unknown."},
    "interview_guide": {"module": 3, "title": "Interview Guide", "per_application": True, "schema": {
        "header": {"candidate": "string — actual candidate name", "current_position": "string — actual position if known, else empty", "organization": "string — actual employer if known, else empty", "board_opportunity": "string — actual organization + its actual board terminology", "suggested_duration": "string — ONLY if a standard interview duration exists in the supplied context; otherwise empty string"},
        "purpose_of_the_interview": {"explanation": "string — a short organization-and-candidate-specific explanation of what the founder should accomplish", "evaluation_questions": ["string — 4 to 6 questions the FOUNDER should be able to answer by the end (e.g. does the candidate demonstrate a genuine connection to this organization's mission; how could their specific background strengthen the board areas being recruited for; do they appear willing to contribute beyond attending meetings; what time and responsibility can they realistically take on; what needs clarification). Adapt to this specific person."]},
        "candidate_snapshot": "string — 1 to 3 concise paragraphs summarizing the candidate's most relevant VERIFIED background: current/previous professional work, expertise, leadership, nonprofit/board experience where known, relevant networks and their stated reason for applying. No generic praise. No selection recommendation.",
        "welcome_and_introductions": {"objective": "string", "talking_points": ["string — practical talking points"], "suggested_opening": "string — short natural wording to welcome and thank the candidate and explain how the conversation will flow. Not a long speech."},
        "introduce_the_organization": {"talking_points": ["string — 3 to 5 concise points from actual organization context: why it exists, mission, current stage, what the board is being built to accomplish"], "transition": "string — a natural transition into candidate questions"},
        "learn_about_this_candidate": [{"question": "string — personalized question referencing ACTUAL candidate CV/application items", "why_this_question_matters": "string — one concise sentence", "listen_for": ["string — 3 to 6 concise things"], "optional_follow_up": "string — one follow-up question, or empty"}],
        "mission_alignment": [{"question": "string — connects candidate experience + organization mission + actual needs", "why_this_question_matters": "string", "listen_for": ["string"], "optional_follow_up": "string"}],
        "contribution_to_the_board": [{"question": "string — explores how this candidate could contribute to the SPECIFIC board needs identified in Module 1 (what they could help lead, expertise, relationships they may open, the responsibility that interests them) — never assign a role automatically", "why_this_question_matters": "string", "listen_for": ["string"], "optional_follow_up": "string"}],
        "commitment_and_participation": [{"question": "string — realistic time availability, meeting participation, committee/leadership participation, follow-through, use of expertise/networks, fundraising participation only where applicable — never invent a required personal donation", "why_this_question_matters": "string", "listen_for": ["string"], "optional_follow_up": "string"}],
        "collaboration_and_accountability": [{"question": "string — 1 to 2 questions about working with other board members and leadership: disagreement, accountability, collaborative decisions, feedback, follow-through. No psychological profiling.", "why_this_question_matters": "string", "listen_for": ["string"], "optional_follow_up": "string"}],
        "candidate_questions": "string — tell the founder to invite the candidate's questions and what to listen for (mission, board role, expectations, direction, contribution). NEVER say that asking about time commitment, meetings or logistics is a negative sign.",
        "closing": "string — natural closing language: thank the candidate, explain the organization is interviewing/reviewing candidates, make clear no final decision is being announced, explain the organization will follow up on next steps",
    }, "note": "You are an experienced nonprofit board recruitment consultant preparing a founder to interview ONE SPECIFIC board candidate. This is NOT a generic interview questionnaire — use the applicant's actual application, CV, background and expressed interests together with the organization's actual mission, board type, current needs, Module 1 priority board profiles, stage and goals. learn_about_this_candidate: 2-3 questions DIRECTLY tied to specific items in the candidate's CV or application. mission_alignment: about 2 questions. contribution_to_the_board: 2-3 questions using only supported areas. NEVER invent candidate employment, achievements, qualifications, board experience, motivation, relationships, availability, personality or beliefs. Never infer sensitive personal characteristics. If candidate information is limited, use only what is actually known — no fake specificity. NEVER include an AI score, fit score, hire/do-not-hire, recommended/not-recommended, or pass/fail — the founder makes the final judgment."},
    "interview_invitation": {"module": 3, "title": "Interview Invitation", "per_application": True, "schema": {
        "subject": "string — exactly: Interview Invitation | Board Member Application — [actual organization name]",
        "body": "string — a finished email inviting THIS candidate to the interview stage. Start 'Dear [actual candidate first name],'. Thank them for applying; state clearly that after reviewing their application the organization would like to invite them to the interview stage; briefly explain the conversation will allow the organization to learn more about their experience, understand their interest in the mission, explore how their background could contribute, answer their questions and determine whether the opportunity is mutually aligned. If a real interview scheduling link is supplied in the context, include it naturally with a clear scheduling call to action; if none is supplied, state naturally that the organization will coordinate a convenient interview time with them directly — never mention that information is missing and NEVER output [Calendly Link], [Scheduling Link] or TBD. Never invent interview format, length or scheduling URL. Do not tell the candidate they have been selected for the board and do not overstate praise — never 'you are an excellent fit' unless the founder explicitly provided that judgment. Close warmly and sign with the actual founder/contact details. 150-250 words. Professional, warm, concise, respectful."}},
    "before_interview_rejection": {"module": 3, "title": "Before-Interview Rejection Email", "per_application": True, "schema": {
        "subject": "string — exactly: Thank You for Your Board Member Application",
        "body": "string — a finished email professionally closing the application for someone the FOUNDER decided not to invite to interview, while preserving the relationship and respecting the person's willingness to serve. Start 'Dear [actual first name],'. Thank them for their interest, the time invested in applying and their willingness to support the mission. State professionally that the organization has decided to move forward to the interview stage with a smaller group of candidates whose backgrounds most closely align with the board's current needs. Never present this as a judgment of the person's overall professional value. NEVER invent a rejection reason and never say 'you lack experience', 'you are not qualified', 'another candidate is better' or 'you are not a fit'. Do not promise to keep their information for future opportunities. Close respectfully and sign with the actual founder/contact information. 175-275 words. Professional, respectful, relationship-preserving, clear — no false hope, never cold or legalistic."}},
    "after_interview_thank_you": {"module": 3, "title": "After-Interview Thank-You Email", "per_application": True, "schema": {
        "subject": "string — exactly: Thank You for Meeting With Us",
        "body": "string — a strictly DECISION-NEUTRAL email sent to a candidate who attended their board interview. Start 'Dear [actual first name],'. Thank them for taking time to meet with the organization about the board opportunity; briefly say the organization appreciated learning more about their professional experience, interest in the mission, perspective and potential contribution — without claiming any decision has been made. Tell them clearly that the organization is completing its interviews/review and will follow up regarding next steps once the process is complete. Close warmly and sign with the actual founder/contact information. 125-200 words. FORBIDDEN words/phrases: 'unfortunately', 'we have decided', 'we are moving forward with other candidates', 'congratulations', 'conditional appointment', 'welcome to the board'."}},
    "interview_invitation_message": {"module": 3, "title": "Interview Invitation — Short Message", "per_application": True, "schema": {"message": "string — a concise personalized direct-message invitation for LinkedIn, text message or another messaging channel: the candidate's name, the organization name, thanks for their interest, the invitation to interview and scheduling information where supplied. NO email subject line. A few sentences only."}},
    "formal_appointment_email": {"module": 5, "title": "Formal Board Appointment Email", "per_application": True, "schema": {"subject": "string", "body": "string — formally welcomes the person as a Board Member or Advisory Board Member (match the organization's selected board type), confirms their appointment, and covers next steps such as the first board meeting where information was supplied"}},
    "board_member_portfolio": {"module": 5, "title": "Board Member Portfolio", "per_application": True, "schema": {
        "sections": [{"title": "string — cover: professional summary/bio; board role and why they were recruited; skills and expertise; relevant networks and relationships; board and leadership experience; fundraising interests; committee interests; agreed board responsibilities where known", "content": "string"}],
    }, "note": "Use ONLY the application, CV, board role and Board Member Profile Form information supplied. NEVER include referee responses, internal interview notes, selection scoring or internal evaluation material."},
    "portfolio_email": {"module": 5, "title": "Board Member Portfolio Email", "per_application": True, "schema": {"subject": "string", "body": "string — a short professional email to the board member sharing their completed Board Member Portfolio"}},
    "after_interview_email": {"module": 3, "title": "After-Interview Email", "per_application": True, "schema": {"subject": "string", "body": "string — respectful email matching the chosen result"}},
    "reference_request_email": {"module": 4, "title": "Reference Request Email", "per_application": True, "schema": {"subject": "string", "body": "string"}},
    "reference_call_script": {"module": 4, "title": "Reference Call Guide", "per_application": True, "schema": {"introduction": "string", "questions": ["string"], "closing": "string"}},
    "reference_evaluation_form": {"module": 4, "title": "Reference Evaluation Form", "per_application": True, "schema": {"sections": [{"title": "string", "items": ["string"]}]}},
    "onboarding_agenda": {"module": 5, "title": "Onboarding Agenda", "per_application": True, "schema": {
        "items": [{"topic": "string — cover welcome; introductions; mission/program overview; organizational priorities; board role; governance expectations; fundraising expectations; committees/responsibilities; important policies; next 90 days; questions; next meeting/action", "details": "string"}],
    }},
    "organization_overview": {"module": 4, "title": "Organization Overview", "per_application": False, "schema": {
        "sections": [{"title": "string", "content": "string"}],
    }, "note": "You are an experienced nonprofit strategist preparing a professional ORGANIZATIONAL OVERVIEW for new members of a nonprofit board — not a marketing brochure and not a dump of intake answers. It should help a new board member understand what this organization is, why it exists, who it serves, what it does, how it approaches its mission, where it is today, where it is going and what role the board plays. Produce sections in this order, OMITTING any section whose information is genuinely unavailable (never write 'Information not provided' or 'Information to Add'): About [Organization Name] (coherent 2-4 paragraph introduction); Our Mission (actual mission); Our Vision (only if a verified vision is known); The Need We Exist to Address; Our Approach; Our Programs and Work (verified only); Who and Where We Serve (only where known); Our Values (ONLY if actual stored values exist); The Role of Our Board (adapted to the actual board type); Our Current Direction; Looking Ahead (verified priorities only); Contact Information (actual organization, website, founder/contact, email where available). NEVER invent programs, statistics, achievements, founding dates, partnerships, locations, legal/tax status, values, beneficiaries or expansion plans. Professional, substantial, clear — roughly 3-6 finished pages of content depending on available information; never pad to reach length."},
    "board_manual": {"module": 4, "title": "Board Member Manual", "per_application": False, "schema": {
        "sections": [{"title": "string", "content": "string"}],
    }, "note": "You are an experienced nonprofit board-development consultant preparing the primary practical handbook that teaches a new board member how to serve effectively in THIS organization — never a generic internet article about nonprofit boards. Produce sections in this order, adapting to the actual board type and omitting unsupported detail: Welcome (what joining this board means); Our Mission and Direction; The Role of Our Board (if governing/working, distinguish board leadership/governance from day-to-day management; if advisory, do NOT assign governing/fiduciary authority); How We Work Together (actual/intended model: strategic planning, shared leadership, areas of ownership, committees, staff support, accountability — only where supported); Responsibilities of Every Board Member (actual expectations); Meetings and Participation (actual meeting information where known); Strategic Leadership; Fundraising and Resource Development (fundraising broadly: introductions, opening doors, donor meetings, corporate partnerships, sponsorship, stewardship, events, grants, expertise, ambassadorship; personal giving ONLY if actually expected — never imply every member must personally solicit money unless that is the organization's policy); Committees and Leadership Responsibilities (known structures only; if committees do not exist yet, explain participation conceptually without inventing names); Confidentiality (high-level, point to the separate agreement); Conflicts of Interest (high-level, point to the separate policy); Professional Conduct and Collaboration (respect, professionalism, constructive disagreement, mission-first decisions, accountability, communication); Accountability; What the Organization Commits to Its Board Members; Getting Started (practical initial actions); Closing (short welcome focused on shared leadership and mission). NEVER invent bylaws, quorum, voting rules, officer powers, statutory requirements, committee names, attendance percentages, donation minimums or term lengths. Roughly 6-12 polished pages depending on actual information."},
    "board_member_agreement": {"module": 4, "title": "Board Member Agreement", "per_application": False, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string", "content": "string"}], "acknowledgement": "string",
    }, "note": "Prepare ONE clear professional organization-level master Board Member Agreement based on the organization's actual board expectations — a controlled organizational agreement, not unnecessary legal language. Sections in this order (omit genuinely unsupported ones): Purpose / Shared Commitment (defines shared expectations between the organization and Board Member); Mission and Organizational Commitment; Participation and Meetings; Strategic Leadership (where appropriate); Committee Participation (where applicable); Professional Expertise and Relationships; Accountability; Fundraising and Resource Development (only where actually applicable); Professional Conduct; Confidentiality Acknowledgement; Conflict of Interest Acknowledgement; Time Commitment (only from known context); Term of Service (ONLY if known); What the Organization Commits to the Board Member; Acknowledgement. NEVER invent fines, penalties, personal donation requirements, attendance percentages, removal procedures, governing law, legal remedies, term lengths or officer positions. The hosted signing system captures identity, signature, date and version — do not include printed signature blanks."},
    "confidentiality_agreement": {"module": 4, "title": "Confidentiality Agreement", "per_application": False, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string", "content": "string"}], "acknowledgement": "string",
    }, "note": "Create a clear Board Member Confidentiality Agreement customized to the actual organization. Sections: Purpose; Confidential Information (appropriate examples such as financial information, donor information, sponsor information, personnel matters, strategic plans, board deliberations, legal matters, contracts, partnerships, proprietary materials, and other information expressly designated confidential); Board Member Responsibilities (keep confidential information secure; use it only to perform board responsibilities; do not disclose without authorization except where required by law; protect electronic and physical information; return/destroy information when appropriately requested); Continuing Confidentiality (obligations may continue after service); Acknowledgement. NEVER invent damages, statutory citations, penalties, criminal consequences or jurisdiction-specific remedies."},
    "conflict_of_interest_agreement": {"module": 4, "title": "Conflict of Interest Agreement", "per_application": False, "agreement": True, "schema": {
        "title": "string", "sections": [{"title": "string", "content": "string"}], "acknowledgement": "string",
    }, "note": "Prepare a clear Conflict of Interest Policy and Disclosure Agreement for Board Members. Sections: Purpose; What Is a Conflict of Interest? (plain-language explanation with potential examples: financial interest, employment/consulting relationship, family relationship, vendor relationship, partnership relationship, related organization, personal benefit); Board Member Responsibility to Disclose; Managing a Conflict (reasonable general principles: disclose, do not improperly influence discussion, abstain where appropriate, follow organization/board procedure — never invent legal procedures); Duty to Act in the Organization's Interests; Ethical Conduct; Disclosure Statement (present the choice 'I currently have no actual, potential or perceived conflict to disclose.' OR 'I have the following actual, potential or perceived conflict to disclose:' with an explanation field); Acknowledgement. NEVER invent statutory citations or legal penalties."},
    "ninety_day_plan": {"module": 5, "title": "New Board Member 90-Day Plan", "per_application": True, "schema": {
        "first_30_days": ["string — learn, attend, understand mission, complete onboarding"],
        "days_31_60": ["string — begin assigned responsibilities and relationship building"],
        "days_61_90": ["string — take ownership of agreed board/fundraising responsibilities"],
        "notes": "string — customized to candidate strengths, assigned responsibility, organizational priorities and fundraising expectations",
    }},
    "first_board_meeting_invitation": {"module": 5, "title": "First Board Meeting Invitation Email", "per_application": False, "schema": {
        "subject": "string — 'First Board Meeting | [actual organization name]' (a natural organization-specific alternative is acceptable — produce ONE subject only)",
        "body": "string — one finished email to the new Board Members ('Dear Board Members,') inviting them to their first Board Meeting and making clear this meeting is the transition from recruitment/onboarding into ACTIVE board participation — not a generic calendar reminder. OPENING: welcome them and explain why the meeting matters: the Board's first opportunity to come together after recruitment/onboarding, better understand the experience represented around the table, and begin deciding how the Board will work together to move the organization forward. Then a section headed 'DURING THE MEETING, WE WILL:' with a concise organization-specific agenda drawn only from supported items (introductions and professional strengths, current stage and priorities, Board-leadership relationship, individual contribution areas, upcoming strategic planning, committees/leadership portfolios where applicable, fundraising and partnerships, shared responsibilities, immediate next steps). If the supplied context says one or more recipients have NOT completed their Board Member Profile, include a section 'Please Complete Your Board Member Profile' briefly explaining why it matters (expertise, leadership interests, networks, fundraising comfort, availability, where they most want to contribute) with the ACTUAL profile URL supplied; if everyone has completed it, OMIT that section entirely. Then 'Board Meeting Details' listing ONLY the actually supplied details (date, time, timezone, format/location, meeting link, meeting ID, passcode, meeting chat, additional instructions) — omit missing items completely, never output placeholders like [Zoom Link] or [To be confirmed]. CLOSING: meaningful — where consistent with the board type, communicate that the goal is not simply names around a table but members who contribute expertise, ideas, relationships, leadership, fundraising support, partnerships and shared responsibility so the mission does not rest on the founder alone; ask them to confirm attendance where appropriate; sign with actual founder/contact information.",
    }},
    "board_member_engagement_guide": {"module": 5, "title": "Board Member Engagement Guide", "per_application": True, "schema": {
        "member": "string — actual member name", "professional_role": "string — actual role/employer where known",
        "primary_expertise": "string — comma-separated actual expertise areas",
        "where_they_create_most_value": ["string — 3 to 5 SPECIFIC ways their actual expertise can support current organizational priorities. Be concrete: instead of 'Use their finance skills' write 'Invite them to help strengthen Board financial oversight, review budgeting assumptions and establish a clearer financial reporting rhythm.' Only where supported."],
        "how_to_engage_them": ["string — practical founder actions grounded in what the member actually said about interests, availability, leadership, networks and fundraising comfort (involve them early in relevant planning; give them ownership of a defined outcome; invite them to open specific relationship types; pair them with the appropriate area; keep responsibilities within their stated available time)"],
        "strong_early_responsibilities": ["string — 2 to 4 concrete responsibilities/projects the founder could DISCUSS with them (suggestions, never automatic assignments)"],
        "relationships_partnerships_fundraising": "string — based on their stated networks and fundraising comfort, useful ways they may contribute (donor/corporate/foundation/community/government introductions, professional associations, speaking, strategy, stewardship — only where supported; never force fundraising activities they said they are uncomfortable with)",
        "leadership_committee_alignment": "string — appropriate areas of board leadership based on expertise and stated interests; never invent an officer title",
        "first_90_days": ["string — 3 to 5 practical actions to engage this person early"],
        "keep_in_mind": ["string — ONLY evidence-based operational considerations (e.g. 'Indicated approximately 2-4 hours of monthly availability, so responsibilities should remain focused and clearly defined.'). NEVER personality judgments such as 'they may be difficult', 'they seem introverted', 'they need praise'."],
    }, "note": "You are an experienced nonprofit board-development consultant advising a founder on how to meaningfully engage ONE specific board member. Create a concise ONE-PAGE INTERNAL guide from verified information only: their application, CV, professional background, board experience, Board Member Profile (expertise, committee/leadership interests, fundraising participation, networks, availability, reason for joining, additional skills), plus organization priorities and Module 1 board needs. NEVER use referee responses, confidential reference data, background-check data, private interview scoring, or protected characteristics (age, race, sex, disability, religion, political belief). No psychological profiling. This guide is internal — never addressed to the member."},
}

SYSTEM_MESSAGE = (
    "You are the Nonprofit Board Builder recruitment assistant. You work ONLY from the information provided in the prompt: "
    "the nonprofit's submitted information, the confirmed recruitment profile, previously approved recruitment materials, and "
    "applicant application information and CV where provided. Never invent facts, real people, statistics or history that was not provided. "
    "WRITING RULES: everything you write must sound like it was professionally written by a real nonprofit founder, executive director or experienced nonprofit consultant. "
    "Never use emojis, smileys, decorative icons, unnecessary symbols, exaggerated marketing language, inflated adjectives, or generic AI phrases such as 'pivotal moment', 'unlock', 'game-changing', 'transformative journey', 'dive into' or similar. "
    "Prefer straightforward sentences. Avoid repetitive introductions, excessive headings and excessive bullet lists. Write as the organization or founder where appropriate. "
    "Emails must read like real professional emails. Formal documents must read like real organizational documents. "
    "BOARD TYPE: always match the organization's selected board type. If they are building an Advisory Board, refer to the Advisory Board, Advisory Board Members, Advisory Board Opportunity, Advisory Board Application and Advisory Board Appointment where appropriate, and focus on professional expertise, strategic advice, relationships, introductions, subject-matter expertise, community connections, mission support and fundraising support where the organization expects it. Never automatically state that Advisory Board Members govern the nonprofit, hold fiduciary responsibility, vote as Directors, oversee the Executive Director or carry statutory governance duties unless the organization explicitly supplied those responsibilities. If a governing/working board, use appropriate director/board-member terminology and keep the organization's stated expectations at full strength. "
    "Never write the phrase 'Information to Add' in anything intended to be publicly shared or sent to another person; instead use the neutral placeholder in square brackets naming exactly what is missing, e.g. '[Application deadline]'. "
    "Never claim documents have been reviewed by a lawyer and never give legal advice. "
    "You must respond with a single valid JSON object matching the requested schema exactly — no markdown, no code fences, no commentary."
)

SYSTEM_MESSAGE += (
    "FINISHED CONTENT STANDARD: you are creating the FINAL version of a professional nonprofit recruitment resource, not a template, outline, draft or notes. "
    "The organization's real name, mission, board type, roles, meeting details, links and candidate names are supplied in the context — use them everywhere they belong. "
    "NEVER output placeholders or template tokens such as [Organization Name], [Mission], [Mission Statement], [Board Type], [Candidate Name], [Meeting Frequency], [Location], [Board Role], [Organization Website], [Insert ...], 'Information to Add', 'To Be Confirmed' or 'TBD'. "
    "The ONLY permitted placeholder is [APPLICANT NAME] and only in explicitly general reusable templates. "
    "If a scheduling link was not supplied, never invent one and never write [Scheduling Link] — omit the line or ask the reader to reply to arrange a time. "
    "Never invent organization facts (programs, impact numbers, founding year, history, requirements, priorities) that were not supplied; write around unknown nonessential details naturally. "
    "Never write advice to the founder inside the resource such as 'Add your mission here', 'Insert meeting frequency', 'Consider adding' or 'You may want to'. "
    "FORMATTING: begin every paragraph flush left with NO first-line indentation, NO leading spaces or tabs, NO blockquote or hanging indents. Use blank lines between paragraphs. "
)

def _flush_left(text: str) -> str:
    return re.sub(r"(?m)^[ \t]+", "", text or "").strip()



def _format_value(value, indent=0):
    pad = "  " * indent
    lines = []
    if isinstance(value, dict):
        for key, item in value.items():
            label = key.replace("_", " ").title()
            if isinstance(item, (dict, list)):
                lines.append(f"{pad}{label}:")
                lines.extend(_format_value(item, indent + 1))
            else:
                lines.append(f"{pad}{label}: {item}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)):
                lines.extend(_format_value(item, indent))
                lines.append("")
            else:
                lines.append(f"{pad}- {item}")
    else:
        lines.append(f"{pad}{value}")
    return lines


STRATEGY_TIMELINE_TEXT = """4. RECRUITMENT TIMELINE

DAY 1
Launch the recruitment campaign. Begin Personal Network outreach where applicable, begin Referral Network outreach where applicable, and publish through your selected Public Outreach channels where applicable.

WITHIN 48 HOURS
Review the first applications and responses. Begin inviting qualified applicants to interview — do not wait until the campaign closes.

WEEKS 1-2
Continue recruitment outreach. Review applicants as they arrive, interview qualified applicants, follow up with strong prospects and continue accepting additional applications while interviews are taking place.

WEEK 3
Complete final interviews and verification for candidates moving forward. Finalize board-member selections, complete required onboarding information, agreements and preparation, and begin onboarding the new board members."""

STRATEGY_ROADMAP_TEXT = """5. YOUR RECRUITMENT EXECUTION ROADMAP

STEP 2 — BUILD YOUR RECRUITMENT STRATEGY
You have now identified the channels you will use to reach the professionals your organization needs.

STEP 3 — LAUNCH YOUR RECRUITMENT CAMPAIGN
Create your recruitment materials, publish your board opportunity and begin personally reaching the professionals and networks identified in your strategy.

STEP 4 — INTERVIEW YOUR APPLICANTS
Review applicants as they arrive and invite qualified candidates to interview. Begin interviewing within the first 48 hours where qualified applicants are available and continue interviews over the next two weeks.

STEP 5 — COMPLETE REFERENCES AND BACKGROUND CHECKS
For the candidates you want to move forward with, complete the reference and verification steps your organization has chosen to use.

STEP 6 — ONBOARD YOUR NEW BOARD MEMBERS
Complete the appointment and onboarding process so your new board members understand the organization, their responsibilities and how they will begin contributing."""

STRATEGY_NEXT_STEP_TEXT = """YOUR NEXT STEP
Your recruitment strategy is ready. The next step is to create the materials you will use to reach applicants and launch your recruitment campaign.

CONTINUE TO STEP 3 — CREATE MY RECRUITMENT MATERIALS"""


def structured_to_display(generation_type: str, structured: dict) -> str:
    meta = GENERATION_TYPES[generation_type]
    if generation_type == "recruitment_strategy":
        lines = ["BOARD RECRUITMENT STRATEGY", "", "EXECUTIVE SUMMARY", structured.get("executive_summary", ""), "", "1. BOARD MEMBERS WE ARE RECRUITING"]
        for role in structured.get("roles", [])[:5]:
            lines.append(f"- {role.get('role_name', '')}: {role.get('person_sought', '')}")
        lines.extend(["", "2. RECRUITMENT CHANNELS"])
        for entry in structured.get("channels", []):
            lines.extend([str(entry.get("channel", "")).upper(), entry.get("approach", ""), ""])
        lines.append("3. SELECTION CRITERIA")
        for criterion in structured.get("selection_criteria", []):
            lines.append(f"- {criterion}")
        lines.extend(["", STRATEGY_TIMELINE_TEXT, "", STRATEGY_ROADMAP_TEXT, "", STRATEGY_NEXT_STEP_TEXT])
        return _flush_left("\n".join(line.rstrip() for line in lines))
    if generation_type == "powerhouse_board_blueprint":
        lines = ["THE BOARD MEMBERS YOUR ORGANIZATION NEEDS", ""]
        if structured.get("recommended_count_statement"):
            lines.extend([structured["recommended_count_statement"], ""])
        for index, role in enumerate(structured.get("priority_roles", []), 1):
            if role.get("summary"):
                lines.extend([f"{index}. {role.get('role_name', '')}", role.get("summary", ""), ""])
                continue
            lines.extend([f"{index}. {role.get('role_name', '')}", "",
                          "Why This Person Is Important", role.get("why_this_person_is_important", ""), "",
                          "How This Person Can Support the Founder and Organization", role.get("how_this_person_can_support", ""), "",
                          "What To Look For"])
            lines.extend([f"- {item}" for item in role.get("what_to_look_for", [])])
            lines.append("")
        return _flush_left("\n".join(lines))
    lines = [meta["title"].upper(), ""]
    lines.extend(_format_value(structured))
    if meta.get("agreement"):
        lines.extend(["", REVIEW_WARNING])
    return _flush_left("\n".join(line.rstrip() for line in lines))


def blueprint_detailed_text(structured: dict) -> str:
    lines = ["BOARD RECRUITMENT PROFILE — DETAILED REPORT", ""]
    if structured.get("recommended_count_statement"):
        lines.extend([structured["recommended_count_statement"], ""])
    for index, role in enumerate(structured.get("detailed_roles", []) or structured.get("priority_roles", []), 1):
        lines.append(f"{index}. {role.get('role_name', '')}")
        for key in ["why_this_person_is_important", "how_this_person_can_support", "why_this_role_matters", "professional_background_to_look_for", "useful_networks", "how_this_role_contributes", "how_this_complements_the_present_board"]:
            if role.get(key):
                lines.append(f"{key.replace('_', ' ').capitalize()}: {role[key]}")
        if role.get("what_to_look_for"):
            lines.append("What to look for: " + "; ".join(role["what_to_look_for"]))
        if role.get("relevant_skills"):
            lines.append("Relevant skills: " + ", ".join(role["relevant_skills"]))
        lines.append("")
    return _flush_left("\n".join(lines))


def parse_json_response(text: str) -> dict:
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)```\s*$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("The model did not return JSON")
    return json.loads(text[start:end + 1])


async def generate_structured(generation_type: str, context: str, instructions: str = "") -> dict:
    """Deliberate, single Claude call. Returns structured dict. Raises on failure."""
    meta = GENERATION_TYPES[generation_type]
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("EMERGENT_LLM_KEY", "")
    model = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
    chat = LlmChat(api_key=api_key, session_id=f"nbb-{generation_type}-{uuid.uuid4()}", system_message=SYSTEM_MESSAGE).with_model("anthropic", model)
    prompt = (
        f"GENERATION TYPE: {meta['title']}\n\n"
        f"CONTEXT (the only information you may use):\n{context}\n\n"
        + (f"SPECIAL REQUIREMENTS: {meta['note']}\n\n" if meta.get("note") else "")
        + (f"ADDITIONAL INSTRUCTIONS:\n{instructions}\n\n" if instructions else "")
        + "Respond with one JSON object matching exactly this schema (descriptions explain each field):\n"
        + json.dumps(meta["schema"], indent=1)
    )
    response = await chat.send_message(UserMessage(text=prompt))
    text = response if isinstance(response, str) else getattr(response, "text", str(response))
    structured = parse_json_response(text)
    if generation_type == "application_questions":
        structured["custom_questions"] = structured.get("custom_questions", [])[:5]
    return structured


def extract_cv_text(content: bytes, filename: str) -> str:
    """Securely extract usable text from a CV file. Never exposes file publicly."""
    extension = os.path.splitext(filename or "")[1].lower()
    try:
        if extension == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            return "\n".join((page.extract_text() or "") for page in reader.pages)[:20000]
        if extension == ".docx":
            import docx
            document = docx.Document(io.BytesIO(content))
            return "\n".join(paragraph.text for paragraph in document.paragraphs)[:20000]
        if extension == ".doc":
            return content.decode("latin-1", errors="ignore")[:20000]
    except Exception as exc:
        logger.warning("CV text extraction failed for %s: %s", filename, exc)
    return ""
