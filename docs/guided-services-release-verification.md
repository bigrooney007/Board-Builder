> Current offer and operational instructions: [Activation services handoff](two-option-services-handoff.md). The latest instruction replaces the earlier public two-tier pricing with one $497 activation-and-platform offer for each of the four pathways. Historical prices in this document describe earlier releases.

# Four-part release: verification, public URLs and synchronization

Read the accompanying [operating guide](guided-services-operating-guide.md) for all seven customer journeys, service-by-service promotional messages and the real admin navigation.

## Release identity and implementation

- Part One started from `feature/fundraising-game-simplified` at `549b3d2db5b6fdf96ae9a396d4e141df3fd77622`.
- Parts Two through Four continued from the completed Part One branch, `feature/nbb-main-consultations`, at `0eb3f603534d3ceba14c66b12ea5ca1a2bd5a659`.
- The release branch is **`feature/guided-board-services`**. It includes Part One and all subsequent guided-service commits. No production branch was force-pushed or merged.
- The final exact sync SHA is supplied in the accompanying handoff. The application verification reference is recorded below. A later documentation-only commit does not change the tested application.

| Instruction | Implemented result |
|---|---|
| Part One | Four-service main directory, friendly Fundraising alias, Meet Rooney with original portrait/testimonials and editable biography, separate $197 consultation, trusted Stripe payment before Calendly, private paid recovery, independent consultation records/notes and admin controls. |
| Part Two | $497 guided Recruitment, dynamic versioned free questions, private AI profiles, timed first email and five follow-ups, personalized videos, separate payment, branding/booking, admin profile/material approval, existing campaign publisher, applicant/CV/interview/onboarding/signature tools and resource delivery. |
| Part Three | $497 guided Recommitment, independent questions/emails/booking, existing personal board forms, editable stable decision labels, reviewed invitations, original responses, interpretation, confirmed outcomes, portfolios, agreements/signatures and delivery. Meet Rooney's transformation button now points to the main directory. |
| Part Four | $1,997 facilitated Planning, three independent question editors, separate leader/board forms, individual program records, admin-controlled existing meeting engine, adopted decisions, consent/transcript/typed notes, plan generation and editing, version history, controlled review release, individual adoption/change requests, final approval and branded downloads/delivery. |

The Fundraising Game's existing questions, $1,497 checkout/configuration, member participation, invitations, group controls, microphone, strategy/adoption, customer workspaces and delivery are preserved. AutoFundraiser has no application changes. Historical product routes, purchases, documents and customer access are retained; new paid engagements use separately scoped internal workspaces without overwriting an earlier campaign belonging to the same email address.

## Public promotional URL directory

Production was inspected using a read-only browser on **20 October 2026 at 06:51 BST**. The deployed site still showed the previous Fundraising homepage. HTTP 200 alone was not accepted as proof that a new service page was live: the browser's final URL and page heading were checked too.

The prices and CTAs below describe this release. **Pending deployment** means the new route/flow is implemented and tested in the release but was not serving that new experience during the production audit.

