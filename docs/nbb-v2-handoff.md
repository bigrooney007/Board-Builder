# Nonprofit Board Builder simplified V2 handoff

Branch: `feature/nbb-simplified-final` in `bigrooney007/Board-Builder`.

Base: `d627263044f606a819366d3b04fe7e240b8e254d` on `codex/recruitment-simple-resources`. The exact original Git tree and all 709 tracked files were restored and verified. The new commit retains that parent, which includes the earlier undeployed changes. The final SHA is supplied in the chat handoff.

No deployment, production merge or Emergent synchronization was performed by Codex. AutoFundraiser was not changed. The original homepage design, content and CSS are preserved; its four service-button destinations now lead to the new education pages, as the owner confirmed. Original product routes, price definitions, purchases and entitlement services are preserved. Small shared changes export existing intake definitions, extract unchanged strategic questions and recommitment validation, add optional form hooks, reuse the email shell, and dispatch explicitly identified V2 Stripe events. Original customer entitlements remain intact.

## Deployment and direct access

The owner wants to sync the code, deploy it themselves, view the implemented pages and request corrections. V2 is now enabled by default and public education/intake pages do not require a preview password unless an administrator deliberately configures `NBB_V2_PREVIEW_KEY`. No new environment settings are required to view `/v2` after normal deployment. An explicit `NBB_V2_ENABLED=false` remains available to disable the new version.

After deployment, customers start at `https://nonprofitboardbuilder.com`. Its four existing service buttons now open the corresponding education page before the customer answers any questions. Each education page's Start for Free button opens the existing introductory question sequence for that product, followed by the written roadmap, $197 checkout and product resources. The technical destinations are `/v2/recruit`, `/v2/board-fundraising-game`, `/v2/strategic-planning` and `/v2/board-recommitment`. Customers do not need to discover a separate chooser URL. `/v2` remains an additional service chooser. Original direct product/intake/customer links remain available. V2 uses separate journey/resource records and purchase entitlements in the existing application database. Public entry does not authorize private applicant answers or purchased resources.

Checkout reuses `STRIPE_SECRET_KEY`, transactional emails reuse the existing Resend service/sender, AI generation reuses the existing AI configuration, secure sessions reuse `JWT_SECRET`, and links reuse `PUBLIC_ORIGIN` with the existing production domain as fallback. `NBB_V2_ORIGIN` remains an optional override. The existing Stripe key determines whether a charge is live or test. Test-only payments and allowlisted email can be explicitly selected for testing; the synthetic fixture does that automatically. Ordinary deployment does not launch campaigns or send applicant-network announcements. Live network distribution remains explicitly controlled by its existing V2 network setting and provider consent checks.

## Customer experience

All four V2 products cost **$197 each**, with separate V2 purchase records. Customers learn the process on the product page, use the current introductory questions, read a personalized written roadmap, confirm organization branding, and choose self-service or the existing Calendly conversation. Professional assistance is quoted separately. The verified existing booking URL is `https://calendly.com/boardbuilder/recruitboard`.

After payment verification, the complete resource inventory, forms and direct-action links are created automatically. Customized recruitment documents are generated in durable background jobs; their rows show preparation or a retriable failure rather than pretending an unfinished document is ready. Customers do not need to request their pack. They can review and edit each document, approve the exact current revision, and receive that saved revision as PDF, DOCX and TXT email attachments. A revision edited after approval needs fresh approval. Duplicate approval does not duplicate delivery.

Recruitment provides 39 resources covering governance, profiles, campaign copy, applications, interviews, references, appointments and optional onboarding templates. No background-check service or output is included. Once the current announcement, application form, job post and LinkedIn post are approved, the leader reviews a campaign preview and explicitly confirms launch. That activates the application, publishes the frozen approved listing in the isolated V2 marketplace, and queues announcements only to registered, opted-in permitted test contacts. The interface distinguishes queued, confirmed, partial, failed and skipped activity. Launch retry, pause and close preserve records and prevent duplicate announcements. New applications notify the leader through a scoped link to the response, supporting document, personalized interview guide, invitation and rejection actions. An optional existing launch instruction video remains available.

