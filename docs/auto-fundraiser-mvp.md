# Auto Fundraiser MVP

This branch adds Auto Fundraiser as an isolated product inside the existing repository. It does not modify Board Fundraising Game, Recruitment, Strategic Planning, Recommitment, or Board Applicant Network product files.

## Product flow

1. `/auto-fundraiser`
   - One dominant fundraising-approach composer.
   - User can type their current approach, attach PDF/DOCX/TXT/MD/CSV, or choose “I don't have a fundraising strategy.”
   - Name, email and organization are captured before analysis.

2. `/auto-fundraiser/review/:token`
   - AI reads the submitted fundraising material first.
   - It checks WHO, WHERE, ATTRACT, RAISE, ASK and SYSTEM.
   - It asks only yes/no clarification questions for missing or unclear elements.
   - It does not ask the user to build the strategy for free.
   - A confirmed “no” ends downstream questioning and moves to diagnosis.

3. `/auto-fundraiser/result/:token`
   - Personalized fundraising diagnosis.
   - No free strategy generation.
   - $497 one-time Strategy Builder checkout.

4. `/auto-fundraiser/strategy/:token`
   - Available only after Stripe confirms payment.
   - Five strategy questions modeled on the existing fundraising-question format.
   - Present fundraising reality across individual donors, businesses and grantors.
   - Personal participation question.
   - Meeting scheduling and contributor invitation.

5. `/auto-fundraiser/contribute/:token`
   - Invited board members, staff, volunteers or other contributors answer the same five questions plus participation.
   - The strategy owner receives an email when someone completes the planning form.

6. `/auto-fundraiser/meeting/:token`
   - Group planning view.
   - Responses are shown by question and source.
   - The group selects the ideas it wants to adopt.
   - Auto Fundraiser builds the final strategy from adopted ideas, present reality and participation commitments.

7. `/auto-fundraiser/admin`
   - Separate Auto Fundraiser admin key.
   - Edit homepage and result-offer copy.
   - See every person who entered the funnel, stage, payment state, contributor count and last activity.
   - Manually send resume or payment follow-up email.

## Automated lifecycle email

A standalone Auto Fundraiser reminder loop runs hourly:

- Incomplete diagnostic: one resume email after 6 hours of inactivity.
- Diagnosis completed but unpaid: one payment reminder after 18 hours of inactivity.
- Contributor completion: immediate email to the strategy owner.

## Required production environment

- `OPENAI_API_KEY`
- `AUTO_FUNDRAISER_MODEL` optional, defaults to `OPENAI_MODEL` then `gpt-4.1-mini`
- `STRIPE_SECRET_KEY`
- `AUTO_FUNDRAISER_STRIPE_WEBHOOK_SECRET`
- `AUTO_FUNDRAISER_FRONTEND_URL` e.g. `https://yourdomain.com`
- `AUTO_FUNDRAISER_ADMIN_KEY` (falls back to `ADMIN_PASSWORD` if present)
- `RESEND_API_KEY`
- `AUTO_FUNDRAISER_FROM_EMAIL` (falls back to `RESEND_FROM_EMAIL` or `EMAIL_FROM`)

Existing `MONGO_URL` and `DB_NAME` are reused, but all product data is isolated in:

- `autofundraiser_leads`
- `autofundraiser_contributors`
- `autofundraiser_settings`

## Board Builder protection

The only existing shared files changed are:

- `frontend/src/App.js` to register Auto Fundraiser routes.
- `backend/server.py` to register the Auto Fundraiser API router.

No Board Fundraising Game, Recruitment, Strategic Planning, Recommitment, Board Applicant Network, board content, board prompts, board emails, board payment logic or board database flow was modified.

## Deployment note

This branch has been built by code inspection only. No local build, test suite, browser automation, Stripe call, Resend call, OpenAI call, screenshot run or deployment has been executed.
