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

## Verified results

Application code verified at `605b06f59e4cbe1dd8d40e86e8c47dd2995ee576`:
https://github.com/bigrooney007/Board-Builder/actions/runs/39266958145

- **101 backend tests passed**, including 18 consultation configuration/HTTP/security/delivery cases and 83 existing-product regressions. The HTTP cases use real FastAPI handlers and disposable Mongo. Stripe and Resend transport are simulated; no real charges or email sends occur.
- **46 React tests passed**, including directory/personal/consultation rendering, safe formatting, unpaid/failed confirmation and the historical main-editor adapter.
- **35 browser acceptance cases passed**: 14 unchanged Fundraising Game desktop/mobile checks and 21 Part One desktop/tablet/mobile checks at 1440, 768 and 390 pixels. These cover four-service links, original intake access, friendly game alias, portrait and testimonial carousel, admin editing/persistence/testimonial ordering, controlled $197 checkout, confirmation email generation, paid recovery, Calendly handoff, cancelled-payment denial, private notes and resend.
- Production build passed locally and in GitHub Actions. Dependencies installed from the unchanged frozen Yarn lockfile.
- Eight public-page initial-HTML/SEO/social-image checks, sitemap/robots checks, route redirects, private consultation analytics/referrer/cache protection, Python compilation and the Part One scope guard passed.
- Desktop and mobile screenshots were inspected, including the personal page, directory and paid confirmation page. No horizontal overflow was detected in the tested customer layouts.
- Read-only production checks returned HTTP 200 for the existing homepage, four original product URLs, API health and payment config. The existing payment config reports live mode. This does not establish that Part One is deployed or verify private Stripe credentials.
- The connected Calendly account confirmed `https://calendly.com/boardbuilder/recruitboard` is active, has a 30-minute event, contains no free-consultation advertisement and imposes no additional Calendly payment. Fifteen bookable times were returned for October 20–26, 2026. No meeting was booked or changed. Its existing event name is **Build A Strong Fundraising Board**; the owner can choose another consultation destination independently in the new admin settings.

The final handoff commit changes this document only; its application code matches the verified commit above. GitHub's existing Fundraising Game branch remains at `549b3d2db5b6fdf96ae9a396d4e141df3fd77622`. No production branch was merged, reset or force-pushed.

## Known limits and production handoff

The legacy `test_blog_workstation.py` suite contains expectations for generating five blog categories, whereas the starting release already restricts new generation to Board Fundraising. Its eight failures were reproduced on an untouched checkout of `549b3d2` and are unrelated to Part One. Blog implementation is unchanged; current public blog/RSS access was checked separately. The historic recovered-release workflow freezes the homepage and routes against `a33a640`, which conflicts with this explicitly authorized Part One. This branch instead uses the full Fundraising Game regression workflow plus `validate_part_one_scope.py`, which protects the actual starting release's product code, prices, questions, meeting tools, testimonials, blogs and existing route registrations.

Real consultation transactions, private production Stripe credentials/webhook configuration, actual email inbox receipt, and the Calendly webhook subscription/signing key remain **unverified**. The application reuses the existing Stripe/Resend services. Live credentials and Emergent deployment controls are not available in the development environment, so no new-production launch or provider delivery is claimed. Calendly URL/activity/availability was verified separately through its connected account.

The core consultation booking journey does not require a new preview feature flag. Customers pay through the dedicated server-side Stripe product and then book using their paid entitlement. Automatic confirmed/cancelled booking status requires the optional signed Calendly webhook subscription; without it the record honestly shows the booking link was opened. This does not prevent choosing a meeting time.

**Committed to GitHub:** yes. **Synchronized to Emergent:** no. **Part One deployed to production:** no.

The owner must synchronize the exact final commit on `feature/nbb-main-consultations` into the existing Emergent project and use the established deployment controls. Do not ask Emergent to recreate or modify the implementation. After deployment, real-provider acceptance must verify the consultation payment, confirmation inbox receipt and booking on the deployed host before calling the live integration fully verified.

Stop after Part One. No AutoFundraiser application files or Parts Two, Three or Four are included.

## Changed files

`A` means added, `M` means modified, compared with the actual starting release.

```text
M	.github/workflows/current-workflow-validation.yml
M	.github/workflows/simplified-fundraising-validation.yml
A	backend/consultation_routes.py
M	backend/payment_routes.py
M	backend/server.py
A	backend/tests/test_consultations.py
M	backend/workflow_delivery.py
A	docs/part-one-professional-entry.md
A	frontend/scripts/consultation-page.cjs
M	frontend/scripts/fundraising-redirects.cjs
M	frontend/scripts/landing-seo-middleware.cjs
M	frontend/scripts/prerender-landings.cjs
M	frontend/scripts/serve-public.cjs
M	frontend/src/App.js
M	frontend/src/admin/FundraisingAdminPage.jsx
M	frontend/src/admin/HomepageTextSection.jsx
A	frontend/src/admin/ProfessionalAdminSection.jsx
M	frontend/src/admin/RecoveredOffers.test.jsx
M	frontend/src/components/TestimonialCarousel.jsx
M	frontend/src/content/landingSeo.json
A	frontend/src/content/professionalEntry.json
M	frontend/src/game/FundraisingPublicPages.jsx
M	frontend/src/pages/MainHomePage.jsx
A	frontend/src/professional/ConsultationPage.jsx
A	frontend/src/professional/MeetRooneyPage.jsx
A	frontend/src/professional/ProfessionalEntry.test.jsx
A	frontend/src/professional/RichContent.jsx
A	frontend/src/professional/content.js
A	frontend/src/professional/professional.css
M	frontend/src/seo/landingMetadata.js
A	tests/consultation_privacy.cjs
M	tests/current_workflow_app.py
M	tests/fundraising_redirects.cjs
A	tests/professional_entry_browser.py
M	tests/simplified_fundraising_browser.py
A	tests/validate_part_one_scope.py
```
