# Guided services, dashboard handover and automatic publishing

This guide supersedes earlier single-price Fundraising and Planning descriptions. Work continues on `feature/guided-board-services`, from `2670a558e861d17abc40e4d166fa2a0d8f54eb16`. It reuses the current Game, Planning engine, private customer records, Stripe dispatcher, delivery outbox and blog scheduler. AutoFundraiser is unchanged.

## The customer journeys

### Board Recruitment: $497

Promote **https://nonprofitboardbuilder.com/recruit**. Start for Free opens a compact name, email and organization dialog, then the published recruitment questions. Questions appear individually with their editable subtitles and current count. The completed submission ends at a thank-you page. Private AI board-profile recommendations appear in Rooney's service workspace, not in the unpaid response.

Approximately one hour later, the configured email invites that customer to the $497 guided service. After verified payment, they provide branding and book through Recruitment's own Calendly setting. In the meeting, Rooney reviews and approves the board profiles, confirms interview arrangements, generates and approves the current recruitment materials, and explicitly launches the campaign. Existing public opportunities, applications/CVs, notifications, interview decisions, references, appointment documents, agreements and signing remain in the original tools. The customer receives a secure resources link and can continue the agreed process independently.

The live opportunity directory is **https://nonprofitboardbuilder.com/board-opportunities**. A campaign appears there only after successful publication. Joining the applicant network remains **https://nonprofitboardbuilder.com/join-a-board**. External distribution is reported only when the existing permitted integration succeeds.

### Board Recommitment: $497

Promote **https://nonprofitboardbuilder.com/board-recommitment**. The same contact dialog leads to the current short questions, followed by a thank-you page. The automatic invitation leads to that customer's own $497 checkout, branding and Recommitment booking setting.

Rooney prepares the organization and invitations in the existing service workspace. Each board member receives an individual form and can recommit, propose another role or step down. Original decisions and explanations remain separate from human-confirmed arrangements. The authorized leader receives response notifications. Existing interpretation, conversation-guide, portfolio, agreement and signature capabilities are reused. Approved resources remain available through secure customer links.

### Board Fundraising: $497 or $1,497

Promote **https://nonprofitboardbuilder.com/board-fundraising**. The existing **/board-fundraising-game** route and How It Works page remain available. The primary action starts the free intake rather than demanding immediate payment.

1. The contact dialog asks for name, email and organization.
2. Six introductory questions collect mission, board size, custom fundraising goal, funding deadline, consequences of missing the goal, and the next board meeting's date, time and time zone. The full audience questionnaire is not asked here.
3. Submission saves a private lead and ends at the confirmation page.
4. The automatic first email, normally 60 minutes later, explains both options. Its two links belong to that particular customer. Subsequent unpaid follow-ups offer the same service and stop after either package is paid for.
5. **$497** buys preparation and self-facilitation. **$1,497** buys Rooney's facilitation and professional completion. The server uses separate Stripe identifiers and validates the selected amount and metadata. A success URL is not payment proof.
6. After payment, the customer supplies branding and opens the Fundraising preparation Calendly link. Mission, goal, deadline and meeting information are retained in the existing Game project.
7. Rooney opens that customer's existing Fundraising workspace, guides the leader through the current audience-by-audience Game, and invites board members. Their individual questionnaire and original responses remain unchanged. Submission emails open the correct organization's response resources.
8. For **$497**, Rooney confirms that preparation is complete and emails a dashboard handover invitation. The leader accepts it and operates the same prepared project. For **$1,497**, Rooney retains the facilitator role.
9. The operator runs the existing synchronized Group Game, discusses each audience, records the group's decisions and agreed participation, and uses the existing microphone/transcript controls with permission. Individual participants acknowledge their own adoption.
10. After the meeting, the operator reviews and edits the current audience-first strategy, saves it, approves it and triggers its email. Its PDF uses the current renderer, separates audiences onto their own pages, includes organization branding and retains only the agreed information. The new intake's goal, deadline and consequences are included. Unknown budgets, dates and commitments are not invented.
11. The operator can confirm each person's agreed role and use the existing current portfolio builder. Portfolios can be edited, approved, downloaded and emailed. Revisions require fresh approval; previous approved versions are retained.

### Strategic Planning: $497 or $1,997

Promote **https://nonprofitboardbuilder.com/strategic-planning**. The short, independently editable entry retains the vision, goals and required-resources defaults. Contact details are collected once. Submission ends at a thank-you page, followed by the independently editable two-option email.

After verified **$497 self-facilitation** or **$1,997 Rooney facilitation** payment, the customer supplies branding and books the preparation meeting. Rooney sets up the planning period, current mission, individual programs, response deadline and board meeting. The leader and board members receive their own independently configured forms. Board members do not receive the leader's private answers as prefills. Each program retains its own identifier and discussion.

For $497, Rooney hands over the existing project after preparation. The leader can manage invitations, view responses, facilitate the current Planning session, use transcription or typed notes, record adopted decisions, generate and edit the plan, release the approved review version, record board adoption/change requests, finalize and deliver it. For $1,997, Rooney operates these same tools from the admin. The transcript supports recorded decisions; it does not silently adopt suggestions. Editing a released plan requires new version-specific review. Leadership portfolios use the existing template and confirmed participant responsibilities, with editing, approval, branded download and delivery controls.

### Meet Rooney: $197 consultation

Promote **https://nonprofitboardbuilder.com/meet-rooney** for Rooney's biography, photograph, testimonials and independent product links. **https://nonprofitboardbuilder.com/consultation** collects the short consultation information and opens its separate $197 Stripe checkout. Only verified payment unlocks the configured Calendly step. A private payment email resumes booking without another charge. Consultation records and private notes remain separate from product customers.

