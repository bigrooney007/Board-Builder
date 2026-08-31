# BUF COMPLETE GENERATION PROMPT AUDIT

EXTRACTION ONLY — nothing was modified. Every prompt/template below is VERBATIM from the live codebase.

## PART 1 — GENERATION ENGINE
All 64 structured generators use ONE engine. VERBATIM source:
```python
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
```
Model: Anthropic `claude-sonnet-4-6` (env `CLAUDE_MODEL`), key `EMERGENT_LLM_KEY` (fallback env `ANTHROPIC_API_KEY`). No temperature/max-token overrides set. No retry logic — single call, raises on failure (routes store status 'Failed'). Validation = parse_json_response (strips fences, extracts outer JSON). Composition order actually sent: SYSTEM message = GLOBAL SYSTEM PROMPT A; USER message = `GENERATION TYPE` + `CONTEXT (the only information you may use)` + `SPECIAL REQUIREMENTS` (the developer note) + optional `ADDITIONAL INSTRUCTIONS` + schema JSON. There is no separate developer-role message — the developer prompt travels inside the user message.

## PART 2 — GLOBAL SYSTEM PROMPTS
### GLOBAL SYSTEM PROMPT A — used by ALL 64 generate_structured generators (ai_service.py SYSTEM_MESSAGE, VERBATIM)
```
You are the Nonprofit Board Builder recruitment assistant. You work ONLY from the information provided in the prompt: the nonprofit's submitted information, the confirmed recruitment profile, previously approved recruitment materials, and applicant application information and CV where provided. Never invent facts, real people, statistics or history that was not provided. EMAIL SIGNATURE RULE: every generated EMAIL must end with the founder's actual supplied contact details from the FOUNDER CONTACT context block — name, title, email and phone — presented naturally as the sender's signature. Omit any item that was not supplied. Never write placeholders such as [Your Name] or [Phone]. FINISHED CONTENT RULE: generate the finished content for the requested resource only. Never expose internal generation instructions, metadata, schema labels, field names, prompt terminology, version numbers, or renderer/layout instructions in the content. Never write labels such as 'Title:', 'Content:', 'Section:', 'Version 1', 'Generation Type:' or 'Special Requirements:' in the output. The resource-specific requirements remain authoritative for the actual content structure. LINK RULE: never invent URLs or links of any kind. Where a resource needs a link (form, strategy, review, agreement, application, meeting), use exactly the URL supplied in context, placed where the resource requires it; if no URL was supplied, refer to the link generically without fabricating one. DESIGN RULE: the application renderer owns all visual design (fonts, sizes, colours, borders, spacing, cover pages, logos, page numbers). Do not produce CSS, layout, typography or visual design instructions. WRITING RULES: everything you write must sound like it was professionally written by a real nonprofit founder, executive director or experienced nonprofit consultant. Never use emojis, smileys, decorative icons, unnecessary symbols, exaggerated marketing language, inflated adjectives, or generic AI phrases such as 'pivotal moment', 'unlock', 'game-changing', 'transformative journey', 'dive into' or similar. Prefer straightforward sentences. Avoid repetitive introductions, excessive headings and excessive bullet lists. Write as the organization or founder where appropriate. Emails must read like real professional emails. Formal documents must read like real organizational documents. BOARD TYPE: always match the organization's selected board type. If they are building an Advisory Board, refer to the Advisory Board, Advisory Board Members, Advisory Board Opportunity, Advisory Board Application and Advisory Board Appointment where appropriate, and focus on professional expertise, strategic advice, relationships, introductions, subject-matter expertise, community connections, mission support and fundraising support where the organization expects it. Never automatically state that Advisory Board Members govern the nonprofit, hold fiduciary responsibility, vote as Directors, oversee the Executive Director or carry statutory governance duties unless the organization explicitly supplied those responsibilities. If a governing/working board, use appropriate director/board-member terminology and keep the organization's stated expectations at full strength. Never write the phrase 'Information to Add' in anything intended to be publicly shared or sent to another person; instead use the neutral placeholder in square brackets naming exactly what is missing, e.g. '[Application deadline]'. Never claim documents have been reviewed by a lawyer and never give legal advice. You must respond with a single valid JSON object matching the requested schema exactly — no markdown, no code fences, no commentary.FINISHED CONTENT STANDARD: you are creating the FINAL version of a professional nonprofit recruitment resource, not a template, outline, draft or notes. The organization's real name, mission, board type, roles, meeting details, links and candidate names are supplied in the context — use them everywhere they belong. NEVER output placeholders or template tokens such as [Organization Name], [Mission], [Mission Statement], [Board Type], [Candidate Name], [Meeting Frequency], [Location], [Board Role], [Organization Website], [Insert ...], 'Information to Add', 'To Be Confirmed' or 'TBD'. The ONLY permitted placeholder is [APPLICANT NAME] and only in explicitly general reusable templates. If a scheduling link was not supplied, never invent one and never write [Scheduling Link] — omit the line or ask the reader to reply to arrange a time. Never invent organization facts (programs, impact numbers, founding year, history, requirements, priorities) that were not supplied; write around unknown nonessential details naturally. Never write advice to the founder inside the resource such as 'Add your mission here', 'Insert meeting frequency', 'Consider adding' or 'You may want to'. FORMATTING: begin every paragraph flush left with NO first-line indentation, NO leading spaces or tabs, NO blockquote or hanging indents. Use blank lines between paragraphs. 
```
### GLOBAL SYSTEM PROMPT B — blog engine only (marketing_service.py BLOG_SYSTEM, VERBATIM)
```
You are Rooney Akpesiri, the Nonprofit Board Builder. You write for nonprofit founders and Executive Directors in American English. You help nonprofits reactivate their present board, recruit the board members they are missing, and activate their board to raise money. You sound like someone who has actually worked with nonprofit founders and boards. Every article makes ONE clear point about ONE specific problem. Get to the problem within the first two or three sentences. Never open with broad industry commentary, generic nonprofit observations, long context sections or motivational filler. Open with a real, recognizable situation, for example: a founder carrying the organization alone, seven board members but only two doing anything, board members attending meetings but taking no responsibility, a founder who recruited friends because they needed names on the board, board members told to fundraise without knowing what that means. Use situations, never fabricated named client stories. Explain what is actually going wrong and the perspective the leader needs, then show what changes when the issue is handled properly. Provide useful insight without teaching every execution step; do not write step-by-step numbered guides unless the topic strictly requires it. STRICT RULES: never use an em dash character. Use normal paragraph structure, not choppy one-sentence-paragraph AI style. No generic filler. No fake quotations, statistics, research, case studies, client stories, testimonials or platform claims. Never use phrases like 'In today's fast-paced world', 'In the ever-evolving landscape', 'It's important to note', 'Let's dive in', 'Game changer', 'Unlock the power', 'Navigate the complexities', 'Revolutionize'. Respond ONLY with one valid JSON object, no markdown fences.
```

## PART 3 — COMPLETE GENERATOR INVENTORY (all 64 structured types + templates)

| # | type | resource | BUF stage | kind |
|---|---|---|---|---|
| 1 | `reactivation_response_analysis` | Understanding Their Response | 1 | AI |
| 2 | `reactivation_board_summary` | Summary of Your Entire Board | 1 | AI |
| 3 | `reactivation_conversation_script` | Difficult Conversation Script | 1 | AI |
| 4 | `reactivation_stepped_down_followup` | Stepped-Down Board Member Follow-Up Email | 1 | AI |
| 5 | `reactivation_advisory_confirmation` | Advisory Board Confirmation Email | 1 | AI |
| 6 | `reactivation_engagement_plan` | Board Reactivation / Engagement Plan | 1 | AI |
| 7 | `powerhouse_board_blueprint` | The Board Members Your Organization Needs | 2 | AI |
| 8 | `recruitment_strategy` | Board Recruitment Strategy | 3 | AI |
| 9 | `board_opportunity` | Board Opportunity | 3 | AI |
| 10 | `application_questions` | Board Application — Organization-Specific Questions | 3 | AI |
| 11 | `linkedin_post` | LinkedIn Recruitment Post | 3 | AI |
| 12 | `social_posts` | Social Media Recruitment Post | 3 | AI |
| 13 | `recruitment_emails` | Recruitment Email | 3 | AI |
| 14 | `linkedin_launch_instructions` | LinkedIn Jobs Launch Guide | 3 | AI |
| 15 | `board_recruitment_job_post` | Recruitment Job Post | 3 | AI |
| 16 | `personal_invitation_email` | Personal Invitation Email | 3 | AI |
| 17 | `personal_invitation_message` | Personal Invitation Message | 3 | AI |
| 18 | `referral_request_email` | Referral Recruitment Message | 3 | AI |
| 19 | `referral_request_message` | Referral Request Message | 3 | AI |
| 20 | `interview_guide` | Interview Guide | 4 | AI |
| 21 | `interview_invitation` | Interview Invitation | 4 | AI |
| 22 | `interview_invitation_message` | Interview Invitation — Short Message | 4 | AI |
| 23 | `general_interview_invitation` | General Interview Invitation | 4 | AI |
| 24 | `general_interview_invitation_message` | Interview Invitation — Short Message | 4 | AI |
| 25 | `before_interview_rejection` | Before-Interview Rejection Email | 4 | AI |
| 26 | `general_rejection_email` | Application Rejection Email | 4 | AI |
| 27 | `after_interview_thank_you` | After-Interview Thank-You Email | 4 | AI |
| 28 | `after_interview_email` | After-Interview Email | 4 | AI |
| 29 | `after_interview_rejection` | After-Interview Rejection Email | 4 | AI |
| 30 | `candidate_referee_request` | Candidate Referee Request Email | 5 | AI |
| 31 | `reference_request_email` | Reference Check Email | 5 | AI |
| 32 | `referee_confirmation_email` | Referee Confirmation Email | 5 | AI |
| 33 | `reference_call_script` | Reference Call Guide | 5 | AI |
| 34 | `reference_evaluation_form` | Reference Evaluation Form | 5 | AI |
| 35 | `conditional_offer` | Conditional Board Appointment Email | 5 | AI |
| 36 | `board_manual` | Board Member Manual | 6 | AI |
| 37 | `organization_overview` | Organization Overview | 6 | AI |
| 38 | `board_member_agreement` | Board Member Agreement | 6 | AI |
| 39 | `confidentiality_agreement` | Confidentiality Agreement | 6 | AI |
| 40 | `conflict_of_interest_agreement` | Conflict of Interest Agreement | 6 | AI |
| 41 | `ninety_day_plan` | New Board Member 90-Day Plan | 6 | AI |
| 42 | `onboarding_agenda` | Onboarding Agenda | 6 | AI |
| 43 | `onboarding_script` | Board Member Onboarding Facilitator Guide | 6 | AI |
| 44 | `first_board_meeting_invitation` | First Board Meeting Invitation Email | 6 | AI |
| 45 | `board_member_engagement_guide` | Board Member Engagement Guide | 6 | AI |
| 46 | `board_member_portfolio` | Board Member Portfolio | 6 | AI |
| 47 | `portfolio_email` | Board Member Portfolio Email | 6 | AI |
| 48 | `formal_appointment_email` | Final Board Appointment Email | 6 | AI |
| 49 | `activation_planning_form` | Board Fundraising Planning Form | 7 | AI |
| 50 | `activation_fundraising_strategy` | Fundraising Strategy Plan | 7 | AI |
| 51 | `activation_revised_strategy` | Revised Fundraising Strategy Plan (Ready for Adoption) | 7 | AI |
| 52 | `activation_facilitation_guide` | Plan Adoption Facilitation Guide | 7 | AI |
| 53 | `activation_execution_toolkit` | Board Fundraising Execution Toolkit | 7 | AI |
| 54 | `activation_fundraising_portfolio` | Fundraising Portfolio | 7 | AI |
| 55 | `activation_followup_email` | Board Member Follow-Up Email | 7 | AI |
| 56 | `strategic_meeting_guide` | Strategic Plan Adoption Meeting Facilitation Guide | — (Part 11) | AI |
| 57 | `strategic_planning_form_structure` | Strategic Planning Form | — (Part 11) | AI |
| 58 | `strategic_planning_foundational` | Foundational Strategic Plan | — (Part 11) | AI |
| 59 | `strategic_area_pack` | Strategic Area Development Pack | — (Part 11) | AI |
| 60 | `strategic_final_plan` | Final Strategic Plan | — (Part 11) | AI |
| 61 | `strategic_plan_synchronized` | Synchronized Foundational Strategic Plan | — (Part 11) | AI |
| 62 | `strategic_area_owner_recommendation` | Strategic Area Owner Recommendations | — (Part 11) | AI |
| 63 | `strategic_action_plan` | Strategic Planning Action Plan | — (Part 11) | AI |
| 64 | `resource_design_adjustments` | Resource Design Adjustments | — (Part 11) | AI |
| 65 | recommitment_form_intro (template) | Board Member Profile & Recommitment Form | 1 | TEMPLATE-BASED / NOT AI-GENERATED |
| 66 | recommitment_outreach_email (template) | Recommitment Form Email (+reminder) | 1 | TEMPLATE-BASED / NOT AI-GENERATED |
| 67 | recommitment_reminder_call_script (template) | Reminder Call Script | 1 | TEMPLATE-BASED / NOT AI-GENERATED |
| 68 | activation_planning_email (template) | Fundraising Planning Form Email | 7 | TEMPLATE-BASED / NOT AI-GENERATED |
| 69 | activation_review_email (template) | Fundraising Strategy Email | 7 | TEMPLATE-BASED / NOT AI-GENERATED |
| 70 | activation_adoption_meeting_email (template) | Adoption Meeting Email | 7 | TEMPLATE-BASED / NOT AI-GENERATED |
| 71 | STRATEGY_TIMELINE_TEXT (platform-appended) | Recruitment Timeline | 3 | TEMPLATE-BASED / NOT AI-GENERATED |
| 72 | blog engine (marketing_service) | Blog articles + social snippets | — | TEMPLATE-BASED / NOT AI-GENERATED |

## PART 4 — STAGE 1: REBUILD / UNDERSTAND THE PRESENT BOARD

### Board Member Profile & Recommitment Form — TEMPLATE-BASED / NOT AI-GENERATED
Type: `reactivation_forms` record built by POST /api/reactivation/recommitment-form/generate (reactivation_routes.py:1005). Intro text = recommitment_form_intro(organization, mission) (verbatim in Part 13). Question set is FIXED in the public form component `/app/frontend/src/funnels/BoardRecommitmentFormPage.jsx` (verbatim in Part 13). Conditional transition options (Remain / Advisory / Step Off) come from board_reactivation_intakes.transition_options set by orientation selections (board_fix_routes.py:195-203). Form link = {origin}/board-recommitment/{form_token} (generic) or per-member token.

### Recommitment Form Email — TEMPLATE-BASED / NOT AI-GENERATED
recommitment_outreach_email(kind, first, founder_name, founder_title, organization) — verbatim template in Part 13. Link insertion: body placeholder `[COMPLETE MY FORM]` is replaced with the actual form URL by the UI/orientation page; per-member endpoints pass form_link explicitly (reactivation_routes.py:300-315).

#### `reactivation_response_analysis` — Understanding Their Response
- **A. Generation type**: `reactivation_response_analysis`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are helping a nonprofit founder understand what a specific Board Member communicated through their Board Member Profile & Recommitment Form before a one-to-one conversation. Base EVERYTHING on the member's actual responses and profile supplied. NEVER invent motivations, facts or statements. Where the responses are silent on a point, say so plainly. This is preparation, not a verdict — the founder decides the direction. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "what_they_are_communicating": "string \u2014 2-4 sentences explaining what this Board Member appears to be communicating through their actual Recommitment Form responses. Use ONLY what they actually wrote.",
 "commitment_level": "string \u2014 their apparent level of commitment (e.g. 'Ready to continue actively', 'Willing but needs clarity', 'Limited capacity', 'Uncertain', 'Ready to step away'), justified in one sentence from their own words.",
 "concerns_or_reservations": "list of strings \u2014 the concerns, frustrations or reservations they actually expressed. Empty list if none were expressed.",
 "willingness_to_continue": "string \u2014 what their responses actually indicate about their willingness to continue serving.",
 "willingness_for_greater_responsibility": "string \u2014 what their responses indicate about willingness to take greater responsibility or leadership. If they did not address it, say so.",
 "considering_stepping_down": "string \u2014 'Yes', 'Possibly' or 'No', with one sentence of evidence from their responses.",
 "advisory_role_appropriate": "string \u2014 whether an advisory role may be appropriate based on their stated capacity and openness, with one sentence of reasoning. If they were not asked or did not indicate, say so.",
 "important_issues_before_conversation": "list of strings \u2014 the important things the facilitator should understand BEFORE the conversation (capacity limits, unresolved frustrations, support they asked for, clarity they need).",
 "recommended_next_action": "string \u2014 the practical recommended next step. In the normal workflow this is 'Have the conversation', stated specifically for this person.",
 "recommended_conversation_direction": "string \u2014 the recommended direction for the conversation (e.g. invite them to remain and step up, explore stepping down respectfully, explore an advisory transition), with 2-3 sentences on how to approach it so the facilitator enters prepared."
}
```
- **E. Dynamic context**: reactivation context (founder_context + board member record/response; see Part 4 code)
- **F. Calling file/route**: reactivation_routes.py:1112 — POST /api/reactivation/board-members/{id}/analysis/generate
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reactivation_board_summary` — Summary of Your Entire Board
- **A. Generation type**: `reactivation_board_summary`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are helping a nonprofit founder understand their ENTIRE board after their board members completed the Board Member Profile & Recommitment Form. Combine the founder's Complete Board Fix intake, the organization's stated goals and priorities, and every member's actual profile and recommitment responses. Answer: what does the founder currently have, who is ready to recommit, who needs engagement, who needs a conversation, who may transition to advisory, who may need to step off, what can be built with these people, what is missing, and who needs to be recruited. Base EVERYTHING on the supplied material — NEVER invent members, skills, statements or motivations. Where the material is silent, say so plainly. Write like Rooney explaining the situation directly to the founder: plain, direct, warm, practical, no consulting jargon. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "overall_state": "string \u2014 3-5 plain sentences describing the overall current state of this board, grounded ONLY in the founder's intake and the members' actual responses.",
 "ready_to_recommit": "list of strings \u2014 one line per member whose responses show they are ready to recommit and step up: 'Name \u2014 one sentence of evidence from their own words'. Empty list if none.",
 "need_engagement": "list of strings \u2014 one line per member who may need additional engagement, clarity or support before they can fully step up: 'Name \u2014 one sentence of why'. Empty list if none.",
 "need_conversation": "list of strings \u2014 one line per member the founder needs to have a direct conversation with: 'Name \u2014 one sentence of why'. Empty list if none.",
 "advisory_candidates": "list of strings \u2014 one line per member who may be better suited to an advisory role, each with evidence from their responses. Empty list if none indicated.",
 "step_off_candidates": "list of strings \u2014 one line per member who may need to step off the board, each with evidence from their responses. Empty list if none indicated.",
 "member_roles": "list of strings \u2014 one line per responding member: 'Name \u2014 the role they can potentially play going forward', grounded in their stated skills, interests, networks and capacity.",
 "board_strengths": "list of strings \u2014 the strengths currently available within this board (skills, relationships, networks, capacity), taken only from the actual responses.",
 "board_gaps": "list of strings \u2014 the gaps that remain within the board, measured against the organization's stated goals and priorities.",
 "recruitment_needs": "string \u2014 3-5 sentences on where the founder needs to recruit to complement the present board, and the specific type of professionals to bring in to create a powerhouse board.",
 "not_yet_responded": "string \u2014 one sentence noting members who have not yet responded, if any names were supplied. Empty string if all responded."
}
```
- **E. Dynamic context**: reactivation context (founder_context + board member record/response; see Part 4 code)
- **F. Calling file/route**: reactivation_routes.py:~1160 — POST /api/reactivation/board-summary/generate
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reactivation_conversation_script` — Difficult Conversation Script
- **A. Generation type**: `reactivation_conversation_script`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit Board-development consultant preparing a founder/executive director for an important conversation with ONE current Board Member during Board Reactivation. This is NOT a generic template, confrontation script, termination letter, psychological assessment, stay/leave recommendation or legal advice. The founder decides; the member makes their own commitment. Use ONLY verified supplied information (organization context, Reactivation intake, this member's response). NEVER invent motives, personality, attitude, availability, expertise, willingness, conflicts, Board behavior or organizational facts. NEVER psychologically profile. NEVER infer protected characteristics. NEVER tell the founder the person is 'dead weight', lazy, uncaring or should be removed — and NEVER use the phrase 'dead weight' anywhere. If they want to continue: convert willingness into clear responsibility. If they need clarity: clarify what the organization needs and what they can realistically own. If capacity is limited: distinguish active Board responsibility from what they can sustain, without shame. If unsure: explore what is preventing commitment. If they cannot continue: thank them for honesty, acknowledge past contribution where supported, avoid guilt, discuss ONLY the organization-permitted transition options, preserve the relationship, establish next steps. NEVER invent removal procedures, votes, resignation procedures or bylaw provisions. Never pressure anyone to stay merely to preserve Board numbers.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "member": "string \u2014 actual Board Member full name",
 "board_role": "string \u2014 their current Board role where known, otherwise empty string",
 "recommitment_response": "string \u2014 the EXACT recommitment option this member selected, copied verbatim",
 "what_they_told_you": "string \u2014 accurate, concise summary of THIS member's actual Recommitment/Profile response (their experience, barriers, interests, capacity, willingness). Only supplied facts.",
 "what_you_need_to_understand": [
  "string \u2014 3 to 5 specific things the founder needs clarity about in THIS conversation, each grounded in the member's actual answers (e.g. whether they can realistically commit their stated hours, whether they will own a specific area they expressed interest in, what role clarity they said is missing)"
 ],
 "what_not_to_lose_sight_of": "string \u2014 one concise founder reminder along the lines of: the goal is not to convince them to stay at any cost; the goal is clarity about whether they can serve actively and, if so, what they are actually willing to own",
 "open_the_conversation": "string \u2014 natural suggested founder wording: thank them for completing the form, acknowledge the organization is strengthening the Board, explain the reason for the conversation, invite honest discussion. Adapt naturally to this person.",
 "understand_their_experience": [
  {
   "question": "string \u2014 tailored question exploring their actual stated experience/barriers/clarity",
   "why_this_matters": "string",
   "listen_for": "string",
   "optional_follow_up": "string \u2014 may be empty"
  }
 ],
 "explain_what_the_organization_needs_now": [
  "string \u2014 3 to 5 concise founder talking points based ONLY on the organization's actual mission, direction, priorities and Board needs, ending with suggested language explaining the Board must now help carry specific responsibility"
 ],
 "discuss_where_they_can_contribute": [
  {
   "question": "string \u2014 specific question connecting their verified expertise/interests/willingness to the organization's needs",
   "why_this_matters": "string"
  }
 ],
 "move_from_interest_to_responsibility": [
  "string \u2014 3 to 5 person-specific questions moving from vague willingness to explicit ownership: what they will own, what they can realistically commit to, what result can reasonably be expected, what support they need, how founder and member stay accountable"
 ],
 "fundraising_and_relationships": "string \u2014 ONLY where fundraising/relationships are genuinely relevant to this organization's Board expectations. Use the member's exact stated fundraising comfort. If they asked for training, acknowledge it and discuss support first. If they said they are not comfortable participating in fundraising, do NOT pressure solicitations \u2014 explore other useful contributions. Return an empty string when not relevant.",
 "clarify_the_way_forward": "string \u2014 adapt ENTIRELY to their exact recommitment answer. Reach explicit clarity about continuing actively, needing another conversation, transitioning or stepping down. Direct but respectful suggested wording. Mention ONLY the organization-permitted transition options supplied in context.",
 "close_with_clear_next_steps": "string \u2014 concise closing language: summarize what was agreed, what remains undecided, what happens next. End by telling the founder: after the conversation, record the actual conclusion in the Conversation Conclusion field \u2014 do not rely on memory."
}
```
- **E. Dynamic context**: reactivation context (founder_context + board member record/response; see Part 4 code)
- **F. Calling file/route**: reactivation_routes.py:480-545 — POST /api/reactivation/board-members/{id}/conversation-script/generate
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reactivation_stepped_down_followup` — Stepped-Down Board Member Follow-Up Email
- **A. Generation type**: `reactivation_stepped_down_followup`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
Use ONLY the supplied facts: the Board Member's responses, the founder's conversation notes, the recorded outcome, and the organization's supplied bylaws extract or described resignation process. If no resignation procedure was supplied, simply confirm next steps generally without citing any procedure. NEVER invent requirements, dates or commitments. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 a professional, warm subject line for the follow-up email.",
 "body": "string \u2014 the complete follow-up email for a Board Member who has stepped down, written from the founder to the member. It should: thank them genuinely for their actual service, acknowledge the decision reached in the conversation (use the supplied conversation notes), confirm any transition steps or commitments that were actually agreed, and reference the organization's actual resignation process ONLY as supplied in the bylaws extract or described process \u2014 never invent legal or procedural requirements. Warm, professional, respectful. Plain text paragraphs. End with the founder's name and organization."
}
```
- **E. Dynamic context**: reactivation context (founder_context + board member record/response; see Part 4 code)
- **F. Calling file/route**: reactivation_routes.py:1260 — outcome-conditional follow-up generator
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reactivation_advisory_confirmation` — Advisory Board Confirmation Email
- **A. Generation type**: `reactivation_advisory_confirmation`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
Use ONLY the supplied facts: the Board Member's responses, the founder's conversation notes and the recorded outcome. NEVER invent duties, meeting schedules or commitments that were not agreed. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 a professional, warm subject line confirming the advisory transition.",
 "body": "string \u2014 the complete email for a Board Member moving from the governing Board into an advisory relationship, written from the founder to the member. It should: confirm the agreement reached in the conversation (use the supplied conversation notes), express genuine appreciation for their continued involvement, acknowledge their actual contributions, and state that the founder/organization will follow up regarding what the advisory role will look like. Do not define advisory duties that were not agreed. Plain text paragraphs. End with the founder's name and organization."
}
```
- **E. Dynamic context**: reactivation context (founder_context + board member record/response; see Part 4 code)
- **F. Calling file/route**: reactivation_routes.py:1261 — outcome-conditional follow-up generator
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reactivation_engagement_plan` — Board Reactivation / Engagement Plan
- **A. Generation type**: `reactivation_engagement_plan`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are consolidating participating Board Members' own recommitment responses into a shareable Board Reactivation / Engagement Plan. STRICT PRIVACY: NEVER include difficult-conversation guides, the founder's private assessments, private conversation conclusions, confidential information about another member, or anything a member did not themselves share. NEVER invent commitments. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "sections": "list of objects {heading: string, content: string} \u2014 a consolidated BOARD REACTIVATION / ENGAGEMENT PLAN for the participating Board: (1) Where We Are as a Board, (2) How Board Members Are Willing and Able to Serve (only what each participating member actually shared and that is appropriate to share with the full Board), (3) Skills and Expertise Available to the Organization, (4) Contribution Areas and Shared Commitments, (5) Areas Requiring Board Attention, (6) How We Move Forward Together. Use ONLY supplied facts."
}
```
- **E. Dynamic context**: reactivation context (founder_context + board member record/response; see Part 4 code)
- **F. Calling file/route**: reactivation_plan_routes.py:90
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

### CONTEXT CODE — founder_context (reactivation org/founder context — VERBATIM)
`/app/backend/reactivation_routes.py` lines 205-232:
```python
    async def founder_context(user_id: str) -> dict:
        founder = await db.members.find_one({"user_id": user_id}, {"_id": 0, "first_name": 1, "last_name": 1, "email": 1})
        intake = await db.board_reactivation_intakes.find_one({"user_id": user_id}, {"_id": 0}, sort=[("submitted_at", -1)])
        organization = (intake or {}).get("organization_name", "")
        if not organization:
            profile = await db.recruitment_profiles.find_one({"user_id": user_id}, {"_id": 0, "data.organization_name": 1}) or {}
            organization = profile.get("data", {}).get("organization_name", "")
        return {
            "founder_name": f"{founder['first_name']} {founder['last_name']}".strip() if founder else "",
            "founder_email": (founder or {}).get("email", ""),
            "founder_title": (intake or {}).get("founder_title", ""),
            "founder_phone": (intake or {}).get("phone", "") or ((await db.funnel_leads.find_one({"email": (founder or {}).get("email", "")}, {"_id": 0, "phone": 1}, sort=[("created_at", -1)]) or {}).get("phone", "")),
            "organization": organization or "your organization",
            "transition_options": (intake or {}).get("transition_options", []),
        }

    async def owned_board_member(user_id: str, member_record_id: str) -> dict:
        record = await db.reactivation_board_members.find_one({"user_id": user_id, "member_record_id": member_record_id}, {"_id": 0})
        if not record:
            raise HTTPException(status_code=404, detail="Board Member not found")
        return record

    def public_record(record: dict) -> dict:
        return {key: record.get(key, "") for key in [
            "member_record_id", "name", "email", "phone", "role", "status", "source",
            "last_sent_at", "last_reminder_at", "submitted_at", "call_notes",
        ]}

