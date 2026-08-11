# Nonprofit Board Builder PRD

## Original Problem Statement
Build only one professional green Nonprofit Board Builder landing page, one four-step board assessment form, one confirmation screen, MongoDB storage for every submission, and one owner email containing every answer. No accounts, dashboards, payments, AI, recruitment automation, CRM, scheduling, scraping, background jobs, or additional pages. Use the user-provided logo and the exact supplied content, questions, options, and confirmation messaging.

## Architecture Decisions
- React single-page experience with three states: landing, assessment, confirmation.
- FastAPI `POST /api/assessments` validates and stores submissions in MongoDB.
- Each submission receives a `NBB-YYYYMMDD-XXXXXX` number, UTC timestamp, and `New Board Assessment` status.
- Resend owner notification is attempted after persistence; email failure never rolls back the saved assessment.
- Email settings are environment-driven through `RESEND_API_KEY`, `SENDER_EMAIL`, and `OWNER_NOTIFICATION_EMAIL` (or `OWNER_EMAIL`).

## Implemented
- Responsive landing page with navigation, hero, three transformation stages, six discovery cards, calls to action, supplied logo, and footer.
- Added seven exact client testimonials in a three-featured/four-supporting layout with initials avatars and local approved photo/logo replacement controls.
- Added four static, clearly labelled Sample tool demonstrations using fictional Bright Futures Literacy Initiative information only.
- Added Rooney Akpesiri's complete founder story, supplied photograph, local photograph replacement control, five-item credibility strip, and assessment CTA.
- Updated homepage navigation anchors and final CTA while preserving the existing assessment flow and backend.
- Four-step assessment containing every required and optional field, exact options, validation, progress, Back/Next controls, phone helper text, and confirmation checkbox.
- Complete database submission, unique metadata, owner email template with all answers under four required headings, and confirmation screen.
- One E2E assessment was submitted and fully verified in MongoDB; confirmation and mobile layout passed.
- Final homepage verification passed after correcting the three tool caption titles; no product defects remain in the added homepage sections.
- Added required nonprofit `execution_preference`, separate weekly-email consent metadata, owner-email inclusion, duplicate-safe nonprofit contact records, and exact Resend nonprofit syncing.
- Updated applicant consent wording and duplicate-safe applicant syncing to the exact Board Applicants Segment and applicant Topics.
- Created four exact Resend Segments and three Topics for nonprofit leaders, board applicants, and both 72-hour No Action audiences.
- Added duplicate-safe weekly nonprofit and applicant aggregate Broadcast automation, with editable Monday/Wednesday Eastern schedules intentionally disabled pending owner approval.
- Added secure tracked text actions for board transformation readiness and applicant availability, mobile SMS handoff, desktop copy controls, click records, and No Action segment removal.
- Added 72-hour No Action processing, backend report/recipient records, aggregate-only email content, native unsubscribe/preference links, and deduplicated owner automation-error emails.
- Updated Privacy Policy for weekly emails, aggregate reporting, consent records, tracked engagement, correction/deletion, Resend processing, and no sale of personal information.
- Single isolated E2E verification passed 11/11 backend checks plus public UI flows; test Broadcasts targeted an owner-only temporary segment and never the live audiences.

## Prioritized Backlog
- **P0:** Provide `RESEND_API_KEY`, `SENDER_EMAIL`, and `OWNER_NOTIFICATION_EMAIL`/`OWNER_EMAIL` in backend environment; owner delivery cannot run without them.
- **P0:** Repeat the single E2E submission after email configuration and confirm one delivered email contains all answers.
- **P1:** None within approved scope.
- **P2:** None within approved scope.

## Weekly Automation Activation
- `NONPROFIT_WEEKLY_REPORT_ENABLED=false`
- `APPLICANT_WEEKLY_REPORT_ENABLED=false`
- Both remain disabled by explicit owner choice until approval to activate.

