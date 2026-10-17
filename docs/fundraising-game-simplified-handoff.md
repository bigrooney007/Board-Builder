# Simplified Fundraising Game handoff

## Branch and preservation

Repository: `bigrooney007/Board-Builder`.
Development branch: `feature/fundraising-game-simplified`.

The branch was created from main `579183080608974dc60706799f41598d2564b2a6`.
That main was 50 commits behind the previously verified working branch. The existing
working services from `fix/planning-fundraising-current-flows-20261015` at
`0164b5baa45cc4a17f1375aad8caeb3af16b50cd` were brought into this development branch
with a normal merge. Neither main nor either historical deployment branch was updated.
No V2 platform was included. Existing documents, entitlements, private product routes,
questionnaire versions and customer records are retained.

No production deployment, production database access, customer-record migration,
real charge, real email delivery or applicant-network broadcast was performed.

## Customer journey and routes

1. `/`: The Fundraising Game, the supplied homepage copy and Rooney biography,
   existing typography, colors, founder image and original testimonial carousel.
2. The homepage CTA opens contact capture. Name, email and organization are saved.
   The form discloses product follow-up without an optional checkbox. New requests enter the five-email sequence; unsubscribe and historical opt-outs remain respected.
3. `/how-the-fundraising-game-works`: the supplied five steps, $497 one-time offer
   and existing 100% Guarantee. It also works as a shared direct URL.
4. Existing `/api/payments/game-checkout` creates a $497 Stripe payment. The existing
   success/account-claim page reuses captured details. Only verified payment grants
   a real entitlement. Existing paid clients are directed to their saved game.
5. `/game/setup`: fundraising goal, mission, annual budget, website and community.
   Partial organization and meeting information is saved independently of completion.
6. `/play/:token`: the same personal questionnaire for leader and board members.
   Five answers per audience, using Rooney’s detailed wording; repeat or skip individuals, businesses and grantmakers,
   then personal participation. Text, existing speech input, editing and resume remain.
7. The leader returns to setup only after completing their own ideas, then saves the
   meeting date/time/time zone/location or online link and invites board members.
8. `/game/dashboard`: own answers, invitations, submitted contributions, facilitation
   guidance, meeting access, strategy, approved portfolios and a help request.
9. `/game/group`: private facilitator controls and prompts. `/group-game/:token`:
   synchronized participant screens. Board proposals precede all leader proposals.
   Approve or disapprove each complete audience before moving forward. Preserve the
   original proposal, edited adopted wording, rejected decisions and accepted roles.
10. Review the agreed summary. Each participant records their own adoption; joined,
    absent and unacknowledged people remain distinct. Close the meeting and let people
    leave. On entering the Group Game, the leader is asked to enable the microphone.
    The request explains transcription and confirms that everyone has been informed
    and agrees before requesting browser access. Transcript text cannot override adopted decisions.
11. Closing prepares the final strategy from adopted information and sends the leader
    “Your Board's Fundraising Strategy Is Ready”. The workspace asks for brand colors,
    previews them and downloads the existing professional PDF. The leader is preparer.
12. Confirm or edit accepted responsibilities, then generate board portfolios. Each
    contains that person's original participation statement, agreed role, adopted
    approaches and practical worksheets/templates for that role. Review, edit, save
    and approve before sending. Copyable email, secure personal link, PDF, delivery
    status and explicit resend are available. Drafts cannot be publicly downloaded.

New games use a version field on existing records. Previously saved questionnaires
and dashboards continue to use their existing components and rules.
Old public offer pages redirect; historical private forms, session links and paid
purchase claims remain. Other new checkout offers return 410; existing payment
status, webhook and entitlement verification are retained.

## Administration

`/admin` uses existing administrator authentication. It contains:

- Board fundraising blog generation, with original articles/RSS retained.
- Independent authoritative homepage and How It Works text editors, including
  biography, CTA text, step explanations, purchase heading and guarantee wording.
- Paying customers and audited read-only inspection of organization details,
  invitations, contributions, meeting state, strategy and portfolios.
- Final-strategy downloads and workspace help requests with administrator notice.
- Identified leads, follow-up enrollment, delivery status, clicks and paid attribution.
- Date-range funnel counts and conversions, distinguishing page views from visitors.
- The five editable follow-up emails on days 3, 6, 9, 12 and 15. Per-email durable
  delivery keys, purchase stop checks and unsubscribe prevent unwanted duplicates. Existing opt-outs are not reversed.
