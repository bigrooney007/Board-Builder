# CLEAN HOUSE CONTRACT

This document is the routing and product-boundary contract for the simplified Nonprofit Board Builder application.

## 1. Public House

The clean public house has six home pages:

| Home page | Canonical route |
|---|---|
| Main Home Page | `/` |
| Board Recruitment | `/recruit` |
| Board Fundraising Game | `/board-fundraising-game` |
| Strategic Planning | `/strategic-planning` |
| Board Recommitment | `/board-recommitment` |
| Let's Organize Your Board Fundraising Game | `/organize-board-fundraising-game` |

The Main Home Page is the shared entry point for the product house.

The four paid Board Builder pathways do not cross-link to one another. The only product-to-product exception is the existing link from the Board Fundraising Game home page to Board Recruitment at `/recruit`.

Legacy public offers may remain in source while they are being retired, but they must not be restored to the clean live router unless the product contract is intentionally changed.

## 2. Four Paid Board Builder Pathways

### Board Recruitment

`/recruit`
→ contact capture
→ `/recruit/walkthrough`
→ Stripe
→ `/purchase/success`
→ `/recruit/welcome?session_id=...`
→ `/app/board-recruitment`

The present recruitment dashboard and the public/support routes it requires remain available until that dashboard is rebuilt separately.

### Board Fundraising Game

`/board-fundraising-game`
→ contact/profile capture
→ `/game/demonstration`
→ Stripe
→ `/game/welcome?session_id=...`
→ `/game/dashboard`

The present game dashboard and the routes required to use the Game remain available until that dashboard is rebuilt separately.

### Strategic Planning

`/strategic-planning`
→ contact capture
→ `/strategic-planning/video?token=...`
→ Stripe
→ `/strategic-planning/payment-confirmed?session_id=...`
→ `/strategic-planning/welcome?session_id=...`
→ `/strategic-planning/dashboard?session_id=...`

The present Strategic Planning dashboard and its participant/session/public-plan routes remain available because an active organization is using this product.

### Board Recommitment

`/board-recommitment`
→ contact capture
→ `/board-recommitment/video?token=...`
→ Stripe
→ `/board-recommitment/payment-confirmed?session_id=...`
→ `/board-recommitment/welcome?session_id=...`
→ `/board-recommitment/dashboard?session_id=...`

The present Recommitment dashboard and the public member response/portfolio routes it requires remain available until that dashboard is rebuilt separately.

## 3. Facilitated Board Fundraising Game

`/organize-board-fundraising-game`
→ `/organize-board-fundraising-game/apply`
→ successful application confirmation: “We have received your application and will be in touch through email.”

This pathway stops after the application. It does not enter Stripe and it does not have a customer dashboard.

## 4. Board Applicant Network

Canonical route: `/join-a-board`.

The Board Applicant Network remains independent of the four paid pathways.

Required behavior:

1. A professional submits the Board Applicant Network application.
2. The complete applicant profile is saved in the admin backend.
3. The applicant receives the existing confirmation email.
4. The admin can inspect individual profiles and export applicant data.
5. When a nonprofit launches a live Board Recruitment opportunity, eligible consenting Board Applicant Network members receive the existing opportunity broadcast with their personalized application route.

Do not replace the existing applicant/opportunity backend with a parallel applicant database or parallel mailing system.

## 5. Eight Platform Videos

Each paid pathway has exactly two top-level funnel videos:

| Product | Demonstration | Onboarding |
|---|---|---|
| Board Recruitment | `recruitment_demonstration` | `recruitment_welcome` |
| Board Fundraising Game | `game_homepage` | `game_welcome` |
| Strategic Planning | `strategic_planning_demonstration` | `strategic_planning_welcome` |
| Board Recommitment | `board_recommitment_demonstration` | `board_recommitment_welcome` |

The admin video area manages these eight entries from one registry.

## 6. Six Home Page Content Sources

The admin home-page editor manages content for the six public home pages listed in Section 1.

Routes, payment destinations, dashboard destinations and the Board Fundraising Game → Board Recruitment exception are structural and must not be editable as marketing copy.

## 7. Admin House

The simplified visible admin navigation contains:

1. 4 Board Builder Pathways
2. 8 Platform Videos
3. 6 Home Page Text
4. Platform Analytics
5. Board Applicant Network
6. Strategic Planning

The Four Board Builder Pathways area must continue opening isolated preview sessions for the four real customer dashboards.

The active Strategic Planning admin workspace is preserved.

Legacy admin code may remain in source while it is being retired, but it should not be restored to the visible admin navigation unless deliberately reintroduced.

## 8. Analytics Contract

The clean analytics layer tracks the following separately by flow:

- unique visitors to each canonical home page
- people who submit contact/application details
- demonstration and onboarding video viewers
- average watch percentage for each of the eight videos
- checkout-start activity
- actual Stripe sessions and paid Stripe transactions by canonical product source
- unique dashboard entries
- unique recorded platform completions
- average active platform use per tracked user

Completion events are tied to meaningful product outcomes:

- Board Recruitment: final Board appointment confirmation
- Board Fundraising Game: Game completion route
- Strategic Planning: final Strategic Plan approval
- Board Recommitment: all recorded Board Member conversations have an outcome and conclusion

Analytics must not combine payment records across products.

## 9. Dashboard Rebuild Boundary

The clean public house, sales/payment paths, onboarding paths, admin controls and analytics foundation are the shared base.

Board Recruitment is now the first dashboard rebuilt on top of that base. Its canonical customer journey is:

1. Answer the Six Recruitment Questions.
2. Review, edit and approve the exact Board Member profiles the organization needs.
3. Review the Board Application and recruitment campaign materials prepared from the approved profiles.
4. Launch the recruitment campaign.
5. Review applicants and add outside applicants when needed.
6. Move applicants into Interviews by generating an interview invitation.
7. Generate a tailored interview guide for each interview candidate.
8. Run Reference Checks for candidates whose interview guide has been generated.
9. Use local Background Check search options when the organization chooses to conduct one.
10. Set the onboarding date/time, approve the organization-level onboarding materials and prepare the appropriate conditional or unconditional appointment email.
11. Facilitate the live onboarding session with presenter notes and a synchronized participant screen.
12. Review and approve each person's Board role before generating a Board Member Portfolio and a separate email draft for the founder to send from their own inbox.

The six Recruitment Questions are the authoritative strategic input for the Recruitment dashboard. Campaign assets are generated only from founder-approved Board Member profiles. Candidate progression is action-driven so the next stage unlocks from meaningful founder actions rather than manual card-moving.

The Board Fundraising Game, Strategic Planning and Board Recommitment dashboards remain separate rebuild phases and must not be redesigned implicitly while working on Recruitment.
