# Nonprofit Board Builder: current free quote journey

Starting point: `feature/guided-board-services` at `b07c6721c8c1caed0dfdef2e8997b93e53d9be15`.

This release implements the October free quote brief. It supersedes earlier contact-anchored email timing and the $497 Strategic Planning activation price for **new quotes only**. Historical purchases, open checkouts, form versions, projects and entitlements remain valid.

## Customer flow

1. A visitor chooses Recruitment (`/recruit`), Recommitment (`/board-recommitment`), Fundraising (`/board-fundraising`, with `/board-fundraising-game` retained), or Planning (`/strategic-planning`).
2. Get a Free Quote opens the existing compact contact dialog. There is no registration or password.
3. They answer the short, independently editable quote questions. Each includes one required open-text outcome-impact question, with stable semantic role `desired_outcome_impact`. Names, email and organization are collected once.
4. Submission preserves the exact answers and question snapshot. A normal first email is scheduled for one hour after **completed submission**, using the durable existing worker. An unfinished contact form does not start the new quote sequence.
5. The email quotes the prospect's stated desired result and connects it to the service. The configured model may select a verbatim excerpt, but cannot rewrite offers or invent facts. A deterministic original-answer fallback handles model failures. Fundraising also references the stated consequences of missing the goal. The editable template controls the surrounding copy and CTA.
6. Server-verified checkout is $497 for Recruitment, Recommitment and Fundraising; $97 for Guided Strategic Planning Setup. A separate quote covers professional facilitation of the actual planning meeting. The existing $197 personal consultation is unchanged.
7. Payment opens the detailed leader questionnaire. Earlier relevant answers are reused. Questions and progress are versioned and saved. Recruitment and Recommitment retain the established detailed questions; Planning uses its independently editable leader question group; Fundraising retains its audience-by-audience Game before booking.
8. The customer then provides branding and opens the configured Calendly link. Board invitations are not required before the first session. Paid customers can return using their secure link without another charge.
9. Rooney prepares and operates the existing customer workspace, then hands over the same saved project through the established secure access mechanism. Existing campaigns, applicant management, board forms, meeting controls, transcription, adopted decisions, document approvals, signatures and downloads remain in their original engines.

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

Test Post-Payment Journey is administrator-only and creates an isolated paid sample using current published questions. It starts at detailed onboarding, needs no charge or board invitations, and permits testing through branding and the booking handoff. Synthetic samples capture email and do not count as commercial sales.

## Central video: prepared, not yet connected

The existing AutoFundraiser implementation and API contract are being finalized separately. The user confirmed that `/video-editor` is intended at `https://autofundraiser.com/video-editor`, but live availability is unverified. **No AutoFundraiser code was changed and no remote endpoint was invented.**

NBB provides owner-only camera/microphone recording, stop, preview, rerecord and private staging in the existing Mongo/GridFS storage. Recordings are tied to the source service/customer. An unconnected submit button is disabled, with a clear status. Existing manual YouTube email composition continues working.

Before connecting, AutoFundraiser must supply a verified contract covering:

- Exact base URL and recording-submission, task-status, revision and callback endpoints.
- Auth mechanism, credential scopes and rotation; signed callbacks with timestamp/replay protection, or verified polling.
- Multipart/streaming upload or protected download contract and supported file/size limits.
- Idempotent assignment creation using source application, source service, source customer ID and unique recording ID.
- The minimal video brief permitted for Moses. NBB must not expose payment data or the customer's full confidential submission.
- A central assignment ID and actual submitted/editing/revision/ready status.
- Returned source customer/service binding, completed HTTPS YouTube URL and transcript.
- Error/retry behavior, 24-hour target turnaround and approval-aware storage cleanup.

NBB's isolated adapter boundary is `app.state.nbb_central_video_adapter` with `contract_verified=True`, and `submit(task, db)`, `status(assignment_id)`, `request_revision(assignment_id, notes)`. This is an internal adapter interface, **not an assumed AutoFundraiser wire protocol**. The verified external contract will determine the transport implementation.

Ready videos can be reviewed, revised, explicitly approved, then separately emailed through NBB's existing customer email composer. The original recording cannot be manually deleted before a verified YouTube result is approved. YouTube URL, transcript and communication history remain saved. Automatic cleanup and authenticated cross-site callbacks will be enabled only with the verified central contract.

## Preserved infrastructure

The original Game engine and questionnaire, Planning methodology, AI document registry, customer routes, recruitment/applicant infrastructure, historical prices, consultation, testimonials, main service directory, RSS and blog automation remain intact. Original app scope validation checks these protected files and route sets. Existing blog generation/publishing schedules and media editors were not replaced.

## Verification and release state

Local production build and existing 59 frontend tests passed. Current quote, scheduling, payment, onboarding, video staging, signed delivery-event and original service regression suites are included in CI, using disposable Mongo and controlled Stripe/email/AI adapters. Desktop/mobile browser acceptance exercises the actual application. Final run results and exact sync SHA are recorded in the final handoff.

Production transactions, actual Gmail receipt, real Calendly reservations and the pending AutoFundraiser connection must not be inferred from synthetic provider tests. GitHub commit, Emergent synchronization and user deployment are separate actions. Emergent instructions remain sync-only.
