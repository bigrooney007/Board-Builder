# Nonprofit Board Builder PRD

## Original Problem Statement
Build only one professional green Nonprofit Board Builder landing page, one four-step board assessment form, one confirmation screen, MongoDB storage for every submission, and one owner email containing every answer. No accounts, dashboards, payments, AI, recruitment automation, CRM, scheduling, scraping, background jobs, or additional pages. Use the user-provided logo and the exact supplied content, questions, options, and confirmation messaging.

## Architecture Decisions
- React single-page experience with three states: landing, assessment, confirmation.
- FastAPI `POST /api/assessments` validates and stores submissions in MongoDB.
- Each submission receives a `NBB-YYYYMMDD-XXXXXX` number, UTC timestamp, and `New Board Assessment` status.
- Resend owner notification is attempted after persistence; email failure never rolls back the saved assessment.
- Email settings are environment-driven through `RESEND_API_KEY`, `SENDER_EMAIL`, and `OWNER_NOTIFICATION_EMAIL` (or `OWNER_EMAIL`).

## Implemented
- Responsive landing page with navigation, hero, three transformation stages, six discovery cards, calls to action, supplied logo, and footer.
- Four-step assessment containing every required and optional field, exact options, validation, progress, Back/Next controls, phone helper text, and confirmation checkbox.
- Complete database submission, unique metadata, owner email template with all answers under four required headings, and confirmation screen.
- One E2E assessment was submitted and fully verified in MongoDB; confirmation and mobile layout passed.

## Prioritized Backlog
- **P0:** Provide `RESEND_API_KEY`, `SENDER_EMAIL`, and `OWNER_NOTIFICATION_EMAIL`/`OWNER_EMAIL` in backend environment; owner delivery cannot run without them.
- **P0:** Repeat the single E2E submission after email configuration and confirm one delivered email contains all answers.
- **P1:** None within approved scope.
- **P2:** None within approved scope.

## Next Tasks
1. Add the missing owner-email environment settings.
2. Repeat the specified E2E flow once to verify delivery.