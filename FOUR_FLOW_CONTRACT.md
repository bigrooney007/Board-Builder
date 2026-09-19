# Canonical Four-Flow Contract

This file is the routing contract for the launch application. A page may move forward only inside the flow that created its lead/payment/session.

## 1. Board Recruitment
`/` → `/recruit` → lead capture → `/recruit/walkthrough` → Stripe → `/purchase/success` → `/recruit/welcome?session_id=...` → four-question assessment and result → `/app/board-recruitment` → recruitment profiles/campaign.

Payment identity: offer_source `recruitment`, $497 entitlement. Recruitment onboarding rejects sessions belonging to the other three flows.

## 2. Board Fundraising Game
`/` → `/board-fundraising-game` → lead and fundraising-goal capture → `/game/demonstration` → Stripe → `/game/welcome?session_id=...` → paid Game at `/game/setup` → `/game/dashboard` → board invitations/group game/strategy/portfolios/execution.

Payment identity: offer_source `board_fundraising_game`, purchase_source `board_fundraising_game_497`.

The product demonstration replaces the former free-game sales experience. `/game/unlock` and `/game/upgrade` are compatibility redirects to `/game/demonstration`; they do not own a second sales page.

## 3. Strategic Planning
`/` → `/strategic-planning` → `/strategic-planning/video?token=...` → Stripe → `/strategic-planning/payment-confirmed?session_id=...` → `/strategic-planning/welcome?session_id=...` → `/strategic-planning/intake?session_id=...` → `/strategic-planning/dashboard?session_id=...`.

Payment identity: offer_source `strategic_planning`, purchase_source `strategic_planning_497`. Lead token, payment session, welcome, intake and dashboard must all resolve to Strategic Planning.

## 4. Board Recommitment
`/` → `/board-recommitment` → `/board-recommitment/video?token=...` → Stripe → `/board-recommitment/payment-confirmed?session_id=...` → `/board-recommitment/welcome?session_id=...` → `/board-recommitment/intake?session_id=...` → `/board-recommitment/dashboard?session_id=...`.

Payment identity: offer_source `board_recommitment`, purchase_source `board_recommitment_497`. Lead token, payment session, welcome, intake and dashboard must all resolve to Board Recommitment.

## Isolation rules
- Never infer a paid product from a generic fallback route.
- Never accept another product's lead token or Stripe session.
- A wrong-flow paid link must stop and return the user to that product's own root, not redirect into another product.
- Public participant links may open only the resource represented by their token.
- Main homepage product buttons point only to the four canonical roots above.
- Legacy/experimental flows are not part of this contract. The pre-hardening application is preserved at `archive/pre-four-flow-hardening-2026-09-19` for later developer cleanup or recovery.
