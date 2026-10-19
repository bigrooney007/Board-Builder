# Nonprofit Board Builder: customer journeys and operating guide

This release implements the four instructions as one service platform. It preserves the existing Fundraising Game and its $1,497 configuration, existing customer journeys and entitlements, blogs, RSS, applicant network and historical administration. AutoFundraiser is an external link only.

The main website is a four-service directory. Recruitment and Recommitment each cost $497. Facilitated Strategic Planning costs $1,997. A separate professional consultation with Rooney costs $197. These purchases do not unlock each other.

## 1. Professional consultation with Rooney

1. A visitor follows **Meet Rooney** from the main homepage, or opens `https://nonprofitboardbuilder.com/meet-rooney` directly. They see the supplied biography, existing professional portrait and selected original testimonials.
2. They can choose the separate AutoFundraiser link, **Complete Board Transformation** back to the main directory, or the $197 professional consultation. A consultation is not required to buy a product.
3. **Book a Session With Rooney** opens `https://nonprofitboardbuilder.com/consultation`. The visitor supplies their name, email, organization, optional website, role and discussion topic.
4. Stripe opens a dedicated $197 consultation checkout. This uses `rooney_professional_consultation_197`, not a board-service entitlement.
5. The server verifies the actual Stripe session, customer association, product, USD amount and paid status. An unpaid or manually opened success URL cannot unlock booking.
6. After confirmation, **Choose My Meeting Time** opens the configured Calendly destination with the customer's name, email and an opaque record identifier. No Stripe references or discussion topics enter that URL.
7. The customer receives a confirmation email with a private resume link. They can return or request recovery without buying again. A cancelled or incomplete checkout does not grant paid access.
8. Rooney sees the consultation separately under **Admin → Meet Rooney & Consultations → Consultation Customers**, including the topic, payment, observed booking status and private before/after notes. Rooney can resend the secure booking link.

Opening Calendly is recorded as a link opening. A confirmed appointment requires the signed Calendly integration to report it. Without that integration the application does not invent a reservation. The website requires payment before its booking step; Calendly's own externally known event URL is not a secret payment system.

## 2. Guided Board Recruitment

1. Promote `https://nonprofitboardbuilder.com/recruit`. The existing visual design and testimonials remain. The visitor starts free.
2. They provide their name, organization and email, then answer the currently published recruitment questions one at a time. The defaults cover mission, present board, desired board members, organizational priorities, missing support, existing capabilities and intended recruitment count. Rooney can change the number, wording, order, instructions, answer format and required settings.
3. Their answers are saved with the precise question version they saw. The free process ends at a thank-you page. It does not reveal detailed recommendations, open the old sales video or demand immediate onboarding.
4. The existing recruitment AI framework prepares private draft board-member profiles. Rooney can inspect them in the recruitment admin. They describe desired people, not candidates supposedly found by the platform. A failed analysis remains visible and can be retried; the email fallback does not claim finished recommendations.
5. Approximately 60 minutes after submission, the background worker sends the editable first invitation with that customer's secure recruitment continuation link. The visitor does not have to keep the browser open.
6. The customer reads the written offer and pays $497 through the separate `rooney_guided_recruitment_497` Stripe product. Payment remains attached to the original answers. After server verification, they upload their logo and select their colors, then open Recruitment's configured Calendly booking step.
7. During the guided meeting, Rooney opens the paid customer record. They review the original answers and proposed profiles, edit/add/remove roles, agree on the recruitment requirements and approve the profiles. Approved profiles become the source for the campaign materials.
8. Rooney confirms interview arrangements and clicks **Generate Recruitment Materials**. The adapter reuses the existing generators. Individual resources can be edited, saved, approved or regenerated without wiping other approved documents.
9. When the required campaign copy and application form are approved, Rooney explicitly confirms **Launch Board Recruitment Campaign**. The existing publisher creates the opportunity and working application link. Network distribution requires the organization's explicit approval and an operational, permission-aware applicant-network integration. The interface reports publication and network status separately; it does not claim LinkedIn or Facebook publication.
10. **Send Recruitment Materials** prepares a reviewable email containing the customer's secure resource-library link. It includes the published campaign, application, approved role profiles and approved documents. The customer can download PDF, editable Word or text where supported, and share the ready-made messages through its own channels.
11. Applicants apply to that campaign and can upload a CV. Their information is linked to the correct organization's opportunity. The leader receives an email with a private action link, not a public CV link.
12. The leader or Rooney can review the application/CV, generate a tailored interview guide, prepare an invitation or rejection, edit the message and approve sending. Confirmed scheduling links or availability are inserted. AI never automatically rejects an applicant or invents meeting availability.
13. Selection remains a human decision. Existing profile forms, references, appointment communications, agreements and onboarding tools remain available. Signed documents retain a frozen version, completion status and authorized download access.

