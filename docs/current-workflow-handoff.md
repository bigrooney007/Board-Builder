# Existing customer workflow updates

Base: `a33a64082199fd6c508b0360552bdadf5c9ee5c3` on the recovered original application.
Branch: `fix/planning-fundraising-current-flows-20261015`.

This branch does not include `feature/nbb-simplified-final`. No deployment, production merge, environment changes or Emergent sync is performed by this work.

## Strategic Planning

The existing Start for Free route collects the exact 15 conversational questions supplied in the brief. The same canonical configuration supplies personal board forms, admin fixtures and the group discussion. Existing mission information is retained as background and is not a questionnaire or adoption topic. The paid handoff saves the leader's original contribution once; it does not ask the leader to repeat it. Logo upload remains available after purchase, followed by the existing meeting setup and invitations.

The existing group route displays attributed proposals under the same 15 questions. The facilitator can select individual ideas, refine wording or save a new discussion idea for explicit selection. Source responses remain intact. A consolidated review contains only selected ideas. Each person uses their own contribution token to acknowledge that revision and accept their own responsibilities. The facilitator adopts the reviewed direction before generating the 24-month plan. The AI receives adopted decisions and existing mission background, without discarded ideas or transcript decisions. Existing final editing, approval, PDF, delegation and portfolio tools remain available. Approving the current plan saves the exact wording and attempts its transactional email and records the delivery result; the existing share action delivers the approved version to participants.

Historical projects retain their original form and session format. There is no migration of completed customer projects.

## Board Fundraising Game

The existing leader and personal invitation routes render one shared audience form. Each audience has six separate answers, an identifier and its contributor. The participant may add further audiences, skip any category, indicate uncertainty, save progress and edit before submission. Personal participation comes last. New games skip the separate present fundraising reality questionnaire; saved older games continue in their original format.

The existing Group Game presents each complete audience approach, attributed to its proposer. The facilitator may edit, add or combine proposals and explicitly adopt or reject each. Combined proposals retain their source identifiers. Participation statements remain proposals until a named person's agreement is explicitly confirmed. The group reviews a selected-only summary, the facilitator adopts it, and each joined participant can independently acknowledge it. Outstanding acknowledgements are displayed without inventing an absent person's agreement.

The strategy preview uses only approved audiences and confirmed commitments. The facilitator approves the exact final wording before it is frozen and delivered to the leader and valid participants through their existing secure links. Downloads use the approved text. Repeated approval and delivery retries use stable event/provider idempotency keys. The existing portfolio data contract is retained using approved audiences and confirmed roles. The group is not forced into additional execution stages.

## Admin Client Testing Center

Existing fresh and preloaded buttons remain. Planning and fundraising now seed the current canonical questionnaires rather than historical fixture copies. Additional introductory-question buttons open the real leader forms with authorized test access. No separate customer-facing test forms are maintained. The test banner displays the workflow version.

All four product launchers continue to open their real client routes. Existing Board Transformation and older Fundraising Activation service test buttons also use separate synthetic identities and the actual client intake routes; they no longer alter a real member's entitlements or copy an administrator password. Historical test progress and customer records are retained.

Synthetic test requests capture Resend emails, including background tasks inheriting the test scope. Normal customer requests retain the original transport. Test checkout handoffs validate ownership and replace payment only for the existing isolated admin identities. Other real checkout actions are disabled for those test identities. Synthetic campaigns are excluded from public marketplace discovery and remain subject to the existing applicant-network test delivery rule.

## Verification

Run the `Current Customer Workflow Validation` GitHub Actions workflow on this branch. It installs existing pinned dependencies and the frozen frontend lockfile, executes current route integration tests against disposable Mongo, runs the recovered regression suites, builds the production frontend, and exercises current and original desktop/mobile pages with Chromium.

- Current backend tests cover shared question parity, all four admin launchers, introductory handoff, leader answer reuse, personal progress/submission, selection-only generation, individual acknowledgements, confirmed fundraising commitments, document approval, failed email retry, duplicate protection, immutable submissions, authorization and historical game compatibility.
- The original backend suites and 31 React checks cover the recovered offers, original Start for Free/checkout connections, video preservation outside payment pages, and recruitment scheduling/publication handlers.
- Browser checks use actual current React components and backend handlers for planning and fundraising. The additional recovered browser suite covers admin content editing, original offers/checkout handoffs and recruitment navigation at desktop/mobile sizes; its provider/workspace calls are explicitly simulated.
- Tests never load production `.env`, contact actual Stripe/AI/Resend providers, or send a test campaign to the applicant network.

The authoritative results and screenshots are attached to the final successful workflow run. A passed synthetic email test establishes application dispatch, scoping and retry behavior; it does not establish inbox receipt.

## Live testing and access

No administrator credentials have been reset or created. The supplied administrator email identifies an existing account; it does not provide an authenticated session. Sign in normally and use Admin → Client Testing Center after syncing and deploying this branch. No GitHub administrator-email secret or GitHub environment is required for those in-app tests.

Live Stripe charges, AI output quality and receipt at the four supplied Gmail addresses remain unverified without authenticated deployed access and the configured live providers. No live emails have been sent by this implementation session. The earlier successful deployed-public check belongs to the recovery release and is not a deployment test of this new branch.
