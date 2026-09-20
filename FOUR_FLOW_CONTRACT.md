# Canonical Four-Flow Contract

This file is the routing contract for the launch application. A page may move forward only inside the flow that created its lead/payment/session.

## 1. Board Recruitment
`/` → `/recruit` → lead capture → `/recruit/walkthrough` → Stripe → `/purchase/success` → `/recruit/welcome?session_id=...` → four-question assessment and result → `/app/board-recruitment` → recruitment profiles/campaign.

Payment identity: offer_source `recruitment`, $497 entitlement. Recruitment onboarding rejects sessions belonging to the other three flows.

## 2. Board Fundraising Game
`/` → `/board-fundraising-game` → lead and fundraising-goal capture → `/game/demonstration` → Stripe → `/game/welcome?session_id=...` → `/game/dashboard` → individual Game → schedule Game Night → board invitations → synchronized Group Game → final strategy → delivery → portfolios → relationship mapping and personal execution assistants.

Payment identity: offer_source `board_fundraising_game`, purchase_source `board_fundraising_game_497`.

The product demonstration replaces the former free-game sales experience. `/game/unlock` and `/game/upgrade` are compatibility redirects to `/game/demonstration`; they do not own a second sales page.

The Group Game has one host-controlled screen. Participants use the secure shared link without login and follow the host through funding audiences, where to find them, attraction, fundraising process, team, technology, materials, budget and execution. Private ranking and separate priority-review routes are not part of the customer flow. Meeting transcription plus every accumulated organization and Board input feed final strategy generation.

## 3. Strategic Planning
`/` → `/strategic-planning` → `/strategic-planning/video?token=...` → Stripe → `/strategic-planning/payment-confirmed?session_id=...` → `/strategic-planning/welcome?session_id=...` → `/strategic-planning/intake?session_id=...` → `/strategic-planning/dashboard?session_id=...`.

Payment identity: offer_source `strategic_planning`, purchase_source `strategic_planning_497`. Lead token, payment session, welcome, intake and dashboard must all resolve to Strategic Planning.

The dashboard contains Tell Us About Your Organization, participant forms, a synchronized Board review screen, deterministic facilitation guide, area delegation packs containing every relevant idea and transcript, editable Final Strategic Plan draft, founder approval, active delegation, leadership portfolios, personal leadership assistants and founder-confirmed follow-up meeting updates.

## 4. Board Recommitment
`/` → `/board-recommitment` → `/board-recommitment/video?token=...` → Stripe → `/board-recommitment/payment-confirmed?session_id=...` → `/board-recommitment/welcome?session_id=...` → `/board-recommitment/intake?session_id=...` → `/board-recommitment/dashboard?session_id=...`.

Payment identity: offer_source `board_recommitment`, purchase_source `board_recommitment_497`. Lead token, payment session, welcome, intake and dashboard must all resolve to Board Recommitment.

## Isolation rules
- Never infer a paid product from a generic fallback route.
- Never accept another product's lead token or Stripe session.
- A wrong-flow paid link must stop and return the user to that product's own root, not redirect into another product.
- Public participant links may open only the resource represented by their token.
- Customer dashboard navigation never exposes another product dashboard.
- Source-owned facilitation guides cannot be silently replaced by stale database content.
- Main homepage product buttons point only to the four canonical roots above.
- Legacy/experimental flows are not part of this contract. The pre-hardening application is preserved at `archive/pre-four-flow-hardening-2026-09-19` for later developer cleanup or recovery.
