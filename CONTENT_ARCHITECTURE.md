# Content Architecture — Nonprofit Board Builder

This document is the reference for where every piece of user-facing copy lives and
how to add new content without creating hardcoded strings.

## Canonical content sources

| Content | Canonical location |
|---|---|
| Public website copy (Homepage, About Rooney, Board Transformation + Result, Recruit/Reactivate/Activate with Rooney, DIY offers, DWM proposals, Start Here pages) | `frontend/src/content/siteContent.js` |
| Authenticated application copy (course shells, Reactivation Steps 1–5, Activation shell, Recruitment shell, shared course navigation/forbidden states, Strategic Planning admin workspace labels) | `frontend/src/content/appContent.js` |
| Module & step definitions — numbers, titles, kinds for Recruitment (Basic + Self-Guided), Reactivation, Activation | `backend/course_content.py` (frontend consumes them via the course APIs — never redefine module titles in React) |
| Static customer email templates (recommitment outreach, reminder, reminder call script, recommitment form introduction) | `backend/content_templates.py` |
| AI resource-generation prompts and output schemas (ALL products + Strategic Planning) | `backend/ai_service.py` → `GENERATION_TYPES` |
| Strategic Planning static emails (form invitation, review invitation, area pack email, final delivery, action plan delivery) | `backend/strategic_planning_routes.py` (template helper functions: `generic_form_email`, `planning_email`, `review_email`, etc.) — candidates for future move into `content_templates.py` |
| Recruitment workspace emails (interview invitation, reference check, conditional offer, portfolio email) | built dynamically in `backend/workspace_routes.py` / `refinement_routes.py` from AI-generated material + candidate data |

## Content key conventions

Use stable, descriptive, dot-path keys, e.g.
`recruitmentContent.module1.heading`, `reactivationContent.step3.understandButton`,
`activationContent.overview.previewBody`, `strategicPlanningAdminContent.buttons.generateDraft`,
`sharedCourseContent.forbidden.heading`.

- Customer wording and Admin/operator wording are SEPARATE entries even when the
  action is the same (`strategicPlanningAdminContent` is operator-only).
- When the same concept intentionally reads differently in two contexts, keep two
  named keys — never force them to share one string.

## What must NEVER move into content files

- Route paths, entitlement identifiers, product keys, DB field names, API
  contracts, feature flags, tokens, test IDs (`data-testid`), CSS classes.
- AI generation prompts/schemas (they are behavioral, canonical in `ai_service.py`).
- Dynamic values (names, counts, dates, AI-generated text).

## How to add new content

1. Add the string to the appropriate canonical file under a descriptive key.
2. Import that key in the component/route — never inline the literal.
3. Static emails: add a template function in `backend/content_templates.py` and
   call it from the route.
4. New module/step: define it in `backend/course_content.py` only.

## Current centralization state (June 2026)

- Public pages: fully centralized in `siteContent.js` (16 pages).
- Reactivation app experience: fully centralized in `appContent.js`.
- Shared course chrome (forbidden card, module-1 training cards, activation
  overview/preview, video placeholders): centralized in `appContent.js`.
- Strategic Planning admin workspace: section headings + primary action buttons
  centralized (`strategicPlanningAdminContent`); remaining inline helper text is
  scheduled to migrate during the next Strategic Planning pass.
- Recruitment/Activation deep workspace components (`ApplicantModules.jsx`,
  `WorkspaceModules.jsx`, `ActivationModule2–5`, `MaterialCard.jsx`) and public
  funnel form pages still hold inline copy — migrate them into `appContent.js`
  during their respective correction passes, using the conventions above.
