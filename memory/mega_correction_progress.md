# Mega-Correction Progress Tracker (June 2026)
User stacked 4 authoritative instructions. Work in phases; update this file as phases complete.

## PHASE 1 — Canonical Videos: DONE (needs verification)
- CANONICAL_COURSE_VIDEOS in /app/backend/course_content.py: explicit (product, module) → youtu.be URL for recruitment_self_guided/basic 1-6, reactivation_self_guided 1-5, activation_self_guided 1-5. Authoritative override in course_routes.merged_course (db fallback).
- Reactivation module 5 video un-hidden (ReactivationCoursePages.jsx).
- Homepage main video lbz713woSB4 added after home-intro section (LandingPage.jsx, siteContent home.mainVideo, .home-video-section CSS).

## PHASE 2 — DWY $5,497 pricing: DONE (needs verification)
- payment_routes.py: 3 DWY resolvers → new env keys STRIPE_DIRECT_BOARD_{RECRUITMENT|REACTIVATION|ACTIVATION}_5497_PRICE_ID (unset), new lookup keys *_5497, unit_amount 549700; txn amounts 549700. DIY untouched (49700). purchase_source keys unchanged (claim routing safe).
- siteContent.js: all $1,997/$2,497 → $5,497 (offerSalesPages reactivation dwy price+button, activation dwy price, legacy page texts).
- Legacy funnel components updated: ReactivateWithRooneyPage, RecruitWithRooneyPage, BoardRecruitmentProposalPage, BoardReactivationProposalPage, BoardActivationProposalPage, ActivateWithRooneyPage (removed $3,997 strikethroughs).

## PHASE 3 — NEXT STEP completion: DONE (all 3 flows: CoursePages, ReactivationCoursePages, ActivationCoursePages — single NEXT STEP completes + advances; Mark-Complete removed; recruitment last→results, activation last→my-fundraising-board)

## PHASE 4 — RECRUITMENT correction: DONE (core items)
- M1: already no resource (training card only). M2: KnownInfoSummary ("What We Already Know") removed; only board list generator (+ conditional ask-only-if-missing org/mission fields kept as backend 422 guard). M3: exactly 5 resources (linkedin_post removed from UI; application panel + 4 generators + existing publish flow kept). M4: external applicant Name+CV ONLY, placed FIRST before applicant list (backend already email-optional). M5: verbose CandidateStatusList + hints removed; BackgroundCheckPanel record removed (search-nearby button kept); START REFERENCING label; reference panel no longer gated on profile form; ConditionalPanel checklist/locks removed; backend 409 doc-gating for conditional_offer REMOVED in workspace_routes.py (links included only for approved/existing resources). M6: stripped to Onboarding Facilitation Guide + FirstMeetingPanel (date/time/format/link/location + invite email + recipient send); members/prepared-resources/Your-Board panels removed.
- Prompts: ai_service GENERATION_TYPES already resource-specific per type (schemas/tone/no-invent) — compliant with spec §32-34. Agreements already signable via /sign/{token} (typed/drawn/uploaded, versioned, immutable).

## PHASE 7 — Global founder email signature: DONE for recruitment context (build_org_context FOUNDER CONTACT block + SYSTEM_MESSAGE EMAIL SIGNATURE RULE in ai_service). PARTIAL: reactivation/activation context builders not yet injected with FOUNDER CONTACT (their prompts already sign with founder name/org; verify + extend later).

## PHASE 5/6 — Reactivation & Activation specs: LARGELY PRE-EXISTING (bylaws upload + resignation-email bylaws usage already implemented in reactivation_intake_routes.py + reactivation_routes.py:1198; recommitment form/email w/ auto link, roster, interpret, call scripts, follow-up outcomes, activation planning/sync/review/strategy/adoption/conclusion/status/portfolios/toolkit all exist per PRD). REMAINING TO VERIFY/GAP-FILL: founder signature injection in reactivation/activation email contexts; M1 no-resource check in both flows; link automation checks.

## PHASE 4 — RECRUITMENT correction (huge spec): TODO
Key points: M1 no resource/no intake panels; M2 only Board Member Recruitment List + remove "What We Already Know About Your Organization"; M3 exactly 5 resources (application form, job post, social post, recruitment email, referral email); M4 outside applicant Name+CV only FIRST then applicant list, per-applicant Generate Interview Guide, interview invite + rejection emails; M5 remove status block, START REFERENCING flow (email confirm → reference form link), background check = search button only, onboarding details (date/time/location) input, 6 doc generators + conditional appointment (NOT blocked by refs/background, auto-includes approved secure links + onboarding details) + after-interview rejection; M6 only facilitation guide + meeting details + invite email (remove applicant names + old materials). Resource-specific prompts in ai_service.py. Admin manual applicant add must work (Name+CV).
Files: member/workspace/WorkspaceModules.jsx, ApplicantModules.jsx, Module1Profile.jsx, MaterialCard.jsx; backend workspace_routes.py, workspace_service.py, ai_service.py.

## PHASE 5 — REACTIVATION spec: TODO
Bylaws upload on intake (stored, used for resignation email); global email signature (founder name/title/email/phone auto in ALL generated emails app-wide); M1 nothing; M2 recommitment form gen (review/approve→secure link) + email w/ auto link; M3 respondent list VIEW/INTERPRET RESPONSE + approve; M4 per-member GENERATE CALL SCRIPT (approve/download); M5 GENERATE FOLLOW-UP notes → outcome-specific: board portfolio / advisory portfolio / bylaws-based resignation email. NEXT STEP everywhere.
Files: member/ReactivationCoursePages.jsx, backend reactivation_routes.py, reactivation intake routes, ai_service.

## PHASE 6 — ACTIVATION spec: TODO
M1 nothing; M2 planning form + email (auto link + signature); M3 respondents + synchronized plan + review link + review email; M4 strategy plan gen/approve + adoption meeting fields + adoption email (auto details+link) + facilitation guide + KEEP conclusion + KEEP status; M5 per-member fundraising portfolio; dashboard: strategy + portfolios + intro email / social post / direct ask email+text generators. NEXT STEP.
Files: member/ActivationCoursePages.jsx, MyFundraisingBoardPage.jsx, backend activation_* routes, ai_service.

## PHASE 7 — Global email signature requirement (applies to ALL flows) — implement once in ai_service/generation context.

## PHASE 8 — TESTED: iteration_50.json backend 100% (11/11) + frontend 100%. Copy fixes applied post-test (appContent.js: NEXT STEP wording in recruitment M1 body + reactivation Step 1; unused markStepComplete removed). purchase_source 'direct_board_activation_project_2497' KEPT INTENTIONALLY (renaming would break PurchaseSuccess claim mapping; amount is 549700). NOT DEPLOYED.
