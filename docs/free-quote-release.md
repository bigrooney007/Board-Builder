# Nonprofit Board Builder: current free quote journey

> Historical release notes. The current single-page forms, separate admin editors/customer profiles, 48-hour follow-ups and removal of personalized video features are documented in [simple-quote-admin-release.md](simple-quote-admin-release.md).

Starting point: `feature/guided-board-services` at `b07c6721c8c1caed0dfdef2e8997b93e53d9be15`.

This release implements the October free quote brief with the owner's subsequent correction: **all four board services cost $497**. It supersedes earlier contact-anchored email timing and the briefly configured $97 Strategic Planning setup price for new checkouts. Historical purchases, open checkouts, form versions, projects and entitlements remain valid.

## Customer flow

1. A visitor chooses Recruitment (`/recruit`), Recommitment (`/board-recommitment`), Fundraising (`/board-fundraising`, with `/board-fundraising-game` retained), or Planning (`/strategic-planning`).
2. Get a Free Quote opens the existing compact contact dialog. There is no registration or password.
3. They answer the short, independently editable quote questions. Each includes one required open-text outcome-impact question, with stable semantic role `desired_outcome_impact`. Names, email and organization are collected once.
4. Submission preserves the exact answers and question snapshot. A normal first email is scheduled for one hour after **completed submission**, using the durable existing worker. An unfinished contact form does not start the new quote sequence.
5. The email quotes the prospect's stated desired result and connects it to the service. The configured model may select a verbatim excerpt, but cannot rewrite offers or invent facts. A deterministic original-answer fallback handles model failures. Fundraising also references the stated consequences of missing the goal. The editable template controls the surrounding copy and CTA.
6. Server-verified checkout is $497 for each of Recruitment, Recommitment, Fundraising and Guided Strategic Planning Setup. A separate quote covers professional facilitation of the actual planning meeting. The existing $197 personal consultation is unchanged.
7. Payment opens the detailed leader questionnaire. Earlier relevant answers are reused. Questions and progress are versioned and saved. Recruitment and Recommitment retain the established detailed questions; Planning uses its independently editable leader question group; Fundraising retains its audience-by-audience Game before booking.
8. The customer then provides branding and opens the configured Calendly link. Board invitations are not required before the first session. Paid customers can return using their secure link without another charge.
9. Rooney prepares and operates the existing customer workspace, then hands over the same saved project through the established secure access mechanism. Existing campaigns, applicant management, board forms, meeting controls, transcription, adopted decisions, document approvals, signatures and downloads remain in their original engines.

## What happens in each service

The question counts below are defaults after the three contact fields, not hardcoded limits. Published admin edits control the next new submission.

| Service | Short quote | Paid preparation and service delivery |
| --- | --- | --- |
| Board Recruitment | Four questions: role, recruitment count, preferred location and desired outcome. | The established detailed recruitment questions collect mission, current board and recruitment needs. After branding and booking, Rooney reviews and agrees the desired profiles, prepares and approves the existing materials, then explicitly launches the campaign. Applicants use the original public application/CV system. Notifications, interview decisions, reference/appointment documents, agreements and onboarding remain available. The same project can be handed to the leader to continue independently. |
| Board Recommitment | Four questions: role, number of members, reason and desired outcome. | The established detailed recommitment questions precede branding and booking. Rooney prepares the original branded recommitment form and reviewed invitations. Active, advisory and step-down responses remain distinct from confirmed organizational decisions. Interpretation, conversation guides, agreed portfolios, signatures and approved resource delivery continue through the existing workspace. |
| Board Fundraising | Six questions: role, board size, goal, deadline, consequences and a separate positive outcome. | The leader completes the established organization questions, audience-by-audience Game and personal participation before branding and booking. Rooney uses the original workspace to prepare the board process and invitations. Participants keep their own answers. The Group Game, microphone/transcript controls, explicit audience adoption, agreed participation, strategy editing and final delivery are preserved. |
| Guided Strategic Planning Setup | Four questions: role, board count, preferred meeting (or unscheduled) and desired outcome. | The $497 setup uses the extensive existing leader planning questions before branding and booking. The initial session prepares the original planning project. Board participants receive independent forms; programs retain their identifiers. The existing section-by-section discussion, explicit adopted decisions, contextual transcript, plan editor, versioned board review/adoption and approved downloads remain available. Professional meeting facilitation is separately quoted. |

