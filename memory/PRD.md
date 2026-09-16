# BOARD FUNDRAISING GAME — PRD

## Original Problem Statement
Zero-account, secure-link SaaS platform helping nonprofit boards build and execute fundraising strategies. Board members access everything via `/play/{token}` links — no accounts.

## Core Product (current state)
- **Individual Game**: strict sequential guided flow. 4 Strategic Areas × 3 screens each:
  1. Why it matters + First Question (First Response — one free-form textarea)
  2. Teaching + Stronger Question "Think A Little Deeper" (Second Response — one free-form textarea)
  3. AI Fine-tuning + Approval (USE THIS / KEEP MY ORIGINAL)
- No voice input, no audio controls, no "Add Another" buttons. Narration auto-plays in background if clips exist; missing audio NEVER blocks gameplay.
- After approval, backend AI extracts structured data (People/Businesses/Grantors, Places, Attraction Ideas, Process) from free-form text for downstream Group Review.
- **Group Review Game**: silent — no voice, no audio, no fine-tuning.
- ElevenLabs TTS: Test/Live voice environments, 9 static narration clips, admin-triggered generation only.

## Architecture
- Frontend: React — `/app/frontend/src/game/GamePlayPage.jsx`, `FineTuneReview.jsx`
- Backend: FastAPI — `game_night_routes.py` (play/save routes), `game_finetune_routes.py` (AI extraction), `voice_routes.py`, `voice_content.py` (9 scripts)
- DB: MongoDB — `game_board_members` (tokens), `game_section_responses` (per-section answers: `first_response`, `final_response`, `extras.second_response`, `fine_tuning`), `game_nights`, `game_profiles`
- Key endpoints: `GET/PUT /api/game/play/{token}/section/{id}`, `POST /api/game/play/{token}/section/{id}/complete`, `POST /api/game/finetune`

## Integrations
- Stripe (payments, user key), Claude via Emergent LLM key (fine-tuning), ElevenLabs (TTS, user key), Resend (email, user key)

## Implemented (dates)
- Game V3 simplification + AI fine-tuning integration
- Voice-guided narration architecture (ElevenLabs, Test/Live envs, admin generation)
- Individual Game rebuild: 3-screen loop per area, free-form text boxes, auto-play audio, voice-input removal
- **2026-06: BUG FIX — Second Response save failure.** Root cause: `save_section()` in `game_night_routes.py` had `completed` in both `$set` and `$setOnInsert` of the same Mongo update → write conflict → 500 on every `/complete` call. Fixed by always setting `completed` in `$set` (True when completing, else preserve existing) and removing it from `$setOnInsert`. Verified with single local curl: `/complete` returns 200 with free-form "Job creators". Fix covers all 8 First/Second responses across the 4 areas plus the section-5 participation "COMPLETE MY GAME" save.

## Constraints (CRITICAL for future agents)
- ABSOLUTE COST CONTROL: no automated tests, no screenshots, no ElevenLabs/AI/Stripe calls unless user explicitly authorizes. User tests manually in production.
- Do not redesign, do not refactor, do not re-add voice input or audio controls.
- Respond in English.

## Backlog / Upcoming
- User to generate the final 9 narration clips from Admin panel (manual)
- User manual verification of full Individual Game flow in production after redeploy
