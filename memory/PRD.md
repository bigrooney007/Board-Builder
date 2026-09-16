# BOARD FUNDRAISING GAME — PRD

## Original Problem Statement
Zero-account, secure-link SaaS platform helping nonprofit boards build and execute fundraising strategies. Board members access everything via `/play/{token}` links — no accounts. Lead user pays $497 to unlock the full platform.

## Core Product (current state)
- **Individual Game**: strict 4 Strategic Areas × 3 screens (First Response → Think A Little Deeper Second Response → AI Fine-tune + Approve). Free-form text only, no voice UI, auto-play narration optional (missing audio never blocks).
- **Lead journey**: complete Individual Game → final approval → DIRECTLY to `/game/upgrade` checkout (two intermediary pages removed) → pay → `/game/setup` second form → submit → immediately to dashboard while Working Strategy generates async.
- **Dashboard order**: Working Fundraising Strategy box FIRST → Adopted/Complete Game Night → goal/status/Tutorial cards → Board Participation → Prepare For Fundraising Day/Night (meeting form, no top resource buttons) → Meeting Resources (Call Script / Facilitation Guide / Checklist — static content, no AI) → Group Game → Complete Your Board Meeting (transcript paste/upload → Compile Final Fundraising Strategy, async) → After Your Board Meeting output cards (Final Strategy / Board Portfolios / Execution Materials / Relationship Mapping with locked→meeting→generating→ready states, NO "Coming Soon") → Strategy History.
- **Tutorial**: in-app 10-step guided tour (DashboardTour.jsx, spotlight overlay, Back/Next/Exit/Finish). No video.
- **Strategy versioning**: every generation saved; StrategyPage has Version dropdown (newest first) + Download Strategy (PDF via reportlab, thin border all margins, no logo, cover → contents → sections). Prepared By: lead name (working) / "The Board of {org}" (final).
- **Final compile (schema_version 2)**: transcript + all data → one AI call → audience-specific KNOW/LIKE/TRUST/ASK/FOLLOW UP/STEWARD processes (Individuals/Businesses/Grantors only if identified), static Board Fundraising Process, team_roles with "ROLE / CAPACITY NEEDED", execution_resources, phased execution timeline (build system → 30-60d KLT → ~30d ask → follow up/steward; separate business & grantor timelines), board_priorities vs additional_board_ideas. Stored as mode "final", status "adopted" (unlocks portfolios/postgame send).
- **Group Game dedup fix**: canonical idea per normalized text (build, presentation, and compute_results merge via alias map); results display only ideas with selection_count > 0; unranked ideas retained in DB for final strategy.
- **Relationship Mapping**: board member form at `/relationship-mapping/{playToken}` (funder type, contact, how known, why match, 4 willingness checkboxes, Add Another). Lead view `/game/relationships` shows ALL entries + "Add My Relationships" (self-play token). Collection `game_relationships`.
- **Send Final Strategy To Board**: postgame send (manual click) — email per spec, button links to `/game/final/{memberToken}` → FinalStrategyMemberPage (strategy + See How I Am Involved → `/board-portfolio/{token}` + Complete My Relationship Mapping). Portfolio page also links to relationship mapping (play_token added to public portfolio API).
- **Execution Materials page**: `/game/execution-materials` lists every member's toolkit status.

## Architecture
- Frontend: React `/app/frontend/src/game/` — GamePlayPage, GameSituationPage, GameDashboardPage, StrategyCards, StrategyPage, strategyRender (v1+v2 sections), MeetingOutputs.jsx, DashboardTour.jsx, RelationshipMappingPage, RelationshipMapDashboardPage, FinalStrategyMemberPage, ExecutionMaterialsPage, GameNightSection, HostToolsSection.
- Backend: FastAPI — game_night_routes.py, game_finetune_routes.py, group_game_routes.py (dedup helpers dedupe_texts/dedupe_idea_docs), strategy_routes.py (prepared_by, /download route), strategy_pdf.py (two-pass TOC PDF), game_meeting_routes.py (transcript/compile-final/overview/relationships/member-final), meeting_review_routes.py (legacy review flow, untouched), portfolio_routes.py, postgame_routes.py (new email copy + /game/final link), host_tools_routes.py ([Meeting Date] token), host_tools_content.py (exact static Call Script/Facilitation/Checklist).
- Key endpoints: POST /api/game/meeting/transcript(+-upload), POST /api/game/meeting/compile-final, GET /api/game/meeting/overview, GET/POST /api/game/play/{token}/relationships, GET /api/game/relationships, GET /api/game/final/{token}, GET /api/game/strategy/view/{id}/download.
- Collections added: game_meeting_transcripts, game_relationships; game_strategy_jobs mode "final".

## Integrations
Stripe (payments), Claude via Emergent LLM key (strategy/fine-tune/compile), ElevenLabs (TTS, admin-generated clips), Resend (email).

## Constraints (CRITICAL for future agents)
- ABSOLUTE COST CONTROL: no automated tests, screenshots, ElevenLabs/AI/Stripe calls unless user explicitly authorizes. User tests manually in production.
- Do not touch Individual Game 3-screen flow/copy, checkout design, price, Group Game 4 areas, invitation architecture, voice/ElevenLabs config.
- Respond in English.

## Implemented (dates)
- 2026-06: Second Response save bug fix ($set/$setOnInsert conflict on `completed`).
- 2026-06: FULL dashboard/strategy/post-game/document workflow update (all 48 spec sections above). Backend restarted cleanly, frontend webpack compiled successfully. NOT functionally tested per user's no-testing rule — user will verify in production.

## Backlog
- User to generate 9 narration clips from Admin panel.
- User manual verification of: pre-checkout skip, post-payment redirect, dashboard tour, transcript→final compile, group game dedup, relationship mapping, PDF download.