| Service or page | Complete public URL | Purpose | Main CTA | Price | Observed live status |
|---|---|---|---|---|---|
| Main Nonprofit Board Builder | https://nonprofitboardbuilder.com/ | Choose among four services or meet Rooney | Explore Our Services | Varies by service | Root is live; it currently shows the previous Fundraising page. New four-service directory pending deployment. |
| Meet Rooney | https://nonprofitboardbuilder.com/meet-rooney | Biography, experience, testimonials and separate ways to proceed | Book a Session With Rooney | Consultation $197 | New page pending deployment; currently redirects to the old root. |
| Professional consultation | https://nonprofitboardbuilder.com/consultation | Short discussion-topic form and paid consultation entry | Continue to Secure Payment | $197 | New journey pending deployment; currently redirects to the old root. |
| Board Recruitment | https://nonprofitboardbuilder.com/recruit | Start the free board-needs intake | Start Board Recruitment for Free | $497 guided service after invitation | New journey pending deployment; currently redirects to the old root. |
| Board Fundraising, friendly link | https://nonprofitboardbuilder.com/board-fundraising | Open the existing Fundraising Game | Existing Game CTA | Existing $1,497 | Currently redirects to the live Fundraising root. The release supplies the dedicated alias to the preserved game landing page. |
| Board Fundraising, canonical route | https://nonprofitboardbuilder.com/board-fundraising-game | Existing Game landing page and entry | Existing Game CTA | Existing $1,497 | Currently redirects to the live Fundraising root. The release restores this dedicated landing route while the root becomes the directory. |
| Board Recommitment | https://nonprofitboardbuilder.com/board-recommitment | Start the free board-situation intake | Start My Board Recommitment for Free | $497 guided service after invitation | New journey pending deployment; currently redirects to the old root. |
| Strategic Planning | https://nonprofitboardbuilder.com/strategic-planning | Start the short vision/goals/resources intake | Start My Strategic Planning for Free | $1,997 after invitation | New journey pending deployment; currently redirects to the old root. |
| Board Applicant Network | https://nonprofitboardbuilder.com/join-a-board | Professionals submit a board-service profile | Join the Board Applicant Network | No service purchase required | Live, correct page and heading verified. |
| Published board opportunities | https://nonprofitboardbuilder.com/board-opportunities | Browse actual published opportunities | Apply to a listed opportunity | No applicant service purchase required | Live, correct page and heading verified. |
| Blog | https://nonprofitboardbuilder.com/blog | Discover published articles | Read an article and follow its relevant offer | Free reading | Live, correct page and heading verified. |
| Fundraising explanation/offer | https://nonprofitboardbuilder.com/how-the-fundraising-game-works | Existing written Game explanation and checkout entry | Existing purchase CTA | Existing $1,497 | Live, correct page and heading verified. |
| Historical facilitated Fundraising entry | https://nonprofitboardbuilder.com/organize-board-fundraising-game | Preserved historical entry link | Existing Fundraising CTA | Existing configuration | Currently redirects to the old Fundraising root. The release sends this alias to the existing how-it-works page; it does not create a separate offer. |
| Blog RSS | https://nonprofitboardbuilder.com/api/blog/feed.xml | Syndicate published articles | Subscribe in a feed reader | Free | HTTP 200 and RSS XML verified. |

The website sitemap and blog sitemap also returned valid XML at `https://nonprofitboardbuilder.com/sitemap.xml` and `https://nonprofitboardbuilder.com/api/blog/sitemap.xml`. Individual article URLs remain `/blog/<actual-published-slug>`; copy them from the existing public blog. No placeholder article slug is presented as a verified promotional link.

Do not promote `/admin`, customer resources, board-member tokens, secure documents, payment sessions or temporary test links. AutoFundraiser's supplied external link remains `https://autofundraiser.com/`; it is a separate business and is not deployed by this release.

## Payment, booking and email integration status

| Integration | Implemented and controlled verification | Production status |
|---|---|---|
| Consultation Stripe | Separate `rooney_professional_consultation_197`, USD 19,700 cents. | Live provider transaction for this new release unverified. |
| Recruitment Stripe | Separate `rooney_guided_recruitment_497`, USD 49,700 cents. | Live provider transaction for this new release unverified. |
| Recommitment Stripe | Separate `rooney_guided_board_recommitment_497`, USD 49,700 cents. | Live provider transaction for this new release unverified. |
| Planning Stripe | Separate `rooney_guided_strategic_planning_1997`, USD 199,700 cents. | Live provider transaction for this new release unverified. |
| Existing Fundraising Stripe | Existing product/configuration and price retained. | Public configuration reported live Stripe mode. No new charge was made. |
| Stripe confirmation | Existing signed `/api/stripe/webhook`, plus server retrieval checking ownership, product, currency, amount and paid state. Wrong product/amount/session and unpaid success URLs are rejected; paid returns do not charge again. | Actual production webhook configuration and new-product payment events were not changed or verified with a real charge. |
| Calendly | Independent settings per service and consultation. Existing verified destination initially reused: `https://calendly.com/boardbuilder/recruitboard`. Booking opens only after payment, and branding for guided services. | Booking-page handoff is implemented. A confirmed reservation requires actual provider confirmation. No test reservation was created. |
| Calendly notifications | Signed `/api/consultations/calendly-webhook` correlates paid records and handles observed bookings/cancellations. | Optional provider subscription/signing-key setup is unverified. Without it, the admin truthfully shows the booking link opened rather than a confirmed meeting. |
| Transactional email | Existing Resend service and durable outbox, organization-scoped action links, retry/deduplication, delivery history and recovery. Templates are editable independently. | Real inbox receipt for these new messages is unverified. Controlled tests use provider substitutes/capture, not Gmail. |
| Prospect follow-ups | One normally 60-minute invitation, then five independent editable messages, with default three-day intervals. Payment/unsubscribe/suppression/manual stop are checked before sending. | Background workers are enabled in normal application startup; no preview flag is required. Their real production sends require the deployed release and existing sender configuration. |
| Applicant-network announcements | Existing marketplace and permitted Resend segment/topic distribution reused, explicit organization approval and separate truthful publication/network status. | Live network distribution was not exercised. Required segment/topic/sender configuration remains an operational dependency. No live applicant campaign was sent. |
| AI generation | Existing profile, resource, interpretation, portfolio and planning generators reused; saved human approvals control release. | Real-provider writing quality is unverified in this environment. Controlled tests verify source selection, organization scope, approvals, output rendering and delivery rather than model quality. |
| Microphone | Explicit consent, start/stop controls, transcript persistence/correction, participant status and typed-note alternative. | Saved transcript and permission controls are tested. Physical microphone/browser speech-service quality is unverified. |