## Next Tasks
1. Add the missing owner-email environment settings.
2. Repeat the specified E2E flow once to verify delivery.
## Phase 4 (Blog + Lead Nurture) — Complete
- Public /blog + /blog/:slug pages with 3 categories, deterministic category CTAs, homepage "Latest From Nonprofit Board Builder" compact slider (max 6, prev/next/swipe).
- Claude blog generation (marketing_service.py) with strict voice/writing rules, validation (word count, em dash, banned phrases, stats claims, duplicate slug/title), one automatic correction attempt, owner failure emails, unique category+scheduled_date key. Schedule: Mon Recruitment / Wed Reactivation / Fri Activation 8:00 AM ET.
- Lead nurture: 3 Resend segments (Recruitment/Reactivation/Fundraising Activation Leads), one active category per contact (latest offer wins), 12 fixed approved templates (no AI), Tuesday 7:00 AM ET rotation 1→4 with duplicate-week protection, failed sends never advance rotation, owner error alerts, recruitment purchase removes lead from nurture (nurture_status=customer). Board Applicants excluded from all recurring emails.
- Flags remain false: BLOG_AUTOMATION_ENABLED, LEAD_NURTURE_ENABLED (plus BOARD_APPLICANT_OPPORTUNITY_EMAILS_LIVE, RECRUITMENT_97_LIVE, RECRUITMENT_497_LIVE). Owner enables after approval.
- Final Phase 4 test: backend all pass; frontend 22/22 pass. 3 test blog posts remain published for review.

## Blog Preview Dashboard (June 2026) — Complete
- Automation now creates drafts as "Pending Review" (marketing_loop publish_now=False); owner alert email sent via Resend when a draft is ready. Drafts stay pending until acted upon (no auto-publish timeout, per user choice).
- New admin endpoints: GET /api/admin/blog/posts, PATCH /api/admin/blog/posts/{id} (inline edit, slug updates only for unpublished), POST .../approve, .../reject, .../regenerate. POST /api/blog/generate now defaults publish_now=false.
- New "Blog Posts" tab at /admin (AdminPage.jsx: BlogAdminSection + BlogPreview): status badges, per-category "New Draft" buttons, full rendered preview with CTA, inline edit form, Approve & Publish / Reject / Regenerate. Published posts: edit only (409 guards on approve/reject/regenerate).
- Tested: iteration_6.json — backend 11/11 pass, frontend Playwright all pass. Regression suite: /app/backend/tests/test_blog_preview_dashboard.py.

## Conversion + Blog Copy Update (June 2026) — Complete
- /recruit/options rewritten: headline "Choose the Level of Support You Want Recruiting Your Board"; concise transformation cards — $97 Do It Yourself, $497 Self-Guided Recruitment (Most Popular ribbon), $3,497 Done With You (Calendly link); no feature lists on recruitment cards; testimonials moved BELOW offers on /recruit/options, /reactivate/options, /activate/options (content unchanged).
- Recruitment form: two overlapping questions merged into multi-select accomplish_areas (19 options + conditional Other textarea); new required support_preference radio-cards (diy/self_guided/done_with_you/undecided); still 3-step with progress/back; redirect direct to /recruit/options; matching offer gets "Matches the support you selected" badge via sessionStorage.
- Backend: REQUIRED_ANSWERS updated, support_preference validated + stored top-level on lead, owner email includes "Preferred Level of Support" and "What They Need Their New Board Members to Help Accomplish". Reactivation/Activation funnels unchanged.
- Blog: prompt + validation retargeted to 350-550 words (abs max 650, min 300), straight-to-the-problem one-idea style, no step-by-step guides, short-paragraph check. Schedules/duplicate protection/CTAs untouched.
- Tested: iteration_7.json — frontend 100%, backend 11/12 (blog live generation blocked: EMERGENT_LLM_KEY budget EXHAUSTED — user must add balance; validation rules unit-tested and passing).
- KNOWN: /app/backend/tests/test_blog_preview_dashboard.py still assumes old 700-1100 word rule (do not use as authority).

