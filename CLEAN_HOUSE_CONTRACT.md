# CLEAN HOUSE CONTRACT

This document is the routing and product-boundary contract for the simplified Nonprofit Board Builder application.

## 1. Public House

The clean public house has six home pages:

| Home page | Canonical route |
|---|---|
| Main Home Page | `/` |
| Board Recruitment | `/recruit` |
| Board Fundraising Game | `/board-fundraising-game` |
| Strategic Planning | `/strategic-planning` |
| Board Recommitment | `/board-recommitment` |
| Let's Organize Your Board Fundraising Game | `/organize-board-fundraising-game` |

The Main Home Page is the shared entry point for the product house.

The four paid Board Builder pathways do not cross-link to one another. The only product-to-product exception is the existing link from the Board Fundraising Game home page to Board Recruitment at `/recruit`.

Legacy public offers may remain in source while they are being retired, but they must not be restored to the clean live router unless the product contract is intentionally changed.

## 2. Four Paid Board Builder Pathways

### Board Recruitment

`/recruit`
→ contact capture
→ `/recruit/walkthrough`
→ Stripe
→ `/purchase/success`
→ `/recruit/welcome?session_id=...`
→ `/app/board-recruitment`

The present recruitment dashboard and the public/support routes it requires remain available until that dashboard is rebuilt separately.

### Board Fundraising Game

`/board-fundraising-game`
→ contact/profile capture
→ `/game/demonstration`
→ Stripe
→ `/game/welcome?session_id=...`
→ `/game/dashboard`

The Board Fundraising Game dashboard has now been rebuilt on the clean-house flow defined in Section 10. Reusable Game infrastructure remains available only where it supports that canonical flow.

### Strategic Planning

`/strategic-planning`
→ contact capture
→ `/strategic-planning/video?token=...`
→ Stripe
→ `/strategic-planning/payment-confirmed?session_id=...`
→ `/strategic-planning/welcome?session_id=...`
→ `/strategic-planning/dashboard?session_id=...`

The present Strategic Planning dashboard and its participant/session/public-plan routes remain available because an active organization is using this product.

### Board Recommitment

`/board-recommitment`
→ contact capture
→ `/board-recommitment/video?token=...`
→ Stripe
→ `/board-recommitment/payment-confirmed?session_id=...`
→ `/board-recommitment/welcome?session_id=...`
→ `/board-recommitment/dashboard?session_id=...`

The Board Recommitment dashboard has now been rebuilt under the clean-house flow defined in Section 11. Reusable Recommitment infrastructure remains only where it supports that canonical four-stage journey.

## 3. Facilitated Board Fundraising Game

`/organize-board-fundraising-game`
→ `/organize-board-fundraising-game/apply`
→ successful application confirmation: “We have received your application and will be in touch through email.”

This pathway stops after the application. It does not enter Stripe and it does not have a customer dashboard.

## 4. Board Applicant Network

Canonical route: `/join-a-board`.

The Board Applicant Network remains independent of the four paid pathways.

Required behavior:

1. A professional submits the Board Applicant Network application.
2. The complete applicant profile is saved in the admin backend.
3. The applicant receives the existing confirmation email.
4. The admin can inspect individual profiles and export applicant data.
5. When a nonprofit launches a live Board Recruitment opportunity, eligible consenting Board Applicant Network members receive the existing opportunity broadcast with their personalized application route.

Do not replace the existing applicant/opportunity backend with a parallel applicant database or parallel mailing system.

## 5. Eight Platform Videos

Each paid pathway has exactly two top-level funnel videos:

| Product | Demonstration | Onboarding |
|---|---|---|
| Board Recruitment | `recruitment_demonstration` | `recruitment_welcome` |
| Board Fundraising Game | `game_homepage` | `game_welcome` |
| Strategic Planning | `strategic_planning_demonstration` | `strategic_planning_welcome` |
| Board Recommitment | `board_recommitment_demonstration` | `board_recommitment_welcome` |