Fundraising provides leader/participant links, invitations, meeting settings, submitted ideas, facilitation guidance and a Group Game. Participants complete one funding audience at a time under Individuals, Businesses and Grantmakers. Each audience preserves its identity, reasons, location, attraction, relationship process, ask and amount; a category can be skipped, uncertainty is accepted, progress is saved, and participation is a separate final answer. The group compares overlapping suggestions without discarding differences, edits or combines them, and explicitly adopts or rejects them. Responsibilities require confirmed consent and connect to approved audiences. A final editable preview contains only adopted ideas and confirmed participation. Approval emails the exact agreed strategy. There are no execution agents or mandatory portfolios.

Strategic Planning preserves the existing questions, program-specific sections and methodology. Branded forms, invitations, source responses, meeting settings and a facilitation guide support one group planning session. The leader controls decisions while an explicitly shared meeting view is read-only. Retaining the existing mission is an explicit decision. The final editable preview uses only adopted decisions, including supplied budget/fundraising information without inventing figures. Approval emails the saved plan. There is no mandatory delegation or project management.

Recommitment reuses the original conditional form and invitation, adds two respectful follow-up templates, and permits copied external email or platform invitations. Externally copied messages are never labelled delivered. Responses notify the leader. A conversation guide is generated from the submitted position, edited, approved and emailed. A submission is not automatically a final recommitment.

## Routes

| Purpose | V2 route |
| --- | --- |
| Board service chooser | `/v2` |
| Four education pages | `/v2/recruit`, `/v2/board-fundraising-game`, `/v2/strategic-planning`, `/v2/board-recommitment` |
| Existing introductory questions | `/v2/:product/start` |
| Written roadmap and $197/Calendly choice | `/v2/:product/offer?journey=...` |
| Verified payment return | `/v2/:product/payment?journey_id=...&session_id=...` |
| Compact purchased resources | `/v2/resources/:journeyId` and `/v2/:product/resources/:journeyId` |
| View/edit/approve/download resource | `/v2/resources/:journeyId/:resourceId` |
| Responses and direct response action | `/v2/responses/:journeyId`, `/v2/responses/:journeyId/:submissionId` |
| Invitations and copyable templates | `/v2/invite/:journeyId` |
| Group session | `/v2/group/:journeyId` |
| Read-only explicitly shared meeting | `/v2/meeting/:token` |
| Campaign preview/launch/pause/close | `/v2/campaign/:journeyId` |
| Token-scoped application/participant form | `/v2/forms/:token` |
| Isolated marketplace | `/v2/marketplace` |
| Secure recovery | `/v2/recover` |
| Email link exchange alias | `/v2/access?token=...` |
| Existing admin, compact V2 tab | `/admin?tab=v2` |

All application endpoints are under `/api/v2`. Owner email links open the needed action directly, exchange an expiring random token for a scoped HttpOnly cookie, and remove the token from browser history. Participant tokens do not grant owner access. Public shared-form drafts have separate opaque secrets and cannot read another participant's saved answers. Private supporting documents and original source submissions remain organization scoped. V2 API and frontend responses are no-store/noindex; routes are not linked from the original homepage. Feature flags and preview-key or administrator access protect discovery.

## Existing services reused

The original free recruitment, guided planning/recommitment and five-question fundraising definitions; the original strategic participant-form builder and recommitment conditional rules; `ApplicationForm` and `BoardRecommitmentFormPage` with optional V2 adapters; the genuine unchanged `TestimonialCarousel`; `ai_service.generate_structured`, its existing schemas/display renderer, `workspace_service.reference_context`, organization context and application questions; CV text extraction; `document_renderer.render_document_pdf`; original invitation content templates; existing Stripe infrastructure, signature validation and `payment_transactions`; the Resend transport, configured senders and reusable email shell; existing opted-in `board_applicants` and marketplace `opportunities` records; existing admin and member authentication.

V2 data uses its own journeys, purchases, resources, submissions, invitations, decisions, commitments, access links and durable email outbox. Marketplace preview records have `V2Published` status and are explicitly excluded from original application routes. Old purchases never gain or lose entitlements through a V2 payment. Network unsubscribe is an explicit action; queued announcements recheck current permission and active campaign status. Necessary owner transactional messages do not change marketing preferences.

## Recruitment inventory