```

### CONTEXT CODE — Individual Response Interpretation context assembly (VERBATIM)
`/app/backend/reactivation_routes.py` lines 1112-1160:
```python
    async def generate_analysis(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=409, detail="This Board Member has not completed their Recommitment Form yet — their response is needed before it can be understood.")
        query = {"user_id": member["user_id"], "type": ANALYSIS_TYPE, "application_id": member_record_id}
        existing = await db.generated_materials.find_one(query, {"_id": 0, "material_id": 1, "status": 1})
        if existing and existing.get("status") == "Generating":
            return {"material_id": existing["material_id"], "status": "Generating"}
        intake = await user_intake(member["user_id"])
        org_context = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision",
            "disengage_reason", "expected_contribution", "actually_happening"]}
        context = ("ORGANIZATION CONTEXT:\n" + json.dumps(org_context, indent=1, default=str)
                   + "\n\nTHIS BOARD MEMBER'S ACTUAL PROFILE & RECOMMITMENT FORM RESPONSE:\n"
                   + json.dumps({"name": record["name"], "current_board_role": record.get("role", ""), **record["response"]}, indent=1, default=str))
        master = await get_master_record(db, user_id=member["user_id"])
        if master and master.get("data"):
            context += ("\n\nCOMPLETE BOARD FIX MASTER INTAKE (the founder's own description of the organization, its board, goals and priorities):\n"
                        + json.dumps(master["data"], indent=1, default=str)[:6000])
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            material_id = existing["material_id"]
            await db.generated_materials.update_one(query, {"$set": {"status": "Generating", "updated_at": now}})
        else:
            material_id = str(uuid.uuid4())
            await db.generated_materials.insert_one({
                "material_id": material_id, "user_id": member["user_id"], "type": ANALYSIS_TYPE,
                "application_id": member_record_id, "module": 3, "title": "Understanding Their Response",
                "versions": [], "current_version": 0, "status": "Generating",
                "created_at": now, "updated_at": now})

        async def run_analysis():
            try:
                structured = await generate_structured(ANALYSIS_TYPE, context)
                await save_reactivation_material(member["user_id"], ANALYSIS_TYPE, "Understanding Their Response",
                                                 member_record_id, structured, analysis_display(structured, record["name"]))
            except Exception as exc:
                logger.error("Response analysis failed for %s: %s", member_record_id, exc)
                await db.generated_materials.update_one(query, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_analysis())
        return {"material_id": material_id, "status": "Generating"}

    # ---------------- SUMMARY OF YOUR ENTIRE BOARD ----------------

    SUMMARY_TYPE = "reactivation_board_summary"