The admin video area manages these eight entries from one registry.

## 6. Six Home Page Content Sources

The admin home-page editor manages content for the six public home pages listed in Section 1.

Routes, payment destinations, dashboard destinations and the Board Fundraising Game → Board Recruitment exception are structural and must not be editable as marketing copy.

## 7. Admin House

The simplified visible admin navigation contains:

1. 4 Board Builder Pathways
2. 8 Platform Videos
3. 6 Home Page Text
4. Platform Analytics
5. Board Applicant Network
6. Strategic Planning

The Four Board Builder Pathways area must continue opening isolated preview sessions for the four real customer dashboards.

The active Strategic Planning admin workspace is preserved.

Legacy admin code may remain in source while it is being retired, but it should not be restored to the visible admin navigation unless deliberately reintroduced.

## 8. Analytics Contract

The clean analytics layer tracks the following separately by flow:

- unique visitors to each canonical home page
- people who submit contact/application details
- demonstration and onboarding video viewers
- average watch percentage for each of the eight videos
- checkout-start activity
- actual Stripe sessions and paid Stripe transactions by canonical product source
- unique dashboard entries
- unique recorded platform completions
- average active platform use per tracked user

Completion events are tied to meaningful product outcomes:

- Board Recruitment: final Board appointment confirmation
- Board Fundraising Game: Game completion route
- Strategic Planning: final Strategic Plan approval
- Board Recommitment: all recorded Board Member conversations have an outcome and conclusion

Analytics must not combine payment records across products.

## 9. Dashboard Rebuild Boundary

The clean public house, sales/payment paths, onboarding paths, admin controls and analytics foundation are the shared base.

Board Recruitment is now the first dashboard rebuilt on top of that base. Its canonical customer journey is:

1. Answer the Six Recruitment Questions.
2. Review, edit and approve the exact Board Member profiles the organization needs.
3. Review the Board Application and recruitment campaign materials prepared from the approved profiles.
4. Launch the recruitment campaign.
5. Review applicants and add outside applicants when needed.
6. Move applicants into Interviews by generating an interview invitation.
7. Generate a tailored interview guide for each interview candidate.
8. Run Reference Checks for candidates whose interview guide has been generated.
9. Use local Background Check search options when the organization chooses to conduct one.
10. Set the onboarding date/time, approve the organization-level onboarding materials and prepare the appropriate conditional or unconditional appointment email.
11. Facilitate the live onboarding session with presenter notes and a synchronized participant screen.
12. Review and approve each person's Board role before generating a Board Member Portfolio and a separate email draft for the founder to send from their own inbox.

The six Recruitment Questions are the authoritative strategic input for the Recruitment dashboard. Campaign assets are generated only from founder-approved Board Member profiles. Candidate progression is action-driven so the next stage unlocks from meaningful founder actions rather than manual card-moving.

Strategic Planning remains a separate rebuild phase. Board Recommitment and the Board Fundraising Game now have their own locked clean-house contracts below and must remain isolated from Recruitment and from each other.


## 10. Board Fundraising Game Dashboard Contract

The Board Fundraising Game is one connected fundraising-strategy process. Its canonical dashboard sequence is:

1. Play the founder's individual Board Fundraising Game.
2. Set the next Board meeting and the funding deadline.
3. Invite Board Members and other selected participants to play their individual Game.
4. Run the nine-screen Group Board Fundraising Game.
5. Generate and review the Final Fundraising Strategy and founder-approved participant delegations.
6. Share the strategy and move participants into their Board Fundraising Portfolios, relationship mapping and execution assistant.

### Founder Individual Game

The founder begins with an introduction and organization-logo setup.

The first four strategic questions are:
- Who should fund our mission?
- Where can we find them?
- How should we attract them?
- What step-by-step process should we use to raise money from them?

For every strategic question, preserve the founder's original idea. AI may make the idea more actionable, but the founder chooses whether to use the actionable version, keep the original or edit the answer.