Organization and governance: recruitment profiles, Organization Overview, Board Manual, Board Member Agreement, Confidentiality Agreement, Conflict of Interest Agreement, printable Board Member Profile Form, responsibilities and expectations.

Campaign: announcement, job post, LinkedIn post, social posts, outreach email, direct invitation, referral request, online/printable application form, public application link and launch instructions.

Interviews: interview invitation and short message, screening/interview guidance, rejection, candidate follow-up, after-interview thank-you and after-interview rejection templates. Applicant-specific guides and communications are generated from the direct response page.

References and appointments: reference-check form, candidate reference request, reference confirmation, reference follow-up, reference call guide, conditional/unconditional appointment emails, appointment letter, acceptance template, onboarding email, onboarding agenda/facilitation guide, portfolio email template and first board meeting invitation. Candidate-dependent templates do not invent a candidate, appointment, reference result, signature or meeting.

## Verification and remaining acceptance

The handoff runs the synthetic HTTP/service suite and source preservation checks documented in the final chat. Tests exercise all four $197 checkout/entitlement flows, complete recruitment inventory, branding, immutable approval attachments, campaign/application/CV/communications, fundraising drafts/categories/adoption/consent, strategic mission/approved-only plan, recommitment response/guide, organization authorization, secure recovery, tampered/expired links, payment replay, failed email retry and duplicate suppression. Only provider seams are replaced; real routes, validators, persistence contracts and document renderers run. JSX parsing and Python compilation also run. No actual customer data, live charge or live network broadcast is used.

Eight original standalone contract validators already fail at the exact base commit; comparing current and base results found no new failures. Original live production journeys were not called as a regression test.

**Verification update:** the owner supplied a report that the production frontend build, 17/17 React/Jest checks and 16/16 synthetic desktop/mobile checks passed for `f799d9c85c63e5ce40fd4fbe6f5b4388d00afdab`. These are reported results for that commit. The subsequent shared V2 typography/layout changes passed source-preservation and syntax checks here; their Chromium checks are blocked by sandbox socket restrictions. No new browser pass is claimed. Live Mongo/Stripe/Resend integration and real AI writing quality remain unverified. See `nbb-v2-verification.md` for the separate scopes and results. The code is ready for isolated preview verification, not certified for release.

The V2 style follow-up increases body text to 16–18px, form labels/inputs to 16px and important supporting text to 14px. Page titles and introductory copy sit centrally; instructions and document bodies remain readable in centered columns. Shared action pages no longer repeat mobile side padding, and long titles and links wrap. The original homepage appearance remains unchanged; only four service destinations were updated.

The complete pack appears immediately as inventory; AI-generated documents finish asynchronously. Neutral styling applies when branding is absent. Agreements, board profile and candidate-dependent appointment/onboarding items are editable/printable resources, not a new appointment or signing workflow. The V2 marketplace is intentionally isolated from the normal public marketplace until release is authorized. No test announcement can be sent to the live network by default. Provider idempotency has a finite retry window; ambiguous older deliveries need administrator reconciliation.

## Commands for isolated verification

From the repository root:

```sh
python -m unittest discover -s backend/tests -p 'test_v2*.py' -v
python tests/validate_v2_contracts.py
node tests/validate_v2_frontend.cjs
python -m compileall -q backend
```

In an environment with the existing frontend dependencies installed:

```sh
cd frontend
REACT_APP_BACKEND_URL= yarn build
CI=true yarn test --watchAll=false --runInBand --testPathPattern=src/v2
```

Then, using two local terminals from the repository root:

```sh
python tests/v2_local_app.py --port 8765
python tests/v2_browser_harness.py --base http://127.0.0.1:8765
```

For shared CSS layout checks without frontend dependencies or provider setup, in an environment that permits Chromium:

```sh
python tests/v2_layout_harness.py
```

This uses synthetic markup and real V2 product copy at four viewport widths. It does not substitute for the actual React browser tests.

The fixture app uses synthetic data and fake providers, verifies its local marker, and never loads the production `.env`. It serves the actual frontend build and clearly refuses browser acceptance when that build is absent. Synthetic automated tests must use this fixture, not the deployment database. The owner can deploy the application normally and review the direct V2 URLs.

Optional configuration names are in `docs/nbb-v2-config.env.example`. Dependencies remain the existing application dependencies; no replacement backend or unrelated product is introduced.