**Complete Board Transformation** points to **https://nonprofitboardbuilder.com/**. AutoFundraiser remains an external link to **https://autofundraiser.com/**.

## Exact admin locations

Open **/admin**. Its service navigation links to:

- **Board Recruitment:** `/admin/services/recruitment`.
- **Board Recommitment:** `/admin/services/board-recommitment`.
- **Board Fundraising:** `/admin/services/board-fundraising`.
- **Strategic Planning:** `/admin/services/strategic-planning`.
- **Meet Rooney & Consultations:** the existing section on the main admin page.

In each service, **Customer Submissions → Open Service Workspace** opens the original answers, payment and booking state, selected package, delivery history and relevant tools. Recruitment and Recommitment retain their established workspace controls. Fundraising's **Open Fundraising Preparation and Facilitation** opens its existing Game workspace; Planning's controls remain embedded in its service record.

For the $497 Fundraising/Planning package, the selected customer has **Dashboard Ownership and Handover**. Confirm preparation, then click **HAND OVER DASHBOARD TO ORGANIZATION**. The invitation is emailed and can be copied during the meeting. Its link expires in 48 hours and exchanges explicitly for an eight-hour HttpOnly operator session. Sessions and invitations can be revoked. Authorization checks the service, paid package, exact customer, current ownership and session version. No empty replacement project or customer signup is created. Professional packages cannot use this control.

**Entry Questions / Free Entry Questions** controls count, wording, subtitles, order, required settings and formats. Planning also has separate **Lead User Planning Questions** and **Board Member Planning Questions**. Stable question/program identifiers and saved snapshots preserve historic answers.

**Landing Page Editor** edits the actual displayed page copy. Fundraising links to its existing full homepage/How It Works/Game instruction editors. **Customer Page Text** edits the confirmation, offer, package explanations, action labels and booking/handover copy. **First Response Email**, **Five-Email Follow-up Sequence**, **Personalized Video Follow-ups**, **Payment and Booking**, and **Invitation and Response Emails** retain independent service settings. The handover email is under Payment and Booking. Save drafts, preview, then publish settings. Changing visible wording cannot change a Stripe amount.

Each customer record provides the manually reviewed **Personalized Video Follow-up** composer. Paid customers receive a continuation link, not another purchase request. Sending a video does not restart the automatic sequence. All five unpaid follow-ups stop after payment, unsubscribe, suppression or a manual stop. Delivery retries reuse their event keys.

## Automatic blog generation and publication

**Admin → Blog Generator → Automatic generation and publishing** controls the existing scheduler's time, time zone and pause setting. This release reinstates automatic publishing by default. A new explicit pause saved in this version is respected.

| Day | Pathway | Article button destination |
| --- | --- | --- |
| Monday | Board Recruitment | `/recruit` |
| Tuesday | Board Fundraising | `/board-fundraising-game` |
| Wednesday | Strategic Planning | `/strategic-planning` |
| Thursday | Board Recommitment | `/board-recommitment` |
| Friday | Board Applicant Network | `/join-a-board` |

The existing background worker checks the schedule every five minutes. The default is 08:00 America/New_York, unless the saved schedule specifies another time. It generates the day's pathway once, validates the article and its cover, and publishes immediately. Failed automatic generations have bounded retries; invalid or failed content is not published. Published and administrator-edited articles are not regenerated by the scheduler.

The five topic libraries, article/graphic editor, stable URLs, archived posts, two fundraising guides, public blog, sitemap, RSS and social-discovery endpoints remain. Open an article and use **Edit Article and Graphic → Save Article and Graphic** whenever you want to change it. Manual generation/regeneration also publishes after generation checks. Historical pending drafts still support review and manual publication.

Public blog: **https://nonprofitboardbuilder.com/blog**. RSS: **https://nonprofitboardbuilder.com/api/blog/feed.xml**. Automatic website publication does not mean an external social network has published a post.

## Templates and compatibility

- Fundraising's authoritative output remains `fundraising_strategy_writing.document_sections`, selected by `fundraising_audiences.document_sections` for v7, then rendered by `strategy_pdf` through `document_renderer`. It retains the latest audience-first headings and page breaks.
- Fundraising portfolios reuse `fundraising_launch.build_portfolio_draft` and its current role-specific practical resources.
- Planning continues to use its original meeting/decision engine and the guided versioned plan editor. Leadership portfolios reuse the existing `/guided/strategic-planning/portfolios` template, with approval and branded delivery added around it.
- Recruitment still uses the existing `ai_service` generation definitions/finished-content formatter, approved-profile adapter, and current appointment-letter, agreement, board-manual and portfolio types. No older generator is substituted.
- Existing paid customers, saved invitations, sessions, source responses, transcripts and documents are not migrated into a new purchase or package. Existing prices and checkout routes remain available for their historical flows. AutoFundraiser is not modified.

## Evidence and release status

The release workflow runs Mongo-backed HTTP acceptance with controlled Stripe, email and AI transports; the production frontend build; current desktop/mobile browser journeys; access and delivery checks; and read-only public availability audits. Its artifact includes `current-screenshots.html`, original PNG screenshots, compact review sheets, downloaded document examples and per-suite JSON results. All pictured organizations and participants are synthetic.

The final handoff supplies the verified Actions run and final GitHub SHA. A GitHub commit, an Emergent sync and a production deployment are separate states. The owner initiates the sync and deployment. Controlled-provider tests do not establish actual Gmail receipt, live Stripe/webhook credentials, the production AI key or Calendly reservation confirmation. Those must not be described as verified without production evidence.