After the four strategic questions, collect the organization's current fundraising reality through exactly these areas:
- current individual donors: who gives, why they give and how the organization raises money from them
- current business/corporate supporters: who supports, why and how the relationship works
- current grantors/institutional funders: who funds, why and how opportunities are found/pursued
- current fundraising team
- current fundraising technology
- current fundraising materials/content
- current fundraising budget

The individual-donor, business and grantor questions may be skipped when they genuinely do not apply. Team, technology, materials/content and budget require a real answer.

The founder then states how they want to participate in building/managing the fundraising system, how they want to help raise money directly, their realistic time commitment and anything else they want the Board to know.

Every question has a narration slot. The Game must remain fully usable when narration audio has not yet been generated.

Founder answers save throughout the journey. Completing the founder Game may prepare working intelligence in the background, but a working strategy must not be surfaced as the final Board strategy before Board participation and the Group Game.

### Meeting And Funding Deadline

Before invitations are sent, the founder must save:
- Board meeting date
- start time
- timezone
- meeting format and meeting link/location where applicable
- funding deadline

The funding deadline becomes the fundraising goal deadline and is authoritative for execution planning. The final execution plan must use the actual days available and must not force an arbitrary 90-day or 120-day plan.

### Board Member Individual Game

Each invited participant receives a private Game link. The founder can send/resend invitations, copy the link, review responses and generate the existing person-specific call script.

Invited participants answer the same four strategic questions and receive the same original-idea → actionable-version → participant-approval treatment.

They then state:
- how they want to help build/manage the fundraising system
- how they want to participate directly in raising money
- their realistic time commitment
- anything else they want to contribute

Invited participants do not repeat the founder's organization-current-reality questions.

### Group Board Fundraising Game

The Group Game contains nine decision screens:
1. Who should fund us?
2. Where will we find them?
3. How will we attract them?
4. What fundraising process will we use?
5. Team
6. Technology
7. Materials and content
8. Budget
9. Execution and accountability

The first four screens bring together founder ideas and participant ideas. The funding-audience screen also includes the organization's present donor, business and grantor reality.

Team combines the present team, every participant's stated willingness to help and the capacity the strategy requires. Missing capacity must be shown as a role/capacity need rather than silently assigned.

Technology, materials/content and budget compare the organization's current reality with the capabilities/resources the chosen strategy requires.

Execution compares current fundraising practice with a deadline-driven execution recommendation based on the actual funding deadline.

The host's selected checkboxes and additional agreed wording are authoritative Board decisions. Meeting transcription is optional enrichment used for clarifications, delegation and nuance. Transcript content must not silently override explicit Group Game decisions.

When the final Group Game screen is adopted, final-strategy generation begins immediately in the background. The completed meeting screen may surface the Final Strategy as soon as generation is finished.

### Final Fundraising Strategy

The Final Strategy should function like a concise two-to-four-page operating roadmap rather than a meeting transcript.

It must make the following executable:
- fundraising goal and funding deadline
- funding audiences
- where/how those audiences will be found repeatedly
- attraction approach
- step-by-step fundraising process
- Board network fundraising process
- team and ownership/capacity gaps
- technology
- materials/content
- budget
- deadline-driven execution timeline

The Board network process must show Board Members how to identify suitable funders in their personal/professional networks, map relationships, make or enable introductions and move prospects through the organization's agreed Know → Like → Trust → Ask → Follow Up → Steward process.

### Founder Delegation Approval

After the Final Strategy is generated, prepare a proposed delegation for every person who actually contributed to the Game or Group Game.

Each proposed delegation separates:
- responsibilities for building/strengthening the fundraising system
- direct fundraising activities and network-based execution

The founder must be able to edit the proposal and explicitly approve it.

A participant's Final Strategy email must remain locked until that person's delegation is founder-approved.

### Strategy → Portfolio → Execution

The Final Strategy email sends one secure strategy link.

The secure strategy contains the CTA **How Do I Get Involved?** which opens that participant's Board Fundraising Portfolio.

