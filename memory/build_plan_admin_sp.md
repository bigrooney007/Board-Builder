# Build Plan — Admin Service Delivery + Content Centralization + Strategic Planning (June 2026)

USER RULES: Build everything first. NO testing until complete. NO emails. NO deploy. Reuse existing engines (forms, secure links, AI gen, PDFs, notifications). Report BUILD STATUS format at end, then STOP.

## Phase 0 (carryover — deployment blocker)
- six_module_migration.py REWRITTEN (crash-safe: legacy_module_number reconstruction, temp-offset recovery, deterministic video rebuild, flag-guarded materials). VERIFY: scratch-DB sim + preview boot. Also fix preview data: course_videos recruitment_self_guided module 6 youtube_url empty -> fdjjsiEnfWc.

## Phase 1 — Backend
- member_auth.py: admin operate-as support (header X-Operate-As, admin JWT, target member must have operator_accessible flag OR be owner-review-admin).
- Extend review-mode test member entitlements to all 3 products (recruitment_self_guided, reactivation_self_guided, activation_self_guided) => Admin Test Product Journey.
- NEW admin_service_routes.py: GET /api/admin/dwm-clients (verified DWM purchases 3 products + intake status + workspace status); POST /api/admin/dwm-clients/{purchase_id}/workspace (idempotent operator member creation, entitlement per product, NO accountability/nurture enrollment).
- NEW strategic_planning_routes.py (admin-only + public token routes): sp_projects, sp_participants, form upload (reuse reference-library extraction) -> hosted form edit/save/approve, secure participant links, prepared email + manual send, responses + notification, foundational plan async AI gen -> edit/save/approve, board review & refinement links (4 choices + comments per area), finalize foundational, areas + AI suggest owner + assignment, area development pack gen + secure link + plan submission (text/upload), adoption conclusions, final strategic plan assembly + PDF.
- server.py: include new routers.

## Phase 2 — Frontend
- AdminPage.jsx: sections "Test Product Journey" (3 buttons), "Do-With-You Clients" (list + OPEN CLIENT WORKSPACE), "Strategic Planning" (link/tab).
- Operator mode: operator context (sessionStorage emergent_operate_as + banner), axios header injection where member API calls made (member auth layer).
- admin/StrategicPlanningPage.jsx (projects list + project workspace with staged flow).
- Public: StrategicPlanningFormPage (/strategic-planning-form/:token), StrategicPlanReviewPage (/strategic-plan-review/:token), AreaPackPage (/area-pack/:token).
- App.js routes.

## Phase 3 — Content centralization
- frontend/src/content/siteContent.js — verbatim copy for: homepage, about-rooney, board-transformation, recruit + recruit-with-rooney + recruit DIY + recruit proposal, reactivate set, activate set, 3 start-here pages, major CTAs/guarantees. Page components import from it. NO copy changes.
- Module headings already centralized backend (course_content.py). Email templates already centralized backend (marketing_service.py etc.) — note as satisfied.

## Status log
- [ ] Phase 0 verify
- [ ] member_auth operate-as
- [ ] admin_service_routes
- [ ] strategic_planning_routes
- [ ] server wiring
- [ ] Admin UI sections
- [ ] StrategicPlanningPage
- [ ] public SP pages
- [ ] App routes
- [ ] content centralization (list pages done individually)
