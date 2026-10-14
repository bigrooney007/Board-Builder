# V2 verification record

## Current homepage-to-service wiring

The main homepage's four service buttons now lead to the corresponding education page. Each product page retains Start for Free and the established introductory questions. The customer path is main homepage → selected service education → Start for Free → existing intake questions → written roadmap → $197 purchase → resources and email-led actions. Homepage styling and copy are unchanged. Historical direct service/intake/customer links remain intact.

This wiring change passed **9/9 source-preservation/navigation checks**, **19 frontend source syntax checks**, Python browser-harness compilation and diff checks. The homepage preservation test permits exactly the four changed destinations and removal of the unused import, and requires the rest of its source and all homepage CSS to match the original base. The actual React browser harness now starts at `/`, clicks each service card, and follows Start for Free into its intake at desktop/mobile sizes. That updated browser traversal has not been run here because frontend dependencies/build and browser sandbox access remain unavailable. The previously passing 44 backend/API/security tests apply to the unchanged backend.

## Current deployment correction

V2 is enabled by default and does not require a preview password when none is configured. After the owner deploys the synchronized code, `/v2` and the four `/v2` product pages are directly accessible. Existing Stripe, email, AI, site-origin and session configuration is reused. Explicit disable, private-key and test-provider overrides remain supported. Paid resource and organization permissions remain enforced.

The current correction passed **44/44 synthetic backend/API/security tests**, **8/8 source-preservation checks**, **18 frontend syntax checks**, Python compilation and diff checks. Five new tests verify direct access without V2 environment setup, all four free intakes without preview login, private-resource denial, optional private-instance gating, existing site-origin fallback, and ordinary payment/transactional delivery defaults with mocked providers. No actual charge or email was sent. Previous browser/real-provider limitations remain as recorded below.

The following sections retain the results and limits of the earlier implementation and styling commits; their disabled/test-only defaults have been superseded by this correction.

The source is based on `d627263044f606a819366d3b04fe7e240b8e254d`. All examples and test records are synthetic. Payment, AI and email provider calls are replaced at their transport boundaries; no production database, real charge or real network broadcast is used.

| Check | Result |
| --- | --- |
| `python -m unittest discover -s backend/tests -p 'test_v2*.py'` | 39 passing service/API/methodology/security tests |
| `python tests/validate_v2_contracts.py` | 8 passing preservation/isolation checks |
| `node tests/validate_v2_frontend.cjs` | 18 actual frontend JS/JSX files parse successfully |
| `python -m compileall -q backend` | Pass |
| `git diff --check` | Pass |
| Existing standalone source-contract results against the exact base | Identical, including 8 pre-existing failing validators |
| Frontend production build and React/Jest tests | Not run: project dependencies unavailable |
| Actual desktop/mobile browser tests | Not run: actual frontend build unavailable |
| Real MongoDB/Stripe/Resend/AI integration | Not run: isolated provider configuration required |

Coverage includes four separate $197 purchases; original entitlements/purchases retained; payment replay/wrong amount/wrong journey/live-test isolation; 39 recruitment resources; exact saved branded PDF/DOCX/TXT approvals; edits requiring fresh approval; delivery retries using identical provider keys and bytes; confirmed campaign launch; application activation; isolated marketplace listing; application/CV/guide/invitation/rejection; registered opt-in network selection and permission rechecks; notification links without owner privileges for candidates; private fundraising drafts and multiple funding categories; overlapping audience proposals; explicit adoption and consent; mission retention; approved-only final plans; recommitment invitations/follow-ups/response-derived guide; worker recovery; noindex/no-store error headers; tenant permissions and token expiry/tampering; immutable source submissions; main homepage and original route/price/source preservation.

Actual provider delivery, model writing quality and complete browser acceptance are separate outstanding release checks. The fixture and commands in `nbb-v2-handoff.md` support those checks before any release authorization. Emergent's task is to synchronize the exact requested commit; deployment remains the owner's responsibility.

## Follow-up: typography and responsive layout

The owner supplied an Emergent report for `f799d9c85c63e5ce40fd4fbe6f5b4388d00afdab`: production frontend build passed, V2 React/Jest tests passed 17/17, and synthetic desktop/mobile checks passed 16/16. Those are reported results for that earlier commit, not independently rerun results for this style follow-up. Genuine Stripe/Resend/AI delivery and a usable isolated provider preview remain unverified.

This follow-up changes only V2 typography/layout and verification support. It sets body text to 16–18px, labels and inputs to at least 16px, important supporting text to 14px, and primary action targets to at least 48px. Page introductions, landing-page hero copy, important section headings, and document headings are centered. Longer instructions, submitted answers, and document bodies retain left alignment within centered columns. Removing repeated action-page side padding gives mobile forms more usable space. Long headings, links, and organization names wrap rather than forcing overflow. The original homepage and global application styles are unchanged.

| Follow-up check | Result |
| --- | --- |
| Existing source-preservation/isolation contracts | 8/8 passed |
| Frontend source parsing | 18 files passed |
| Python harness compilation and fixture preparation | Passed; 29 synthetic page-layout fixtures prepared |
| `git diff --check` | Passed |
| New Chromium CSS layout checks | Blocked: sandbox denies Chromium's socket operations; no passing result claimed |
| New full React build/browser acceptance | Not rerun: frontend dependencies/build unavailable locally |

`python tests/v2_layout_harness.py` checks the actual shared styles against synthetic layout markup at 320, 390, 768 and 1440px, with screenshots. Its scope is CSS sizing/alignment, not React behavior or full journeys. `v2_browser_harness.py` also uses the same sizing/alignment assertions against the actual built React landing, offer and resources pages. No live provider calls or customer data are involved.