The initial organization-wide collection includes overview, board manual, board-member agreement, confidentiality agreement, conflict-of-interest agreement, opportunity, recruitment job post, LinkedIn post, social posts, outreach emails, direct invitation, referral request, general interview invitation, recruitment communications, onboarding script and onboarding agenda, plus the application form. Applicant-specific tools reuse interview guides/invitations/rejections, reference requests and confirmations, reference call/evaluation materials, conditional/unconditional offers, appointment letters, onboarding emails, engagement guidance and portfolios where the agreed information supports them. They are generated for the appropriate applicant rather than inventing applicant details in advance.

The 30-minute guided launch is achievable when the necessary information and approvals are ready. The system does not silently mark unfinished work complete. Existing paid recruitment customers keep their earlier dashboards, purchases, application links and resources.

## 3. Guided Board Recommitment

1. Promote `https://nonprofitboardbuilder.com/board-recommitment`. The visitor starts free and supplies their contact details.
2. The editable defaults ask about the mission, why recommitment is needed, what members should contribute and how many members are involved. No branding is requested before payment.
3. The complete answers are saved with their original question version. The free process ends with the recommitment thank-you page.
4. Approximately one hour later, the independently editable first email invites the leader to the $497 guided service. The customer's own secure link leads to `rooney_guided_board_recommitment_497`, not the consultation or recruitment checkout.
5. Verified payment unlocks branding and then Recommitment's configured Calendly link. Paid customers can resume through their email or recovery without paying twice.
6. Rooney opens the customer in **Admin → Board Recommitment**. During the session, they clarify the current situation, expected contributions, participants and deadline, then prepare and approve the form and invitations.
7. Rooney can add participants manually or explicitly import existing organization-related member records. Each participant receives their own secure link. Invitations can be reviewed, edited, approved, sent individually or to selected people, copied or resent. Delivery status reflects platform delivery; copied external emails are not falsely marked delivered.
8. The existing board-member form is reused. Editable labels map to stable **active**, **advisory/alternative role**, and **step-down** decisions. Conditional questions and explanations are editable, while each participant's original form version and complete answers remain readable.
9. Submission saves the member's preference and notifies the authorized leader with a private resource link. It does not automatically recommit, appoint, reassign or remove anyone.
10. Rooney and the leader review the original response, prepare an AI interpretation and conversation guide, and edit/approve the relevant material. The leader can conduct the conversation independently and approve an edited guide for email delivery.
11. After the appropriate conversations and organizational decisions, they record the confirmed outcome, agreed role, responsibilities, support and next steps. These are separate from the person's initial preference.
12. They can prepare the relevant confirmation, alternative-role discussion, step-down acknowledgement or follow-up invitation. Agreed portfolios and relevant agreements reuse the existing generators and signing tools. Portfolios must reflect actual accepted commitments and be reviewed before delivery.
13. **Send Recommitment Materials** prepares the leader's resource-delivery email for review and approval. Approved documents remain available through the customer's private resources page. An individual portfolio can also be sent to its intended member.

The objective is clarity and a practical process the organization can continue. It does not guarantee every member will respond or recommit within seven days. Historic recommitment purchases, forms, decisions, portfolios and signed documents remain intact.

## 4. Professionally facilitated Strategic Planning