- Protected legacy planning search/export and access to `/admin/legacy`.
- Client Testing: a fresh synthetic identity using the actual customer components.
  Checkout and email are captured safely. The workspace can add three sample board
  members, prefill their real questionnaires, and open personal links for testing.
  Group participation uses the actual shared session. Fresh tests clear previous
  lead state and member cookies so they cannot mutate an old real member session.

Legacy planning export prefers `original_response`, then `submitted_response`, then
saved `response`. It uses saved original question labels where available and preserves
full wording rather than generating a summary. The export identifies its source.
The actual For All the Children / Katherine or Catherine production record has NOT
been inspected here. Its presence and the availability of an unmodified original
submission must be confirmed in the protected admin search after approval/deployment.
The synthetic export test does not establish that production record's existence.

## Existing infrastructure reused

- Stripe checkout, verified claims, webhook and historical entitlements.
- Member/admin authentication, personal tokens, customer records and audit collection.
- Existing lead, analytics, CMS and Resend transport with durable delivery records.
- Audience questionnaire, speech/narration components, invitation and response tools.
- Shared Group Game sessions, participant device identities, polling and decisions.
- Existing microphone chunks, transcript persistence and document rendering.
- Existing strategy records, PDF renderer, portfolios and secure personal links.
- Existing design CSS, carousel, founder image, blog generation and RSS.

There are no AI-generated funding audiences or independent recommendations in this
journey. Document assembly preserves approved wording and recorded commitments.

## Verification

The CI workflow is `.github/workflows/simplified-fundraising-validation.yml`.
It uses disposable Mongo, synthetic organizations and contacts, the actual React
production build, the actual backend handlers, and substituted external providers.
It never loads production `.env` or connects to the production database.

Checks include:

- Backend HTTP journey: checkout adapter, unpaid denial, verified paid claim,
  idempotent repeat claim, captured organization details and retained setup progress.
- Shared five-question schema, legacy six-question compatibility, skip/repeat data,
  participant-first ordering and absence of unapproved content in final documents.
- Admin save/read/public content, authentication and exact original-response PDF.
- Draft resume, capped recovery, five durable marketing deliveries, shared-email
  duplicate protection, unsubscribe and verified-payment stop before account claim.
- Explicit adoption, recoverable meeting closure, branded PDF, confirmed roles,
  portfolio approval before send and duplicate delivery prevention.
- Existing planning/fundraising, finished-resource, recruitment, prepayment and
  historical route regression tests.
- Existing React journey tests, frozen-lockfile dependency install and production build.
- Initial HTML, canonical metadata, social images, sitemap and retired HTTP redirects.
- Playwright Chromium at 1440×1000 and 390×844, real customer pages, three participant
  browsers, private host prompts, live device updates, speech-event integration,
  individual adoption, strategy PDF, portfolio editing/approval/captured send,
  both admin editors and a fresh test after a previous member session.

CI artifacts include screenshots, walkthrough videos, browser results and server
logs. The Actions run for the final source commit is the authoritative result.
Any failed intermediate runs are retained as diagnostics, not counted as passes.

## Limits of verification

Real Stripe provider behavior, actual Gmail receipt, production credentials,
production database records, physical microphone recognition quality and every
previously paid customer's browser session have not been verified by these tests.
Speech events and email transport are substituted. “Sent” means provider acceptance,
not proof of inbox receipt. Admin simulations clearly show captured mail and no charge.
The public read-only availability check reports the currently deployed site only;
it does not prove this development commit has been deployed.

## Review and release

Review this feature branch and its CI artifacts. Do not merge, deploy or synchronize
without the owner's approval. No new preview-enablement environment flag is required.
The admin test uses existing administrator permissions and the same application flow.
After approval, synchronize the exact tested feature-branch SHA. Emergent should only
synchronize; the owner decides when to deploy. Do not synchronize an old V2 branch.

## Latest requested corrections

The homepage has four purchase-path buttons: after the heading/introduction, after
the main explanation, after the biography, and after the testimonials. Each opens
the same contact form. The follow-up checkbox is removed; the form discloses the
product follow-up, and every promotional email retains unsubscribe.

Both leader and participants see one detailed question at a time. They complete
one audience before adding another, proceed through individuals, businesses and
grantmakers, then explain how they want to help based on their own ideas. Earlier
saved optional audiences remain preserved and editable when present. Board-member
completion thanks them and explains the next board-meeting discussion.

The host is prompted for microphone access when entering an unfinished Group Game.
Browser denial and retry are supported. Participant consent is explained in the
request, and the transcript never overrides the group’s explicit decisions.