The runtime available to Codex had no bound production Stripe/Resend/AI credentials or authenticated deployed administrator session. No production settings, customer records or integrations were changed. Provider receipt or live deployment is not inferred from successful local/CI tests.

## Verification results

The final application commit tested was **`f52b29f55b950848b499d791abd50c9a5d7c5e78`**, tree `c61355471a015052dceb0fbee1176972f70ff884`.

[GitHub Actions run 39376516822](https://github.com/bigrooney007/Board-Builder/actions/runs/39376516822) completed successfully on **20 October 2026**. Both `guided-services` and `validate` jobs passed. The final handoff commit adds documentation only; the application is identical to this tested commit.

| Release check | Result |
|---|---|
| Guided Recruitment/shared HTTP and configuration | **23/23 passed**. Includes versioned questions, email preview/timing/retries, five follow-ups, payment ownership/amount/product checks, branding/booking, private profiles, resources, campaign publication, applicant/CV tools, customer appointment controls and frozen signing. |
| Guided Recommitment HTTP and configuration | **7/7 passed**. Covers three underlying decisions, personal invitations, version preservation, organization isolation, response interpretation, confirmed outcomes, conversation guides and portfolio/resource delivery. |
| Guided Planning HTTP and configuration | **8/8 passed**. Covers independent forms, program association, private responses, adopted decisions, transcript consent, generation recovery, versioned review/adoption, final approval and branded downloads. |
| Existing backend and consultation regressions | **101/101 passed** across the selected existing suites. Combined backend release total: **139 passed**. |
| Frontend tests | **48/48 passed**, 12 suites. |
| Lockfile dependency installation and production build | **Passed** with the existing frozen `frontend/yarn.lock`; frontend compiled successfully. Python compilation passed. |
| Browser: existing Fundraising Game | **14/14 passed** on desktop/mobile. |
| Browser: directory, Meet Rooney and consultation | **21/21 passed**, including desktop, tablet and mobile. |
| Browser: guided Recruitment | **4/4 passed**, including free entry, $497 payment, branding, resource approval/campaign and secure applicant review on desktop/mobile. |
| Browser: guided Recommitment | **2/2 passed**, including responses, conversation guide approval and resources on desktop/mobile. |
| Browser: guided Planning | **2/2 passed**, including personal forms, separate programs, meeting decisions, transcript notes, board adoption and final plan delivery on desktop/mobile. |
| Combined browser checks | **43/43 passed**. |
| SEO, route aliases and private-page analytics/referrer protections | **Passed**. |
| Protected-source and legacy checkout/route scope | **Passed**. Fundraising core files also match the preserved `549b3d2` base directly. |
| Read-only production route/RSS/payment-mode audit | **Completed**, with actual route resolution recorded in the public directory above. New pages were not yet deployed. |

The run retains screenshots, JSON results and the synthetic server log as artifact **`current-workflow-acceptance`**, ID `12243970984`. No production customer database was used. These passing checks cover the release suites, not every historical test in the repository; the unrelated blog-category baseline discrepancy is recorded below.

The controlled environment uses real React pages, actual FastAPI handlers, a disposable MongoDB service and the real original resource/meeting/signing adapters. Only external payment/email/AI transports and synthetic identities are substituted. The production `.env` and customer database are not loaded. The time-controlled email checks advance the clock across the one-hour delay and follow-up intervals; they do not require a browser to remain open.

The original browser journeys include the Fundraising Game at desktop/mobile sizes. New entry, payment, admin, participant, meeting, plan-review and resource pages are checked at desktop/mobile sizes; Part One additionally includes a tablet layout. Screenshots and JSON results are retained in the GitHub Actions acceptance artifact.

## Technical scope and reused capabilities

The complete changed-file inventory is in `guided-services-files.txt`.

- **New public entry routes:** `/meet-rooney`, `/consultation`, `/consultation/confirmed`, `/consultation/resume/:token`, and `/board-fundraising` alias. Existing `/`, `/recruit`, `/board-recommitment` and `/strategic-planning` are the corresponding entry pages.
- **Private guided routes:** `/services/:service/start`, `/services/:service/:stage/:token`, with start/received/offer/setup/resources stages. These are operational routes, not another V2 platform or preview-only product.
- **New service admin:** `/admin/services/recruitment`, `/admin/services/board-recommitment`, `/admin/services/strategic-planning`, linked from the existing `/admin`.
- **Existing participant/review routes reused:** `/board-recommitment/:token`, `/strategic-planning-form/:token`, `/strategic-session/:token`, `/strategic-plan-review/:token`, `/strategic-plan/:token`, `/portfolio/:token`, `/sign/:token`, board application/CV/profile/reference routes and legacy paid dashboards.
- **Shared service layer:** `guided_service_defaults.py`, `guided_services.py` and existing `workflow_delivery.py` provide independent configurations, versioned questions, payment records, secure continuation/recovery, scheduled communications and outbox retry. New internal workspaces opt out of old dashboard lifecycle mail; actual customer preferences are not overwritten.
- **Recruitment:** `guided_workspace.py` delegates to existing workspace, opportunity, CV/interview, profile, reference, document and signing services. Original AI generators and templates are preserved.
- **Recommitment:** `guided_recommitment.py` extends existing reactivation participants/forms/materials/portfolios/signature records. Stable decision constants preserve legacy categories.
- **Planning:** `guided_planning.py` adapts existing `sp_projects`, `sp_participants`, `sp_forms`, `sp_sessions` and `sp_plans`. The existing Strategic Planning session/adoption/generation handlers remain the meeting engine; new-project guards provide admin facilitation, independent personal form snapshots, program subjects, controlled final review and versioned delivery. Historic projects retain their earlier behavior.
- **Documents:** Existing PDF rendering, resource formatting and editable Word support are reused. PNG, JPEG and WebP logos are validated; Word exports normalize accepted images to PNG. Finalized signatures preserve their frozen document text.
- **Protection:** Scope checks compare protected Fundraising engines/UI, original planning methodology, legacy routes, existing checkout definitions, AI engines, homepage styling, testimonials and blog infrastructure with the preserved base. New and legacy purchases remain separate.

## Synchronization and deployment

1. GitHub: the implementation is committed on `feature/guided-board-services`.
2. Emergent: **not synchronized by Codex**. There is no Emergent control connection in this environment. Use the exact commit in the accompanying sync-only instruction.
3. Production: **not deployed by Codex**. The read-only production audit still observed the earlier website. The user will synchronize and deploy using the established process.

Emergent needs only the repository, branch, exact SHA and a sync-only instruction. It is not being asked to recreate the changes, perform the coding/testing, merge production, change environment settings, send campaigns or deploy.

After the user deploys, verify the root directory and individual landing pages against the pending-deployment entries above, then confirm the actual provider behavior with the user's authorized test contacts and controlled payment arrangements. Existing application secrets/settings should be preserved; the new services are not gated behind `NBB_V2_ENABLED` or an unrelated preview key.

## Known limitations

- This release's production deployment and real Stripe, Resend/Gmail, AI and Calendly confirmations are not verified. A CI fixture result is not a live payment or inbox receipt.
- Network announcements depend on the existing recipient segment/topic and sender configuration. Tests deliberately do not send campaigns to the live network.
- Browser speech recognition is device/browser/provider dependent. The manual transcript alternative remains available.
- A configured Calendly URL alone does not establish that its webhook subscription exists. The admin does not display a booking as confirmed without a trustworthy event.
- Final Planning approval currently requires the current-version adoption of every participating reviewer plus an explicit operator confirmation of the organization's applicable formal approval. The application does not replace governance procedures.
- The preserved historical blog-workstation suite has eight previously reproduced category expectations that differ from the existing fundraising-only blog configuration. This unrelated baseline discrepancy was not repaired by changing blog behavior. The current publishing/RSS and scoped regression checks remain the release checks.