## Public links retained

- Main service directory: https://nonprofitboardbuilder.com/
- Recruitment: https://nonprofitboardbuilder.com/recruit
- Recommitment: https://nonprofitboardbuilder.com/board-recommitment
- Fundraising: https://nonprofitboardbuilder.com/board-fundraising (existing `/board-fundraising-game` remains valid)
- Planning: https://nonprofitboardbuilder.com/strategic-planning
- Meet Rooney: https://nonprofitboardbuilder.com/meet-rooney
- Separate personal consultation: https://nonprofitboardbuilder.com/consultation
- Board Applicant Network: https://nonprofitboardbuilder.com/join-a-board
- Published board opportunities: https://nonprofitboardbuilder.com/board-opportunities
- Blog: https://nonprofitboardbuilder.com/blog
- RSS: https://nonprofitboardbuilder.com/api/blog/feed.xml

These are public entry points. Customer-specific links, participant tokens and payment sessions are deliberately excluded. The release's read-only public audit checks existing production availability; it does not establish that this new GitHub build has been deployed.

## Emails

Sender: `Rooney A. The Nonprofit Board Builder <rooney@nonprofitboardbuilder.com>`.
Reply-to: `rooney@nonprofitboardbuilder.com`.

Messages and previews are left-aligned. Each service retains editable subject, preview text, headline, body, personalization placement, support text, signature, CTA and timing. Payment URLs are generated for the correct customer and service.

The default five intervals are three days after each successful preceding email, approximately days 3, 6, 9, 12 and 15. Payment, unsubscribe, suppression, bounce/complaint, pause or manual stop prevents further promotional messages. Provider idempotency keys protect retries. Manual personalized video emails remain separately approved and never automatically send when an editor finishes a video.

Resend acceptance is recorded as provider acceptance, not inbox receipt. Optional signed Resend delivery events use `/api/webhooks/service-email` and `RESEND_WEBHOOK_SECRET`. Only authenticated Svix events can update delivery status; late events cannot overwrite newer statuses. This release does not set production environment secrets or claim that a webhook has been configured.

## Designated public test address

`fundraisingschoolfornonprofits@gmail.com` can start a fresh quote repeatedly on all four public forms without login. Every completed quote has its own record and immediate first-email attempt. Network retries reuse the original request/submission and outbox event. Failed sends remain retryable.

These records are labelled **CLIENT FLOW TEST** in administration, excluded from commercial overview totals, blocked from real checkout and never enrolled in the five unpaid follow-ups. The email address grants no member, paid or administrator privilege. Ordinary suppression protections remain in force.

## Administration

The `/admin` primary sections are Overview; Board Recruitment; Board Recommitment; Board Fundraising; Strategic Planning; Video Follow-Ups; Blog & Content; Website Management; Settings. Existing tools remain under the expandable Existing Website and Service Tools menu.

Each service has a searchable/filterable customer table and a compact Actions menu. Opening a record shows What This Customer Wants to Accomplish, exact original answers, the saved personalization passage, journey statuses, email history and the same service workspace.

Manage This Offer opens the actual existing landing editor, quote form editor, first email, follow-ups, detailed post-payment questions, payment/booking controls and current journey tests. The outcome wording is editable; its required open-text semantic role is protected. Editing questions never changes historic snapshots.

Test Post-Payment Journey is administrator-only and creates an isolated paid sample using current published questions. It starts at detailed onboarding with editable synthetic prefilled answers, needs no charge or board invitations, and permits testing through branding and the booking handoff. Synthetic samples capture email and do not count as commercial sales.

## Central video: prepared, not yet connected

The existing AutoFundraiser implementation and API contract are being finalized separately. The user confirmed that `/video-editor` is intended at `https://autofundraiser.com/video-editor`, but live availability is unverified. **No AutoFundraiser code was changed and no remote endpoint was invented.**

NBB provides owner-only camera/microphone recording, stop, preview, rerecord and private staging in the existing Mongo/GridFS storage. Recordings are tied to the source service/customer. An unconnected submit button is disabled, with a clear status. Existing manual YouTube email composition continues working.

Before connecting, AutoFundraiser must supply a verified contract covering:

