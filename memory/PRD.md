# Nonprofit Board Builders — PRD

## Original Problem Statement
SaaS for nonprofit board building (React + FastAPI + MongoDB). Three funnels (Recruitment, Reactivation, Fundraising Activation) unified under the "Complete Board Fix System" umbrella funnel. Master intake prepopulates secondary intakes; chronological Admin tracking dashboard. Manual founder engagement is intentional (founder sends all emails/forms themselves).

## Status (June 2026)
- Complete Board Fix System fully coded, INCLUDING the June structural update below. FULL FUNNEL E2E TESTING STILL PENDING per user's standing "do not test yet" directive.
- Stripe checkout MOCKED (test mode locally). AI generation via Emergent LLM key. Resend for emails.
- OPEN ITEM: Live production Stripe webhook (https://nonprofitboardbuilder.com/api/stripe/webhook) failing per Stripe (19 retries). Investigation so far: prod endpoint reachable, returns 400 "Invalid Stripe signature" → likely STRIPE_WEBHOOK_SECRET mismatch in prod env vs live Stripe webhook signing secret. Deployment scan also flagged: .gitignore blocks .env files (deploy blocker) + destructive startup migration in six_module_migration.py (delete_one/delete_many at startup). NOT yet fixed — user pivoted to structural update.

## June 2026 Structural Update (Complete Board Fix flow/pricing) — IMPLEMENTED, UNTESTED
1. Pricing: /offer/board-fix now shows Option 1 "Complete Board Fix System" regular $997, discounted $497 (50% OFF, 7 days) + Option 2 "Do It With Me" $5,497. All price text lives in siteContent.js offerSalesPages["board-fix"].options (configurable, not hardcoded in components).
2. DWM: new /api/payments/board-fix-dwm-checkout (549700¢, purchase_source board_fix_dwm_5497, env STRIPE_BOARD_FIX_DWM_5497_PRICE_ID). Same account/purchase-success architecture. After master intake, DWM customers are redirected to Calendly https://calendly.com/boardbuilder/recruitboard. board_fix_journeys.experience = "do_it_with_me"|"self_guided". Admin row includes experience.
3. Entitlements (member_routes): board_fix 497 & dwm_5497 both grant board_fix_system + recruitment_self_guided + reactivation_self_guided + activation_self_guided + recruitment_selection_onboarding (needed for recruitment modules 4-6 generators).
4. Canonical 10-step journey (board_fix_routes JOURNEY_STAGES + roadmap frontend): Orientation → Rebuild Your Present Board (reactivation all modules) → Identify (recr. mod 1-2) → Launch (3) → Select & Interview (4) → References & Background Checks (5) → Onboard (6) → Fundraising Planning (activ. mod 1-2) → Create Strategy (3) → Adopt (4) → Execute (5). needs_intake on identify/fundraising_planning stages.
5. References step: new generation types referee_confirmation_email, candidate_referee_request (includes secure /reference-form link when process exists); reference_request_email rewritten as Reference Check Email; ReferenceEmailsPanel added in module 5 UI (4 cards incl. reference_call_script). Conditional appointment preserved.
6. Onboard step: formal_appointment_email (Final Board Appointment Email) ADDED to GENERATION_TYPES (frontend card existed but backend type was missing = was broken). Reuses conditional_offer links block (onboarding materials/agreements/profile form links).
7. Gap analysis (powerhouse_board_blueprint): context now instructs founder counted as present board member + includes completed recommitment responses.
8. Strategy creation: approval/disapproval concept REMOVED — StrategyReviewPage idea Approve/Disapprove UI removed (plan displayed read-only + position/discussion/contribution retained); backend submit_review no longer validates/stores idea decisions; Module 4 approved/disapproved counters removed; revised-strategy prompt reworded. Strategy generated from planning responses + founder intake + framework (already the case).
9. Strategy email (activation_review_email) body: approval language removed; contains plan review link inline (copy/paste ready). Planning email already contains form link.
10. Execution (activation step 5): toolkit context includes all recommitment responses; per-member fundraising portfolio includes that member's recommitment response (matched by email).
11. Continuation links: Reactivation end → "Continue to Identify the Board Members You Need"; Recruitment end → "Continue to Fundraising Planning".

UNCHANGED: all direct-purchase funnels (recruitment/reactivation/activation), all existing generators, master intake form/fields, reference process automation, adoption flow, admin structure, orientation page.

## Earlier this fork
- Scoped public-page centering via body.public-centered (tested iteration_57, passed). Homepage copy replaced verbatim with user copy (hero/introduction/builder pillars); "Introduction" heading removed, first paragraph bolded. member-nav width fix.

## Backlog
- P0: Fix live Stripe webhook (confirm prod STRIPE_WEBHOOK_SECRET matches live endpoint secret; fix .gitignore .env blocking; make six_module_migration non-destructive) — awaiting user resume.
- P0: Full E2E testing of Complete Board Fix System incl. new 10-step journey, DWM flow, new emails — BLOCKED until user go-ahead.
- P2: Real YouTube IDs for board-fix sales video + orientation.

## Key files
- Backend: payment_routes.py (checkouts+webhook), member_routes.py (entitlements), board_fix_routes.py (journey/roadmap/admin), board_fix_master.py, ai_service.py (GENERATION_TYPES), workspace_routes.py (generate context), activation_planning_routes.py, content_templates.py
- Frontend: funnels/OfferVideoPage.jsx, content/siteContent.js, funnels/BoardFixIntakePage.jsx, member/BoardFixRoadmapPage.jsx, member/BoardFixContinuation.jsx, member/workspace/ApplicantModules.jsx, funnels/StrategyReviewPage.jsx, member/ActivationModule4.jsx

## Credentials
See /app/memory/test_credentials.md (admin rooney@nonprofitboardbuilder.com; member module-tester@example.com / ModuleTest123!)
