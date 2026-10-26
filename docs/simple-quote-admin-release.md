# Current quote forms and administration

This release follows `f3889681c32263e6e73b5265f83267904a0b6ff0` on `feature/guided-board-services`. It implements the owner's latest simplification. Older documents describing a contact popup, sequential free questions, personalized video production or inline customer records are historical.

## Customer journey

Each existing offer landing page explains its service and sends every Get a Free Quote button to a separate, complete form:

| Offer | Public landing page | Quote form |
| --- | --- | --- |
| Recruitment | https://nonprofitboardbuilder.com/recruit | https://nonprofitboardbuilder.com/services/recruitment/quote |
| Recommitment | https://nonprofitboardbuilder.com/board-recommitment | https://nonprofitboardbuilder.com/services/board-recommitment/quote |
| Fundraising | https://nonprofitboardbuilder.com/board-fundraising | https://nonprofitboardbuilder.com/services/board-fundraising/quote |
| Planning | https://nonprofitboardbuilder.com/strategic-planning | https://nonprofitboardbuilder.com/services/strategic-planning/quote |

Each form collects name, email and organization, followed by exactly the latest requested questions. Recruitment asks role, number to recruit, timing, location and intended contribution. Recommitment asks role, number involved, why they should recommit or step down and timing. Fundraising asks role, board size, fundraising amount and how board fundraising would help. Planning asks role, board size and how planning would help.

Submitting saves one customer record and opens a confirmation page. The first email is scheduled 60 minutes after completed submission. The first unpaid follow-up is scheduled 2,880 minutes (48 hours) after the first successful email. Further follow-ups default to 48 hours after the preceding successful email. All five can be edited, disabled or paused. Payment, unsubscribe, suppression and manual stopping retain their existing safeguards. A failed delivery does not start the next interval. The background task runs independently of the visitor's browser.

Every board offer remains $497. Emails contain the customer's correct payment link. After verified payment, the existing detailed leader questionnaire, branding and booking steps remain available without repeating the quote or paying again. Existing product workspaces, resources, participant forms, meetings, application links, documents and purchases are preserved.

## How to operate the admin

Open `/admin` and choose Recruitment, Recommitment, Strategic Planning or Board Fundraising. Blog & Content, Website Management and Help Requests are also visible there.

Each offer has these links above its searchable, paginated customer list. Every link opens its own page:

| Link | Contents |
| --- | --- |
| Edit Landing Page | Existing public-page content editor, including the actual fundraising homepage and explanation sections |
| Edit Quote Form | Heading, subtitle, contact labels, submit button, question wording/subtitles, count, order, required status, formats and preview |
| Edit Confirmation Message | Heading and message shown after submission |
| Edit First Email | Subject, preview, headline, message, CTA, supporting text, signature, timing and rendered preview |
| Edit Follow-Up Emails | Five independent templates and intervals, enabled status and offer-wide pause |
| Edit Post-Payment Form | The existing detailed leader questions and other paid-page copy; links to the relevant participant-question editor |
| Payment and Booking | Correct-service Calendly URL and payment, resource, dashboard, invitation and notification email templates |

Changes save to the existing database. Draft/publish controls apply to service configuration. Landing-page editors retain their existing save controls. Historic answers retain their original question snapshots when questions are edited, reduced, archived or removed.

Beside those editing links, each offer has one **Test Post-Payment Flow** button. It opens an isolated sample directly on the page a customer sees after payment, with prefilled leader answers. Continue through the paid questions and branding, then click the booking button to reach that offer's configured Calendly destination. It does not ask you to choose a customer, complete a quote or make a payment. Samples remain outside the customer list, and their emails are captured. The sample always uses the published post-payment questions and current booking configuration.

Click a customer's name to open a separate profile. It contains three areas: their quote request, their post-payment answers and branding, and their customer dashboard. Payment and first-email status appear above them. The customer list does not remain underneath the profile.

For a paid customer, Open Customer Dashboard opens the existing operational workspace. The owner can perform the service there. Copy Customer Dashboard Link returns the same saved dashboard address. The address includes a private capability in its fragment. Sharing the full address lets that customer return without a customer login. The server exchanges the capability for an HttpOnly, tenant-scoped session and checks paid access. Existing access revocation also invalidates this link and its sessions. Treat it as private customer access.

All personalized video recording, upload, assignment and sending controls and endpoints have been removed. AutoFundraiser is unchanged.

## Samples and blog publication

Explicit test/sample records are excluded from the normal customer list. Older records associated with the supplied test contacts and the administrator's email are archived from that list using a fixed cleanup cutoff, and their promotional sequences are stopped. No customer record, purchase, document or signed agreement is deleted. New ordinary quote submissions use the normal customer journey, even if that email address was previously used to test.

Blog & Content opens the existing five-pathway generator, article editor and schedule. Automatic weekday generation and publication are enabled by the updated configuration default. Once this configuration is saved, an explicit administrative pause remains authoritative. Existing duplicate prevention, bounded retries, article validation, images, published URLs and RSS remain in place. Real generation still requires the deployed application's working AI credentials and background worker.

## Verification

Email payment and continuation buttons appear before the sender's signature in all four services, including the first invitation, follow-ups and operational templates. The admin preview uses the same layout. This presentation change does not rewrite published or draft email settings; existing text, button labels, signatures and timing remain editable. Failed delivery retries retain their original content and links, and completed deliveries are not resent.

Verification completed: 192 backend tests, 62 frontend tests and 61 browser checks passed. The production frontend build, SEO, privacy and route checks passed. The full database/browser run used the existing GitHub Actions workflow with disposable MongoDB, the production frontend build and Playwright. See [the verification record](simple-quote-admin-verification.md) for the exact tested revision and the final local edge-case checks.

The release workflow exercised actual React/API navigation, all four quote/payment/post-payment paths, admin edit/save/reload, separate customer profiles, dashboard links in a fresh browser, full existing service workspaces, payment failure/security/legacy entitlement checks, email scheduling and duplicate suppression, and automatic blog publication. Stripe, email and AI providers were controlled in these tests. [Download the full desktop/mobile screenshot gallery](https://github.com/bigrooney007/Board-Builder/actions/runs/40094363241/artifacts/12560177707).

No live charge, production email, campaign, deployment or Emergent synchronization is performed by this release task. Controlled delivery tests establish application behavior, not a Gmail inbox receipt or production provider configuration. The owner initiates Emergent synchronization and deployment after receiving the final verified SHA.