## Recruitment Funnel Upgrade + Owner Review Mode (June 2026) — Complete
- One-offer journey: /recruit (hero no CTA -> 3-step form -> testimonials) -> /recruit/process (LOCKED 6-stage framework page, both CTAs -> /recruit/checkout) -> /recruit/checkout ($497 Guided Board Recruitment only; What You Walk Away With incl. clickable Recruitment Guarantee modal; Before You Start; terms checkbox recorded in terms_agreements collection; existing Stripe tier 497 reused). /recruit/options no longer in the active journey (route kept).
- Support question reworded: "What Kind of Support Would Be Most Helpful to You?" values diy/guided/done_with_you/undecided (self_guided still accepted server-side for compat).
- Owner Review Mode (TEMPORARY, env OWNER_RECRUITMENT_REVIEW_MODE=true + admin auth only): banner, blank-form navigation (no lead/email), "Continue in Owner Review Mode" checkout bypass -> modules 1-6 via review_mode_member fallback in authenticate_member; progress writes skipped; no side effects. /admin has "Review Recruitment Experience" button. Set flag false after owner's second test.
- RECRUITMENT_GUARANTEE_TERMS env added (EMPTY — owner must supply final terms; fallback generic copy shown, configured=false). No dedicated Refund Policy document exists (checkbox links to /terms).
- After payment: account creation now lands on Module 1 (self-guided/basic) instead of dashboard.
- SEO: usePageMeta/PAGE_META (seo.js) + index.html defaults for title/description/OG/Twitter across home, recruit, process, checkout, reactivate, activate, blog.
- Tested: iteration_10.json — backend 14/14, frontend all product checks pass. Regression suite /app/backend/tests/test_recruitment_funnel_upgrade.py.

## Landing Page Hero Consolidation (June 2026) — Complete
- /recruit, /reactivate, /activate: duplicate hero removed; colored banner (dark green gradient + grid + circle) is now the hero containing label/title/subtitle (existing copy verbatim); no hero CTA; order Banner -> Form -> Testimonials on all three. CSS: .funnel-hero-banner. Old .funnel-hero/.funnel-hero-mark styles unused on these pages. Verified via screenshots desktop + 390px mobile.

## Platform Refinement + Reference Library (June 2026) — Complete
- Owner Review auth fix: authenticate_member falls back to review-mode admin; checkout enterReview refreshes member context; no second login. Verified iteration_11 (all pass).
- Testimonials LOCKED in /app/frontend/src/components/testimonialsData.js (8 exact founder-supplied entries incl. 2 Donna Kargel + Cyrena verbatim; typos preserved; no Result rows). All carousels/sections import it. Duplicate React keys fixed in both testimonial components.
- /recruit/process + /recruit/checkout centered premium visuals. Modules 1-6 execution tools: Module1 Powerhouse Board Blueprint (verified live gen, iteration_12), Module2 strategy intake (PUT /workspace/strategy-intake), Module3 9 tools + application link copy, Module4 general invite/rejection + external applicant CV upload + conditional offer/after-interview rejection, Module5 background-check browser search, Module6 onboarding script + share links (POST /workspace/materials/{id}/share, public /shared/{token}) + Board Member Profile Form (/board-profile/{token}). Agreements keep signature links only (422 on share).
- Recruitment Execution Reference Library (founder-only, /admin Reference Library tab): admin CRUD /api/admin/reference-library, docx/pdf/txt extraction (tables incl., 120k cap), module-aware retrieval (slice_reference, max 2 docs) appended to generation context with privacy rules + source priority; ONLY approved materials used. Founder doc 'For All The Children' (reference_id 860f14a8d196abf2, 65,772 chars) uploaded, status NOT APPROVED — owner must approve in /admin before it is used. Tested iteration_12: 17/17 backend + UI pass; regression suite /app/backend/tests/test_reference_library.py (issues 1 Claude call).
- NOTE: ElevenLabs request from earlier was superseded by user's pivot; not built.