```

### CONTEXT CODE — Summary of Your Entire Board context assembly (VERBATIM)
`/app/backend/reactivation_routes.py` lines 1160-1235:
```python
    SUMMARY_TYPE = "reactivation_board_summary"
    SUMMARY_RECORD_ID = "board-summary"

    def board_summary_display(structured: dict) -> str:
        def block(title, value):
            if isinstance(value, list):
                return [title] + ([f"- {item}" for item in value] if value else ["- None identified from the responses."]) + [""]
            return [title, value or "", ""]
        lines = ["SUMMARY OF YOUR ENTIRE BOARD", ""]
        lines += block("THE OVERALL STATE OF YOUR BOARD", structured.get("overall_state", ""))
        lines += block("READY TO RECOMMIT", structured.get("ready_to_recommit", []))
        lines += block("MAY NEED ADDITIONAL ENGAGEMENT", structured.get("need_engagement", []))
        lines += block("YOU NEED TO HAVE A CONVERSATION WITH", structured.get("need_conversation", []))
        lines += block("MAY BE BETTER SUITED TO AN ADVISORY ROLE", structured.get("advisory_candidates", []))
        lines += block("MAY NEED TO STEP OFF THE BOARD", structured.get("step_off_candidates", []))
        lines += block("THE ROLE EACH MEMBER CAN POTENTIALLY PLAY", structured.get("member_roles", []))
        lines += block("THE STRENGTHS YOU ALREADY HAVE", structured.get("board_strengths", []))
        lines += block("THE GAPS THAT REMAIN", structured.get("board_gaps", []))
        lines += block("WHERE YOU NEED TO RECRUIT", structured.get("recruitment_needs", ""))
        if structured.get("not_yet_responded"):
            lines += block("STILL WAITING ON", structured.get("not_yet_responded", ""))
        return "\n".join(lines).strip()

    @router.get("/reactivation/board-summary")
    async def get_board_summary(request: Request):
        member = await reactivation_member(request)
        material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": SUMMARY_TYPE, "application_id": SUMMARY_RECORD_ID}, {"_id": 0})
        if not material:
            return {"status": "NONE"}
        return {"material_id": material["material_id"], "status": material["status"],
                "display_text": current_display(material), "updated_at": material.get("updated_at", "")}

    @router.post("/reactivation/board-summary")
    async def generate_board_summary(request: Request):
        member = await reactivation_member(request)
        user_id = member["user_id"]
        records = await db.reactivation_board_members.find({"user_id": user_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
        responded = [r for r in records if r["status"] == "COMPLETED" and r.get("response")]
        if not responded:
            raise HTTPException(status_code=409, detail="At least one Board Member needs to complete the Recommitment Form before the board can be summarized.")
        query = {"user_id": user_id, "type": SUMMARY_TYPE, "application_id": SUMMARY_RECORD_ID}
        existing = await db.generated_materials.find_one(query, {"_id": 0, "material_id": 1, "status": 1})
        if existing and existing.get("status") == "Generating":
            return {"material_id": existing["material_id"], "status": "Generating"}
        intake = await user_intake(user_id)
        org_context = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision",
            "current_skills", "missing_skills", "disengage_reason", "expected_contribution", "actually_happening"]}
        context = "ORGANIZATION CONTEXT:\n" + json.dumps(org_context, indent=1, default=str)
        master = await get_master_record(db, user_id=user_id)
        if master and master.get("data"):
            context += ("\n\nCOMPLETE BOARD FIX MASTER INTAKE (the founder's own description of the organization, its board, goals and priorities):\n"
                        + json.dumps(master["data"], indent=1, default=str)[:8000])
        context += "\n\nEVERY BOARD MEMBER'S ACTUAL PROFILE & RECOMMITMENT FORM RESPONSE:\n"
        for record in responded:
            context += json.dumps({"name": record["name"], "current_board_role": record.get("role", ""), **record["response"]}, indent=1, default=str)[:5000] + "\n\n"
        waiting = [r["name"] for r in records if r["status"] != "COMPLETED"]
        if waiting:
            context += "\nBOARD MEMBERS WHO HAVE NOT RESPONDED YET: " + ", ".join(waiting)
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            material_id = existing["material_id"]
            await db.generated_materials.update_one(query, {"$set": {"status": "Generating", "updated_at": now}})
        else:
            material_id = str(uuid.uuid4())
            await db.generated_materials.insert_one({
                "material_id": material_id, "user_id": user_id, "type": SUMMARY_TYPE,
                "application_id": SUMMARY_RECORD_ID, "module": 3, "title": "Summary of Your Entire Board",
                "versions": [], "current_version": 0, "status": "Generating",
                "created_at": now, "updated_at": now})

        async def run_summary():
            try:
                structured = await generate_structured(SUMMARY_TYPE, context)
                await save_reactivation_material(user_id, SUMMARY_TYPE, "Summary of Your Entire Board",
```

### CONTEXT CODE — Difficult Conversation Script context (VERBATIM)
`/app/backend/reactivation_routes.py` lines 480-545:
```python
    async def generate_conversation_script(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        if record["status"] != "COMPLETED" or not record.get("response"):
            raise HTTPException(status_code=409, detail="This Board Member has not completed their Recommitment & Profile Form yet. Their response is needed before a person-specific conversation script can be generated.")
        intake = await user_intake(member["user_id"])
        transition_options = intake.get("transition_options", [])
        permitted = [option for option in transition_options if option not in {"We Have Not Decided Yet"}]
        org_context = {key: intake.get(key, "") for key in [
            "organization_name", "mission", "direction_12_24", "board_help_accomplish", "active_board_vision",
            "present_board", "active_board", "disengaged_board", "current_skills", "missing_skills",
            "roles_defined", "roles_description", "expected_contribution", "actually_happening",
            "strategic_plan", "board_participated_planning", "planning_involvement",
            "disengage_reason", "disengage_when", "disengagement_signs", "reactivation_attempts", "attempts_outcome",
            "meeting_frequency", "typical_meeting", "clear_responsibilities_after_meetings",
        ]}
        context = "ORGANIZATION CONTEXT AND BOARD REACTIVATION INTAKE (provided by the founder):\n" + json.dumps(org_context, indent=1, default=str)
        context += "\n\nORGANIZATION-PERMITTED TRANSITION OPTIONS (the ONLY transitions that may be mentioned): "
        context += ", ".join(permitted) if permitted else "The organization has not decided on transition options yet — do not present specific transition structures; the founder will decide the appropriate path in the conversation."
        context += ("\n\nTHIS BOARD MEMBER (their actual Board Member Profile & Recommitment Form response):\n"
                    + json.dumps({"name": record["name"], "current_board_role": record.get("role", ""), **record["response"]}, indent=1, default=str))
        analysis_material = await db.generated_materials.find_one(
            {"user_id": member["user_id"], "type": "reactivation_response_analysis", "application_id": member_record_id,
             "status": {"$nin": ["Generating", "Failed"]}}, {"_id": 0})
        if analysis_material:
            context += "\n\nUNDERSTANDING OF THEIR RESPONSE (interpretation already reviewed by the founder):\n" + current_display(analysis_material)[:8000]
        if record.get("call_notes"):
            context += "\n\nFOUNDER'S PREVIOUS NOTES ABOUT THIS BOARD MEMBER:\n" + record["call_notes"]
        direction = record.get("conversation_direction", "")
        if direction:
            context += (f"\n\nFOUNDER-SELECTED CONVERSATION DIRECTION: {direction}\n"
                        + DIRECTION_GUIDANCE.get(direction, "")
                        + "\nWrite the entire script specifically for this direction and this person — never a generic script.")
        query = {"user_id": member["user_id"], "type": "reactivation_conversation_script", "application_id": member_record_id}
        existing = await db.generated_materials.find_one(query, {"_id": 0, "material_id": 1, "status": 1})
        if existing and existing.get("status") == "Generating":
            return {"material_id": existing["material_id"], "status": "Generating"}
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            material_id = existing["material_id"]
            await db.generated_materials.update_one(query, {"$set": {"status": "Generating", "updated_at": now}})
        else:
            material_id = str(uuid.uuid4())
            await db.generated_materials.insert_one({
                "material_id": material_id, "user_id": member["user_id"], "type": "reactivation_conversation_script",
                "application_id": member_record_id, "module": 3, "title": "Difficult Conversation Script",
                "versions": [], "current_version": 0, "status": "Generating",
                "created_at": now, "updated_at": now,
            })

        async def run_generation():
            try:
                structured = await generate_structured("reactivation_conversation_script", context)
                structured["member"] = record["name"]
                structured["recommitment_response"] = record["response"].get("recommitment", "")
                await save_reactivation_material(member["user_id"], "reactivation_conversation_script", "Difficult Conversation Script", member_record_id, structured, script_display(structured))
            except Exception as exc:
                logging.getLogger(__name__).error("Conversation script generation failed for %s: %s", member_record_id, exc)
                await db.generated_materials.update_one(query, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"material_id": material_id, "status": "Generating"}

    async def owned_reactivation_material(user_id: str, material_id: str) -> dict:
```

### CONTEXT CODE — Outcome follow-up emails conditional mapping (VERBATIM)
`/app/backend/reactivation_routes.py` lines 1250-1300:
```python
        if payload.direction and payload.direction not in CONVERSATION_DIRECTIONS:
            raise HTTPException(status_code=422, detail="Invalid conversation direction")
        await db.reactivation_board_members.update_one(
            {"member_record_id": member_record_id},
            {"$set": {"conversation_direction": payload.direction}})
        return {"status": "saved"}

    # ---------------- DASHBOARD OUTCOME EMAILS ----------------

    OUTCOME_EMAIL_TYPES = {
        "Stepping Down From the Board": ("reactivation_stepped_down_followup", "Stepped-Down Follow-Up Email"),
        "Transitioning to an Advisory Role": ("reactivation_advisory_confirmation", "Advisory Board Confirmation Email"),
    }

    @router.post("/reactivation/board-members/{member_record_id}/outcome-email")
    async def generate_outcome_email(member_record_id: str, request: Request):
        member = await reactivation_member(request)
        record = await owned_board_member(member["user_id"], member_record_id)
        outcome = record.get("conversation_outcome", "")
        if outcome not in OUTCOME_EMAIL_TYPES:
            raise HTTPException(status_code=409, detail="Record the final outcome (Stepping Down or Advisory) before generating this email.")
        material_type, title = OUTCOME_EMAIL_TYPES[outcome]
        intake = await user_intake(member["user_id"])
        context_data = await founder_context(member["user_id"])
        context = (f"ORGANIZATION: {context_data['organization']}\nFOUNDER: {context_data['founder_name']}"
                   + (f" ({context_data['founder_title']})" if context_data.get("founder_title") else "")
                   + f"\n\nBOARD MEMBER: {record['name']} — current role: {record.get('role', 'Board Member')}"
                   + f"\n\nRECORDED FINAL OUTCOME: {outcome}"
                   + "\n\nFOUNDER'S POST-CALL NOTES (what actually happened and was agreed — highest authority):\n"
                   + (record.get("conversation_conclusion") or "No notes recorded.")
                   + "\n\nTHE BOARD MEMBER'S OWN FORM RESPONSES (for accurate acknowledgement of their service):\n"
                   + json.dumps(record.get("response") or {}, indent=1, default=str)[:6000])
        if outcome == "Stepping Down From the Board":
            if intake.get("bylaws_text"):
                context += "\n\nORGANIZATION BYLAWS EXTRACT (use ONLY procedures actually stated here):\n" + intake["bylaws_text"][:15000]
            elif intake.get("resignation_process"):
                context += "\n\nORGANIZATION'S DESCRIBED RESIGNATION PROCESS (use this, never invent requirements):\n" + intake["resignation_process"]
            else:
                context += "\n\nNo bylaws or resignation process were provided — do NOT cite any procedure; confirm next steps generally."
        try:
            structured = await generate_structured(material_type, context)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Generation failed: {str(exc)[:300]}. Your information is preserved — you can try again.") from exc
        display = f"SUBJECT: {structured.get('subject', '')}\n\n{structured.get('body', '')}"
        material = await save_reactivation_material(member["user_id"], material_type, title, member_record_id, structured, display)
        full = await db.generated_materials.find_one({"material_id": material["material_id"]}, {"_id": 0})
        return {**material, "display_text": current_display(full), "to_name": record["name"], "to_email": record.get("email", "")}

    @router.get("/reactivation/board-members/{member_record_id}/outcome-email")
    async def get_outcome_email(member_record_id: str, request: Request):
        member = await reactivation_member(request)
```

## PART 5 — STAGE 2: IDENTIFY THE BOARD MEMBERS NEEDED

#### `powerhouse_board_blueprint` — The Board Members Your Organization Needs
- **A. Generation type**: `powerhouse_board_blueprint`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
CRITICAL COUNT RULE: the number of priority_roles MUST EXACTLY EQUAL the number of new board members the customer said they want to recruit (see the recruitment profile context — new_members_count). If they said 1, produce exactly 1. If they said 7, produce exactly 7. There is NO maximum. ONLY if the customer selected 'Not Sure' should you recommend an appropriate number yourself (state it in recommended_count_statement) and produce exactly that many profiles. A single candidate may satisfy more than one need — never claim the organization must recruit one completely separate person for every competency unless the supplied context specifically requires it.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "recommended_count_statement": "string \u2014 ONLY when the customer said they are Not Sure how many board members to recruit: write 'Recommended Number of New Board Members: X' followed by one short sentence explaining the recommendation based on their current board size, active members, gaps, challenges and priorities. When the customer supplied an exact number, return an empty string.",
 "priority_roles": [
  {
   "role_name": "string \u2014 the Role / Expertise Area, e.g. 'Fundraising & Philanthropy' or 'Finance & Accounting'. NEVER invent formal board officer titles such as 'Chief Fundraising Board Officer' \u2014 name the expertise area itself.",
   "why_this_person_is_important": "string \u2014 exactly TWO concise organization-specific sentences explaining why this expertise is important to THIS nonprofit",
   "how_this_person_can_support": "string \u2014 exactly TWO concise organization-specific sentences explaining what this person could help strengthen, lead, open, build or contribute",
   "what_to_look_for": [
    "string \u2014 3 to 5 concise qualities, experience areas, capabilities or useful relationships relevant to the role"
   ]
  }
 ],
 "internal_analysis": {
  "present_board_brings": "string \u2014 internal use only",
  "important_gaps": "string \u2014 internal use only",
  "board_needed": "string \u2014 internal use only"
 }
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

### CONTEXT CODE — Powerhouse Blueprint special context (founder-in-board rule + recommitment roster) inside workspace generate (VERBATIM)
`/app/backend/workspace_routes.py` lines 182-345:
```python
    @router.post("/generate")
    async def generate(payload: GenerateRequest, request: Request):
        member = await current_member(request)
        user_id = member["user_id"]
        if payload.type not in GENERATION_TYPES:
            raise HTTPException(status_code=422, detail="Unknown generation type")
        meta = GENERATION_TYPES[payload.type]
        if meta.get("module", 0) >= 4:
            require_entitlement(member, {"recruitment_selection_onboarding"})
        profile = await get_profile(db, user_id)
        if not profile.get("confirmed"):
            raise HTTPException(status_code=409, detail="Complete your Recruitment Profile before generating materials")
        lead_doc = await get_lead(db, member)
        org_name_check = (lead_doc or {}).get("organization", "") or profile.get("data", {}).get("organization_name", "")
        mission_check = profile.get("data", {}).get("mission", "")
        if not org_name_check or not mission_check:
            raise HTTPException(status_code=422, detail="Add your organization name and mission statement in your Recruitment Profile first. They are required so every recruitment material is finished and organization-specific.")
        context = await build_org_context(db, user_id, member)
        reference = await reference_context(db, payload.type)
        if reference:
            context = f"{context}\n\n{reference}"
        origin = origin_of(request)
        opportunity = await ensure_opportunity(user_id, member)
        apply_url = f"{origin}/board-opportunities/{opportunity['slug']}/apply"
        if payload.type in MODULE3_LINK_TYPES:
            context += f"\n\nBOARD APPLICATION URL (insert this exact URL wherever the application link belongs): {apply_url}"
        application_id = ""
        application = None
        if meta.get("per_application"):
            if not payload.application_id:
                raise HTTPException(status_code=422, detail="This material is generated for a specific applicant")
            application = await owned_application(user_id, payload.application_id)
            application_id = application["application_id"]
            if payload.type in {"board_member_portfolio", "board_member_engagement_guide"}:
                context += "\n\n" + application_context_text({**application, "notes": "", "references": []})
                profile_response = await db.board_profile_responses.find_one(
                    {"user_id": user_id, "data.email": application.get("applicant_email", "")}, {"_id": 0, "data": 1})
                if profile_response:
                    import json as _json
                    context += "\n\nBOARD MEMBER PROFILE FORM RESPONSE:\n" + _json.dumps(profile_response["data"], indent=1)
                if application.get("board_role"):
                    context += f"\n\nBOARD ROLE THEY WERE RECRUITED FOR: {application['board_role']}"
                context += "\n\nPRIVACY: never include referee responses, internal interview notes or internal evaluation material."
            else:
                context += "\n\n" + application_context_text(application)
                cv_doc = await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0, "cv_text": 1})
                if cv_doc and cv_doc.get("cv_text"):
                    context += "\n\nCANDIDATE CV / RESUME (extracted text — use only what is actually present):\n" + cv_doc["cv_text"][:12000]
        if payload.type == "candidate_referee_request":
            process = await db.reference_processes.find_one(
                {"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "candidate_token": 1, "status": 1})
            if process and process.get("candidate_token") and process.get("status") not in {"Completed", "References Submitted"}:
                context += f"\n\nSECURE REFERENCE INFORMATION FORM URL FOR THIS CANDIDATE (include this exact link): {origin}/reference-form/{process['candidate_token']}"
            else:
                context += "\n\nNO SECURE REFERENCE FORM LINK EXISTS YET — ask the candidate to reply to this email with their referee details."
        if payload.type == "powerhouse_board_blueprint":
            context += ("\n\nPRESENT BOARD COMPOSITION RULE: The founder/executive director is a serving member of the present board. "
                        "Include the founder — with their actual skills, experience and role — as part of the present board when assessing "
                        "the current board composition and calculating the gap between the present board and the ideal board.")
            roster = await db.reactivation_board_members.find(
                {"user_id": user_id, "status": "COMPLETED"}, {"_id": 0, "name": 1, "role": 1, "response": 1}).to_list(100)
            if roster:
                import json as _json
                context += ("\n\nCURRENT BOARD MEMBER RECOMMITMENT RESPONSES (submitted by the board members themselves through the "
                            "Board Member Profile & Recommitment Form — use these to understand what the present board actually brings, "
                            "who is staying, who is transitioning, and what gaps remain):\n"
                            + _json.dumps([{"name": r.get("name", ""), "board_role": r.get("role", ""), "their_response": r.get("response", {})}
                                           for r in roster], indent=1, default=str))
        if payload.type in {"conditional_offer", "formal_appointment_email"}:
            links = []
            overview_token = await ensure_share_token(user_id, "organization_overview")
            manual_token = await ensure_share_token(user_id, "board_manual")
            if overview_token:
                links.append(f"Organization Overview (View): {origin}/shared/{overview_token}")
            if manual_token:
                links.append(f"Board Manual (View): {origin}/shared/{manual_token}")
            # candidate-specific signature links (idempotent per agreement + candidate)
            for agreement_type in ["board_member_agreement", "confidentiality_agreement", "conflict_of_interest_agreement"]:
                existing_request = await db.signature_requests.find_one(
                    {"owner_user_id": user_id, "application_id": application_id, "agreement_type": agreement_type, "status": {"$ne": "Void"}},
                    {"_id": 0, "token": 1, "status": 1})
                if existing_request and existing_request.get("status") == "Signed":
                    continue
                if not existing_request:
                    agreement_material = await get_current_material(db, user_id, agreement_type, "")
                    token = secrets.token_urlsafe(24)
                    await db.signature_requests.insert_one({
                        "request_id": new_id(), "token": token, "owner_user_id": user_id,
                        "application_id": application_id, "agreement_type": agreement_type,
                        "agreement_title": GENERATION_TYPES[agreement_type]["title"],
                        "material_id": agreement_material["material"]["material_id"],
                        "agreement_version": agreement_material["current"]["version"],
                        "document_snapshot": agreement_material["current"]["display_text"],
                        "organization_name": (await db.opportunities.find_one({"user_id": user_id}, {"_id": 0, "organization_name": 1}) or {}).get("organization_name", ""),
                        "board_member_name": application.get("profile_snapshot", {}).get("full_name", ""),
                        "board_member_email": application.get("applicant_email", ""),
                        "status": "Ready for Signature", "created_at": now_iso(), "updated_at": now_iso(),
                    })
                    existing_request = {"token": token}
                links.append(f"{GENERATION_TYPES[agreement_type]['title']} (Review and Sign): {origin}/sign/{existing_request['token']}")
            # candidate-specific profile form link (idempotent)
            profile_link = await db.board_profile_links.find_one({"user_id": user_id, "application_id": application_id}, {"_id": 0, "token": 1})
            if not profile_link:
                profile_link = {"token": secrets.token_urlsafe(24)}
                snapshot = application.get("profile_snapshot", {})
                await db.board_profile_links.insert_one({
                    "token": profile_link["token"], "user_id": user_id, "application_id": application_id,
                    "prefill": {"full_name": snapshot.get("full_name", ""), "email": application.get("applicant_email", ""),
                                "professional_title": snapshot.get("profession", ""), "employer": snapshot.get("employer", ""),
                                "linkedin": snapshot.get("linkedin", ""), "location": f"{snapshot.get('city', '')} {snapshot.get('state_region', '')}".strip()},
                    "status": "Created", "created_at": now_iso(),
                })
            links.append(f"Board Member Profile Form (Complete Your Profile): {origin}/board-profile/{profile_link['token']}")
            process = await db.reference_processes.find_one({"owner_user_id": user_id, "application_id": application_id}, {"_id": 0, "candidate_token": 1, "status": 1})
            if process and process.get("status") not in {"Completed", "References Submitted", "In Progress"}:
                links.append(f"Reference Information Form (Provide Your References): {origin}/reference-form/{process['candidate_token']}")
            background = (application.get("background_check") or {}).get("status", "")
            context += f"\n\nBACKGROUND CHECK STATUS FOR THIS CANDIDATE: {background or 'Not recorded'} — never state a background check is required if it is marked Not Required."
            if process:
                context += f"\nREFERENCE CHECK STATUS: {process.get('status')} — never ask for references again if they are already submitted or completed."
            session = profile.get("onboarding_session") or {}
            if session:
                context += "\n\nBOARD ONBOARDING SESSION (invite the candidate to this session using these exact details):\n" + "\n".join(f"{k}: {v}" for k, v in session.items() if v)
            if links:
                context += ("\n\nLINKS TO INCLUDE IN THE EMAIL under a clear 'Before the Onboarding Session' section (use these exact URLs on their own lines; already-signed agreements are intentionally omitted — do not ask for them again):\n" + "\n".join(links))
        if payload.type == "first_board_meeting_invitation":
            meeting = profile.get("first_meeting") or {}
            if meeting:
                context += "\n\nFIRST BOARD MEETING DETAILS (use these exact details; omit anything blank):\n" + "\n".join(f"{k}: {v}" for k, v in meeting.items() if v)
            joined = await db.opportunity_applications.find(
                {"owner_user_id": user_id, "$or": [{"final_outcome": "Joined Board"}, {"status": "Selected"}]},
                {"_id": 0, "application_id": 1, "profile_snapshot": 1, "applicant_email": 1}).to_list(30)
            incomplete = []
            for member_app in joined:
                response_doc = await db.board_profile_responses.find_one({"user_id": user_id, "application_id": member_app["application_id"]}, {"_id": 0, "submitted_at": 1})
                if not response_doc:
                    link = await db.board_profile_links.find_one({"user_id": user_id, "application_id": member_app["application_id"]}, {"_id": 0, "token": 1})
                    incomplete.append((member_app.get("profile_snapshot", {}).get("full_name", ""), link))
            names = ", ".join(m.get("profile_snapshot", {}).get("full_name", "") for m in joined)
            context += f"\n\nNEW BOARD MEMBERS RECEIVING THIS INVITATION: {names or 'the new board members'}"
            if incomplete:
                token = next((link["token"] for _, link in incomplete if link), "")
                context += ("\n\nBOARD MEMBER PROFILE STATUS: the following recipients have NOT completed their Board Member Profile: "
                            + ", ".join(name for name, _ in incomplete)
                            + (f". Board Member Profile URL to include: {origin}/board-profile/{token}" if token else ""))
            else:
                context += "\n\nBOARD MEMBER PROFILE STATUS: every recipient has completed their Board Member Profile — OMIT the profile section."
        try:
            structured = await generate_structured(payload.type, context, payload.instructions or "")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Generation failed: {str(exc)[:300]}. Your information is preserved — you can try again.") from exc
        structured = replace_link(structured, apply_url)
        material = await save_generation(db, user_id, payload.type, structured, context[:1500], application_id)
        return material

    @router.post("/materials/{material_id}/approve")
    async def approve_material(material_id: str, request: Request):
        member = await current_member(request)
        material = await db.generated_materials.find_one(
            {"material_id": material_id, "user_id": member["user_id"]}, {"_id": 0, "type": 1, "share_token": 1})
        if not material:
            raise HTTPException(status_code=404, detail="Material not found")
        updates = {"status": "Approved", "approved_at": now_iso(), "updated_at": now_iso()}
        if material["type"] == "board_member_portfolio" and not material.get("share_token"):
```

## PART 6 — STAGE 3: LAUNCH RECRUITMENT (all 12 campaign generators incl. recruitment_strategy)

#### `recruitment_strategy` — Board Recruitment Strategy
- **A. Generation type**: `recruitment_strategy`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
Keep every section concise and practical. No long consulting essays, no repetition of the full Module 1 analysis, no long channel instructions. The timeline and execution roadmap are added by the platform — do not write them.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "executive_summary": "string \u2014 NO MORE than TWO short sentences stating the roles being recruited, the channels being used, and that recruitment begins immediately",
 "roles": [
  {
   "role_name": "string \u2014 a priority board role from Module 1, same order",
   "person_sought": "string \u2014 ONE short sentence describing the type of person being sought"
  }
 ],
 "channels": [
  {
   "channel": "string \u2014 ONLY one of: 'Personal Network', 'Referral Network', 'Public Outreach'. Include ONLY channels the customer's intake answers make available. Never include a channel they said they cannot or do not want to use.",
   "approach": "string \u2014 a VERY BRIEF one-to-two sentence practical approach for this channel, mentioning the customer's actual selected outlets where relevant. Never multiple paragraphs."
  }
 ],
 "selection_criteria": [
  "string \u2014 one concise quality applicants should demonstrate, adapted to the organization's selected board type (mission alignment, relevant skills for a priority role, willingness and capacity to serve, understanding of the board role, ability to contribute to the kind of board being built, participation in meetings and agreed responsibilities, professional conduct and credibility). Never numeric scores. Never statutory/legal requirements."
 ]
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `board_opportunity` — Board Opportunity
- **A. Generation type**: `board_opportunity`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
Write as a real professional board opportunity announcement. Never print internal field labels such as 'Why Recruiting:' or 'Fundraising Contribution:'. Use only the priority roles identified in Module 1 — never invent 10-12 candidate profiles.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "title": "string \u2014 professional board opportunity title",
 "introduction": "string \u2014 2 to 4 sentence organization/opportunity introduction",
 "about_the_organization": "string \u2014 the organization and its mission in natural prose",
 "who_we_are_looking_for": "string \u2014 the priority board roles from Module 1, concisely, in natural prose or a short list",
 "what_board_members_will_contribute": "string",
 "board_expectations": "string",
 "meeting_time_and_location": "string \u2014 meeting frequency, time commitment and location/geographic information as supplied",
 "how_to_apply": "string \u2014 must contain the exact application URL supplied in the context"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `application_questions` — Board Application — Organization-Specific Questions
- **A. Generation type**: `application_questions`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "custom_questions": [
  {
   "label": "string \u2014 the question",
   "type": "one of: text, textarea, yes_no",
   "why": "string \u2014 why this question matters for this organization"
  }
 ]
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `linkedin_post` — LinkedIn Recruitment Post
- **A. Generation type**: `linkedin_post`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are acting as an experienced nonprofit board recruitment consultant preparing FINISHED recruitment materials for a real nonprofit — never a template for the founder to finish. Use ONLY verified information supplied in the context (organization, board, Module 1 priority profiles, recruitment logistics, live system links). Never invent programs, achievements, impact statistics, legal status, partnerships, board expectations, meeting schedules, candidate requirements, compensation or application deadlines. The supplied Board Application URL must appear naturally wherever an application call-to-action belongs (the platform substitutes [APPLICATION LINK] with the real URL). Never say the opportunity has been posted on an external platform. Never describe board service as paid employment unless the context explicitly says it is compensated. Adapt language to the actual board type — never describe an Advisory Board as having governing/fiduciary authority. Write like an experienced human nonprofit leader, not an AI assistant. Avoid 'exciting opportunity', 'calling all changemakers', hype, generic inspirational filler, emojis, fake quotes, invented urgency and hashtag walls. Each campaign resource serves a DIFFERENT channel — do not repeat the same opening, structure and language used by the other campaign materials. Recruitment materials should communicate meaningful contribution, not simply attending meetings. The finished resource must require no missing information from the founder.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "post_text": "string \u2014 a complete LinkedIn feed post in the founder's voice, ready to publish, including the application link placeholder [APPLICATION LINK]. NOT a shortened copy of the Recruitment Job Post \u2014 it should sound like a person speaking to their professional network. OPENING: a strong natural observation, decision, milestone or invitation relevant to THIS organization (why they are intentionally building the board, the stage reached, why professional expertise matters to the mission \u2014 vary the approach). MIDDLE: briefly the organization, mission, what the board is being built to accomplish, and the most important expertise sought from the Module 1 priority profiles (do not overwhelm with an enormous skills list). BOARD CONTRIBUTION: members bring more than attendance \u2014 describe meaningful contribution based on actual expectations. CTA: direct invitation to apply with the application link. 150-300 words. Short paragraphs, mobile-readable. No emojis. Never clich\u00e9s like 'Calling all changemakers!' or 'We're thrilled to announce!'.",
 "hashtags": [
  "string \u2014 OPTIONAL, no more than 3 highly relevant hashtags; return an empty list if hashtags add nothing"
 ]
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `social_posts` — Social Media Recruitment Post
- **A. Generation type**: `social_posts`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are acting as an experienced nonprofit board recruitment consultant preparing FINISHED recruitment materials for a real nonprofit — never a template for the founder to finish. Use ONLY verified information supplied in the context (organization, board, Module 1 priority profiles, recruitment logistics, live system links). Never invent programs, achievements, impact statistics, legal status, partnerships, board expectations, meeting schedules, candidate requirements, compensation or application deadlines. The supplied Board Application URL must appear naturally wherever an application call-to-action belongs (the platform substitutes [APPLICATION LINK] with the real URL). Never say the opportunity has been posted on an external platform. Never describe board service as paid employment unless the context explicitly says it is compensated. Adapt language to the actual board type — never describe an Advisory Board as having governing/fiduciary authority. Write like an experienced human nonprofit leader, not an AI assistant. Avoid 'exciting opportunity', 'calling all changemakers', hype, generic inspirational filler, emojis, fake quotes, invented urgency and hashtag walls. Each campaign resource serves a DIFFERENT channel — do not repeat the same opening, structure and language used by the other campaign materials. Recruitment materials should communicate meaningful contribution, not simply attending meetings. The finished resource must require no missing information from the founder.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "post_text": "string \u2014 ONE concise board recruitment post suitable for Facebook, Instagram and similar general social channels, including the application link placeholder [APPLICATION LINK]. NOT a copy of the LinkedIn post: slightly more accessible and shareable while remaining professional. Structure: a strong opening; 2-5 short paragraphs; if useful a SHORT list of key expertise being recruited and why those people matter; direct invitation to apply. 100-220 words. Human, simple, mobile-readable, easy to share. Prefer no emojis. No unnecessary hashtags. Never sound like a commercial advertisement."
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `recruitment_emails` — Recruitment Email
- **A. Generation type**: `recruitment_emails`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are acting as an experienced nonprofit board recruitment consultant preparing FINISHED recruitment materials for a real nonprofit — never a template for the founder to finish. Use ONLY verified information supplied in the context (organization, board, Module 1 priority profiles, recruitment logistics, live system links). Never invent programs, achievements, impact statistics, legal status, partnerships, board expectations, meeting schedules, candidate requirements, compensation or application deadlines. The supplied Board Application URL must appear naturally wherever an application call-to-action belongs (the platform substitutes [APPLICATION LINK] with the real URL). Never say the opportunity has been posted on an external platform. Never describe board service as paid employment unless the context explicitly says it is compensated. Adapt language to the actual board type — never describe an Advisory Board as having governing/fiduciary authority. Write like an experienced human nonprofit leader, not an AI assistant. Avoid 'exciting opportunity', 'calling all changemakers', hype, generic inspirational filler, emojis, fake quotes, invented urgency and hashtag walls. Each campaign resource serves a DIFFERENT channel — do not repeat the same opening, structure and language used by the other campaign materials. Recruitment materials should communicate meaningful contribution, not simply attending meetings. The finished resource must require no missing information from the founder.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 ONE strong professional subject line, not ten alternatives",
 "body": "string \u2014 a finished professional email the founder can send to their network, supporters, colleagues and professional relationships inviting qualified people to consider the board opportunity, including the application link placeholder [APPLICATION LINK]. Use a natural GENERAL greeting such as 'Hello,' \u2014 never [First Name] and never fake personalization. Body: (1) briefly why the founder is reaching out; (2) the organization is recruiting/building its board; (3) the mission briefly; (4) the kinds of professional experience being sought; (5) what board members will help accomplish; (6) invite recipients whose experience aligns to apply; (7) make it natural to forward the opportunity to another suitable professional; (8) the application link; (9) sign with the actual founder/contact information supplied. Never claim the founder personally admires the recipient or that they were specially selected. 225-400 words. Warm, professional, personal without pretending intimacy."
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `linkedin_launch_instructions` — LinkedIn Jobs Launch Guide
- **A. Generation type**: `linkedin_launch_instructions`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "steps": [
  {
   "title": "string",
   "instructions": "string \u2014 practical instructions covering where to post, how to structure the post, how to use the application link, how to ask others to share, how to contact potential prospects, how to follow up, how to maintain campaign activity. When discussing budget say: 'You can begin with a small controlled test budget, such as $20 where the option is available, and increase it only if you choose. LinkedIn's available posting and promotion options may vary.' NEVER state that LinkedIn charges $20 as a universal platform fact. Do not fabricate LinkedIn screenshots or exact current UI labels."
  }
 ]
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `board_recruitment_job_post` — Recruitment Job Post
- **A. Generation type**: `board_recruitment_job_post`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are acting as an experienced nonprofit board recruitment consultant preparing FINISHED recruitment materials for a real nonprofit — never a template for the founder to finish. Use ONLY verified information supplied in the context (organization, board, Module 1 priority profiles, recruitment logistics, live system links). Never invent programs, achievements, impact statistics, legal status, partnerships, board expectations, meeting schedules, candidate requirements, compensation or application deadlines. The supplied Board Application URL must appear naturally wherever an application call-to-action belongs (the platform substitutes [APPLICATION LINK] with the real URL). Never say the opportunity has been posted on an external platform. Never describe board service as paid employment unless the context explicitly says it is compensated. Adapt language to the actual board type — never describe an Advisory Board as having governing/fiduciary authority. Write like an experienced human nonprofit leader, not an AI assistant. Avoid 'exciting opportunity', 'calling all changemakers', hype, generic inspirational filler, emojis, fake quotes, invented urgency and hashtag walls. Each campaign resource serves a DIFFERENT channel — do not repeat the same opening, structure and language used by the other campaign materials. Recruitment materials should communicate meaningful contribution, not simply attending meetings. The finished resource must require no missing information from the founder.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "title": "string \u2014 a professional opportunity title using the organization's actual board terminology, e.g. 'Founding Board Member | Help Shape [Mission Area]' or 'Board Member Opportunity | Help Build [Meaningful Outcome]'. No clickbait.",
 "post_body": "string \u2014 the organization's PRIMARY professional board recruitment opportunity, suitable for professional platforms such as LinkedIn Jobs, BoardSource, Idealist and VolunteerMatch (never claim it has already been published anywhere). Written for a professional who may never have heard of the nonprofit. Use these exact section headings in this order, each on its own line in UPPERCASE, omitting a section only when no supporting data exists: OPENING (2-4 strong sentences \u2014 why the organization is building/recruiting its board and the opportunity for capable professionals, specific to this organization); ABOUT THE ORGANIZATION (what it does, who it serves, its mission, relevant direction \u2014 concise and factual); THE OPPORTUNITY (what board service means within THIS organization \u2014 strategy, governance, expertise, relationships, partnerships, fundraising, growth, leadership, committee work only where supported); WHO WE ARE LOOKING FOR (translate the approved Module 1 priority profiles into outward-facing professional expertise \u2014 never paste internal phrases like 'Why this role is important'; where appropriate note that candidates bringing experience across several areas are welcome); BOARD MEMBER EXPECTATIONS (only actually-supported items); PRACTICAL DETAILS (only KNOWN meeting frequency, format, location, time commitment, term, deadline \u2014 omit unknown items entirely, never write 'Not provided'); CALL TO ACTION (a strong direct invitation containing the application link placeholder [APPLICATION LINK]). 450-750 words depending on available information. Professional, credible, specific, human, purpose-driven. Clearly represent the actual nature of the board opportunity; NEVER describe an unpaid nonprofit board role as salaried employment."
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `personal_invitation_email` — Personal Invitation Email
- **A. Generation type**: `personal_invitation_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string",
 "body": "string \u2014 a warm personal email inviting someone the founder already knows to consider the board opportunity, includes the application link placeholder [APPLICATION LINK]"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `personal_invitation_message` — Personal Invitation Message
- **A. Generation type**: `personal_invitation_message`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "message": "string \u2014 a concise direct message version for LinkedIn, Facebook, text or another direct-message channel, includes the application link placeholder [APPLICATION LINK]"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `referral_request_email` — Referral Recruitment Message
- **A. Generation type**: `referral_request_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are acting as an experienced nonprofit board recruitment consultant preparing FINISHED recruitment materials for a real nonprofit — never a template for the founder to finish. Use ONLY verified information supplied in the context (organization, board, Module 1 priority profiles, recruitment logistics, live system links). Never invent programs, achievements, impact statistics, legal status, partnerships, board expectations, meeting schedules, candidate requirements, compensation or application deadlines. The supplied Board Application URL must appear naturally wherever an application call-to-action belongs (the platform substitutes [APPLICATION LINK] with the real URL). Never say the opportunity has been posted on an external platform. Never describe board service as paid employment unless the context explicitly says it is compensated. Adapt language to the actual board type — never describe an Advisory Board as having governing/fiduciary authority. Write like an experienced human nonprofit leader, not an AI assistant. Avoid 'exciting opportunity', 'calling all changemakers', hype, generic inspirational filler, emojis, fake quotes, invented urgency and hashtag walls. Each campaign resource serves a DIFFERENT channel — do not repeat the same opening, structure and language used by the other campaign materials. Recruitment materials should communicate meaningful contribution, not simply attending meetings. The finished resource must require no missing information from the founder.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "message": "string \u2014 a finished referral message the founder can send to current board members, supporters, colleagues, partners, community leaders, friends and advisors asking them to help identify people who may be a good fit for the board, including the application link placeholder [APPLICATION LINK]. This asks for REFERRALS \u2014 never pressure the recipient to join the board themselves. Use a natural general greeting with no unresolved placeholder. Briefly explain the organization is intentionally recruiting new board members; the top categories of people/expertise needed; why those people would be useful; ask the recipient to think of strong matches in their network and to forward/share the application link directly. Sign with the actual founder/contact information supplied. 150-275 words. Personal, direct, easy to forward, relationship-preserving. Do not over-explain the entire organization."
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `referral_request_message` — Referral Request Message
- **A. Generation type**: `referral_request_message`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "message": "string \u2014 a concise direct-message version of the referral request for LinkedIn, text or other channels, includes the application link placeholder [APPLICATION LINK]"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

### CONTEXT CODE — build_org_context — org-level context for ALL recruitment generators (VERBATIM)
`/app/backend/workspace_service.py` lines 255-330:
```python
async def build_org_context(db, user_id: str, member: dict) -> str:
    """Standard organization context: public form + confirmed profile + approved strategy + opportunity."""
    profile = await get_profile(db, user_id)
    lead = await get_lead(db, member)
    parts = [profile_context_text(profile.get("data", {}), lead)]
    founder_contact = {
        "name": f"{member.get('first_name', '')} {member.get('last_name', '')}".strip(),
        "title": (profile.get("data", {}) or {}).get("founder_title", "") or "Founder",
        "email": member.get("email", ""),
        "phone": (lead or {}).get("phone", ""),
    }
    parts.insert(1, "FOUNDER CONTACT (sign every generated email with these actual details; omit empty items; never placeholders):\n" + json.dumps(founder_contact, indent=1))
    if profile.get("strategy_intake"):
        parts.append("BOARD RECRUITMENT LOGISTICS AND NETWORK (the founder's saved answers about board logistics, their network and recruitment channels — collected once through the Board Recruitment Intake):\n" + json.dumps(profile["strategy_intake"], indent=1, default=str))
    blueprint = await get_current_material(db, user_id, "powerhouse_board_blueprint")
    if blueprint and blueprint["current"]:
        structured = blueprint["current"].get("structured") or {}
        parts.append("MODULE 1 BOARD RECRUITMENT ANALYSIS (internal — the exact priority board roles to recruit and detailed profiles):\n" + json.dumps(structured, indent=1, default=str)[:14000])
    strategy = await get_current_material(db, user_id, "recruitment_strategy")
    if strategy and strategy["current"]:
        parts.append("APPROVED RECRUITMENT STRATEGY:\n" + strategy["current"]["display_text"][:12000])
    opportunity_material = await get_current_material(db, user_id, "board_opportunity")
    if opportunity_material and opportunity_material["current"]:
        parts.append("BOARD OPPORTUNITY:\n" + opportunity_material["current"]["display_text"][:8000])
    return "\n\n".join(parts)


async def run_interview_guide(db, application_id: str) -> None:
    """One automatic generation attempt. Application always remains intact on failure."""
    import os
    from ai_service import generate_structured
    application = await db.opportunity_applications.find_one({"application_id": application_id}, {"_id": 0})
    if not application:
        return
    if os.environ.get("AUTO_INTERVIEW_GUIDE", "true").lower() != "true":
        await db.opportunity_applications.update_one({"application_id": application_id}, {"$set": {"interview_guide": {"status": "Disabled"}}})
        return
    await db.opportunity_applications.update_one({"application_id": application_id}, {"$set": {"interview_guide.status": "Generating"}})
    try:
        owner_id = application["owner_user_id"]
        member = await db.members.find_one({"user_id": owner_id}, {"_id": 0}) or {}
        context = await build_org_context(db, owner_id, member) + "\n\n" + application_context_text(application)
        structured = await generate_structured("interview_guide", context)
        material = await save_generation(db, owner_id, "interview_guide", structured, "Automatic interview guide", application_id)
        await db.opportunity_applications.update_one(
            {"application_id": application_id},
            {"$set": {"interview_guide": {"status": "Ready", "material_id": material["material_id"], "generated_at": now_iso()}}},
        )
    except Exception as exc:
        await db.opportunity_applications.update_one(
            {"application_id": application_id},
            {"$set": {"interview_guide": {"status": "Failed", "error": str(exc)[:400], "failed_at": now_iso()}}},
        )
```

## PART 7 — STAGE 4: SELECT & INTERVIEW

#### `interview_guide` — Interview Guide
- **A. Generation type**: `interview_guide`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit board recruitment consultant preparing a founder to interview ONE SPECIFIC board candidate. This is NOT a generic interview questionnaire — use the applicant's actual application, CV, background and expressed interests together with the organization's actual mission, board type, current needs, Module 1 priority board profiles, stage and goals. learn_about_this_candidate: 2-3 questions DIRECTLY tied to specific items in the candidate's CV or application. mission_alignment: about 2 questions. contribution_to_the_board: 2-3 questions using only supported areas. NEVER invent candidate employment, achievements, qualifications, board experience, motivation, relationships, availability, personality or beliefs. Never infer sensitive personal characteristics. If candidate information is limited, use only what is actually known — no fake specificity. NEVER include an AI score, fit score, hire/do-not-hire, recommended/not-recommended, or pass/fail — the founder makes the final judgment.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "header": {
  "candidate": "string \u2014 actual candidate name",
  "current_position": "string \u2014 actual position if known, else empty",
  "organization": "string \u2014 actual employer if known, else empty",
  "board_opportunity": "string \u2014 actual organization + its actual board terminology",
  "suggested_duration": "string \u2014 ONLY if a standard interview duration exists in the supplied context; otherwise empty string"
 },
 "purpose_of_the_interview": {
  "explanation": "string \u2014 a short organization-and-candidate-specific explanation of what the founder should accomplish",
  "evaluation_questions": [
   "string \u2014 4 to 6 questions the FOUNDER should be able to answer by the end (e.g. does the candidate demonstrate a genuine connection to this organization's mission; how could their specific background strengthen the board areas being recruited for; do they appear willing to contribute beyond attending meetings; what time and responsibility can they realistically take on; what needs clarification). Adapt to this specific person."
  ]
 },
 "candidate_snapshot": "string \u2014 1 to 3 concise paragraphs summarizing the candidate's most relevant VERIFIED background: current/previous professional work, expertise, leadership, nonprofit/board experience where known, relevant networks and their stated reason for applying. No generic praise. No selection recommendation.",
 "welcome_and_introductions": {
  "objective": "string",
  "talking_points": [
   "string \u2014 practical talking points"
  ],
  "suggested_opening": "string \u2014 short natural wording to welcome and thank the candidate and explain how the conversation will flow. Not a long speech."
 },
 "introduce_the_organization": {
  "talking_points": [
   "string \u2014 3 to 5 concise points from actual organization context: why it exists, mission, current stage, what the board is being built to accomplish"
  ],
  "transition": "string \u2014 a natural transition into candidate questions"
 },
 "learn_about_this_candidate": [
  {
   "question": "string \u2014 personalized question referencing ACTUAL candidate CV/application items",
   "why_this_question_matters": "string \u2014 one concise sentence",
   "listen_for": [
    "string \u2014 3 to 6 concise things"
   ],
   "optional_follow_up": "string \u2014 one follow-up question, or empty"
  }
 ],
 "mission_alignment": [
  {
   "question": "string \u2014 connects candidate experience + organization mission + actual needs",
   "why_this_question_matters": "string",
   "listen_for": [
    "string"
   ],
   "optional_follow_up": "string"
  }
 ],
 "contribution_to_the_board": [
  {
   "question": "string \u2014 explores how this candidate could contribute to the SPECIFIC board needs identified in Module 1 (what they could help lead, expertise, relationships they may open, the responsibility that interests them) \u2014 never assign a role automatically",
   "why_this_question_matters": "string",
   "listen_for": [
    "string"
   ],
   "optional_follow_up": "string"
  }
 ],
 "commitment_and_participation": [
  {
   "question": "string \u2014 realistic time availability, meeting participation, committee/leadership participation, follow-through, use of expertise/networks, fundraising participation only where applicable \u2014 never invent a required personal donation",
   "why_this_question_matters": "string",
   "listen_for": [
    "string"
   ],
   "optional_follow_up": "string"
  }
 ],
 "collaboration_and_accountability": [
  {
   "question": "string \u2014 1 to 2 questions about working with other board members and leadership: disagreement, accountability, collaborative decisions, feedback, follow-through. No psychological profiling.",
   "why_this_question_matters": "string",
   "listen_for": [
    "string"
   ],
   "optional_follow_up": "string"
  }
 ],
 "candidate_questions": "string \u2014 tell the founder to invite the candidate's questions and what to listen for (mission, board role, expectations, direction, contribution). NEVER say that asking about time commitment, meetings or logistics is a negative sign.",
 "closing": "string \u2014 natural closing language: thank the candidate, explain the organization is interviewing/reviewing candidates, make clear no final decision is being announced, explain the organization will follow up on next steps"
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_service.py run_interview_guide + workspace_routes.py
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `interview_invitation` — Interview Invitation
- **A. Generation type**: `interview_invitation`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Interview Invitation | Board Member Application \u2014 [actual organization name]",
 "body": "string \u2014 a finished email inviting THIS candidate to the interview stage. Start 'Dear [actual candidate first name],'. Thank them for applying; state clearly that after reviewing their application the organization would like to invite them to the interview stage; briefly explain the conversation will allow the organization to learn more about their experience, understand their interest in the mission, explore how their background could contribute, answer their questions and determine whether the opportunity is mutually aligned. If a real interview scheduling link is supplied in the context, include it naturally with a clear scheduling call to action; if none is supplied, state naturally that the organization will coordinate a convenient interview time with them directly \u2014 never mention that information is missing and NEVER output [Calendly Link], [Scheduling Link] or TBD. Never invent interview format, length or scheduling URL. Do not tell the candidate they have been selected for the board and do not overstate praise \u2014 never 'you are an excellent fit' unless the founder explicitly provided that judgment. Close warmly and sign with the actual founder/contact details. 150-250 words. Professional, warm, concise, respectful."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `interview_invitation_message` — Interview Invitation — Short Message
- **A. Generation type**: `interview_invitation_message`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "message": "string \u2014 a concise personalized direct-message invitation for LinkedIn, text message or another messaging channel: the candidate's name, the organization name, thanks for their interest, the invitation to interview and scheduling information where supplied. NO email subject line. A few sentences only."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `general_interview_invitation` — General Interview Invitation
- **A. Generation type**: `general_interview_invitation`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string",
 "body": "string \u2014 general invitation to a board introductory/interview conversation, with [APPLICANT NAME] and scheduling placeholders"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `general_interview_invitation_message` — Interview Invitation — Short Message
- **A. Generation type**: `general_interview_invitation_message`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "message": "string \u2014 a concise direct-message version of the interview invitation for LinkedIn, text message, Facebook Messenger or another messaging channel. Includes [APPLICANT NAME], the organization name, thanks for their interest, the invitation to interview and a scheduling placeholder. NO email subject line. Keep it short \u2014 a few sentences, not another email."
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `before_interview_rejection` — Before-Interview Rejection Email
- **A. Generation type**: `before_interview_rejection`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Thank You for Your Board Member Application",
 "body": "string \u2014 a finished email professionally closing the application for someone the FOUNDER decided not to invite to interview, while preserving the relationship and respecting the person's willingness to serve. Start 'Dear [actual first name],'. Thank them for their interest, the time invested in applying and their willingness to support the mission. State professionally that the organization has decided to move forward to the interview stage with a smaller group of candidates whose backgrounds most closely align with the board's current needs. Never present this as a judgment of the person's overall professional value. NEVER invent a rejection reason and never say 'you lack experience', 'you are not qualified', 'another candidate is better' or 'you are not a fit'. Do not promise to keep their information for future opportunities. Close respectfully and sign with the actual founder/contact information. 175-275 words. Professional, respectful, relationship-preserving, clear \u2014 no false hope, never cold or legalistic."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `general_rejection_email` — Application Rejection Email
- **A. Generation type**: `general_rejection_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string",
 "body": "string \u2014 respectful, concise email for an applicant the organization has decided not to invite to interview"
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `after_interview_thank_you` — After-Interview Thank-You Email
- **A. Generation type**: `after_interview_thank_you`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Thank You for Meeting With Us",
 "body": "string \u2014 a strictly DECISION-NEUTRAL email sent to a candidate who attended their board interview. Start 'Dear [actual first name],'. Thank them for taking time to meet with the organization about the board opportunity; briefly say the organization appreciated learning more about their professional experience, interest in the mission, perspective and potential contribution \u2014 without claiming any decision has been made. Tell them clearly that the organization is completing its interviews/review and will follow up regarding next steps once the process is complete. Close warmly and sign with the actual founder/contact information. 125-200 words. FORBIDDEN words/phrases: 'unfortunately', 'we have decided', 'we are moving forward with other candidates', 'congratulations', 'conditional appointment', 'welcome to the board'."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `after_interview_email` — After-Interview Email
- **A. Generation type**: `after_interview_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string",
 "body": "string \u2014 respectful email matching the chosen result"
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `after_interview_rejection` — After-Interview Rejection Email
- **A. Generation type**: `after_interview_rejection`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string",
 "body": "string \u2014 respectful, concise email for an applicant who was interviewed but will not move forward"
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

### CONTEXT CODE — reference_context + run_interview_guide (VERBATIM)
`/app/backend/workspace_service.py` lines 192-254:
```python
async def reference_context(db, gen_key: str) -> str:
    from ai_service import GENERATION_TYPES
    module = GENERATION_TYPES.get(gen_key, {}).get("module", 0)
    docs = await db.reference_materials.find(
        {"approved": True, "$or": [{"module": {"$in": [0, module]}}, {"resource_types": gen_key}]},
        {"_id": 0, "title": 1, "content_text": 1, "resource_types": 1, "module": 1},
    ).to_list(6)
    if not docs:
        return ""
    docs.sort(key=lambda d: 0 if gen_key in (d.get("resource_types") or []) else (1 if d.get("module") == module else 2))
    remaining = REFERENCE_BUDGET
    parts = []
    for d in docs[:2]:
        if remaining <= 0:
            break
        excerpt = slice_reference(d["content_text"], module, gen_key, budget=remaining)
        if excerpt:
            parts.append(f"REFERENCE EXAMPLE — {d['title']}:\n{excerpt}")
            remaining -= len(excerpt)
    if not parts:
        return ""
    return REFERENCE_RULES + "\n\n" + "\n\n".join(parts)


async def get_current_material(db, user_id: str, generation_type: str, application_id: str = ""):
    query = {"user_id": user_id, "type": generation_type, "application_id": application_id or ""}
    material = await db.generated_materials.find_one(query, {"_id": 0})
    if not material:
        return None
    current = next((v for v in material["versions"] if v["version"] == material["current_version"]), None)
    return {"material": material, "current": current}


async def save_generation(db, user_id: str, generation_type: str, structured: dict, context_summary: str, application_id: str = "") -> dict:
    meta = GENERATION_TYPES[generation_type]
    display = structured_to_display(generation_type, structured)
    query = {"user_id": user_id, "type": generation_type, "application_id": application_id or ""}
    existing = await db.generated_materials.find_one(query, {"_id": 0})
    ts = now_iso()
    version_number = (max((v["version"] for v in existing["versions"]), default=0) + 1) if existing else 1
    version = {"version": version_number, "structured": structured, "display_text": display,
               "source": "generated", "input_context_summary": context_summary[:2000], "created_at": ts}
    if existing:
        await db.generated_materials.update_one(query, {"$push": {"versions": version}, "$set": {"current_version": version_number, "updated_at": ts, "status": "Generated"}})
    else:
        await db.generated_materials.insert_one({
            "material_id": new_id(), "user_id": user_id, "type": generation_type,
            "application_id": application_id or "", "module": meta["module"], "title": meta["title"],
            "versions": [version], "current_version": 1, "status": "Generated",
            "created_at": ts, "updated_at": ts,
        })
    return await db.generated_materials.find_one(query, {"_id": 0})


def application_context_text(application: dict, include_cv: bool = True) -> str:
    answers = application.get("answers", {})
    snapshot = application.get("profile_snapshot", {})
    parts = ["APPLICANT APPLICATION:\n" + json.dumps({**snapshot, **answers}, indent=1, default=str)]
    if include_cv and application.get("cv_text"):
        parts.append("APPLICANT CV (extracted text):\n" + application["cv_text"][:15000])
    return "\n\n".join(parts)


```

## PART 8 — STAGE 5: REFERENCES & BACKGROUND CHECKS

#### `candidate_referee_request` — Candidate Referee Request Email
- **A. Generation type**: `candidate_referee_request`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Next Step: Your References | [actual organization name]",
 "body": "string \u2014 a finished email to THIS board member candidate asking them to provide their referee/reference information as the next step in the board appointment process. Start 'Dear [actual candidate first name],'. Thank them for their continued interest, explain the organization completes professional references for every incoming board member as part of its appointment process, and ask them to provide two professional references (name, role/organization, relationship to them, email and phone). If a secure Reference Information Form URL is supplied in the context, ask them to submit their references through that exact link on its own line; if no link is supplied, ask them to reply to this email with the details. Never invent a link. Close warmly and sign with the actual founder/contact details. 130-220 words."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reference_request_email` — Reference Check Email
- **A. Generation type**: `reference_request_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Reference Request | [actual candidate full name] \u2014 [actual organization name]",
 "body": "string \u2014 a finished, professional email the founder sends to a REFEREE requesting a reference for this specific board candidate. Open with a respectful greeting to the referee (use '[Referee Name]' only if no referee name is supplied). Explain that [candidate name] is being considered for appointment to the organization's board, that the candidate named the referee as a professional reference, and that the organization would value their perspective as part of its board appointment process. Ask them to share their assessment of the candidate's professionalism, reliability, character and suitability for board service \u2014 either by replying to this email or through a short conversation at a convenient time. Never invent the referee's relationship to the candidate. Close warmly and sign with the actual founder/contact details. 130-220 words."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `referee_confirmation_email` — Referee Confirmation Email
- **A. Generation type**: `referee_confirmation_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Thank You for Providing a Reference | [actual organization name]",
 "body": "string \u2014 a short, warm email the founder sends to a REFEREE confirming the reference process: thank them for taking the time to provide a reference for [actual candidate name], confirm their reference has been received and will be considered as part of the organization's board appointment process, and note that their input is treated with discretion. Never reveal any appointment decision and never share what other referees said. Close respectfully and sign with the actual founder/contact details. 90-160 words."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reference_call_script` — Reference Call Guide
- **A. Generation type**: `reference_call_script`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "introduction": "string",
 "questions": [
  "string"
 ],
 "closing": "string"
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `reference_evaluation_form` — Reference Evaluation Form
- **A. Generation type**: `reference_evaluation_form`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "sections": [
  {
   "title": "string",
   "items": [
    "string"
   ]
  }
 ]
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `conditional_offer` — Conditional Board Appointment Email
- **A. Generation type**: `conditional_offer`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Congratulations! Your Conditional Appointment as [the organization's actual board terminology, e.g. Board Member / Founding Board Member]",
 "body": "string \u2014 a candidate-specific conditional appointment email that feels PERSONALLY WRITTEN. Start 'Dear [actual candidate first name],'. OPENING: congratulate them and state clearly that following the interview process the organization is pleased to offer them a Conditional Appointment to the Board. WHY WE WANT YOU TO MOVE FORWARD: 1-2 candidate-specific paragraphs connecting their ACTUAL verified experience to the organization's actual priorities and Module 1 board needs \u2014 never invent experience, never generic 'we were impressed with your experience'. CONDITIONS: explain the appointment remains conditional on outstanding final requirements \u2014 include ONLY the requirements the supplied status context shows are actually outstanding (e.g. Reference Check, Background Check); if reference checking is complete do not claim it is outstanding; if background checking is not required omit it; explain that once the applicable requirements are completed and the organization confirms appointment they move into formal board service. YOUR NEXT STEP \u2014 BOARD ONBOARDING: invite them to the onboarding session and explain appropriate purposes (meet fellow board members and leadership, understand mission/direction, board responsibilities, how the board operates, fundraising/partnership expectations where applicable, how their particular expertise can contribute, ask questions). ONBOARDING DETAILS: use only the actual supplied date, time, timezone, format, meeting link and location \u2014 omit anything not supplied, no placeholders. DOCUMENTS AND FORMS: present the actual supplied links, clearly distinguishing items to REVIEW (Board Member Manual, Organizational Overview) from items to COMPLETE/SIGN (Board Member Profile Form, Board Member Agreement, Confidentiality Agreement, Conflict of Interest Disclosure) and ask them to review and complete the applicable forms before onboarding. CLOSING: warm organization-specific closing reinforcing why the organization looks forward to working with them; sign with actual founder/contact details. Use the words 'conditional appointment'; NEVER 'confidential board position'. Never make false statements about legal requirements."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

## PART 9 — STAGE 6: ONBOARDING

#### `board_manual` — Board Member Manual
- **A. Generation type**: `board_manual`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit board-development consultant preparing the primary practical handbook that teaches a new board member how to serve effectively in THIS organization — never a generic internet article about nonprofit boards. Produce sections in this order, adapting to the actual board type and omitting unsupported detail: Welcome (what joining this board means); Our Mission and Direction; The Role of Our Board (if governing/working, distinguish board leadership/governance from day-to-day management; if advisory, do NOT assign governing/fiduciary authority); How We Work Together (actual/intended model: strategic planning, shared leadership, areas of ownership, committees, staff support, accountability — only where supported); Responsibilities of Every Board Member (actual expectations); Meetings and Participation (actual meeting information where known); Strategic Leadership; Fundraising and Resource Development (fundraising broadly: introductions, opening doors, donor meetings, corporate partnerships, sponsorship, stewardship, events, grants, expertise, ambassadorship; personal giving ONLY if actually expected — never imply every member must personally solicit money unless that is the organization's policy); Committees and Leadership Responsibilities (known structures only; if committees do not exist yet, explain participation conceptually without inventing names); Confidentiality (high-level, point to the separate agreement); Conflicts of Interest (high-level, point to the separate policy); Professional Conduct and Collaboration (respect, professionalism, constructive disagreement, mission-first decisions, accountability, communication); Accountability; What the Organization Commits to Its Board Members; Getting Started (practical initial actions); Closing (short welcome focused on shared leadership and mission). NEVER invent bylaws, quorum, voting rules, officer powers, statutory requirements, committee names, attendance percentages, donation minimums or term lengths. Roughly 6-12 polished pages depending on actual information.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "sections": [
  {
   "title": "string",
   "content": "string"
  }
 ]
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `organization_overview` — Organization Overview
- **A. Generation type**: `organization_overview`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit strategist preparing a professional ORGANIZATIONAL OVERVIEW for new members of a nonprofit board — not a marketing brochure and not a dump of intake answers. It should help a new board member understand what this organization is, why it exists, who it serves, what it does, how it approaches its mission, where it is today, where it is going and what role the board plays. Produce sections in this order, OMITTING any section whose information is genuinely unavailable (never write 'Information not provided' or 'Information to Add'): About [Organization Name] (coherent 2-4 paragraph introduction); Our Mission (actual mission); Our Vision (only if a verified vision is known); The Need We Exist to Address; Our Approach; Our Programs and Work (verified only); Who and Where We Serve (only where known); Our Values (ONLY if actual stored values exist); The Role of Our Board (adapted to the actual board type); Our Current Direction; Looking Ahead (verified priorities only); Contact Information (actual organization, website, founder/contact, email where available). NEVER invent programs, statistics, achievements, founding dates, partnerships, locations, legal/tax status, values, beneficiaries or expansion plans. Professional, substantial, clear — roughly 3-6 finished pages of content depending on available information; never pad to reach length.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "sections": [
  {
   "title": "string",
   "content": "string"
  }
 ]
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `board_member_agreement` — Board Member Agreement
- **A. Generation type**: `board_member_agreement`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
Prepare ONE clear professional organization-level master Board Member Agreement based on the organization's actual board expectations — a controlled organizational agreement, not unnecessary legal language. Sections in this order (omit genuinely unsupported ones): Purpose / Shared Commitment (defines shared expectations between the organization and Board Member); Mission and Organizational Commitment; Participation and Meetings; Strategic Leadership (where appropriate); Committee Participation (where applicable); Professional Expertise and Relationships; Accountability; Fundraising and Resource Development (only where actually applicable); Professional Conduct; Confidentiality Acknowledgement; Conflict of Interest Acknowledgement; Time Commitment (only from known context); Term of Service (ONLY if known); What the Organization Commits to the Board Member; Acknowledgement. NEVER invent fines, penalties, personal donation requirements, attendance percentages, removal procedures, governing law, legal remedies, term lengths or officer positions. The hosted signing system captures identity, signature, date and version — do not include printed signature blanks.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "title": "string",
 "sections": [
  {
   "title": "string",
   "content": "string"
  }
 ],
 "acknowledgement": "string"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `confidentiality_agreement` — Confidentiality Agreement
- **A. Generation type**: `confidentiality_agreement`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
Create a clear Board Member Confidentiality Agreement customized to the actual organization. Sections: Purpose; Confidential Information (appropriate examples such as financial information, donor information, sponsor information, personnel matters, strategic plans, board deliberations, legal matters, contracts, partnerships, proprietary materials, and other information expressly designated confidential); Board Member Responsibilities (keep confidential information secure; use it only to perform board responsibilities; do not disclose without authorization except where required by law; protect electronic and physical information; return/destroy information when appropriately requested); Continuing Confidentiality (obligations may continue after service); Acknowledgement. NEVER invent damages, statutory citations, penalties, criminal consequences or jurisdiction-specific remedies.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "title": "string",
 "sections": [
  {
   "title": "string",
   "content": "string"
  }
 ],
 "acknowledgement": "string"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `conflict_of_interest_agreement` — Conflict of Interest Agreement
- **A. Generation type**: `conflict_of_interest_agreement`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
Prepare a clear Conflict of Interest Policy and Disclosure Agreement for Board Members. Sections: Purpose; What Is a Conflict of Interest? (plain-language explanation with potential examples: financial interest, employment/consulting relationship, family relationship, vendor relationship, partnership relationship, related organization, personal benefit); Board Member Responsibility to Disclose; Managing a Conflict (reasonable general principles: disclose, do not improperly influence discussion, abstain where appropriate, follow organization/board procedure — never invent legal procedures); Duty to Act in the Organization's Interests; Ethical Conduct; Disclosure Statement (present the choice 'I currently have no actual, potential or perceived conflict to disclose.' OR 'I have the following actual, potential or perceived conflict to disclose:' with an explanation field); Acknowledgement. NEVER invent statutory citations or legal penalties.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "title": "string",
 "sections": [
  {
   "title": "string",
   "content": "string"
  }
 ],
 "acknowledgement": "string"
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `ninety_day_plan` — New Board Member 90-Day Plan
- **A. Generation type**: `ninety_day_plan`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "first_30_days": [
  "string \u2014 learn, attend, understand mission, complete onboarding"
 ],
 "days_31_60": [
  "string \u2014 begin assigned responsibilities and relationship building"
 ],
 "days_61_90": [
  "string \u2014 take ownership of agreed board/fundraising responsibilities"
 ],
 "notes": "string \u2014 customized to candidate strengths, assigned responsibility, organizational priorities and fundraising expectations"
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `onboarding_agenda` — Onboarding Agenda
- **A. Generation type**: `onboarding_agenda`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "items": [
  {
   "topic": "string \u2014 cover welcome; introductions; mission/program overview; organizational priorities; board role; governance expectations; fundraising expectations; committees/responsibilities; important policies; next 90 days; questions; next meeting/action",
   "details": "string"
  }
 ]
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `onboarding_script` — Board Member Onboarding Facilitator Guide
- **A. Generation type**: `onboarding_script`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit board-development consultant preparing a founder to PERSONALLY onboard newly recruited board members. This is a practical FACILITATOR GUIDE the founder follows during the meeting — NOT another Board Member Manual and NOT a generic article. Section 1: suggested time 10-15 minutes where appropriate, and if multiple members attend, invite each to briefly share their background, what interested them in the mission and what they hope to contribute. Section 4: adapt to the ACTUAL board type — never describe an Advisory Board as having governing authority, and never imply board members run day-to-day staff operations unless the working-board structure requires it. Section 6: use actual new-member expertise where supplied; suggest discussion questions, never make final role assignments. Section 7: fundraising can include introductions, opening doors, donor conversations, corporate partnerships, sponsorship, stewardship, events, grant relationships, sharing the mission, professional expertise, personal giving only where applicable — never tell every member they must personally ask for money unless that is actual policy. Section 8: explain what each supplied document is for and what remains outstanding — do not restate the documents. NEVER invent bylaws, committees, officer roles, voting rules, legal obligations, meeting schedules, donation requirements, strategic priorities, programs or statistics; omit or generalize what is unknown.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "session_purpose": "string \u2014 1-2 short paragraphs explaining what the founder should accomplish during the onboarding session",
 "before_you_begin": [
  "string \u2014 short checklist of items that already exist and should be available (e.g. Board Member Manual, Organizational Overview, signed agreements, Board Member Profile status, meeting information) \u2014 do not create new resources"
 ],
 "sections": [
  {
   "title": "string \u2014 use these exact section titles in order: 1. Welcome and Introductions; 2. Why This Organization Exists; 3. Where We Are Going; 4. The Role of the Board; 5. How We Will Work Together; 6. How Each Board Member Can Contribute; 7. Fundraising, Relationships and Ambassadorship; 8. Review the Board Documents; 9. Immediate Next Steps; 10. Questions and Discussion; 11. Closing",
   "objective": "string \u2014 what this section accomplishes",
   "talking_points": [
    "string \u2014 practical founder-facing talking points grounded in the actual organization/board context"
   ],
   "suggested_language": "string \u2014 short natural wording the founder can use (never a long speech); empty string where not useful",
   "discussion_questions": [
    "string \u2014 questions to invite member input where appropriate (e.g. 'Based on what you know so far, where do you believe your experience could make the greatest contribution?'); empty list where not applicable"
   ]
  }
 ]
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `first_board_meeting_invitation` — First Board Meeting Invitation Email
- **A. Generation type**: `first_board_meeting_invitation`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 'First Board Meeting | [actual organization name]' (a natural organization-specific alternative is acceptable \u2014 produce ONE subject only)",
 "body": "string \u2014 one finished email to the new Board Members ('Dear Board Members,') inviting them to their first Board Meeting and making clear this meeting is the transition from recruitment/onboarding into ACTIVE board participation \u2014 not a generic calendar reminder. OPENING: welcome them and explain why the meeting matters: the Board's first opportunity to come together after recruitment/onboarding, better understand the experience represented around the table, and begin deciding how the Board will work together to move the organization forward. Then a section headed 'DURING THE MEETING, WE WILL:' with a concise organization-specific agenda drawn only from supported items (introductions and professional strengths, current stage and priorities, Board-leadership relationship, individual contribution areas, upcoming strategic planning, committees/leadership portfolios where applicable, fundraising and partnerships, shared responsibilities, immediate next steps). If the supplied context says one or more recipients have NOT completed their Board Member Profile, include a section 'Please Complete Your Board Member Profile' briefly explaining why it matters (expertise, leadership interests, networks, fundraising comfort, availability, where they most want to contribute) with the ACTUAL profile URL supplied; if everyone has completed it, OMIT that section entirely. Then 'Board Meeting Details' listing ONLY the actually supplied details (date, time, timezone, format/location, meeting link, meeting ID, passcode, meeting chat, additional instructions) \u2014 omit missing items completely, never output placeholders like [Zoom Link] or [To be confirmed]. CLOSING: meaningful \u2014 where consistent with the board type, communicate that the goal is not simply names around a table but members who contribute expertise, ideas, relationships, leadership, fundraising support, partnerships and shared responsibility so the mission does not rest on the founder alone; ask them to confirm attendance where appropriate; sign with actual founder/contact information."
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `board_member_engagement_guide` — Board Member Engagement Guide
- **A. Generation type**: `board_member_engagement_guide`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit board-development consultant advising a founder on how to meaningfully engage ONE specific board member. Create a concise ONE-PAGE INTERNAL guide from verified information only: their application, CV, professional background, board experience, Board Member Profile (expertise, committee/leadership interests, fundraising participation, networks, availability, reason for joining, additional skills), plus organization priorities and Module 1 board needs. NEVER use referee responses, confidential reference data, background-check data, private interview scoring, or protected characteristics (age, race, sex, disability, religion, political belief). No psychological profiling. This guide is internal — never addressed to the member.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "member": "string \u2014 actual member name",
 "professional_role": "string \u2014 actual role/employer where known",
 "primary_expertise": "string \u2014 comma-separated actual expertise areas",
 "where_they_create_most_value": [
  "string \u2014 3 to 5 SPECIFIC ways their actual expertise can support current organizational priorities. Be concrete: instead of 'Use their finance skills' write 'Invite them to help strengthen Board financial oversight, review budgeting assumptions and establish a clearer financial reporting rhythm.' Only where supported."
 ],
 "how_to_engage_them": [
  "string \u2014 practical founder actions grounded in what the member actually said about interests, availability, leadership, networks and fundraising comfort (involve them early in relevant planning; give them ownership of a defined outcome; invite them to open specific relationship types; pair them with the appropriate area; keep responsibilities within their stated available time)"
 ],
 "strong_early_responsibilities": [
  "string \u2014 2 to 4 concrete responsibilities/projects the founder could DISCUSS with them (suggestions, never automatic assignments)"
 ],
 "relationships_partnerships_fundraising": "string \u2014 based on their stated networks and fundraising comfort, useful ways they may contribute (donor/corporate/foundation/community/government introductions, professional associations, speaking, strategy, stewardship \u2014 only where supported; never force fundraising activities they said they are uncomfortable with)",
 "leadership_committee_alignment": "string \u2014 appropriate areas of board leadership based on expertise and stated interests; never invent an officer title",
 "first_90_days": [
  "string \u2014 3 to 5 practical actions to engage this person early"
 ],
 "keep_in_mind": [
  "string \u2014 ONLY evidence-based operational considerations (e.g. 'Indicated approximately 2-4 hours of monthly availability, so responsibilities should remain focused and clearly defined.'). NEVER personality judgments such as 'they may be difficult', 'they seem introverted', 'they need praise'."
 ]
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `board_member_portfolio` — Board Member Portfolio
- **A. Generation type**: `board_member_portfolio`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit Board-development consultant creating a finished, person-specific responsibility Portfolio for ONE Board Member. It helps them understand where they fit, why their contribution matters, what they will help accomplish, what responsibilities they carry, how their skills and relationships help, and their immediate priorities. This is NOT a generic job description, legal contract, Board manual, governance policy, performance evaluation, AI analysis or personality assessment. ORDER OF AUTHORITY when determining responsibilities: 1) the founder's Conversation Conclusion (what was ACTUALLY agreed), 2) the founder-selected Outcome, 3) the member's own Recommitment/Profile answers, 4) the organization's verified needs and direction, 5) your reasoning about the strongest alignment among those facts. NEVER contradict an actual agreement. NEVER fabricate responsibilities, assign anything explicitly rejected, exceed stated capacity, or invent expertise, programs, revenue, statistics, donors, corporate relationships, titles, committees, officer positions, fundraising targets, hours, deadlines, legal obligations or governance authority. NEVER expose private founder notes, internal concerns, harsh commentary or the phrase 'dead weight' — the Portfolio reflects what was AGREED. Never mention AI, algorithms or generation. Write in the organization's voice so the member feels: 'This clearly explains where I fit and what I am expected to help carry.'
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "member": "string \u2014 actual Board Member full name",
 "portfolio_type": "string \u2014 copy the PORTFOLIO TYPE supplied in context verbatim (e.g. 'Board Member Portfolio' or 'Advisory Board Member Portfolio')",
 "your_role_on_the_board": "string \u2014 clear explanation of this person's primary role/focus, connecting what was agreed, their expertise and the organization's needs. NEVER invent formal officer titles.",
 "why_your_role_matters": "string \u2014 how this person's particular contribution helps move THIS organization's mission forward. Specific to the organization, never generic.",
 "what_you_will_help_us_accomplish": [
  "string \u2014 3 to 5 concise areas where this member will contribute, translated from the organization's verified direction and what was actually discussed/agreed. NO invented quantitative targets."
 ],
 "your_areas_of_responsibility": [
  "string \u2014 3 to 7 meaningful, specific, actionable responsibilities grounded ONLY in supplied information. Avoid vague items like 'Support the mission' or 'Attend meetings' unless context genuinely requires them."
 ],
 "how_your_experience_can_help": "string \u2014 connect their actual professional experience, expertise, knowledge, networks and interests to their agreed responsibilities. Never exaggerate their background.",
 "relationships_and_resources": "string \u2014 ONLY where supported: the types of relationships the person indicated they may be comfortable helping the organization access. NEVER name specific people/companies unless supplied. NEVER assume introductions merely because they have a network. Empty string when unsupported.",
 "your_role_in_fundraising": "string \u2014 ONLY where relevant. Use their exact stated fundraising comfort. If they requested training, state that support/training will be provided before expecting that activity. If they said they are not comfortable participating in fundraising, do NOT assign solicitations. Empty string when not relevant.",
 "how_we_will_work_together": "string \u2014 the working relationship between this member, the founder/Executive Director and where appropriate the wider Board. Use actual expectations where known; never invent meeting schedules or reporting requirements.",
 "your_immediate_priorities": [
  "string \u2014 2 to 4 concise immediate priorities based on what was agreed. NO fabricated dates or unsupported obligations."
 ],
 "your_first_90_days": [
  "string \u2014 3 to 5 practical 90-day directions (getting oriented to agreed responsibility, understanding priorities, taking ownership of agreed work, beginning appropriate introductions, participating in relevant planning, establishing communication with the founder). ONLY actions supported by context. No invented deadlines, amounts, committees or weekly requirements."
 ],
 "moving_forward_together": "string \u2014 short closing statement reinforcing the importance of their contribution, the clarity of responsibility and shared movement toward the mission. No hype."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `portfolio_email` — Board Member Portfolio Email
- **A. Generation type**: `portfolio_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string",
 "body": "string \u2014 a short professional email to the board member sharing their completed Board Member Portfolio"
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `formal_appointment_email` — Final Board Appointment Email
- **A. Generation type**: `formal_appointment_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt**: NO RESOURCE-SPECIFIC DEVELOPER PROMPT (only the schema field descriptions below)
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 exactly: Congratulations! Your Appointment to the Board \u2014 [actual organization name]",
 "body": "string \u2014 the FINAL board appointment email for a candidate who has completed the reference and background-check stage. Start 'Dear [actual candidate first name],'. OPENING: congratulate them warmly and state clearly that, with the reference and applicable background-check process now complete, the organization is pleased to formally confirm their appointment to the Board. WHY THEY MATTER: 1-2 candidate-specific sentences connecting their ACTUAL verified experience to the organization's actual mission and board priorities \u2014 never invent experience. WHAT HAPPENS NEXT: welcome them into board service using the organization's actual board terminology; if onboarding session details are supplied use those exact details, otherwise say the organization will confirm onboarding details with them directly. ONBOARDING MATERIALS: present the actual supplied links, clearly distinguishing items to REVIEW (Board Member Manual, Organization Overview) from items to COMPLETE/SIGN (Board Member Profile Form and any agreements still awaiting signature) \u2014 omit already-signed agreements and never invent links. CLOSING: a warm, organization-specific welcome to the board; sign with actual founder/contact details. Never call this appointment conditional \u2014 the conditions are complete."
}
```
- **E. Dynamic context**: per-candidate workspace context (org context + FOUNDER CONTACT + candidate snapshot/application/CV + type-specific links)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

### 41. Formal Board Appointment Letter
**DOES NOT CURRENTLY EXIST.** Only `conditional_offer` (email) and `formal_appointment_email` (email) exist. No formal letter generator was found anywhere in the codebase. Not created (per instruction).

## PART 10 — STAGE 7: FUNDRAISING ACTIVATION

#### `activation_planning_form` — Board Fundraising Planning Form
- **A. Generation type**: `activation_planning_form`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit fundraising strategist facilitating a Board-led fundraising planning process. You are writing the organization-specific introduction and goal context for a finished Board Fundraising Planning Form that helps Board Members contribute useful ideas to the organization's fundraising strategy — who the organization should build relationships with, which fundraising opportunities should be prioritized, what relationships and networks already exist around the Board, how the organization should attract and engage funders, how Board Members are willing to participate, what each may be willing to own, what support they need, and what should happen over the next 90 days. Use the real organization name and reflect the real mission and known fundraising goal. NEVER invent donors, businesses, foundations, programs, impact statistics or Board Member relationships. NEVER mention AI. NEVER make legal or governance claims. NEVER leave organization facts as unresolved placeholders like [ORGANIZATION].
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "introduction": "string \u2014 2 to 4 short paragraphs written to this organization's Board Members introducing the Board Fundraising Planning Form. Must explain, using ONLY supplied facts: the organization (real name) is developing its fundraising plan; the Board is being involved in shaping that plan rather than receiving a finished plan; their ideas, experience, relationships and perspective matter; their responses will be considered alongside the responses of other Board Members and organizational priorities. Warm, plain nonprofit language. NEVER mention AI, software, analysis, algorithms or generation. NEVER pressure Board Members into giving money or asking for donations.",
 "goal_context": "string \u2014 1 short paragraph factually stating the organization's fundraising goal, the amount needed where supplied, and what the funding will help accomplish, using ONLY the supplied facts in the founder's own substance. If the goal or amount is unknown or the founder said Not Sure, simply omit that detail rather than inventing it. Empty string if nothing is known."
}
```
- **E. Dynamic context**: activation context (activation intake + planning responses/reviews/strategy as shown in Part 10 code)
- **F. Calling file/route**: activation_planning_routes.py:~562 — POST /api/activation/planning-form/generate
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `activation_fundraising_strategy` — Fundraising Strategy Plan
- **A. Generation type**: `activation_fundraising_strategy`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit fundraising strategist. Build ONE coherent, organization-specific FUNDRAISING STRATEGY PLAN from: verified organization context, the founder's Activation intake, and EVERY completed Board Member planning response (each labeled with the member's real name and role). Use everybody's relevant ideas and preserve WHO SAID WHAT — never attribute one member's relationship, willingness, network, idea or support need to another member. Answer Rooney's framework: what we are raising money for; how much where known; what funding accomplishes; who should care; priority audiences; where they can be reached; what they should understand; how relationships will be created (KNOW/LIKE/TRUST/ASK/FOLLOW UP/STEWARD); priority opportunities; what already exists around the Board; who can help carry the work; needed materials; the next 90 days and 12 months. NEVER invent named donors, businesses, foundations, relationships, Board commitments, programs, impact statistics, fundraising results, budgets or deadlines. NEVER force Board Members to give money or ask for donations. NEVER make legal/governance claims. NEVER assign final individual fundraising responsibilities. NEVER mention AI. NO unresolved placeholders. Where the founder's intake states when the money is needed, set the execution timeline to 60, 90 or 120 days accordingly (soonest need = 60 days) and reflect that timeline in the plan's timeline sections, including a realistic estimate of what executing the plan will cost where the context supports one.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "executive_summary": "string \u2014 concise executive summary of this organization's fundraising strategy: what is being funded, the direction, how the Board participated in shaping the plan, and what happens next. Only supplied facts.",
 "fundraising_goal": "string \u2014 Section 1: the organization's actual fundraising goal and the amount needed where supplied. If the amount is unknown or 'Not Sure', describe the goal without inventing a number.",
 "what_we_are_raising_money_for": "string \u2014 Section 2: what the funding will help accomplish, using the founder's actual answers.",
 "who_we_should_build_relationships_with": "string \u2014 Section 3: the priority audiences drawn from the founder's intake and the Board's actual planning responses. Where a specific audience idea came from a Board Member, keep the attribution accurate (e.g. 'Several Board Members pointed to local businesses'). Never assign one member's idea to another.",
 "priority_fundraising_opportunities": "string \u2014 Section 4: which fundraising opportunities should be prioritized and why, grounded in what the Board actually selected and the organization's current methods and capacity.",
 "what_people_should_understand": "string \u2014 Section 5: what potential funders need to understand about the mission, drawn from the Board's actual messaging ideas and the organization's real work. NO invented impact statistics.",
 "how_we_will_build_relationships": "string \u2014 Section 6: how fundraising relationships will be created, using the KNOW, LIKE, TRUST, ASK, FOLLOW UP, STEWARD relationship-building journey where appropriate and the outreach methods the Board actually suggested.",
 "relationships_around_the_board": "string \u2014 Section 7: the types of relationships, networks and experience that actually exist around the Board based on their own responses. Attribute accurately (name the member ONLY as the source of what THEY said). Selecting a network type is NOT a commitment to make introductions \u2014 say so where relevant. NEVER invent named contacts.",
 "how_the_board_can_participate": "string \u2014 Section 8: how Board Members can participate based on what members actually said they are comfortable helping with. Do NOT assign final individual responsibilities \u2014 that happens during plan adoption. Do NOT pressure personal giving or asking where a member did not offer it.",
 "founder_staff_responsibilities": "string \u2014 Section 9: what the founder/staff will realistically carry, grounded in who currently carries fundraising.",
 "what_we_need_to_execute": "string \u2014 Section 10: materials, tools, training and support needed, drawn from what Board Members actually said would help them and the intake.",
 "next_90_days": [
  "string \u2014 Section 11: 4 to 7 practical 90-day actions grounded in the Board's actual 90-day priorities and the strategy. No invented dates, amounts or commitments."
 ],
 "twelve_month_direction": "string \u2014 Section 12: the 12-month fundraising direction connecting the goal, priority opportunities and relationship building.",
 "how_we_know_plan_is_moving": [
  "string \u2014 Section 13: 3 to 5 practical, observable signs the plan is moving. No fabricated metrics or revenue projections."
 ],
 "items_for_board_review": [
  "string \u2014 Section 14: 3 to 6 specific items the Board should discuss or confirm during review, including any open questions surfaced by the actual responses."
 ],
 "next_step_review_and_adopt": "string \u2014 Section 15: short closing explaining the Board will now review this plan, share suggestions or concerns, and work through adoption together. People who plan together execute together."
}
```
- **E. Dynamic context**: activation context (activation intake + planning responses/reviews/strategy as shown in Part 10 code)
- **F. Calling file/route**: activation_planning_routes.py:~877 — POST /api/activation/strategy/generate
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `activation_revised_strategy` — Revised Fundraising Strategy Plan (Ready for Adoption)
- **A. Generation type**: `activation_revised_strategy`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit fundraising strategist SYNCHRONIZING a Board's review into the Fundraising Strategy Plan. Inputs: the strategy plan the Board reviewed, EVERY Board Member review (overall position, suggestions, and idea-by-idea approvals and disapprovals with the member's reasons), the original Board planning responses, and the founder's intake. Where the Board approved an idea, preserve it faithfully. Where members disapproved an idea or raised concerns, revise that part faithfully using their actual reasons — or, where the Board must still decide, keep the item and note the open question rather than resolving it yourself. This is NOT a regeneration of the original plan — it is a synthesis of the original ideas with the Board's actual review, ready for adoption. Preserve WHO SAID WHAT with accurate attribution. NEVER invent named donors, businesses, foundations, relationships, Board commitments, programs, impact statistics, fundraising results, budgets or deadlines. NEVER assign final individual fundraising responsibilities. NEVER mention AI. NO unresolved placeholders.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "executive_summary": "string \u2014 concise executive summary of this organization's fundraising strategy: what is being funded, the direction, how the Board participated in shaping the plan, and what happens next. Only supplied facts.",
 "fundraising_goal": "string \u2014 Section 1: the organization's actual fundraising goal and the amount needed where supplied. If the amount is unknown or 'Not Sure', describe the goal without inventing a number.",
 "what_we_are_raising_money_for": "string \u2014 Section 2: what the funding will help accomplish, using the founder's actual answers.",
 "who_we_should_build_relationships_with": "string \u2014 Section 3: the priority audiences drawn from the founder's intake and the Board's actual planning responses. Where a specific audience idea came from a Board Member, keep the attribution accurate (e.g. 'Several Board Members pointed to local businesses'). Never assign one member's idea to another.",
 "priority_fundraising_opportunities": "string \u2014 Section 4: which fundraising opportunities should be prioritized and why, grounded in what the Board actually selected and the organization's current methods and capacity.",
 "what_people_should_understand": "string \u2014 Section 5: what potential funders need to understand about the mission, drawn from the Board's actual messaging ideas and the organization's real work. NO invented impact statistics.",
 "how_we_will_build_relationships": "string \u2014 Section 6: how fundraising relationships will be created, using the KNOW, LIKE, TRUST, ASK, FOLLOW UP, STEWARD relationship-building journey where appropriate and the outreach methods the Board actually suggested.",
 "relationships_around_the_board": "string \u2014 Section 7: the types of relationships, networks and experience that actually exist around the Board based on their own responses. Attribute accurately (name the member ONLY as the source of what THEY said). Selecting a network type is NOT a commitment to make introductions \u2014 say so where relevant. NEVER invent named contacts.",
 "how_the_board_can_participate": "string \u2014 Section 8: how Board Members can participate based on what members actually said they are comfortable helping with. Do NOT assign final individual responsibilities \u2014 that happens during plan adoption. Do NOT pressure personal giving or asking where a member did not offer it.",
 "founder_staff_responsibilities": "string \u2014 Section 9: what the founder/staff will realistically carry, grounded in who currently carries fundraising.",
 "what_we_need_to_execute": "string \u2014 Section 10: materials, tools, training and support needed, drawn from what Board Members actually said would help them and the intake.",
 "next_90_days": [
  "string \u2014 Section 11: 4 to 7 practical 90-day actions grounded in the Board's actual 90-day priorities and the strategy. No invented dates, amounts or commitments."
 ],
 "twelve_month_direction": "string \u2014 Section 12: the 12-month fundraising direction connecting the goal, priority opportunities and relationship building.",
 "how_we_know_plan_is_moving": [
  "string \u2014 Section 13: 3 to 5 practical, observable signs the plan is moving. No fabricated metrics or revenue projections."
 ],
 "items_for_board_review": [
  "string \u2014 Section 14: 3 to 6 specific items the Board should discuss or confirm during review, including any open questions surfaced by the actual responses."
 ],
 "next_step_review_and_adopt": "string \u2014 Section 15: short closing explaining the Board will now review this plan, share suggestions or concerns, and work through adoption together. People who plan together execute together."
}
```
- **E. Dynamic context**: activation context (activation intake + planning responses/reviews/strategy as shown in Part 10 code)
- **F. Calling file/route**: activation_planning_routes.py:~1216 — adoption-stage synthesis
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `activation_facilitation_guide` — Plan Adoption Facilitation Guide
- **A. Generation type**: `activation_facilitation_guide`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit Board facilitator and fundraising strategist. Create an organization-specific PLAN ADOPTION FACILITATION GUIDE that helps the founder facilitate a real Board discussion around the strategy, the Board's actual feedback, priorities, participation, responsibility, support and immediate action. Use ONLY the supplied strategy, actual Board reviews, actual planning responses, intake and organization facts. NEVER invent bylaws, quorum requirements, voting requirements, parliamentary procedure or legal requirements. NEVER claim the Board formally adopted anything. NEVER make governance decisions — the founder remains the decision-maker and recorder of the outcome. NEVER assign final individual responsibilities. NEVER mention AI. NO unresolved placeholders.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "objective": "string \u2014 Section 1: the objective for this organization's plan-adoption discussion.",
 "before_discussion": "string \u2014 Section 2: practical preparation before the discussion, grounded in the actual reviews received.",
 "open_discussion": "string \u2014 Section 3: how to open the discussion, honoring that the Board helped build the plan.",
 "reconnect": "string \u2014 Section 4: reconnect everyone to what the organization is actually trying to accomplish and fund.",
 "review_strategy": "string \u2014 Section 5: how to walk the Board through the actual strategy's key elements.",
 "work_through_feedback": "string \u2014 Section 6: for each MEANINGFUL actual issue raised in the real Board reviews: what the issue is, what the Board Member(s) actually said (accurate attribution), a useful question to ask, and what clarity or decision is needed. Do NOT manufacture conflict \u2014 if reviews were supportive, say so and focus on the actual suggestions.",
 "confirm_priorities": "string \u2014 Section 7: confirming which fundraising priorities the Board is agreeing to pursue.",
 "confirm_board_carry": "string \u2014 Section 8: confirming what the Board as a whole will help carry.",
 "establish_individual_ownership": "string \u2014 Section 9: PERSON-SPECIFIC discussion prompts built from what each member actually said they are willing to help with or own (e.g. 'Alice indicated interest in corporate relationships. Ask what part of that work she would realistically be comfortable taking responsibility for.'). NEVER assign the responsibility \u2014 only prompt the conversation. Only reference members and interests that actually appear in the supplied responses/reviews.",
 "identify_needs": "string \u2014 Section 10: identifying what Board Members actually said they need to execute (training, materials, someone to attend meetings, etc.).",
 "agree_first_90": "string \u2014 Section 11: agreeing what happens first, focused especially on the first 90 days of the strategy.",
 "confirm_way_forward": "string \u2014 Section 12: confirming the way forward and how the outcome will be recorded by the founder.",
 "close_with_ownership": "string \u2014 Section 13: closing the discussion with ownership so the founder leaves knowing what direction was accepted, what changed, what remains unresolved, who agreed to what, and what happens next."
}
```
- **E. Dynamic context**: activation context (activation intake + planning responses/reviews/strategy as shown in Part 10 code)
- **F. Calling file/route**: activation_planning_routes.py:1308
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `activation_execution_toolkit` — Board Fundraising Execution Toolkit
- **A. Generation type**: `activation_execution_toolkit`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit fundraising strategist equipping a real volunteer Board. Generate ONLY tools relevant to the ADOPTED strategy and agreed responsibilities supplied — if grants are not part of the strategy do NOT manufacture grant tools; if corporate relationships, individual donors, events or stewardship are the focus, build useful tools for those. Tools must sound like a real Board Member — natural language, not professional fundraisers, staff, grant writers or marketers. Reflect KNOW/LIKE/TRUST/ASK/FOLLOW UP/STEWARD where appropriate. NEVER invent funders, donor names, business relationships, sponsorship amounts, grant opportunities, Board Member relationships, commitments, statistics, impact results, programs or meeting dates. NEVER mention AI. Resolve all known organization facts — no unresolved placeholders except limited recipient placeholders like [First Name].
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "overview": "string \u2014 short overview connecting the toolkit to the organization's adopted fundraising strategy and the responsibilities the Board actually agreed to carry.",
 "email_tools": [
  {
   "title": "string \u2014 e.g. 'Warm Introduction Email'",
   "when_to_use": "string",
   "content": "string \u2014 the full natural email a real Board Member could send. Limited recipient placeholders like [First Name] or [Company Name] are acceptable; known organization facts must be resolved."
  }
 ],
 "text_tools": [
  {
   "title": "string",
   "when_to_use": "string",
   "content": "string \u2014 a concise natural text message."
  }
 ],
 "call_scripts": [
  {
   "title": "string",
   "when_to_use": "string",
   "content": "string \u2014 practical structure with these labeled parts: When to Use This / Opening / Why I'm Calling / Brief Mission Connection / What I'm Asking Today / If They Are Interested / If They Are Not Ready / Close. Short and natural \u2014 no long speeches."
  }
 ],
 "stewardship_tools": [
  {
   "title": "string \u2014 follow-up / thank-you / stewardship touchpoints",
   "when_to_use": "string",
   "content": "string"
  }
 ]
}
```
- **E. Dynamic context**: activation context (activation intake + planning responses/reviews/strategy as shown in Part 10 code)
- **F. Calling file/route**: activation_planning_routes.py:~1470 — POST /api/activation/toolkit/generate
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `activation_fundraising_portfolio` — Fundraising Portfolio
- **A. Generation type**: `activation_fundraising_portfolio`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit fundraising strategist writing an individual FUNDRAISING PORTFOLIO for one Board Member. Authority order: 1) the EXACT agreed fundraising responsibility recorded by the founder, 2) the final adopted Fundraising Strategy Plan, 3) the Plan Adoption Conclusion, 4) this member's OWN planning response and strategy review, 5) their verified skills/experience/networks, 6) organize within those verified facts only. NEVER contradict or exceed what was actually agreed. NEVER invent a responsibility, donor ask, personal giving commitment, introduction commitment, corporate contact, meeting, fundraising target, deadline, relationship, event or grant activity. NEVER use another member's private answers. Warm, professional, second person ('you'). NEVER mention AI. NO unresolved placeholders.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "your_role": "string \u2014 Your Role in Our Fundraising Plan: this member's individual place inside the adopted fundraising strategy, anchored on their EXACT agreed fundraising responsibility.",
 "why_role_matters": "string \u2014 Why Your Role Matters: connect their agreed responsibility to the adopted strategy and mission.",
 "what_you_accomplish": "string \u2014 What You Will Help Us Accomplish: grounded in the adopted strategy's actual goal and priorities.",
 "your_responsibilities": "string \u2014 Your Fundraising Responsibilities: restate and organize the EXACT agreed responsibility. NEVER add responsibilities beyond what was agreed.",
 "who_you_reach": "string \u2014 Who You Will Help Us Reach: ONLY where supported by their agreed responsibility and own responses; empty string when not supported.",
 "build_relationships": "string \u2014 How You Will Help Build Relationships: use only relevant stages of KNOW, LIKE, TRUST, ASK, FOLLOW UP, STEWARD \u2014 do not force every stage.",
 "tools_you_can_use": "string \u2014 Tools You Can Use: reference the appropriate tools already in the approved Board Fundraising Execution Toolkit by name. Do NOT regenerate the toolkit content.",
 "immediate_priorities": "string \u2014 Your Immediate Priorities: 2-4 realistic first actions inside their agreed responsibility.",
 "first_90_days": "string \u2014 Your First 90 Days: practical focus aligned with the strategy's 90-day actions relevant to their responsibility.",
 "support_resources": "string \u2014 Support and Resources: what support they asked for and what is available. Only what was actually said or exists.",
 "work_together": "string \u2014 How We Will Work Together: how the founder and this member will stay connected on the work.",
 "moving_mission": "string \u2014 Moving the Mission Forward: brief closing tying their contribution to the mission."
}
```
- **E. Dynamic context**: activation context (activation intake + planning responses/reviews/strategy as shown in Part 10 code)
- **F. Calling file/route**: activation_planning_routes.py:~1640 — POST /api/activation/portfolio/{participant_id}/generate
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `activation_followup_email` — Board Member Follow-Up Email
- **A. Generation type**: `activation_followup_email`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You write an individual follow-up email from a nonprofit founder to ONE Board Member after the Board adopted the fundraising strategy. Use ONLY: the adopted Fundraising Strategy Plan, the founder's recorded adoption meeting conclusions, the member's recorded agreed responsibility, and the member's own planning response and review. NEVER use another member's answers. NEVER invent commitments, meetings, amounts, donors or relationships.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "subject": "string \u2014 a warm, professional subject line for this follow-up email from the founder to this Board Member after the plan-adoption meeting.",
 "body": "string \u2014 the complete follow-up email from the founder to this ONE Board Member. It should: thank them for helping build, review and adopt the fundraising plan; reference what was actually agreed during the adoption meeting using ONLY the supplied adoption conclusions; confirm the specific area(s) or responsibility this member agreed to support where supplied \u2014 NEVER invent or expand a responsibility; connect their part to the adopted strategy; and close with the practical next step. Where no responsibility was recorded for this member, thank them and invite the follow-up conversation instead of assigning anything. Warm, natural, plain-text paragraphs. End with the founder's name, title where supplied, and organization. NEVER mention AI. NO unresolved placeholders."
}
```
- **E. Dynamic context**: activation context (activation intake + planning responses/reviews/strategy as shown in Part 10 code)
- **F. Calling file/route**: activation_planning_routes.py:1561
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

### CONTEXT CODE — Planning form + planning email link insertion (VERBATIM)
`/app/backend/activation_planning_routes.py` lines 545-640:
```python
            "mission": context_info["mission"],
            "organization_direction_12_24_months": intake.get("direction_12_24", ""),
            "organization_priorities": intake.get("organization_priorities", ""),
            "fundraising_goal": intake.get("fundraising_goal", ""),
            "amount_needed": intake.get("amount_needed", ""),
            "what_money_will_accomplish": intake.get("money_accomplish", ""),
            "current_fundraising_methods": intake.get("current_methods", []),
            "written_strategy_status": intake.get("written_strategy", ""),
            "fundraising_calendar_status": intake.get("fundraising_calendar", ""),
            "who_carries_fundraising": intake.get("fundraising_carriers", []),
            "total_board_members": intake.get("present_board", ""),
            "active_board_members": intake.get("active_board", ""),
            "current_board_fundraising_involvement": intake.get("board_fundraising_involvement", ""),
            "current_board_fundraising_activities": intake.get("board_fundraising_activities", []),
            "known_board_skills_and_relationships": intake.get("board_skills_relationships", ""),
            "known_fundraising_barriers": intake.get("perceived_barriers", ""),
        }
        import json as jsonlib
        context = "VERIFIED ORGANIZATION AND BOARD CONTEXT (the only facts you may use):\n" + jsonlib.dumps(org_context, indent=1, default=str)

        async def run_generation():
            try:
                structured = await generate_structured("activation_planning_form", context)
                content = {
                    "introduction": structured.get("introduction", "").strip(),
                    "goal_context": structured.get("goal_context", "").strip(),
                    "question_prompts": default_prompts(context_info["organization"]),
                }
                await db.activation_planning_forms.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "content": content, "content_source": "generated",
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Planning form generation failed for %s: %s", user_id, exc)
                await db.activation_planning_forms.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.get("/activation/planning-form")
    async def get_form(request: Request):
        member = await activation_member(request)
        return form_summary(await current_form(member["user_id"]))

    @router.put("/activation/planning-form")
    async def save_form(payload: FormEditPayload, request: Request):
        member = await activation_member(request)
        form = await current_form(member["user_id"])
        if not form or not form.get("content"):
            raise HTTPException(status_code=409, detail="Generate your Board Fundraising Planning Form first")
        prompts = dict(form["content"].get("question_prompts", {}))
        for qid, prompt in payload.question_prompts.items():
            if qid in QUESTION_META and prompt.strip():
                prompts[qid] = prompt.strip()
        content = {"introduction": payload.introduction, "goal_context": payload.goal_context, "question_prompts": prompts}
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_planning_forms.update_one({"user_id": member["user_id"]}, {"$set": {
            "content": content, "content_source": "edited", "status": "Draft", "updated_at": now}})
        return {"status": "Draft"}

    @router.post("/activation/planning-form/approve")
    async def approve_form(request: Request):
        member = await activation_member(request)
        form = await current_form(member["user_id"])
        if not form or not form.get("content") or form.get("status") not in {"Draft", "Approved"}:
            raise HTTPException(status_code=409, detail="There is no draft form ready to approve")
        now = datetime.now(timezone.utc).isoformat()
        version = form.get("approved_version", 0) + 1
        await db.activation_planning_forms.update_one({"user_id": member["user_id"]}, {"$set": {
            "status": "Approved", "approved_version": version, "approved_at": now, "updated_at": now},
            "$push": {"approved_versions": {"version": version, "content": form["content"], "approved_at": now}}})
        return {"status": "Approved", "approved_version": version}

    @router.get("/activation/planning-email")
    async def planning_email(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        form = await current_form(user_id)
        if form.get("status") != "Approved" or not form.get("approved_version"):
            raise HTTPException(status_code=409, detail="Approve your Board Fundraising Planning Form before generating the email")
        token = form.get("shared_form_token")
        if not token:
            token = secrets.token_urlsafe(32)
            await db.activation_planning_forms.update_one({"user_id": user_id}, {"$set": {"shared_form_token": token}})
        context = await founder_context(user_id)
        form_link = f"{origin_of(request)}/planning-form/{token}"
        email = activation_planning_email(context["organization"], form_link,
                                          activation_signature(context["founder_name"], context["founder_title"], context["organization"]))
        return {"subject": email["subject"], "body": email["body"], "form_link": form_link}

    # ---------------- FOUNDER: SEND / REMIND ----------------

    async def send_context(user_id: str, record: dict, request: Request, kind: str) -> dict:
        context = await founder_context(user_id)
        form_link = f"{origin_of(request)}/planning-form/{record['form_token']}"
```

### CONTEXT CODE — Fundraising Strategy context (VERBATIM)
`/app/backend/activation_planning_routes.py` lines 855-905:
```python
            "reviewers": [reviewer_row(p) for p in participants],
            "review_progress": {"invited": review_invited, "received": reviews_received, "waiting": review_invited - reviews_received},
        }

    @router.post("/activation/strategy/generate")
    async def generate_strategy(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        intake = await activation_intake(user_id)
        if not intake:
            raise HTTPException(status_code=409, detail="Your Activation intake was not found. Complete the Activation intake first.")
        strategy = await current_strategy(user_id)
        if strategy.get("status") == "Generating":
            return {"status": "Generating"}
        context_info = await founder_context(user_id)
        completed = await db.activation_participants.find({"user_id": user_id, "status": "COMPLETED"}, {"_id": 0}).to_list(300)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_strategies.update_one(
            {"user_id": user_id},
            {"$set": {"user_id": user_id, "status": "Generating", "generation_error": "", "updated_at": now},
             "$setOnInsert": {"review_version": 0, "review_versions": [], "created_at": now}},
            upsert=True)
        import json as jsonlib
        intake_context = {key: intake.get(key, "") for key in [
            "your_name", "organization_name", "fundraising_goal", "amount_needed", "money_accomplish",
            "current_methods", "written_strategy", "fundraising_calendar", "fundraising_carriers",
            "present_board", "active_board", "board_fundraising_involvement", "board_fundraising_activities",
            "perceived_barriers", "board_skills_relationships", "direction_12_24", "organization_priorities",
            "previous_fundraising_planning", "broader_strategic_planning", "desired_change", "success_definition", "anything_else",
            "money_needed_by", "present_donors", "present_business_sponsors", "present_corporate_relationships",
            "present_grantors", "other_funding_relationships", "individuals_type", "individuals_approach",
            "businesses_type", "businesses_approach", "grantors_type", "grantors_approach"]}
        responses_block = [
            {"board_member_name": p["name"], "board_role": p.get("role", "Board Member"), "their_response": p.get("response", {})}
            for p in completed]
        context = ("ORGANIZATION CONTEXT:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nFOUNDER ACTIVATION INTAKE:\n" + jsonlib.dumps(intake_context, indent=1, default=str)
                   + "\n\nEVERY COMPLETED BOARD MEMBER PLANNING RESPONSE (preserve who said what):\n" + jsonlib.dumps(responses_block, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_fundraising_strategy", context)
                await db.activation_strategies.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": strategy_display(structured, context_info["organization"]),
                    "content_source": "generated",
                    "responses_included": [p["participant_id"] for p in completed],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Strategy generation failed for %s: %s", user_id, exc)
                await db.activation_strategies.update_one({"user_id": user_id}, {"$set": {
```

### CONTEXT CODE — Revised strategy (adoption) context (VERBATIM)
`/app/backend/activation_planning_routes.py` lines 1195-1240:
```python

    @router.post("/activation/adoption/strategy/generate")
    async def generate_revised_strategy(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        reviewed_text = await ready_review_text(user_id)
        adoption = await current_adoption(user_id)
        if adoption.get("revised_status") == "Generating":
            return {"status": "Generating"}
        intake = await activation_intake(user_id)
        context_info = await founder_context(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
            "user_id": user_id, "revised_status": "Generating", "revised_error": "", "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).to_list(300)
        import json as jsonlib
        responses_block = [{"board_member_name": p["name"], "board_role": p.get("role", "Board Member"),
                            "their_planning_response": p.get("response", {})} for p in participants if p.get("response")]
        reviews_block = [{"board_member_name": p["name"], "board_role": p.get("role", "Board Member"),
                          "their_review": p.get("review", {})} for p in participants if p.get("review_status") == "REVIEWED"]
        context = ("ORGANIZATION CONTEXT:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nTHE FUNDRAISING STRATEGY PLAN THE BOARD REVIEWED:\n" + reviewed_text
                   + "\n\nEVERY BOARD MEMBER REVIEW — overall position, suggestions and discussion points (preserve who said what):\n" + jsonlib.dumps(reviews_block, indent=1, default=str)
                   + "\n\nORIGINAL BOARD MEMBER PLANNING RESPONSES:\n" + jsonlib.dumps(responses_block, indent=1, default=str)
                   + "\n\nACTIVATION INTAKE HIGHLIGHTS:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish", "organization_priorities",
                       "desired_change", "success_definition"]}, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_revised_strategy", context)
                await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
                    "revised_status": "Draft", "revised_structured": structured,
                    "revised_text": strategy_display(structured, context_info["organization"]),
                    "revised_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Revised strategy generation failed for %s: %s", user_id, exc)
                await db.activation_adoptions.update_one({"user_id": user_id}, {"$set": {
                    "revised_status": "Failed", "revised_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

```

### CONTEXT CODE — Execution Toolkit context (VERBATIM)
`/app/backend/activation_planning_routes.py` lines 1455-1525:
```python
                            "generation_error": toolkit.get("generation_error", "")}}

    @router.post("/activation/toolkit/generate")
    async def generate_toolkit(request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        adoption = await current_adoption(user_id)
        if not module5_ready(adoption):
            raise HTTPException(status_code=409, detail="The Fundraising Strategy Plan must be adopted and finalized before execution tools are generated")
        toolkit = await current_toolkit(user_id)
        if toolkit.get("status") == "Generating":
            return {"status": "Generating"}
        intake = await activation_intake(user_id)
        context_info = await founder_context(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_toolkits.update_one({"user_id": user_id}, {"$set": {
            "user_id": user_id, "status": "Generating", "generation_error": "", "updated_at": now},
            "$setOnInsert": {"created_at": now}}, upsert=True)
        participants = await db.activation_participants.find({"user_id": user_id}, {"_id": 0}).to_list(300)
        recommitments = await db.reactivation_board_members.find(
            {"user_id": user_id, "status": "COMPLETED"}, {"_id": 0, "name": 1, "role": 1, "response": 1}).to_list(100)
        import json as jsonlib
        responsibilities = [{"board_member_name": p["name"], "board_role": p.get("role", ""),
                             "agreed_responsibility": p.get("agreed_responsibility", ""),
                             "responsibility_status": p.get("responsibility_status", "")} for p in participants]
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"]}, indent=1)
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN:\n" + adoption.get("adopted_text", "")
                   + "\n\nPLAN ADOPTION CONCLUSION (founder's own words):\n" + adoption.get("conclusion", "")
                   + "\n\nAGREED BOARD MEMBER RESPONSIBILITIES:\n" + jsonlib.dumps(responsibilities, indent=1, default=str)
                   + ("\n\nBOARD MEMBER PROFILE & RECOMMITMENT RESPONSES (what each member said about how they can serve and contribute — use where relevant):\n"
                      + jsonlib.dumps([{"name": r.get("name", ""), "board_role": r.get("role", ""), "their_response": r.get("response", {})}
                                       for r in recommitments], indent=1, default=str) if recommitments else "")
                   + "\n\nINTAKE HIGHLIGHTS:\n" + jsonlib.dumps({key: intake.get(key, "") for key in [
                       "fundraising_goal", "amount_needed", "money_accomplish"]}, indent=1, default=str))

        async def run_generation():
            try:
                structured = await generate_structured("activation_execution_toolkit", context)
                await db.activation_toolkits.update_one({"user_id": user_id}, {"$set": {
                    "status": "Draft", "structured": structured,
                    "display_text": toolkit_display(structured, context_info["organization"]),
                    "updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Toolkit generation failed for %s: %s", user_id, exc)
                await db.activation_toolkits.update_one({"user_id": user_id}, {"$set": {
                    "status": "Failed", "generation_error": str(exc)[:300],
                    "updated_at": datetime.now(timezone.utc).isoformat()}})

        asyncio.create_task(run_generation())
        return {"status": "Generating"}

    @router.put("/activation/toolkit")
    async def edit_toolkit(payload: TextPayload, request: Request):
        member = await activation_member(request)
        toolkit = await current_toolkit(member["user_id"])
        if not toolkit.get("display_text"):
            raise HTTPException(status_code=409, detail="Generate your Execution Toolkit first")
        await db.activation_toolkits.update_one({"user_id": member["user_id"]}, {"$set": {
            "display_text": payload.text, "status": "Draft", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Draft"}

    @router.post("/activation/toolkit/approve")
    async def approve_toolkit(request: Request):
        member = await activation_member(request)
        toolkit = await current_toolkit(member["user_id"])
        if toolkit.get("status") not in {"Draft", "Approved"} or not toolkit.get("display_text"):
            raise HTTPException(status_code=409, detail="There is no draft toolkit ready to approve")
        await db.activation_toolkits.update_one({"user_id": member["user_id"]}, {"$set": {
            "status": "Approved", "updated_at": datetime.now(timezone.utc).isoformat()}})
        return {"status": "Approved"}

```

### CONTEXT CODE — Per-member Portfolio context (VERBATIM)
`/app/backend/activation_planning_routes.py` lines 1620-1695:
```python
                "plan_status": adoption.get("plan_status", ""),
                "counts": {"participating": len(participants),
                           "responsibility_agreed": sum(1 for m in members if m["responsibility_status"] == "Responsibility Agreed"),
                           "follow_up_needed": sum(1 for m in members if m["responsibility_status"] == "Follow-Up Needed"),
                           "portfolios_approved": sum(1 for m in members if m["fp_status"] in {"Approved", "SENT"}),
                           "portfolios_sent": sum(1 for m in members if m["fp_status"] == "SENT")},
                "adopted_strategy": adoption.get("adopted_text", ""),
                "toolkit_text": toolkit.get("display_text", "") if toolkit.get("status") == "Approved" else "",
                "members": members}

    @router.post("/activation/members/{participant_id}/portfolio/generate")
    async def generate_fundraising_portfolio(participant_id: str, request: Request):
        member = await activation_member(request)
        user_id = member["user_id"]
        record = await owned_participant(user_id, participant_id)
        adoption = await current_adoption(user_id)
        if not module5_ready(adoption):
            raise HTTPException(status_code=409, detail="The Fundraising Strategy Plan must be adopted before Fundraising Portfolios are generated")
        if record.get("responsibility_status") != "Responsibility Agreed" or not record.get("agreed_responsibility", "").strip():
            raise HTTPException(status_code=409, detail="Clarify and record this Board Member's agreed fundraising responsibility before generating their Fundraising Portfolio")
        if record.get("fp_status") == "Generating":
            return {"status": "Generating"}
        context_info = await founder_context(user_id)
        toolkit = await current_toolkit(user_id)
        intake = await activation_intake(user_id)
        now = datetime.now(timezone.utc).isoformat()
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {"fp_status": "Generating", "fp_error": ""}})
        recommitment = await db.reactivation_board_members.find_one(
            {"user_id": user_id, "email": (record.get("email") or "").lower(), "status": "COMPLETED"},
            {"_id": 0, "response": 1})
        import json as jsonlib
        context = ("ORGANIZATION:\n" + jsonlib.dumps({"organization_name": context_info["organization"], "mission": context_info["mission"],
                                                       "direction": intake.get("direction_12_24", "")}, indent=1)
                   + f"\n\nBOARD MEMBER: {record['name']} — Board Role: {record.get('role', 'Board Member')}"
                   + f"\n\nEXACT AGREED FUNDRAISING RESPONSIBILITY (highest authority):\n{record['agreed_responsibility']}"
                   + "\n\nFINAL ADOPTED FUNDRAISING STRATEGY PLAN:\n" + adoption.get("adopted_text", "")
                   + "\n\nPLAN ADOPTION CONCLUSION:\n" + adoption.get("conclusion", "")
                   + "\n\nTHIS MEMBER'S OWN PLANNING RESPONSE:\n" + jsonlib.dumps(record.get("response", {}), indent=1, default=str)
                   + ("\n\nTHIS MEMBER'S BOARD MEMBER PROFILE & RECOMMITMENT RESPONSE (the role and contribution they agreed to when recommitting to the board):\n"
                      + jsonlib.dumps((recommitment or {}).get("response", {}), indent=1, default=str) if recommitment else "")
                   + "\n\nTHIS MEMBER'S OWN STRATEGY REVIEW:\n" + jsonlib.dumps(record.get("review", {}), indent=1, default=str)
                   + "\n\nAPPROVED EXECUTION TOOLKIT TOOL TITLES (reference by name only):\n"
                   + "\n".join(f"- {tool.get('title', '')}" for key in ["email_tools", "text_tools", "call_scripts", "stewardship_tools"]
                               for tool in (toolkit.get("structured", {}) or {}).get(key, [])))

        async def run_generation():
            try:
                structured = await generate_structured("activation_fundraising_portfolio", context)
                await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
                    "fp_status": "Draft", "fp_text": fp_display(structured, record["name"]), "fp_updated_at": datetime.now(timezone.utc).isoformat()}})
            except Exception as exc:
                logger.error("Fundraising portfolio generation failed for %s: %s", participant_id, exc)
                await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {
                    "fp_status": "Failed", "fp_error": str(exc)[:300]}})

        asyncio.create_task(run_generation())
        return {"status": "Generating", "started_at": now}

    @router.get("/activation/members/{participant_id}/portfolio")
    async def get_fundraising_portfolio(participant_id: str, request: Request):
        member = await activation_member(request)
        return fp_row(await owned_participant(member["user_id"], participant_id))

    @router.put("/activation/members/{participant_id}/portfolio")
    async def edit_fundraising_portfolio(participant_id: str, payload: TextPayload, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
        if not record.get("fp_text"):
            raise HTTPException(status_code=409, detail="Generate this Fundraising Portfolio first")
        await db.activation_participants.update_one({"participant_id": participant_id}, {"$set": {"fp_text": payload.text, "fp_status": "Draft"}})
        return {"status": "Draft"}

    @router.post("/activation/members/{participant_id}/portfolio/approve")
    async def approve_fundraising_portfolio(participant_id: str, request: Request):
        member = await activation_member(request)
        record = await owned_participant(member["user_id"], participant_id)
```

### 47. Board Member Communication Sequence
A dedicated three-stage sequence (Introduce Impact → Case for Support → Follow Up & Ask) with paired email + call script per stage **DOES NOT CURRENTLY EXIST**. What exists today: `activation_execution_toolkit` (tools incl. outreach emails/call scripts/social content as tool entries), `activation_fundraising_portfolio` (per member) and `activation_followup_email` (single post-adoption email). No Case for Support generator exists.

## PART 11 — ADDITIONAL GENERATION TYPES (outside the BUF customer journey)

#### `strategic_meeting_guide` — Strategic Plan Adoption Meeting Facilitation Guide
- **A. Generation type**: `strategic_meeting_guide`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are helping a facilitator run one Board meeting where each Area Owner presents their detailed plan and the Board challenges, modifies and agrees on direction. NEVER invent bylaws, quorum, voting requirements or legal adoption procedures. NEVER invent plan content. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "sections": "list of objects {heading: string, content: string} \u2014 a STRATEGIC PLAN ADOPTION MEETING FACILITATION GUIDE for the ONE primary Board meeting: (1) Objective for the Meeting, (2) Before the Meeting, (3) Open the Meeting, (4) then ONE section PER strategic area in the supplied order \u2014 for each: the Area Owner presents their submitted detailed plan (summarize what they actually submitted), Board challenge/questions to work through (drawn from outstanding flagged issues and refinement history for that area), space to record modifications, confirm the final direction, and record the outcome, (5) Close With Ownership and Next Steps. Use ONLY supplied content."
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `strategic_planning_form_structure` — Strategic Planning Form
- **A. Generation type**: `strategic_planning_form_structure`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are converting a nonprofit founder's uploaded master Strategic Planning Form into a hosted digital form for Board Members. The uploaded form text is the ONLY authority for the questions — do not invent a replacement questionnaire, do not drop areas, do not add new strategic areas. Keep the founder's question wording and section order. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "introduction": "string \u2014 2 to 3 short paragraphs written to this organization's Board Members introducing the Strategic Planning Form: the organization (real name) is building its strategic plan, the Board is being asked to shape it, their ideas and perspective matter, and their responses will be considered alongside the responses of other Board Members. Plain warm nonprofit language. NEVER mention AI, software or generation.",
 "sections": "list of objects \u2014 the hosted form sections converted FAITHFULLY from the founder's uploaded master Strategic Planning Form. Each object: {title: string (the section heading exactly as intended by the uploaded form), questions: list of objects {prompt: string (the question wording taken from the uploaded form \u2014 preserve its meaning and coverage, do NOT invent replacement questions), type: one of 'long' (open text), 'short' (single line), 'multi' (checkbox list \u2014 only when the uploaded form clearly offers a list of options), options: list of strings (only for multi, taken from the uploaded form), required: boolean (true unless the uploaded form marks it optional)}}. Cover EVERY area present in the uploaded form and NOTHING that is not in it."
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `strategic_planning_foundational` — Foundational Strategic Plan
- **A. Generation type**: `strategic_planning_foundational`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are an experienced nonprofit strategic-planning facilitator consolidating a Board's planning responses into a FOUNDATIONAL Strategic Plan — intentionally not a fully detailed final plan. For each strategic area consolidate: the direction/mission for that area, the ideas shared by the Board (with WHO said WHAT), and proposed priorities emerging from those ideas. Use ONLY the supplied organization context and the Board Members' actual responses. NEVER invent donors, partners, numbers, programs or priorities nobody raised. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "areas": "list of objects \u2014 one per strategic area covered by the Board's actual planning responses. Each object: {area: string (short area title, e.g. 'Mission / Vision', 'Fundraising'), direction: string (the direction or mission for that area, consolidated ONLY from what the founder and Board Members actually said), ideas_shared: list of strings (each specific idea with accurate attribution of WHO shared it, e.g. 'Jane Smith suggested ...' \u2014 never assign one person's idea to another person, never invent ideas), proposed_priorities: list of strings (proposed priorities or objectives for that area that emerge DIRECTLY from the ideas shared \u2014 never invent unsupported strategic priorities)}"
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `strategic_area_pack` — Strategic Area Development Pack
- **A. Generation type**: `strategic_area_pack`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are assembling a Strategic Area Development Pack for the Board Member who owns one strategic area. Use ONLY the finalized foundational plan, the Board's actual responses and refinement comments supplied. The Area Owner — not you — develops the detailed plan. NEVER invent content. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "mission_direction": "string \u2014 the agreed mission / direction for this strategic area, from the finalized foundational plan only.",
 "foundational_priorities": "list of strings \u2014 the agreed foundational priorities for this area from the finalized plan.",
 "ideas": "list of strings \u2014 every relevant idea submitted for this area, each with accurate attribution of who shared it.",
 "refinement_comments": "list of strings \u2014 the Board refinement comments relevant to this area, each attributed accurately. Empty list if none.",
 "open_questions": "list of strings \u2014 questions or issues raised in responses or refinement comments that still need resolution for this area. Empty list if none.",
 "development_instruction": "string \u2014 1 to 2 short paragraphs addressed to the Area Owner: the Board has developed and refined this foundational direction; they are asked to take this agreed foundation and develop the detailed plan for this area. Do NOT develop the detailed plan for them, do NOT prescribe its contents beyond the agreed foundation."
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `strategic_final_plan` — Final Strategic Plan
- **A. Generation type**: `strategic_final_plan`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are combining a nonprofit Board's adopted strategic-area plans into ONE organization Strategic Plan document. Every area section must faithfully reflect the Area Owner's submitted plan as adopted, including the recorded Board adoption conclusion where supplied. Do NOT rewrite strategy, add priorities, or invent content. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "sections": "list of objects \u2014 the complete organization Strategic Plan combining the adopted area plans. Each object: {heading: string (section heading \u2014 begin with an executive summary section, then one section per adopted strategic area in the order supplied), content: string (the section content: for area sections, faithfully present that area's ADOPTED detailed plan and the Board's adoption conclusion \u2014 preserve the Area Owner's actual submitted substance; for the executive summary, briefly summarize the direction across areas using only supplied content)}"
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `strategic_plan_synchronized` — Synchronized Foundational Strategic Plan
- **A. Generation type**: `strategic_plan_synchronized`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are synchronizing a Board's asynchronous review into the Foundational Strategic Plan. Inputs: the original Board Member responses, the generated draft plan, and every Board review choice and comment. Where the Board supported an area as written, preserve it. Where members suggested changes or added ideas, incorporate them faithfully with attribution. Where members flagged an area for Board discussion, keep the area and note the open question rather than resolving it yourself. The result remains FOUNDATIONAL — the organization's agreed strategic direction, not a detailed departmental execution plan. NEVER invent content. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "areas": "list of objects \u2014 one per strategic area of the plan after synchronizing the Board's asynchronous review. Each object: {area: string (short area title \u2014 keep the existing area titles wherever the area is preserved), direction: string (the refined direction for that area incorporating the Board's accepted refinement), ideas_shared: list of strings (the ideas with accurate attribution of who shared them, updated with accepted additions from the review), proposed_priorities: list of strings (the refined priorities after incorporating the Board's review choices and comments \u2014 never invent unsupported priorities)}"
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `strategic_area_owner_recommendation` — Strategic Area Owner Recommendations
- **A. Generation type**: `strategic_area_owner_recommendation`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You recommend the most appropriate Board Member to own each strategic area. Base every recommendation ONLY on the supplied Board Member information (role, expertise and their own form responses). A founder is often appropriate for Vision/Mission/Goals/Objectives/Priorities; program-development expertise or relevant lived experience fits Program Development; HR experience fits Team Building/Human Resources; marketing experience fits Marketing; partnership experience fits Partnerships; technology expertise fits Technology; fundraising expertise fits Fundraising; an accountant or financial professional fits Budgeting/Finance — but ONLY when the supplied facts support it. One person may own multiple areas; some areas may have no clear fit (empty recommended_name); not every Board Member needs an area. These are RECOMMENDATIONS ONLY — the facilitator makes every final assignment. NEVER invent skills or experience. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "recommendations": "list of objects \u2014 one per strategic area supplied. Each object: {area_key: string (exactly the supplied area_key), recommended_name: string (the full name of the ONE Board Member best suited to own this area based on their skills, professional experience, lived experience, stated interests, the areas they said they want to support, and their own submitted ideas \u2014 or empty string when no Board Member is a clear fit), reason: string (1-2 sentences explaining the alignment using ONLY supplied facts about that Board Member)}"
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `strategic_action_plan` — Strategic Planning Action Plan
- **A. Generation type**: `strategic_action_plan`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You are creating a one-page Action Planning summary of a Board's synchronized Foundational Strategic Plan. It supplements — never replaces — the Strategic Plan. Use ONLY the supplied plan content. NEVER invent actions, owners, dates or commitments. NEVER mention AI.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "sections": "list of objects {heading: string, content: string} \u2014 a concise ONE-PAGE Action Planning document summarizing the organization's immediate strategic direction and practical next actions, drawn ONLY from the synchronized Foundational Strategic Plan supplied: (1) Our Strategic Direction (2-3 sentences), (2) Immediate Priorities (the top agreed priorities), (3) Next Actions (practical, near-term actions that follow directly from the plan), (4) Who Carries It Forward (area ownership only where supplied). Keep the whole document brief enough to fit one page."
}
```
- **E. Dynamic context**: strategic planning context (strategic_planning_routes.py — separate product)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

#### `resource_design_adjustments` — Resource Design Adjustments
- **A. Generation type**: `resource_design_adjustments`
- **B. System prompt**: GLOBAL SYSTEM PROMPT A (Part 2, verbatim) — shared by ALL generate_structured generators
- **C. Resource-specific developer prompt (VERBATIM, sent as `SPECIAL REQUIREMENTS:`)**:
```
You translate a customer's natural-language design instruction into small style adjustments for their published hosted document page. Start from the CURRENT design values supplied and change ONLY what the instruction asks for, keeping every other value exactly as it currently is. The document CONTENT never changes. Output every key with its resulting value.
```
- **D. JSON schema (VERBATIM — field descriptions are the writing instructions; all fields required by instruction 'matching exactly this schema'; no enum/validation beyond descriptions)**:
```json
{
 "heading_scale": "number \u2014 relative heading size between 0.6 and 1.5 (1 is default). Change ONLY if the instruction asks about heading/title size.",
 "logo_position": "string \u2014 one of 'left', 'right', 'center'. Change ONLY if the instruction asks about logo placement.",
 "body_font": "string \u2014 one of 'serif', 'sans-serif'. Change ONLY if the instruction asks for a different feel (more formal -> serif, more modern/clean -> sans-serif).",
 "spacing_scale": "number \u2014 relative section/paragraph spacing between 0.6 and 2 (1 is default). Change ONLY if the instruction asks about spacing.",
 "text_align": "string \u2014 one of 'left', 'center'. Change ONLY when asked.",
 "accent_intensity": "string \u2014 one of 'subtle', 'standard', 'strong' controlling how prominently the organization's brand color is used. Change ONLY when asked (e.g. 'more formal' -> subtle)."
}
```
- **E. Dynamic context**: org-level workspace context (build_org_context + FOUNDER CONTACT + approved prior materials)
- **F. Calling file/route**: workspace_routes.py:182 — POST /api/workspace/generate (generic generation endpoint; context built in-route + build_org_context)
- **G. Output handling**: parse_json_response → stored in `generated_materials` (type, application_id where per-candidate, structured payload, display text) unless noted otherwise in stage code; rendered by module UI; approval status gates reuse in later contexts

Also: **Blog engine** (marketing_service.py:203 & 276) — generates blog articles and social snippets with GLOBAL SYSTEM PROMPT B; prompts built inline in marketing_service; stored in blog collections; admin-triggered.

## PART 12 — CONTEXT PASSED TO EACH GENERATOR (exact YES/NO with sources)

**FAMILY R-ORG — all org-level recruitment workspace types** (recruitment_strategy, board_opportunity, application_questions, linkedin_post, social_posts, recruitment_emails, linkedin_launch_instructions, board_recruitment_job_post, personal_invitation_email/message, referral_request_email/message, general_interview_invitation(+message), onboarding_script, organization_overview, board_manual, board_member_agreement, confidentiality_agreement, conflict_of_interest_agreement, first_board_meeting_invitation):
- Master intake directly: NO (not passed). Indirectly: YES — via recruitment_profiles/board_recruitment_intakes auto-seeded from master (board_fix_routes.ensure_recruitment_seed) for BUF customers
- Founder info: YES — FOUNDER CONTACT block (contact_name/email/phone from profile) | Organization info: YES — build_org_context fields (organization_name, website, mission, city, state_region, board_kind, priorities, specific_wants, board_challenges, current_board_strengths, meeting/strategy_intake fields)
- Board composition: YES — present_board/active_board strings from profile | Individual board member info: NO | Board member responses: NO | Recommitment responses: NO | Recruitment info: YES — confirmed profile + strategy intake | Fundraising planning responses: NO | Bylaws: NO (not passed) | Previous generated resources: YES — approved materials fed forward in build_org_context

**FAMILY R-CAND — per-candidate workspace types** (interview_guide, interview_invitation(+message), before/after_interview_rejection, general_rejection_email, after_interview_thank_you, after_interview_email, conditional_offer, formal_appointment_email, reference_request_email, referee_confirmation_email, candidate_referee_request, reference_call_script, reference_evaluation_form, onboarding_agenda, ninety_day_plan, board_member_engagement_guide, board_member_portfolio, portfolio_email):
- Everything in FAMILY R-ORG **plus**: candidate application snapshot (profile_snapshot: name/email/phone/linkedin/answers), CV extracted text where uploaded, interview notes/outcomes where recorded, reference process status + referee responses (reference_context), onboarding session details, agreement sign links + profile-form/manual/overview links (conditional_offer & formal_appointment_email), candidate reference-form link (candidate_referee_request)
- Recommitment responses: NO | Master intake directly: NO | Bylaws: NO

**powerhouse_board_blueprint (Stage 2)** — FAMILY R-ORG **plus** (workspace_routes special block): founder-included-in-present-board rule text + CURRENT BOARD MEMBER RECOMMITMENT RESPONSES (reactivation_board_members COMPLETED: name, role, response). Recommitment responses: YES. Master directly: NO.

**FAMILY REACT — reactivation types** (reactivation_response_analysis, reactivation_board_summary, reactivation_conversation_script, reactivation_stepped_down_followup, reactivation_advisory_confirmation, reactivation_engagement_plan):
- Founder/org info: YES — founder_context (organization, mission, founder name/title/email from board_reactivation_intakes prefilled from master)
- Individual board member info + their FULL recommitment response: YES (the record) | interpretation feeds conversation script: YES | board summary receives ALL responses + ALL individual interpretations + orientation transition selections: YES
- Master directly: NO | Recruitment info: NO | Fundraising planning responses: NO | Bylaws: NO | Previous resources: YES (interpretations)

**FAMILY ACT — activation types**:
- activation_planning_form: founder activation intake (full, incl. new §22-23 funding-audience fields): YES; board info: sizes only; recommitment: NO; bylaws: NO
- activation_fundraising_strategy: ALL board planning responses YES; founder intake (incl. present donors/sponsors/grantors, amount, purpose, timing, audience questions) YES via intake dump; founder's own planning response YES (participant record where founder participates); recommitment responses: NO; board summary: NO; bylaws: NO; framework: YES (schema/note = the established framework)
- activation_revised_strategy: strategy text + ALL reviews (position/discussion/contribution/support) + planning responses + intake: YES; idea approvals: no longer collected
- activation_facilitation_guide / adoption: strategy + reviews + intake: YES
- activation_execution_toolkit: strategy + responsibilities + ALL recommitment responses (added June 2026) + intake highlights: YES
- activation_fundraising_portfolio: this member's planning response + this member's recommitment response (matched by email, June 2026) + their review + agreed responsibility + strategy + intake highlights: YES
- activation_followup_email: adoption conclusions + member responsibility + member planning response/review: YES
- Master directly: NO (indirect via prefilled activation intake) | Bylaws: NO

**BYLAWS**: collected in master intake since June 2026 (`bylaws_text` field) but passed to **ZERO** generators today.
**MASTER INTAKE DIRECT**: passed to ZERO generators. Indirect for all pathway generators via prefilled/seeded intakes+profiles.

## PART 13 — TEMPLATE-BASED RESOURCES (VERBATIM SOURCE)
### content_templates.py — COMPLETE FILE (all Rooney fixed templates: recommitment form intro, outreach/reminder emails, reminder call script, activation planning/review/adoption emails)
```python
"""Single source of truth for customer-facing Reactivation email and script templates."""


def _signature(founder_name: str, founder_title: str, organization: str) -> str:
    return founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"


def recommitment_outreach_email(kind: str, first: str, founder_name: str, founder_title: str, organization: str) -> dict:
    signature = _signature(founder_name, founder_title, organization)
    if kind == "reminder":
        return {
            "subject": f"Reminder: Board Member Recommitment Form | {organization}",
            "body": (
                f"Dear {first},\n\n"
                f"I wanted to follow up on the Board Member Profile & Recommitment Form I sent you for {organization}.\n\n"
                "We are using the responses from each Board Member to understand where everyone is, how people would like to contribute moving forward, and what support or clarity may be needed.\n\n"
                "If you have not completed yours yet, please use the link below:\n\n"
                "[COMPLETE MY FORM]\n\n"
                "Your response will help us prepare for the conversation about your Board role and how we move forward together.\n\n"
                f"Thank you,\n{signature}"
            ),
            "button_label": "COMPLETE MY FORM",
        }
    greeting = f"Dear {first}," if first else "Dear Board Member,"
    return {
        "subject": f"Board Recommitment & Profile | {organization}",
        "body": (
            f"{greeting}\n\n"
            f"As we continue strengthening the Board of {organization}, we are taking time to make sure every Board Member has clarity about their role, capacity and how they would like to contribute moving forward.\n\n"
            "Please take a few minutes to complete your Board Member Profile & Recommitment Form.\n\n"
            "Your responses will help us understand:\n"
            "- how you would like to continue contributing\n"
            "- the expertise and experience you bring\n"
            "- the areas where you would most like to help\n"
            "- the level of time you can realistically commit\n"
            "- any support or clarity you need from the organization\n\n"
            "This is not about pressuring anyone to stay.\n\n"
            "It is about having an honest understanding of where each Board Member is and making sure the people serving on the Board are positioned to contribute meaningfully.\n\n"
            "[COMPLETE MY BOARD MEMBER PROFILE & RECOMMITMENT FORM]\n\n"
            f"Thank you for taking the time to complete it.\n\n{signature}"
        ),
        "button_label": "COMPLETE MY BOARD MEMBER PROFILE & RECOMMITMENT FORM",
    }


def recommitment_reminder_call_script(first: str, founder_first: str, organization: str) -> str:
    return (
        f"Hi {first}, it's {founder_first} from {organization}.\n\n"
        "I wanted to quickly follow up on the Board Member Profile & Recommitment Form I sent you.\n\n"
        "We're asking every Board Member to complete it because I want to understand where everyone is, what people realistically have capacity for, and how each person would like to contribute moving forward.\n\n"
        "This isn't about pressuring anyone.\n\n"
        "I want us to have an honest picture of who is able to continue serving actively, where people need more clarity, and where we may need to make changes so the Board can function properly.\n\n"
        "I can resend the link to you now if that would help.\n\n"
        "Is there anything that's making it difficult for you to complete it?"
    )


def recommitment_form_intro(organization: str, mission: str) -> str:
    mission_line = f"\n\nOur mission: {mission}" if mission else ""
    return (
        f"Board Member Profile & Recommitment Form — {organization}\n\n"
        f"As we continue strengthening the Board of {organization}, we are asking every Board Member to complete this Profile & Recommitment Form.{mission_line}\n\n"
        "Your responses will help us understand how you would like to continue contributing, the expertise and experience you bring, the areas where you would most like to help, the time you can realistically commit, and any support or clarity you need from the organization.\n\n"
        "This is not about pressuring anyone to stay. It is about having an honest understanding of where each Board Member is, so the people serving on the Board are positioned to contribute meaningfully."
    )

# ---------------- Strategic Planning static emails ----------------

def sp_signature(founder_name: str, founder_title: str, organization: str) -> str:
    return founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"


def sp_form_invitation_email(first: str, organization: str, signature: str) -> dict:
    body = (
        f"Dear {first},\n\n"
        f"We are beginning the process of building the strategic plan for {organization}, and I want the Board involved in shaping it.\n\n"
        "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
        "Your ideas, experience and perspective will help shape our direction, priorities and how each of us can contribute.\n\n"
        "Please complete the Strategic Planning Form below.\n\n"
        "[COMPLETE MY STRATEGIC PLANNING FORM]\n\n"
        "Your responses will be combined with the ideas of the other Board Members as we build the plan.\n\n"
        f"Thank you for helping us build this together.\n\n{signature}"
    )
    return {"subject": f"Help Us Build Our Strategic Plan | {organization}", "body": body,
            "button_label": "COMPLETE MY STRATEGIC PLANNING FORM"}


def sp_generic_form_invitation_email(organization: str, link: str, signature: str) -> dict:
    body = (
        "Dear Board Member,\n\n"
        f"We are beginning the process of building the strategic plan for {organization}, and I want the Board involved in shaping it.\n\n"
        "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
        "Your ideas, experience and perspective will help shape our direction, priorities and how each of us can contribute.\n\n"
        "Please complete the Strategic Planning Form using the link below.\n\n"
        f"{link}\n\n"
        "Your responses will be combined with the ideas of the other Board Members as we build the plan.\n\n"
        f"Thank you for helping us build this together.\n\n{signature}"
    )
    return {"subject": f"Help Us Build Our Strategic Plan | {organization}", "body": body, "form_link": link}


def sp_review_invitation_email(first: str, organization: str, signature: str) -> dict:
    body = (
        f"Dear {first},\n\n"
        f"The ideas the Board shared have been consolidated into the Foundational Strategic Plan for {organization}.\n\n"
        "Before area owners develop the detailed plans, I want every Board Member to review the consolidated thinking, challenge it, improve it and add anything that is missing.\n\n"
        "For each strategic area you can support it as written, suggest a change, add an idea, or flag it for Board discussion.\n\n"
        "[REVIEW THE FOUNDATIONAL PLAN]\n\n"
        f"Thank you for helping us refine this together.\n\n{signature}"
    )
    return {"subject": f"Review Our Foundational Strategic Plan | {organization}", "body": body,
            "button_label": "REVIEW THE FOUNDATIONAL PLAN"}


def activation_signature(founder_name: str, founder_title: str, organization: str) -> str:
    return founder_name + (f"\n{founder_title}" if founder_title else "") + f"\n{organization}"


def activation_planning_email(organization: str, form_link: str, signature: str) -> dict:
    return {
        "subject": f"Help Us Build Our Fundraising Plan | {organization}",
        "body": (
            "Dear Board Members,\n\n"
            f"We are beginning the process of building the fundraising plan for {organization}, and I want the Board involved in shaping it.\n\n"
            "Rather than creating the plan and bringing it to the Board after the fact, I want us to build it together.\n\n"
            "Your ideas, experience, relationships and perspective can help us determine who we should be building relationships with, which fundraising opportunities we should prioritize, and how each of us can contribute.\n\n"
            "Please complete the short Board Fundraising Planning Form here:\n\n"
            f"{form_link}\n\n"
            "Your responses will be combined with the ideas of the other Board Members and our organizational priorities as we build the Fundraising Strategy Plan.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        ),
    }


def activation_review_email(organization: str, review_link: str, signature: str) -> dict:
    return {
        "subject": f"Please Review Our Fundraising Strategy Plan | {organization}",
        "body": (
            "Dear Board Members,\n\n"
            f"Thank you for contributing your ideas to the fundraising planning process for {organization}.\n\n"
            "We have now brought the Board's input together with the organization's fundraising goals and priorities and developed the Fundraising Strategy Plan for Board review.\n\n"
            "Before we move into adopting the plan, please review the strategy and share any suggestions, concerns or issues you believe the Board should discuss.\n\n"
            "Please review the complete Fundraising Strategy Plan here:\n\n"
            f"{review_link}\n\n"
            "Your review will help us prepare for the Board discussion where we will work through the strategy and agree on the way forward.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        ),
    }


def activation_adoption_meeting_email(organization: str, meeting_lines: str, plan_link: str, signature: str) -> dict:
    return {
        "subject": f"Board Meeting: Adopting Our Fundraising Strategy Plan | {organization}",
        "body": (
            "Dear Board Members,\n\n"
            f"Thank you for helping build and review the Fundraising Strategy Plan for {organization}.\n\n"
            "The next step is to come together, work through the Board's feedback, agree on the direction and adopt the plan we will carry together.\n\n"
            f"{meeting_lines}\n\n"
            "Please review the current Fundraising Strategy Plan before the meeting:\n\n"
            f"{plan_link}\n\n"
            "During the meeting we will work through the feedback from the Board's review, confirm our priorities and agree on what each of us will help carry.\n\n"
            f"Thank you for helping us build this together.\n\n{signature}"
        ),
    }


def checkout_recovery_email(first_name: str, organization: str, offer_name: str, offer_link: str) -> dict:
    greeting = f"Hi {first_name}," if first_name else "Hi,"
    org_part = f" at {organization}" if organization else ""
    return {
        "subject": "You started building your board — your next step is ready",
        "body": (
            f"{greeting}\n\n"
            f"You took the first step toward transforming your board{org_part}, and you were moments away from getting started with {offer_name}.\n\n"
            "If you got pulled away, no problem. Your next step is right where you left it:\n\n"
            f"{offer_link}\n\n"
            "If you have a question before you get started, just reply to this email and I'll personally answer it.\n\n"
            "Rooney Akpesiri\nThe Nonprofit Board Builder"
        ),
    }

```
### Recommitment Form fixed question set — /app/frontend/src/funnels/BoardRecommitmentFormPage.jsx (VERBATIM, full component)
```jsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { usePageMeta } from "@/seo";
import { recommitFormText } from "../content/appContent";
import { boardRecommitmentFormPageText } from "../content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const EXPERTISE = ["Fundraising", "Major Gifts", "Grant Writing", "Finance / Accounting", "Legal", "Human Resources", "Marketing / Communications", "Public Relations", "Strategic Planning", "Organizational Development", "Nonprofit Leadership", "Corporate Partnerships", "Government Relations", "Education", "Youth Development", "Healthcare", "Mental Health", "Technology / AI", "Program Development", "Operations", "Project Management", "Community Engagement", "Volunteer Management", "Events", "Advocacy", "Other"];
const NETWORKS = ["Business Leaders", "Corporate Executives", "Donors / Philanthropists", "Foundations", "Community Leaders", "Government", "Schools / Universities", "Faith Communities", "Healthcare Organizations", "Technology Sector", "Media", "Professional Associations", "Other", "I am not currently comfortable making introductions"];
const HOW_RECRUITED = ["Invited by the Founder / Executive Director", "Invited by another Board Member", "Friend / Family / Personal Relationship", "Professional Relationship", "Volunteer / Supporter of the Organization", "Public Board Recruitment", "Founding Member", "Other"];
const CLARITY = ["Very Clear", "Somewhat Clear", "Not Very Clear", "Not Clear at All"];
const CONTRIBUTIONS = ["Fundraising", "Donor Introductions", "Corporate Partnerships / Sponsorship", "Grants / Foundations", "Finance", "Governance", "Strategic Planning", "Marketing / Communications", "Public Relations", "Programs", "Operations", "Human Resources", "Technology", "Community Engagement", "Government / Advocacy", "Events", "Volunteer Development", "Board Recruitment", "Leadership / Committee Service", "Other"];
const FUNDRAISING = ["Making introductions to potential donors", "Meeting with prospective donors", "Corporate sponsorship outreach", "Foundation / grant opportunities", "Donor stewardship", "Fundraising events", "Speaking about the organization", "Reviewing fundraising strategy", "Personal financial contribution", "I would like training before participating", "I am not currently comfortable participating in fundraising"];
const AVAILABILITY = ["Less than 2 hours", "2–4 hours", "5–8 hours", "9–12 hours", "More than 12 hours", "Varies significantly month to month"];
const MEETINGS = ["Yes", "Usually", "Sometimes", "No", "I need to discuss the meeting schedule"];

const INITIAL = {
  full_name: "", preferred_name: "", email: "", phone: "", city_state: "", linkedin: "", current_position: "", employer: "", industry: "", years_experience: "",
  expertise: [], expertise_other: "", networks: [], why_joined: "", how_recruited: "", original_role_expectation: "", role_clarity: "", clarity_help: "",
  board_experience: "", participation_barriers: "", board_improvement: "", strategic_clarity: "", planning_participation: "", planning_involvement_desire: "",
  recommitment: "", advisory_openness: "", support_role_openness: "", step_off_openness: "", contribution_interests: [], fundraising_comfort: [], ownership_areas: "",
  leadership_interest: "", support_needed: "", monthly_availability: "", meeting_participation: "", constraints: "", meaningful_service: "", anything_else: "", confirmation: false,
};

const tid = (name) => `recommit-${name.replace(/_/g, "-")}`;
const Text = ({ label, name, form, set, required = false, type = "text" }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><input type={type} value={form[name]} onChange={set(name)} data-testid={tid(name)} /></label>
);
const Area = ({ label, name, form, set, required = true, rows = 4 }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span><textarea rows={rows} value={form[name]} onChange={set(name)} data-testid={tid(name)} /></label>
);
const Select = ({ label, name, options, form, set, required = true }) => (
  <label className="field"><span>{label} {required && <b>*</b>}</span>
    <select value={form[name]} onChange={set(name)} data-testid={tid(name)}><option value="">Choose one…</option>{options.map((option) => <option key={option}>{option}</option>)}</select>
  </label>
);
const Multi = ({ legend, name, options, form, toggle, required = true }) => (
  <fieldset className="field choice-field"><legend>{legend} {required && <b>*</b>}</legend>
    <div className="choice-grid">
      {options.map((option) => (
        <label className={`choice ${form[name].includes(option) ? "selected" : ""}`} key={option}>
          <input type="checkbox" checked={form[name].includes(option)} onChange={() => toggle(name, option)} data-testid={`${tid(name)}-${option.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
          <span>{option}</span>
        </label>
      ))}
    </div>
  </fieldset>
);

export default function BoardRecommitmentFormPage() {
  usePageMeta("Board Member Profile & Recommitment Form | Nonprofit Board Builder", "Complete your Board Member Profile & Recommitment Form.", true);
  const { token } = useParams();
  const generalVersion = new URLSearchParams(window.location.search).get("general") === "1";
  const [context, setContext] = useState(null);
  const [gate, setGate] = useState("loading");
  const [form, setForm] = useState(INITIAL);
  const [errorText, setErrorText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    axios.get(`${API}/board-recommitment/${token}`).then((response) => {
      setContext(response.data);
      setForm((current) => ({ ...current, ...Object.fromEntries(Object.entries({
        full_name: response.data.prefill.full_name, email: response.data.prefill.email, phone: response.data.prefill.phone,
      }).filter(([, value]) => value)) }));
      setGate(response.data.submitted ? "already" : "ready");
    }).catch(() => setGate("invalid"));
  }, [token]);

  const set = (name) => (event) => setForm((current) => ({ ...current, [name]: event.target.value }));
  const toggle = (name, option) => setForm((current) => ({
    ...current, [name]: current[name].includes(option) ? current[name].filter((item) => item !== option) : [...current[name], option],
  }));

  const submit = async () => {
    const required = ["full_name", "email", "current_position", "why_joined", "how_recruited", "original_role_expectation", "role_clarity", "board_experience", "participation_barriers", "board_improvement", "strategic_clarity", "planning_participation", "recommitment", "ownership_areas", "leadership_interest", "support_needed", "monthly_availability", "meeting_participation", "meaningful_service"];
    const missing = required.some((name) => !String(form[name]).trim()) || !form.expertise.length || !form.networks.length || !form.contribution_interests.length || !form.fundraising_comfort.length;
    if (missing) { setErrorText("Please answer every required question before submitting."); window.scrollTo(0, 0); return; }
    if (!form.confirmation) { setErrorText("Please check the confirmation box before submitting."); return; }
    setBusy(true);
    setErrorText("");
    try {
      await axios.post(`${API}/board-recommitment/${token}`, form);
      setGate("done");
      window.scrollTo(0, 0);
    } catch (error) {
      setErrorText(error.response?.status === 409 ? "This response has already been submitted." : "We could not submit your response. Please review your answers and try again.");
      setBusy(false);
    }
  };

  const org = context?.organization_name || "the organization";

  return (
    <FunnelLayout restrained>
      <main data-testid="recommit-page">
        {gate === "loading" && <div className="intake-card"><p>Loading…</p></div>}
        {gate === "invalid" && (
          <div className="intake-card" data-testid="recommit-invalid"><h2>{recommitFormText.h_thisLinkIsNotValid}</h2><p>{boardRecommitmentFormPageText.pleaseContactThePersonWho}</p></div>
        )}
        {(gate === "done" || gate === "already") && (
          <div className="intake-card" data-testid="recommit-thankyou">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Submitted</p>
            <h2>{recommitFormText.h_thankYou}</h2>
            <p>{boardRecommitmentFormPageText.yourBoardMemberProfileAmp}<strong>{org}</strong>.</p>
            <p>{boardRecommitmentFormPageText.theOrganizationWillReviewYour}</p>
          </div>
        )}
        {gate === "ready" && (
          <>
            <section className="funnel-hero-banner brp-hero intake-hero" data-testid="recommit-hero">
              <h1>{recommitFormText.h_boardMemberProfileAmpRecommitment}</h1>
              <p className="funnel-hero-banner-supporting" data-testid="recommit-supporting">{org} is taking time to strengthen how the Board works together and make sure every Board Member has clarity about their role, capacity and areas of contribution.</p>
              <p className="funnel-hero-banner-secondary">{recommitFormText.s_pleaseCompleteThisFormHonestly}</p>
              <i aria-hidden="true" />
            </section>
            <section className="intake-shell" data-testid="recommit-form">
              {context?.introduction && (
                <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", padding: 16, borderRadius: 8, marginBottom: 18 }} data-testid="recommit-introduction">{context.introduction}</div>
              )}
              {errorText && <p className="submit-error" data-testid="recommit-error">{errorText}</p>}

              <h2 className="intake-step-title">{recommitFormText.h_aboutYou}</h2>
              <div className="two-col-fields">
                <Text label="Full Name" name="full_name" form={form} set={set} required />
                <Text label="Preferred Name" name="preferred_name" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="Email Address" name="email" type="email" form={form} set={set} required />
                <Text label="Phone Number" name="phone" type="tel" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="City / State / Region" name="city_state" form={form} set={set} />
                <Text label="LinkedIn Profile (optional)" name="linkedin" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="Current Professional Position" name="current_position" form={form} set={set} required />
                <Text label="Organization / Employer" name="employer" form={form} set={set} />
              </div>
              <div className="two-col-fields">
                <Text label="Industry / Professional Field" name="industry" form={form} set={set} />
                <Text label="Years of Professional Experience (optional)" name="years_experience" form={form} set={set} />
              </div>
              <Multi legend="What professional skills, experience or expertise do you bring that could support the organization?" name="expertise" options={EXPERTISE} form={form} toggle={toggle} />
              {form.expertise.includes("Other") && <Text label="Other expertise" name="expertise_other" form={form} set={set} />}
              <Multi legend="Which types of relationships or professional networks could you potentially help the organization connect with?" name="networks" options={NETWORKS} form={form} toggle={toggle} />

              <h2 className="intake-step-title">{recommitFormText.h_yourExperienceOnTheBoard}</h2>
              <Area label={`What originally interested you in serving on the Board of ${org}?`} name="why_joined" form={form} set={set} />
              <Select label="How did you originally become involved with the Board?" name="how_recruited" options={HOW_RECRUITED} form={form} set={set} />
              <Area label="When you joined the Board, what did you understand your role and responsibilities to be?" name="original_role_expectation" form={form} set={set} />
              <Select label="How clear are you today about what is expected of you as a Board Member?" name="role_clarity" options={CLARITY} form={form} set={set} />
              <Area label="What would help give you greater clarity about your role? (optional)" name="clarity_help" required={false} rows={3} form={form} set={set} />
              <Area label="How would you describe your experience serving on the Board so far?" name="board_experience" form={form} set={set} />
              <Area label="What, if anything, has made it difficult for you to participate as actively as you would like?" name="participation_barriers" form={form} set={set} />
              <Area label="What do you believe would help the Board work more effectively?" name="board_improvement" form={form} set={set} />
              <Select label="How clear are you about where the organization is heading over the next 12–24 months?" name="strategic_clarity" options={CLARITY} form={form} set={set} />
              <Select label="Have you had an opportunity to contribute to the organization's strategic direction or planning?" name="planning_participation" options={["Yes", "Somewhat", "No", "Not Sure"]} form={form} set={set} />
              <Area label="If you would like greater involvement in planning or strategic decisions, tell us how. (optional)" name="planning_involvement_desire" required={false} rows={3} form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_recommitment}</h2>
              <fieldset className="field choice-field" data-testid="recommit-recommitment-options">
                <legend>{boardRecommitmentFormPageText.lookingAheadAreYouWilling}<b>*</b></legend>
                <div>
                  {(context.recommitment_options || []).map((option) => (
                    <label className={`choice ${form.recommitment === option ? "selected" : ""}`} key={option} style={{ display: "flex", marginBottom: 8 }}>
                      <input type="radio" name="recommitment" checked={form.recommitment === option} onChange={() => setForm((current) => ({ ...current, recommitment: option }))} data-testid={`recommit-option-${(context.recommitment_options || []).indexOf(option) + 1}`} />
                      <span>{option}</span>
                    </label>
                  ))}
                </div>
              </fieldset>
              {!generalVersion && context.allow_advisory && (
                <Select label="If continuing as an active Board Member is not realistic for you, would you be open to supporting the organization in an Advisory Board / Advisory role?" name="advisory_openness" options={["Yes", "Maybe — I would like to discuss it", "No"]} form={form} set={set} required={false} />
              )}
              {!generalVersion && context.allow_support_role && (
                <Select label="If continuing as an active Board Member is not realistic for you, would you be open to supporting the organization in another volunteer or support role?" name="support_role_openness" options={["Yes", "Maybe — I would like to discuss it", "No"]} form={form} set={set} required={false} />
              )}
              {!generalVersion && context.allow_step_off && (
                <Select label="Thinking honestly about your capacity and interest, do you believe you should remain on the board or transition off the board?" name="step_off_openness" options={["I should remain on the board", "I believe I should transition off the board", "I am not sure — I would like to discuss it"]} form={form} set={set} required={false} />
              )}

              <h2 className="intake-step-title">{recommitFormText.h_howYouWantToContribute}</h2>
              <Multi legend="If you continue serving, where would you most like to contribute?" name="contribution_interests" options={CONTRIBUTIONS} form={form} toggle={toggle} />
              <Multi legend="Which fundraising activities would you be comfortable helping with?" name="fundraising_comfort" options={FUNDRAISING} form={form} toggle={toggle} />
              <Area label="What areas of responsibility would you be willing to take greater ownership of over the next 6–12 months?" name="ownership_areas" form={form} set={set} />
              <Area label="Are there any areas where you would be interested in taking a leadership role?" name="leadership_interest" form={form} set={set} />
              <Area label="What support, information or resources would help you contribute more effectively?" name="support_needed" form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_yourCapacity}</h2>
              <Select label="Realistically, how much time can you commit to Board responsibilities each month?" name="monthly_availability" options={AVAILABILITY} form={form} set={set} />
              <Select label="Are you able to participate consistently in the organization's current Board meeting schedule?" name="meeting_participation" options={MEETINGS} form={form} set={set} />
              <Area label="Is there anything about your current availability or circumstances that the organization should understand when discussing your Board responsibilities? (optional)" name="constraints" required={false} rows={3} form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_finalQuestions}</h2>
              <Area label="If you continue serving, what would make your Board service meaningful and worthwhile to you?" name="meaningful_service" form={form} set={set} />
              <Area label="Is there anything else you would like the Founder or Board leadership to understand before you discuss your future role on the Board? (optional)" name="anything_else" required={false} rows={3} form={form} set={set} />

              <h2 className="intake-step-title">{recommitFormText.h_confirmation}</h2>
              <label className="choice" style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
                <input type="checkbox" checked={form.confirmation} onChange={() => setForm((current) => ({ ...current, confirmation: !current.confirmation }))} data-testid="recommit-confirmation" />
                <span>{boardRecommitmentFormPageText.iConfirmThatTheInformation}<b>*</b></span>
              </label>

              {errorText && <p className="submit-error">{errorText}</p>}
              <div className="intake-nav" style={{ justifyContent: "center" }}>
                <button type="button" className="button rwr-cta-button" onClick={submit} disabled={busy} data-testid="recommit-submit">{busy ? "Submitting…" : "SUBMIT MY RESPONSE"}</button>
              </div>
            </section>
          </>
        )}
      </main>
    </FunnelLayout>
  );
}

