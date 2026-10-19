# Part One: main directory and Rooney consultations

Starting release: `feature/fundraising-game-simplified` at `549b3d2db5b6fdf96ae9a396d4e141df3fd77622`.
Working branch: `feature/nbb-main-consultations`.

## Customer routes

- `/`: the existing MainHomePage design, restored as a four-service directory with the supplied headlines, promises and landing-page buttons. Existing blog links, testimonials and applicant network access remain.
- `/board-fundraising`: friendly alias preserving query parameters and opening `/board-fundraising-game`.
- `/board-fundraising-game`: the existing Fundraising Game landing page. The game itself, its $1,497 checkout, organization setup, questions, invitations, participant links, microphone, transcription, adoption, strategy generation and dashboards are unchanged.
- `/meet-rooney`: supplied biography, existing portrait, original testimonials, $197 consultation and independent product links.
- `/consultation`: short consultation form and dedicated Stripe checkout.
- `/consultation/confirmed`: server-verified payment confirmation.
- `/consultation/resume/:token`: secure recovery and booking, without another purchase.

The existing recruitment, strategic planning and recommitment public landing/intake/payment pages are accessible again. Their questionnaires, pricing, backend access controls, product configuration and dashboards are unchanged. Existing `session_id` payment returns still go through `/purchase/success`. Existing participant, applicant, strategy and resource URLs remain registered. Historical game entry aliases remain intact.

## Administration

`/admin` retains the current Fundraising Game administration and adds:

- **Main Homepage**: directory headings, text, four service cards and labels.
- **Meet Rooney & Consultations → Personal Page Editor**: all personal-page copy, safe Markdown formatting with toolbar/preview, portrait URL, product links, original testimonial selection and ordering.
- **Consultation Settings**: Calendly destination, optional duration, form/confirmation/recovery wording, email wording and call-to-action labels. Price is not a text-editable setting.
- **Consultation Customers**: separately paginated records, discussion topic, organization/contact details, payment references/status, observed booking status, private before/after notes, email delivery status and secure-link resend.

The existing Fundraising Game homepage editor is labelled **Fundraising Page Editor** to distinguish it from the main directory editor. No Fundraising Game editing controls were removed.
The historical administration's main-homepage editor reads and writes the same new directory content, so it cannot silently save text to an unused page.

## Payments, email and booking

The consultation uses `rooney_professional_consultation_197`, $197 USD (`19700` cents), in a separate `consultations` collection. It never grants any of the four product entitlements or creates a product member account.

The existing Stripe account/resolver creates or retrieves the dedicated product and price. Optional `STRIPE_ROONEY_CONSULTATION_197_PRICE_ID` must identify an active, one-time USD $197 price. Existing Stripe and product prices are unchanged.

The existing signed `/api/stripe/webhook` dispatches consultation events separately. Server retrieval verifies session ownership, consultation metadata, product identifier, USD subtotal/total and paid status. Visiting a success URL alone does not unlock booking. Open checkouts are reused, expired sessions can be replaced with a new idempotency key, and paid records return their existing booking entitlement. Prior session IDs remain in the record.

Existing Resend transactional delivery provides a durable outbox, stable provider idempotency keys and safe retries. Confirmation and recovery emails contain a high-entropy secure resume link. A separate recovery loop reconciles interrupted confirmations and failed email delivery. Its messages do not expose discussion topics or payment references. Existing product email rendering retains its default call-to-action.

The booking destination initially reuses the existing project URL, `https://calendly.com/boardbuilder/recruitboard`, and can be changed independently in Consultation Settings. Booking is released by the payment-checked server redirect, with name, email and an opaque consultation ID only. Opening Calendly is recorded as **link opened**, never as a confirmed reservation.

Optional signed Calendly notifications use `/api/consultations/calendly-webhook` and `CALENDLY_WEBHOOK_SIGNING_KEY`, subscribing to `invitee.created` and `invitee.canceled`. They correlate the paid record using `tracking.utm_content` and invitee email. Without this integration, booking status remains unconfirmed; no meeting details are invented. Configuring a signing key alone does not create the provider webhook subscription. A normal Calendly URL can still be visited outside this application; the website booking journey requires payment.

Private consultation pages/APIs are noindex, no-store and use a no-referrer policy. Their initial HTML excludes public analytics and session-recording scripts while retaining the application's local bundles and styles. Consultation buttons load this private document directly. Previously verified paid entitlements can resume even during a Stripe outage. Admin content and customer records require existing administrator authentication. Public responses omit booking destinations, Stripe references, private notes and email delivery records.

## Verification and release status

Initial local production build, eight public-page SEO checks, redirect checks and 45 React tests pass. The historical-editor adapter has an additional passing regression test. Python compilation and private-page privacy checks pass. The initial GitHub Actions run passed 100 backend tests, including 17 consultation checks, and all 14 existing Fundraising Game desktop/mobile checks. The new-page browser run identified an admin field label requiring an explicit accessible name; this was corrected. The expanded final run includes paid-resume provider-outage coverage and Chromium desktop/tablet/mobile workflows; its final results must be recorded before handoff.

The legacy `test_blog_workstation.py` suite contains expectations for generating five blog categories, whereas the starting release already restricts new generation to Board Fundraising. Its eight failures were reproduced on an untouched checkout of `549b3d2` and are unrelated to Part One. Blog implementation is unchanged; current public blog/RSS access is checked separately. The historic recovered-release workflow freezes the homepage and routes against `a33a640`, which conflicts with this explicitly authorized Part One. This branch instead uses the full Fundraising Game regression workflow plus `validate_part_one_scope.py`, which protects the actual starting release's product code, prices, questions, meeting tools, testimonials, blogs and existing route registrations.

Production integration settings are not available in the development environment. Real Stripe account permissions, deployed webhook subscriptions, real email inbox receipt and the Calendly event configuration are not verified by simulations. Deployment requires the existing Emergent environment and established synchronization/deployment process. No production deployment or synchronization is performed by the implementation tests.

Stop after Part One. No AutoFundraiser application files or Parts Two, Three or Four are included.