The Portfolio shows their founder-approved system-building and direct-fundraising responsibilities. The participant may approve it or request a change.

After approval, the existing relationship-mapping, execution-material and Board Fundraising Executive Assistant capabilities support execution from the adopted strategy and approved Portfolio.

Do not scatter duplicate strategy-send controls back into the Board invitation section. Final strategy delivery belongs in the final Strategy / Execution stage of the dashboard.


## 11. Board Recommitment Dashboard Contract

Board Recommitment is a four-stage decision and transition process. Do not restore the prior multi-module dashboard, Founder Board Audit, separate invitation stage or standalone progress section.

### Stage 1: Answer Four Important Questions

The founder answers these questions one screen at a time:
1. Organization mission statement.
2. Why the Board needs to recommit and step up now.
3. What the organization needs these Board Members to help accomplish.
4. The date by which the renewed Board commitment needs to be in place.

The opening screen also allows the organization logo to be added. The organization name is already known and must not be asked again.

Every answer is saved into the same Recommitment context and is available to all downstream forms, response interpretation, call scripts and Board Member Portfolios.

### Stage 2: Prepare And Send The Recommitment Forms

The founder prepares one approved Recommitment Form introduction and receives two public form variants:

1. **Active Board / Advisory Board**: the Board Member may recommit as an active Board Member and step up, or transition into an Advisory Board role. This form must not offer stepping down.
2. **Full Recommitment / Transition**: the Board Member may recommit as an active Board Member and step up, transition into an Advisory Board role, or step down gracefully.

The old unsure pathway and generic volunteer/support-role pathway are not part of the clean product.

The founder can:
- copy either public form link,
- edit and approve the outreach email,
- copy the approved email with the correct form link inserted,
- add a Board Member by name and email,
- choose which form that person receives,
- send or resend the form directly from the platform.

### Stage 3: Review Responses And Prepare The Conversation

Every submitted form appears automatically.

For each respondent, the founder can:
- view the complete submitted response,
- download the response,
- generate and review an interpretation of the response,
- generate, review, edit, approve and download the person-specific one-on-one call script.

The submitted choice supplies the default conversation direction:
- active recommitment -> Remain and Step Up
- Advisory Board -> Move to Advisory Board
- step down -> Step Down

That direction is preparation only. The founder's saved post-conversation agreement and final outcome remain authoritative.

### Stage 4: Confirm The Final Outcome And Move The Person Forward

After the one-on-one conversation, the founder records what was actually agreed and chooses exactly one final path:
- Continuing as an Active Board Member
- Transitioning to an Advisory Role
- Stepping Down From the Board

For Active and Advisory outcomes, the founder must confirm or edit the person's final role before any Portfolio can be generated.

An Active Board Member receives a Board Member Portfolio built from the confirmed role, submitted profile information and authoritative conversation agreement.

An Advisory Board Member receives an Advisory Board Member Portfolio plus the Advisory transition email.

A person stepping down does not receive a Portfolio. The platform prepares the Board departure email using the actual conversation agreement and any verified governance/resignation context supplied by the organization.

### Portfolio Delivery And Execution

The founder reviews and approves the Portfolio before delivery.

The Portfolio email can be:
- copied for sending from the founder's own inbox, or
- sent directly from the platform.

An approved Active or Advisory Board Member Portfolio includes access to that person's Executive Assistant.

The Executive Assistant is constrained by:
- the approved Portfolio,
- the founder-confirmed role,
- the authoritative conversation agreement,
- the verified organization context.

It must not invent responsibilities or authority outside the approved role. It may help turn approved responsibilities into next actions, checklists, working drafts and execution materials.

### Dashboard UX

The customer-facing dashboard contains only four primary collapsible sections corresponding to the four stages above.

Every section has its own admin-managed YouTube help-video slot.

A persistent branded support area remains at the bottom of the dashboard.

Do not add the old Founder Board Audit, old separate invitation module, old separate progress module, support-role pathway or unsure pathway back into the canonical clean dashboard.