1. Promote `https://nonprofitboardbuilder.com/strategic-planning`. The visitor starts free, supplies their contact details and answers three editable default questions: the future they envision in 12 to 24 months, the goals needed to reach it, and the resources required.
2. Those answers are saved as a planning lead. The free process ends at a thank-you page. No board invitations or full planning dashboard open yet.
3. Approximately one hour later, the independently editable invitation explains the facilitated process and links to the customer's $1,997 checkout, using `rooney_guided_strategic_planning_1997`.
4. After trusted Stripe confirmation, the leader provides the logo and colors and opens Strategic Planning's configured Calendly link. This first booking is the preparation meeting, separate from the later board session.
5. Rooney opens the organization's planning workspace in the admin. They save the planning period, board meeting date/time/time zone, response deadline, current mission and individually identified existing programs. The form does not require rewriting the mission.
6. Rooney prepares the leader's personal form and adds board participants. Lead-user and board-member questions have separate editors. Existing vision/goals answers are reused for the leader to expand; board members start with their own blank responses.
7. Each participant receives a personal invitation containing the purpose, period, meeting details, deadline and secure form link. The form covers vision, goals, objectives, programs, people, funding, budget, partnerships, marketing, technology, risks, action priorities, measurement and participation. Questions and section identifiers remain associated with their original version.
8. Each existing program has its own questions and saved answers. Participants can also suggest new programs or changes. Progress is saved. They do not see other people's private responses while completing their forms.
9. A completed board response notifies the leader and becomes available to Rooney. The leader's private resources page permits authorized review of the original submissions.
10. Rooney opens **Live Strategic Planning Controls** from that same customer record and starts the existing planning session. The session presents one subject at a time, including each program separately, with contributors identified.
11. Rooney can adopt, reject or mark ideas for modification, preserve sources when combining wording, enter a newly agreed idea, add a proposed program for separate discussion, save facilitator notes and record responsibilities only with the person's agreement.
12. With explicit participant consent, the microphone can transcribe the discussion. Rooney can stop it, correct/save the transcript, or use typed/pasted notes when browser transcription is unavailable. The transcript supports the decisions; it cannot silently turn a rejected suggestion into an adopted priority.
13. Completing the session shows the adopted decisions and outstanding subjects. Rooney can return to discussion to correct them before confirming the agreed direction. Participants can acknowledge that direction and their own responsibilities through their personal meeting screens.
14. The existing plan generator prepares a draft from the adopted decisions, organization context, confirmed notes and contextual transcript. It must not invent programs, amounts, owners, deadlines or consensus. Missing agreements remain outstanding. Interrupted generation can be retried from the saved meeting decisions.
15. Rooney edits the complete plan inside the admin and saves a version. The prior generated draft and saved versions remain in history. Ordinary corrections do not require downloading and uploading a file.
16. **Approve Plan and Prepare Board Review** prepares personal review links. They do not disclose the draft until Rooney explicitly releases that approved version.
17. Each participating reviewer can **Adopt This Strategic Plan** or **Request a Change**. The name, decision, time, requested changes and exact plan version are recorded. Editing the plan creates a new version and requires fresh review; old approvals cannot be reused to claim approval of revised text.
18. After the participating reviewers adopt the current version and Rooney confirms the applicable formal organizational approval, **Finalize Strategic Plan** releases the approved document. **Email Final Plan**, PDF/Word/text download and **Copy Secure Plan Link** provide delivery. The leader receives a private resources link and can share the approved document with authorized board members.

The organization carries out its plan independently. The new service does not require delegation portfolios, a project-management platform or ongoing execution agents. Historic planning projects retain their original routes and purchased functionality.

## 5. Existing Board Fundraising Game

This flow is preserved, not replaced by the three new guided-service funnels.

1. Promote `https://nonprofitboardbuilder.com/board-fundraising`. It safely aliases the existing `https://nonprofitboardbuilder.com/board-fundraising-game` landing page. Old game links remain registered.
2. The landing-page CTA opens the existing short name/email/organization dialog. Saving leads to **How the Fundraising Game Works**. The current offer is $1,497 per organization. This is not one of the $497 guided-service checkouts.
3. After payment/access verification, the leader supplies the fundraising goal and deadline, board count, mission, people served, location, consequences of not raising the funds, branding and current approach or uploaded plan.
4. The leader completes the existing audience-by-audience questionnaire and personal participation statement, then saves the next board meeting details and invites board members. Invited members use their personal links and do not pay.
5. Individuals, businesses and grantmakers are handled by the existing audience sequence. Participant submissions remain their own ideas. The leader receives response notifications and can review responses.
6. Rooney's existing facilitator workspace runs the Group Game. It reviews the submitted audiences and complete approaches, records explicit audience decisions and agreed participation, and supports the existing consent/microphone/transcript process and participant meeting links.
7. The group reviews its selected strategy and adoption. Rooney can review/edit/approve the final strategy in the existing administration. The leader receives the approved strategy link and configured execution-discussion booking link, with existing downloads and sharing retained.

The old game setup, invitation, questionnaire, group, strategy, transcript, customer dashboard and delivery engines are unchanged. Historical legacy game tools remain available under their original access controls.

## 6. Board Applicant Network

Promote `https://nonprofitboardbuilder.com/join-a-board`. The current network is for professionals living in the United States or United Kingdom. The existing multi-step form collects contact/location information, professional experience and skills, optional CV, causes and board interests, availability, prior board experience, fundraising relationships, motivation and required permissions.

The profile is saved and the existing integrations attempt applicant-segment synchronization, applicant confirmation and owner notification, recording failures for review. Joining the network is not an appointment and does not automatically submit applications to every organization.

