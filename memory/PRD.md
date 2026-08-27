# Nonprofit Board Builders — PRD

## Original Problem Statement
SaaS for nonprofit board building (React + FastAPI + MongoDB). Three funnels (Recruitment, Reactivation, Fundraising Activation) unified under the "Complete Board Fix System" ($497) umbrella funnel: Homepage -> Short Form -> Sales Page -> Checkout -> Master Intake -> Orientation -> Understand Board -> Reactivation -> Recruitment -> Activation. Master intake prepopulates secondary intakes; chronological Admin tracking dashboard.

## Status (June 2026)
- Complete Board Fix System fully coded. FULL FUNNEL E2E TESTING STILL PENDING per user's standing "do not test the funnel yet" directive.
- Stripe checkout MOCKED. AI generation via Emergent LLM key. Resend for emails.

## Recent changes (this fork)
- Site-wide centering audit requested, then CORRECTED to be scoped: `body.public-centered` class toggled by `PublicCenteringScope` in `App.js` for public/marketing routes only (/, /board-fix, /board-fix-intake, /board-fix-orientation, /recruit, /reactivate, /activate, /recruit/process, /*-with-rooney, /about-rooney, /offer/*). CSS scoped block at end of App.css. Admin, member app, forms, tables keep left alignment.
- Homepage (June 2026, latest): FULL COPY REPLACEMENT with exact user-provided copy. Sections now: Hero (Fix Your Board. Transform Your Organization. / consultant line / CTA) -> "Introduction" (2 paragraphs + CTA) -> "Become a Nonprofit Board Builder" (subheading, paragraph, RECRUIT/REACTIVATE/ACTIVATE pillars, CTA). Video embed removed earlier. Old boardFix* intro/list copy and mainVideo keys removed from siteContent.js home. Structure/design/nav/testimonials/footer untouched.
- Homepage: video embed REMOVED; intro restructured — 3 bold stacked heading lines (boardFixHeadings), "That includes:" + numbered list (1/2/3, .home-includes-list ol with CSS counters), corrected grammar ("This is why, at Nonprofit Board Builders, LLC..."), fixed "proccess"->"process", item 2 comma added.
- Fixed member-nav shrink bug (.member-nav width:100%).
- Testing iteration_57: all centering scope checks PASSED (frontend-only, no funnel testing). Homepage styling defects found there have been fixed (bold headings, numbered list) — user verifying preview personally, no screenshots allowed.

## Backlog
- P0: Full E2E testing of Complete Board Fix System (payment -> master intake -> orientation -> understand board -> reactivation -> recruitment -> activation, prepopulation, admin chronological tracking). BLOCKED until user gives go-ahead.
- P1: Verify master intake prepopulation across all 3 secondary pathways.
- P2: Insert real YouTube video IDs for Board Fix sales page + orientation/roadmap (user to provide). Homepage video was removed intentionally.

## Key files
- Backend: board_fix_routes.py, board_fix_master.py, reactivation_routes.py
- Frontend: components/LandingPage.jsx, content/siteContent.js (home.*), member/BoardFixOrientationPage.jsx, member/BoardFixRoadmapPage.jsx, member/BoardFixContinuation.jsx, admin/BoardFixSection.jsx, App.js (PublicCenteringScope), App.css (scoped centering + home-intro styles at end)

## Credentials
See /app/memory/test_credentials.md (admin rooney@nonprofitboardbuilder.com; member module-tester@example.com / ModuleTest123!)