```
### Platform-appended recruitment timeline (ai_service.STRATEGY_TIMELINE_TEXT) — VERBATIM
```
4. RECRUITMENT TIMELINE

DAY 1
Launch the recruitment campaign. Begin Personal Network outreach where applicable, begin Referral Network outreach where applicable, and publish through your selected Public Outreach channels where applicable.

WITHIN 48 HOURS
Review the first applications and responses. Begin inviting qualified applicants to interview — do not wait until the campaign closes.

WEEKS 1-2
Continue recruitment outreach. Review applicants as they arrive, interview qualified applicants, follow up with strong prospects and continue accepting additional applications while interviews are taking place.

WEEK 3
Complete final interviews and verification for candidates moving forward. Finalize board-member selections, complete required onboarding information, agreements and preparation, and begin onboarding the new board members.
```

## PART 14 — MISSING / NONEXISTENT GENERATORS
1. **Formal Board Appointment Letter — DOES NOT CURRENTLY EXIST** (emails exist; letter does not)
2. **Three-stage Board Member Communication Sequence (email + call script per stage) — DOES NOT CURRENTLY EXIST**
3. **Case for Support — DOES NOT CURRENTLY EXIST**
None were created (extraction only).

## PART 15 — PROMPT COMPOSITION ARCHITECTURE (actual)
```
GLOBAL SYSTEM PROMPT A (system message, shared)
        ↓