`https://nonprofitboardbuilder.com/board-opportunities` lists published opportunities. An applicant can open an opportunity and apply to its organization. Where the existing Resend segment/topic configuration and recipient permissions support it, an approved network announcement can link registered contacts to an opportunity. The system does not buy contacts, claim external social publication or guarantee candidates. Live network distribution is a separately configured integration; publication can succeed while distribution fails or is not requested.

## 7. Blog and content discovery

Promote `https://nonprofitboardbuilder.com/blog`. Individual published articles use `https://nonprofitboardbuilder.com/blog/<actual-published-slug>`. Use the actual article link from the public blog; do not promote a placeholder slug.

Existing daily publishing, article URLs, images, RSS at `https://nonprofitboardbuilder.com/api/blog/feed.xml`, blog sitemap and social publishing endpoints remain. The present blog generator and its existing categories are retained. Articles can contain relevant offer links; existing fundraising articles continue leading to the Fundraising Game. This release does not rebuild the publishing engine or invent a new publication schedule for the other services.

## Shared email and access rules

Recruitment, Recommitment and Planning have independent settings and records on the same shared infrastructure. Each has one first invitation, normally after 60 minutes, followed by up to five short messages. The defaults space additional messages three days after the previous successful message. Rooney can edit each subject/body/button/signature and interval, pause the service sequence, or stop/suppress an individual prospect.

Payment, unsubscribe, suppression or a manual stop prevents unpaid follow-ups. Publishing edited questions or emails does not restart completed sequences. Failures are recorded, retries use stable event/provider identifiers, and necessary purchased-service messages remain separate from promotional unsubscribe preferences.

**Send Personalized Video** is manual. Rooney pastes a YouTube link, previews and edits the service-specific email, then explicitly approves sending. Unpaid prospects receive their own service's offer link; paid customers receive a continuation link without another payment demand. Communication history remains with that customer.

The application does not mark a provider-accepted message as proof of Gmail inbox receipt. Customer emails have private action links and omit confidential answers. Customers can recover paid access by email. Administrative samples use the actual current configuration but capture messages and cannot charge a real card or announce a campaign to the live network. Sample labels stay inside the controlled admin experience.

## HOW TO RUN NONPROFIT BOARD BUILDER FROM THE ADMIN DASHBOARD

Start at `https://nonprofitboardbuilder.com/admin` and sign in with your existing administrator account.

| Task | Actual admin location/action |
|---|---|
| Edit the four-service main homepage | **Main Homepage**. Edit directory text/cards and save. |
| Edit biography, portrait, product links and testimonials | **Meet Rooney & Consultations → Personal Page Editor**. The board-transformation button points to the main homepage. |
| Change consultation Calendly URL or confirmation wording | **Meet Rooney & Consultations → Consultation Settings**. The price remains server-verified $197. |
| Review consultation payments, booking status, topic and private notes | **Meet Rooney & Consultations → Consultation Customers → Open Full Consultation Record**. Use **Resend Secure Booking Link** for a paid customer. |
| Open guided-service management | Top links **Board Recruitment**, **Board Recommitment**, **Strategic Planning**. Direct routes are `/admin/services/recruitment`, `/admin/services/board-recommitment`, `/admin/services/strategic-planning`. |
| Edit Recruitment or Recommitment entry questions | Open that service → **Entry Questions**. Edit/add/archive/reorder, preview, **Save Draft**, then **Save and Publish Settings**. |
| Edit Planning's three question groups | **Strategic Planning → Free Entry Questions**, **Lead User Planning Questions**, or **Board Member Planning Questions**. Keep the stable section identifiers; per-program questions repeat for each configured program. |
| Edit the board-member recommitment choices/form | **Board Recommitment → Board Member Form**. Public labels are editable; the three underlying decisions remain distinct. Preview before publishing. |
| Edit guided landing-page wording | Open the service → **Landing Page Copy**. Recruitment's other existing page text remains in the preserved historical landing-page editor under `/admin/legacy`. Planning/Recommitment process copy is also editable in the service editor. |
| Edit a service's first email and one-hour delay | Open that service → **First Response Email**. The delay is in minutes. Preview and publish. |
| Edit follow-up subjects, messages, timing or pause | Open that service → **Five-Email Follow-up Sequence**. Each interval begins after the preceding successful email. |
| Change a service's Calendly destination and paid/resource emails | Open that service → **Payment and Booking**. These settings are independent from the consultation and the Fundraising Game. |
| Edit invitations, response notices, recovery and signature wording | Open that service → **Invitation and Response Emails**. Save and publish the appropriate template. |
| Review original submissions, payment and booking | Open the service → **Customer Submissions → Open Service Workspace**. Use **Original Questions and Answers** and **Refresh Workspace**. |
| Review AI recruitment recommendations | Open a recruitment record. Review/edit the proposed profiles and **Approve Agreed Board Member Profiles**. |
| Generate/approve recruitment resources and publish | Open the recruitment record, confirm interview arrangements, **Generate Recruitment Materials**, edit/approve required documents, then explicitly confirm **Launch Board Recruitment Campaign**. Network distribution is a separate consent. |
| Review applicants and conduct selection/onboarding | In the recruitment record or the customer's private resources, open the applicant. Review CV, generate guide, prepare invitation/rejection, and use existing selection/profile/reference/agreement tools. |
| Run recommitment | Open the Recommitment record. Save setup, prepare/approve form, add/import members, review/send invitations, inspect responses, edit interpretations, record confirmed outcomes and approve portfolios/materials. |
| Facilitate strategic planning | Open the Planning record. Save setup/programs, prepare the leader form, add/invite members, review original responses and **Open Live Strategic Planning Controls**. |
| Edit, review and deliver a plan | In the same Planning record, use **Final Strategic Plan Editor**, save the draft, prepare/release review, inspect version-specific adoption, confirm organizational approval, **Finalize Strategic Plan**, then **Email Final Plan**. |
| Send a personal video | Open the service's customer record → **Personalized Video Follow-up**. Paste YouTube URL, prepare, edit, approve/send. |
| Review communications or stop an unpaid sequence | Open the record → **Customer Activity and Delivery History** and **Unpaid Follow-up Controls**. |
| Test current Recruitment/Recommitment/Planning | Open the service → **Start Current Customer Journey Test**. Complete the current questions in the sample, then use **Run Next Due Sample Email** or **Simulate Confirmed Payment**. Continue branding, forms and admin operations using that same sample record. |
| Test the existing Fundraising Game | Main admin → **Client Testing**. Its original fresh/preloaded test controls remain. |
| Operate existing Fundraising customers | Main admin → **Customers and Workspaces**, or **Strategy Review and Approval**. Its booking link, questions, follow-up editors and game tools remain in their existing sections. |
| Manage articles and publishing | Main admin → **Blog Generator**. Historical applicant/content/administrative tools remain under `/admin/legacy`. |

