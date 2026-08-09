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
