# Product Flow and Ownership Audit

Audited against the launch application after baseline
`87818e7e18593ee7735de7f5f1b2574d3e8f8197`.

| Product/page | Route and component | Content owner | Submission/API | Next route | Access boundary |
|---|---|---|---|---|---|
| Main homepage | `/` → `MainHomePage.jsx` | Same component | None | Four explicit product roots | Public |
| Recruitment homepage | `/recruit` → `RecruitFreePage` + `RecruitmentHomePage` | `siteContent.js/recruitmentHomeContent` | `POST /api/recruit/free/start` | `/recruit/walkthrough` | Public lead capture |
| Recruitment demonstration | `/recruit/walkthrough` → `RecruitWalkthroughPage` | Same component; narration from Voice settings | `POST /api/payments/checkout` | Stripe → `/purchase/success` | Valid Recruitment lead ID |
| Recruitment onboarding | `/recruit/welcome` then `/recruit?onboarding=1` | `RecruitWelcomePage` and `RecruitFreePage` | Four paid answers under `/api/recruit/free/...` | `/app/board-recruitment` | Recruitment payment contract, authenticated claimed purchase |
| Recruitment workspace | `/app/board-recruitment` → `BoardRecruitmentPage` | Component plus workspace APIs | Recruitment workspace APIs | Six execution sections | Recruitment entitlement only |
| Game homepage | `/board-fundraising-game` → `GameHomePage` | `backend/game_routes.py/DEFAULT_CONTENT` | `POST /api/members/game-free-start` | `/game/demonstration` | Secure guest session; existing accounts must log in |
| Game demonstration | `/game/demonstration` → `GameDemonstrationPage` | Component; video key `game_homepage` | `POST /api/payments/game-checkout` | Stripe → `/game/welcome` | Authenticated member session; no entitlement granted here |
| Paid Game welcome | `/game/welcome` → `GameWelcomePage` | Component; video key `game_welcome` | `POST /api/game/claim` | `/game/setup` | Stripe payment reverified; Game entitlement required afterward |
| Paid Game and dashboard | `/game/setup`, `/play/:token`, `/game/dashboard`, downstream Game routes | Game source files and controlled Game content APIs | Game APIs | Dashboard, invitations, group review, strategy and portfolios | Game entitlement on protected owner APIs; token-scoped board links |
| Strategic Planning landing/video | `/strategic-planning` and `/strategic-planning/video` → guided product pages | `GuidedProductPages.jsx/CONFIG` | `POST /api/guided/lead`, then `POST /api/payments/guided-checkout` | Payment-confirmed → welcome → intake | Strategic lead token and `strategic_planning_497` payment contract |
| Strategic Planning workspace | `/strategic-planning/dashboard` plus participant/review/plan routes | Strategic Planning components and APIs | `/api/strategic-planning/...` | Draft, review, delegation, final plans and portfolios | Strategic session and token boundaries |
| Board Recommitment landing/video | `/board-recommitment` and `/board-recommitment/video` → guided product pages | `GuidedProductPages.jsx/CONFIG` | Guided lead and checkout APIs | Payment-confirmed → welcome → intake | `board_recommitment_497` contract; existing accounts log in |
| Board Recommitment workspace | `/board-recommitment/dashboard` plus token forms | `BoardRecommitmentDashboard` and Reactivation APIs | `/api/reactivation/...` | Interpretation, conversations, outcomes and materials | Authenticated linked member and Recommitment entitlement |
| Facilitated Game | `/organize-board-fundraising-game` → `FacilitatedGamePage` | Same component | Application route | `/organize-board-fundraising-game/apply` | Public; no checkout |
| Facilitated application | `/organize-board-fundraising-game/apply` → `FacilitatedGameApplicationPage` | Same component | `POST /api/facilitated-game-application` | Application confirmation; follow-up through email | No payment; persisted application |

## Deterministic ownership decisions

- The Game homepage reads only versioned `DEFAULT_CONTENT`. Historical
  `marketing_settings.game_site_content` values cannot override a deployment.
- The obsolete Admin homepage editor was removed. Its former write endpoint
  remains as an authenticated HTTP 409 guard so stale clients cannot recreate
  competing ownership.
- Game videos remain deliberately admin-editable under `flow_videos`; copy and
  video URLs have separate owners.
- `/game/unlock` and `/game/upgrade` are compatibility redirects to the single
  product demonstration. Checkout cancellation and unpaid lifecycle links use
  that same destination.
- The four primary payment contracts remain separate:
  `recruitment_497`/`recruitment_self_guided_497`,
  `board_fundraising_game_497`, `strategic_planning_497`, and
  `board_recommitment_497`.
- The facilitated application has no Calendly redirect. It confirms receipt and
  tells the applicant that the team will follow up through email.

## Known launch limitations preserved

- Strategic Planning detailed-plan editing remains textarea-based.
- Product video placeholders remain where no video URL has been supplied.
- Recruitment cross-device onboarding recovery still depends on the browser's
  local assessment token.
- Source review and builds do not replace live production journey testing.