Secure customer resources are at `/services/<service>/resources/<private-token>`. These are recovery/action pages, not promotional links. Do not post customer tokens, participant links, admin routes, checkout sessions or private documents publicly.

## Promotional messaging reference

| Topic / who should follow the link | Best link | Before payment | Paid result |
|---|---|---|---|
| Complete board transformation or a leader unsure where to begin | `https://nonprofitboardbuilder.com/` | Choose one of four independent services or meet Rooney. | Depends on the selected service. |
| Rooney's experience, professional advice, starting or strengthening an organization | `https://nonprofitboardbuilder.com/meet-rooney` | Read the biography/testimonials and choose consultation or an existing product. | $197 professional consultation, if selected. |
| Direct invitation to discuss an organizational challenge | `https://nonprofitboardbuilder.com/consultation` | Short contact/role/topic form. | Pay $197, then choose the configured meeting time. |
| Recruiting the board members an organization needs | `https://nonprofitboardbuilder.com/recruit` | Free questions and an emailed personal invitation. | $497 guided profile review, prepared recruitment campaign/application and continuing resources. |
| Helping passive or disengaged board members decide their involvement | `https://nonprofitboardbuilder.com/board-recommitment` | Free questions and an emailed invitation. | $497 guided setup, individual decisions, follow-up resources and agreed portfolios. |
| Bringing the board into its organization's future direction | `https://nonprofitboardbuilder.com/strategic-planning` | Three introductory questions and an emailed invitation. | $1,997 preparation, independent contributions, facilitated planning and an adopted branded plan. |
| Getting the board participating in fundraising | `https://nonprofitboardbuilder.com/board-fundraising` | Existing contact dialog and written how-it-works page. | Existing $1,497 Fundraising Game and facilitated strategy process. |
| Professionals interested in serving on a nonprofit board | `https://nonprofitboardbuilder.com/join-a-board` | Existing profile, experience, availability and permissions form. | No paid service is required to join the network. |
| Current board vacancies | `https://nonprofitboardbuilder.com/board-opportunities` | Browse actual published opportunities and open an organization's application. | Applicant applications do not purchase a board service. |
| Educational content and articles | `https://nonprofitboardbuilder.com/blog` | Read an actual published article and follow its relevant offer link. | Determined by the offer chosen. |

The production availability and final release status for these URLs are recorded separately in `guided-services-release-verification.md`. A source-code route is not evidence that this release is deployed.
