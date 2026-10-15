# Recovered Board Builder release preparation

Working branch: `fix/preserve-original-ui-editable-offers-20261015`.
Original recovery base: `d627263044f606a819366d3b04fe7e240b8e254d`.

## Application scope review

Every application change against the recovery base is confined to these files:

| Files | Purpose |
| --- | --- |
| `backend/clean_platform_routes.py` | Permit four payment-page keys in the existing content storage/API. |
| `frontend/src/admin/HomepageTextSection.jsx` | Add four payment editors, match recruitment defaults, preserve saved fundraising overrides, guard against stale loads and saves before loading. |
| `frontend/src/clean/platform.js` | Respect administrator text even when the fundraising content-version marker is older. Other products retain their existing default/override merge. |
| `frontend/src/content/offerTextDefaults.js` | Initial written explanations for the existing four payment pages. |
| `frontend/src/components/DemoOfferCards.jsx` | Optional editable explanatory headings; unchanged defaults for all other callers, prices, buttons and checkout callbacks. |
| `frontend/src/funnels/OfferTextRoadmap.jsx` | Centered, sequential written explanations using existing styling. Local display override prevents inherited two-column grid layout. |
| `frontend/src/funnels/RecruitmentHomePage.jsx` | Replace hardcoded overrides with matching defaults so saved text is visible. Layout and default public wording retained. |
| `frontend/src/funnels/GuidedProductPages.jsx` | Make existing landing section headings editable and replace only the two payment-page videos with editable text. Preserve questionnaires, purchase callbacks, prices and dashboards. |
| `frontend/src/funnels/RecruitWalkthroughPage.jsx`, `frontend/src/game/GameUpgradePage.jsx` | Replace payment-page videos with editable explanations; retain checkout handlers and pricing. |
| `frontend/src/member/RecruitCampaignSetupPage.jsx` | Save scheduling before navigating to materials; remove materials/launch from this page and retain a resume link. |
| `frontend/src/member/RecruitCampaignMaterialsPage.jsx` | Mount the existing application, five campaign resource cards and launch controls. Enforce prerequisites and return to the original applicants dashboard after launch. |
| `frontend/src/App.js` | Register only the separate materials route. |
| `frontend/src/pages/AdminPage.jsx` | Rename the existing editor tab and allow its direct admin link. |

All other added/changed files are narrowly scoped tests, test infrastructure or this document. The scope validator checks the complete changed-file list. The main homepage, CSS, testimonial component/content, questionnaires, dashboards, AI engines, payment services, entitlements and marketplace/network services remain byte-for-byte unchanged against the recovery base. No V2 modules are included.

## Access

- Existing landing pages: `/recruit`, `/board-fundraising-game`, `/strategic-planning`, `/board-recommitment`.
- Existing payment pages: `/recruit/walkthrough`, `/game/upgrade`, `/strategic-planning/video`, `/board-recommitment/video`. Existing journey authentication/tokens still apply.
- Existing admin: **Landing & Payment Text**, also `/admin?tab=homepages`.
- New resources route: `/app/board-recruitment/setup/materials`.

## Repeatable validation and its limits

Run the **Recovered Offer Validation** GitHub Actions workflow on the exact branch head. It installs frontend dependencies with `yarn install --frozen-lockfile`, builds through the existing `yarn build` command, executes original frontend journey regressions and new editor regressions, compiles the backend, runs relevant backend tests, and runs the production bundle in Chromium at 1440×1000 and 390×844.

Content tests use the real existing FastAPI routes, administrator JWT authentication and disposable MongoDB databases. They verify all eight keys, independent saves, public retrieval, unauthorized rejection and application recreation. Browser tests edit and reload all eight pages through the existing admin with real Mongo-backed content endpoints, test older fundraising versions, testimonials, existing Start for Free forms, original checkout handoffs, and recruitment profile approval/scheduling/materials editing/approval/launch navigation and retry behavior.

Customer API state and checkout/email/AI providers are substituted in browser tests. Separate backend tests execute the existing scheduling/publication handler bodies against disposable Mongo, substituting authentication, generated materials/readiness and outbound delivery. They verify scheduling validation and persistence, approval requirements, one publication record and duplicate-broadcast prevention. Live Stripe payment completion, AI quality, email delivery, live applicant-network delivery and a full live customer journey remain **unverified**. No real customer data, charges or network announcements are used. The unchanged dashboard's wider behavior is outside the narrow browser fixture.

Eight older static contract validators already fail identically on the original base and recovery branch: admin client testing, admin dashboard previews, admin preview fixtures, dashboard audio, fundraising clean-house, platform communications, recruitment clean-house, and strategic-planning clean-house. These pre-existing failures are outside the three authorized improvements; their validators and unrelated application features have not been rewritten. The older Clean House Validation workflow may therefore remain red on a pull request independently of the scoped validation result.

## Sync and history

At review time GitHub `main` was `579183080608974dc60706799f41598d2564b2a6`, an ancestor of this recovery branch. Its existing code is retained through the original base. The last Emergent sync confirmed in the conversation was the separate V2 branch at `dc9b01259f7fe56dc51a09e660eebd67798fb652`. Its current external configuration is not exposed by GitHub and cannot be certified from repository metadata.

Do not merge the V2 branch into this recovery branch or cherry-pick recovery changes into V2 and call that a recovery. Keep any merge into the deployment branch pending until its identity is confirmed. A direct sync can explicitly select the recovery branch and exact reviewed commit without changing another GitHub branch. Preserve Emergent environment settings and customer records. Sync and deployment are initiated by the owner; this work does neither.