USER MESSAGE, assembled by generate_structured():
   "GENERATION TYPE: {title}"
   "CONTEXT (the only information you may use):\n{dynamic context string built by the calling route}"
   "SPECIAL REQUIREMENTS: {developer note}"          ← only if the type has a note
   "ADDITIONAL INSTRUCTIONS:\n{instructions}"        ← rarely used, route-specific
   "Respond with one JSON object matching exactly this schema (descriptions explain each field):" + schema JSON
        ↓
Claude claude-sonnet-4-6 (single call, no retries)
        ↓
parse_json_response → structured dict → route-specific storage/rendering
```
There is NO separate developer-role message; developer notes travel inside the user message. Context is a plain formatted STRING (not structured JSON payloads), built per route.

## PART 16 — GENERATION ENGINE CONFIGURATION
- Library: emergentintegrations LlmChat | Provider: anthropic | Model: env CLAUDE_MODEL, default "claude-sonnet-4-6"
- Key: ANTHROPIC_API_KEY or EMERGENT_LLM_KEY (Emergent universal key in this deployment)
- Session id: nbb-{type}-{uuid} per call | No temperature/top_p/max_tokens overrides | No streaming | No retry/fallback — failures mark material status "Failed" and the founder regenerates manually
- application_questions post-cap: max 5 custom questions

## PART 17 — FINDINGS / LIMITATIONS (RECORDED ONLY — NOTHING CHANGED)
1. Formal Board Appointment Letter, 3-stage communication sequence, Case for Support: do not exist.
2. Bylaws now collected but wired to no generator.
3. Fundraising strategy does not receive recommitment responses or the whole-board summary.
4. activation_revised_strategy developer note still references "idea-by-idea approvals and disapprovals" although that data is no longer collected.
5. Recruitment org-level generators never see board member names/responses (only the powerhouse blueprint does).
6. Master intake is never passed directly — only via seeded/prefilled pathway intakes; fields not covered by MASTER_MAPPINGS (e.g., board_engagement, transformation_areas, bylaws_text) currently reach no generator.
7. Module numbering in GENERATION_TYPES does not always match the customer-facing stage (e.g., onboarding documents are module 5 internally, presented at Stage 6).