- Exact base URL and recording-submission, task-status, revision and callback endpoints.
- Auth mechanism, credential scopes and rotation; signed callbacks with timestamp/replay protection, or verified polling.
- Multipart/streaming upload or protected download contract and supported file/size limits.
- Idempotent assignment creation using source application, source service, source customer ID and unique recording ID.
- The minimal video brief permitted for Moses. NBB sends only the service, customer association, name and organization with the recording. Raw quote answers, outcome statements, contact email and payment data are not part of that brief. Rooney sees the full preparation details inside NBB.
- A central assignment ID and actual submitted/editing/revision/ready status.
- Returned source customer/service binding, completed HTTPS YouTube URL and transcript.
- Error/retry behavior, 24-hour target turnaround and approval-aware storage cleanup.

NBB's isolated adapter boundary is `app.state.nbb_central_video_adapter` with `contract_verified=True`, and `submit(task, db)`, `status(assignment_id)`, `request_revision(assignment_id, notes)`. This is an internal adapter interface, **not an assumed AutoFundraiser wire protocol**. The verified external contract will determine the transport implementation.

Ready videos can be reviewed, revised, explicitly approved, then separately emailed through NBB's existing customer email composer. The original recording cannot be manually deleted before a verified YouTube result is approved. YouTube URL, transcript and communication history remain saved. Automatic cleanup and authenticated cross-site callbacks will be enabled only with the verified central contract.

## Preserved infrastructure

The original Game engine and questionnaire, Planning methodology, AI document registry, customer routes, recruitment/applicant infrastructure, historical prices, consultation, testimonials, main service directory, RSS and blog automation remain intact. Original app scope validation checks these protected files and route sets. Existing blog generation/publishing schedules and media editors were not replaced.

## Verification and release state

The complete CI run, including the all-four-$497 pricing correction, passed on application commit `859569b117124b1c73ecbb3ed3c81c71e0166f8d`: https://github.com/bigrooney007/Board-Builder/actions/runs/40039912149 . Any later release-documentation commit leaves this tested application code unchanged.

- Pricing-specific checks verified the actual $497 Stripe product/amount, rejection of $97 for new purchases, preservation of historical purchases, saved admin email migration without overwriting custom wording, and $497 in the first email and all five follow-ups.
- Backend: **188 passed** (87 guided quote/service/blog tests and 101 original regressions), using disposable Mongo and controlled Stripe/email/AI adapters.
- Frontend: **60 passed**, across 14 suites.
- Frozen-lockfile dependency installation, production build, Python compilation, protected-scope checks, metadata, redirects and consultation privacy checks passed.
- Browser acceptance: **61 passed cases** across current entries/editors, the original Fundraising Game, consultation, Recruitment, Recommitment, Planning, secure handover, and the eight four-service desktop/mobile quote journeys. Browser recording was exercised with a controlled camera device; microphone permission and production audio quality are not inferred from this fixture.
- The browser journeys covered campaign approval/publication and resource delivery, recommitment responses/decisions/portfolios, planning forms/programs/adoption/final delivery, and the retained Fundraising Game/adoption/strategy workflow. Provider calls were controlled and no real charge, live applicant campaign or production promotional email was made.
- **173 actual screenshots** are in the run's `current-workflow-acceptance` artifact: https://github.com/bigrooney007/Board-Builder/actions/runs/40039912149/artifacts/12539605317 . Open `current-screenshots.html` after downloading. The gallery includes each service flow, admin/workstation editors, customer workspaces and mobile views. Compact review sheets were inspected.
- The read-only production audit found the principal public pages available, along with the blog/RSS and applicant entries. The public payment configuration reports live Stripe mode; this is not a verified transaction. The older `/organize-board-fundraising-game` currently lands at `/` in production instead of the explanation page. This branch retains its explicit explanation-page redirect, which passed the build route checks. The deployed commit was not verified.

### Integration and release limits

Production transactions, actual Gmail receipt, real Calendly reservations, model output quality with the live provider and the pending AutoFundraiser connection remain **unverified**. Existing provider configuration was preserved. Signed email-event delivery reporting requires its hosting secret/provider webhook; no production setting was changed here. Automatic cross-site video callbacks and cleanup await the verified central contract, as agreed with the owner.

The implementation and fixes are pushed to `feature/guided-board-services`; the final handoff supplies the final documentation-inclusive SHA. Emergent has not synchronized this release and production has not been deployed by Codex. GitHub commit, Emergent synchronization and user deployment remain separate actions. Emergent instructions are sync-only.
