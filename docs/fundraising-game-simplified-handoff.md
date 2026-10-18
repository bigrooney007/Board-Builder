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
3. `/how-the-fundraising-game-works`: the supplied four steps, $997 one-time offer
   and existing 100% Guarantee. It also works as a shared direct URL.
4. Existing `/api/payments/game-checkout` creates a $997 Stripe payment. The existing
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
   guidance, meeting access, strategy download/sharing and a help request.
9. `/game/group`: private facilitator controls and prompts. `/group-game/:token`:
   synchronized participant screens. Board proposals precede all leader proposals.
   Approve or disapprove each complete audience before moving forward. Preserve the
   original proposal, edited adopted wording, rejected decisions and accepted roles.
10. Review the agreed summary. Each participant records their own adoption; joined,
    absent and unacknowledged people remain distinct. Close the meeting and let people
    leave. On entering the Group Game, the leader is asked to enable the microphone.
    The request explains transcription and confirms that everyone has been informed
    and agrees before requesting browser access. Transcript extraction proposes source-quoted additions under the appropriate
    audience/question. Each addition requires explicit facilitator confirmation.
    New audiences remain pending until separately approved. Rejected contributions
    stay excluded. Manual transcript review remains available if the provider fails.
    A changed transcript requires a fresh review before strategy adoption.
11. Closing prepares the final strategy from adopted information and sends the leader
    “Your Board's Fundraising Strategy Is Ready”. The workspace asks for brand colors,
    accepts a PNG/JPEG logo, previews the branding and downloads the professional PDF.
    A secure approved-strategy link and copyable board email are provided. This is
    the final stage. New games cannot generate portfolios; historical records and
    legacy access remain. The leader is identified as the preparer.

New games use a version field on existing records. Previously saved questionnaires
and dashboards continue to use their existing components and rules.
Old public offer pages redirect; historical private forms, session links and paid
purchase claims remain. Other new checkout offers return 410; existing payment
status, webhook and entitlement verification are retained.

## Administration

`/admin` uses existing administrator authentication. It contains:

- Board fundraising blog generation, with original articles/RSS retained.
- Independent authoritative homepage and How It Works text editors, including
  biography, CTA text, the complete four-step written offer and guarantee wording.
- Paying customers and audited read-only inspection of organization details,
  invitations, contributions, meeting state and strategy. Historical portfolios
  are visible only when previously saved records exist.
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
- Existing strategy records, PDF renderer and secure personal links. Historical
  portfolio records and customer access remain preserved.
- Existing design CSS, carousel, founder image, blog generation and RSS.

AI extracts only source-backed meeting contributions. It cannot independently
adopt an idea or invent fundraising recommendations. Document assembly preserves
approved wording and confirmed responsibilities.

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
- Explicit adoption, recoverable meeting closure, logo/color-branded PDF, approved
  responsibilities, secure sharing and no active portfolio generation.
- Existing planning/fundraising, finished-resource, recruitment, prepayment and
  historical route regression tests.
- Existing React journey tests, frozen-lockfile dependency install and production build.
- Initial HTML, canonical metadata, social images, sitemap and retired HTTP redirects.
- Playwright Chromium at 1440×1000 and 390×844, real customer pages, three participant
  browsers, private host prompts, live device updates, speech-event integration,
  individual adoption, strategy PDF, logo upload and secure sharing without portfolios,
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

## Final corrections from the latest supplied files

New sales cost $997 once per organization. The Stripe resolver verifies one-time
USD 99700 pricing; claims verify that subtotal and the currency before granting
a new $997 purchase. Existing Stripe tax calculation can add tax to the total.
Historical $497 purchases retain their price and entitlement. No $97 offer exists.

The complete supplied How It Works copy is authoritative and has four steps. Its
wording is stored as editable content. Old CMS revisions cannot silently restore
the superseded offer or portfolio promises. The homepage retains the earlier
supplied copy, biography, design and testimonial carousel, with four CTAs.

Both leader and participants use the exact five-question audience flow and final
participation question. The leader finishes before meeting setup/invitations.
The Group Game discusses all board recommendations before all leader proposals.

The transcript review has explicit include/dismiss controls and source quotes.
New audiences must be completed and approved; responsibilities require agreement.
A provider outage or a long transcript offers manual review rather than blocking
the meeting. No suggestions enter the document until confirmed.

The last stage is the adopted strategy, with a ready notification, optional logo
and brand colors, PDF, secure share link and copyable email. There are no active
portfolio buttons, generation, approval or delivery steps for new games.

Follow-ups retain days 3/6/9/12/15, unsubscribe, paid stop and durable deduplication.
No optional checkbox appears on the public form. Explicit historical opt-outs are
preserved. Where explicit opt-in is required, the existing deployment can enable
FUNDRAISING_FOLLOWUP_REQUIRES_OPT_IN to prevent automatic follow-up enrollment.
This task does not change environment configuration or claim checkbox consent.

The latest CI run linked to the final commit is the source for test results.
Real provider quality, Gmail receipt, physical microphone recognition and the
actual Catherine/Katherine production record remain unverified here.

## Centered public copy and written strategy presentation

The homepage and complete How It Works copy now use centered text within the
existing readable column. Their wording, four homepage CTAs and testimonials are
retained. Contact form inputs and customer tools keep their normal alignment.

When the facilitator reviews the agreed strategy, the existing AI transport edits
only adopted audience content into the organization's voice. Supporting source
quotes and amounts are checked. A source-preserving fallback handles outages.
The written preview is shown to the leader and participating devices before the
existing strategy-adoption step. Returning to discussion and changing a decision
invalidates that preview. Closing saves and delivers the exact preview adopted.

The Group Game retains original submissions and contributor names. The finished
strategy removes reporting such as "Alex said". Named agreed responsibilities and
the adoption record remain. Five personal questionnaire questions are unchanged.
The facilitator can record an audience name, separate amount, follow-up and donor
stewardship details when agreed; these are optional, not extra intake steps.
Unsupported follow-up or stewardship activities are never filled in automatically.

New structured PDFs have bold headings and subheadings, readable paragraphs and
bullets. Each approved audience starts on a new page and cannot share a page with
the next audience; long content continues naturally rather than becoming illegible.
Logo/color branding is preserved. Shared web documents use the same structure.
Historical finalized documents and the original generic renderer remain unchanged.

The latest audience presentation uses "Ideal Funding Audience:", a specific
audience name and eight bullet subheadings. Approved detailed explanations are
retained rather than replaced with generic summaries. Editorial checks reject
rewrites that omit source details or numbers; the original approved narrative
remains available as the fallback. Teachers and parents in Pittsburgh are sample
audiences only and are never inserted into customer strategies automatically.

The complete eight-part teachers example fits one audience page at 11-point body
text. The layout test checks both complete detail retention and readable type.
