// Complete Board Fix — static execution instructions (supplied by Rooney; do not AI-generate).
// Keyed by "<pathway>-<moduleNumber>".

export const BUF_STEP_INSTRUCTIONS = {
  "reactivation-3": {
    doing: [
      "Your Board Members have now received the Board Member Profile & Recommitment Form. As their responses come in, each completed response will appear below.",
      "Start by opening each Board Member's response so you understand what they actually said about their commitment, capacity, expertise and how they would like to contribute.",
      "If you want additional help understanding what their response means, use Understand Their Response. This gives you additional context before you speak with them; it does not make the decision for you.",
      "The next thing you need to do is have the conversation. Choose the direction you want to explore with that Board Member, then generate their Conversation Script. Read through it before calling them. You do not have to read the script word for word. Use it to understand the conversation, the questions you need to ask and the issues you need to clarify.",
      "After the conversation, record what actually happened in the Conversation Conclusion. The conversation, not the original form and not AI, determines the final outcome.",
      "Once the conclusion is recorded, prepare the appropriate follow-up communication confirming what was actually agreed.",
    ],
    completeIntro: "For each Board Member:",
    complete: [
      "View their original response.",
      "Use Understand Their Response where helpful.",
      "Choose the direction of the conversation.",
      "Generate and review their Conversation Script.",
      "Have the conversation.",
      "Record the actual Conversation Conclusion.",
      "Prepare and send the appropriate follow-up communication.",
    ],
    outro: [
      "Once enough Board Member conversations are complete, use Summary of Your Entire Board to understand the Board you actually have after Reactivation: who is continuing, who has stepped down or transitioned, the strengths that remain, and the gaps you may now need to fill.",
      "That summary leads directly into the next step: identifying the Board Members your organization needs.",
    ],
  },
  "recruitment-2": {
    doing: [
      "Board recruitment is not about filling empty seats. It is about bringing in people who complement the Board you already have so that your organization has the skills, experience, expertise and relationships it needs to move forward.",
      "The system will use what we know about your organization, the Board you currently have and the gaps that remain to identify the Board Members you should recruit.",
      "Generate The Board Members Your Organization Needs below. Review the result carefully. Make sure the people being recommended genuinely reflect the Board you want to build. Edit anything that needs to change. When you are satisfied, approve it.",
      "Your approved Board needs become the foundation for the recruitment campaign in the next step. The recruitment materials should be built around the people you have decided you actually need.",
    ],
    complete: [],
    outro: [
      "Generate → Review → Edit if necessary → Approve.",
      "Do not move into campaign launch until you are comfortable with the Board Members you have identified.",
    ],
  },
  "recruitment-3": {
    doing: [
      "You now know who you need on your Board. This step is about taking that need into the market and giving the right people an opportunity to apply.",
      "Your recruitment campaign needs a professional Board Application and the materials you will use to promote the opportunity. The resources below give you the application, recruitment posts, emails, referral messages and other campaign materials you need.",
      "Generate each resource you intend to use. Read it carefully, edit anything that should sound more like your organization, save it and approve it.",
      "Your Board Application gives you a live application link. Use that link wherever you promote the opportunity so applicants can enter the recruitment process.",
      "Use the approved materials across the channels available to you: LinkedIn, your professional network, Board Member and supporter referrals, social media and other appropriate places where the people you are looking for can be reached.",
      "Once the campaign is live, applicants who use your Board Application will begin appearing automatically in the next stage.",
    ],
    complete: [
      "Prepare and approve the Board Application.",
      "Generate the campaign materials you need.",
      "Review, edit and approve them.",
      "Launch the campaign using the approved materials and application link.",
      "Begin watching for applicants.",
    ],
  },
  "recruitment-4": {
    doing: [
      "Now that your recruitment campaign is running, this is where you begin deciding who should move deeper into the process.",
      "Applicants who used your Board Application will appear below with their application information and CV where supplied. If someone applied through an external channel, use the external-applicant function to bring their information into the process.",
      "First decide who you want to speak with. For anyone you want to move forward, prepare the Interview Invitation and the Interview Guide.",
      "The interview should feel like a professional Board introductory conversation: you are learning about them while they are learning about your organization and the Board opportunity. Use the Interview Guide to help you ask the right questions, explore the expertise and experience you are actually looking for, understand alignment and clarify expectations.",
      "Do not appoint somebody during the interview simply because you like them. Complete the conversation, then record your actual decision.",
    ],
    completeIntro: "For each applicant:",
    complete: [
      "Review their application and CV.",
      "Decide whether you want to move them into a conversation.",
      "Prepare and send the appropriate invitation.",
      "Generate and review their Interview Guide.",
      "Hold the conversation.",
      "Record your actual decision.",
      "Use the appropriate post-interview communication.",
    ],
    outro: ["People you decide to move forward with can then proceed to References and Background Checks."],
  },
  "recruitment-5": {
    doing: [
      "This step helps you verify the people you are seriously considering before final appointment.",
      "For candidates you have decided to move forward with, begin by requesting their professional referee information using the Candidate Referee Request. Once referee information is available, use the reference resources provided here to complete the reference process professionally.",
      "The Reference Call Guide gives you the questions and structure for speaking with a referee. The Reference Record & Evaluation Form gives you a consistent place to record what the referee actually said.",
      "Nothing here decides for you whether a reference is good or bad, and nothing passes or fails a candidate. You review the evidence and decide how to proceed.",
      "Background checks are separate. Where your organization decides a background check is appropriate, use the tracker here to record the process and status. The platform does not perform a background check itself.",
    ],
    completeIntro: "For each candidate moving forward:",
    complete: [
      "Obtain the referee information.",
      "Complete the professional reference process.",
      "Record the results factually.",
      "Complete and record any applicable background-check process.",
      "Decide whether any genuine conditions remain before formal appointment.",
    ],
  },
  "recruitment-6": {
    doing: [
      "The people reaching this stage have moved through your recruitment and selection process and are now being brought properly into the Board.",
      "Onboarding is where you bring the new Board Members together and make sure they understand the organization, the Board, their responsibilities, expectations and commitments.",
      "The important meeting resource in this step is the Board Member Onboarding Facilitation Guide. Generate the Facilitation Guide before the onboarding session. The guide gives you a complete read-through structure for facilitating the meeting: what to say, the issues to work through, the questions to ask, how to confirm understanding and how to reach clarity with the new Board Members.",
      "Read through it before the meeting. Use it to lead the session naturally rather than simply reading mechanically from a script.",
    ],
    complete: [
      "Make sure the people attending have been properly appointed through the current process.",
      "Make sure the appropriate approved onboarding documents have been shared with them.",
      "Generate the Board Member Onboarding Facilitation Guide.",
      "Review it before the meeting.",
      "Hold the onboarding session.",
      "Record the actual agreements and conclusions required by the onboarding workflow.",
      "Complete the remaining onboarding actions for each new Board Member.",
    ],
  },
  "activation-2": {
    doing: [
      "Fundraising Activation begins with planning together. People are much more likely to take ownership of a plan they helped build.",
      "This step gives every Board Member an opportunity to contribute their ideas, relationships, perspective and the ways they may be comfortable supporting the fundraising work before the strategy is created.",
      "If your Fundraising Information has not yet been completed, complete that first using the action on this page.",
      "Then generate the Board Fundraising Planning Form. This is one organization-level planning form, but every Board Member receives their own secure link so their response remains connected to them.",
      "Prepare and send the Planning Email to each participating Board Member. Use the Reminder communication for people who have not yet responded where necessary.",
      "Their answers at this stage are ideas and expressions of willingness. They are not final assignments or fundraising responsibilities.",
    ],
    complete: [
      "Complete the required Fundraising Information if prompted.",
      "Generate, review and approve the Board Fundraising Planning Form.",
      "Send each Board Member their unique secure Planning Form link using the Planning Email.",
      "Track responses.",
      "Follow up with outstanding members where needed.",
      "Move forward when you have enough Board input to build the strategy.",
    ],
  },
  "activation-3": {
    doing: [
      "Your Board Members have now shared their fundraising ideas and perspective. The next step is to bring that information together with your organization's fundraising goals and priorities and build one complete Fundraising Strategy Plan.",
      "Before generating, review the response count below. Ideally, give every participating Board Member the opportunity to contribute. If somebody has not responded and you want their input included, follow up with them before generating.",
      "When you click Generate, the Fundraising Strategy Plan uses your verified fundraising information, every completed Board Fundraising Planning response, verified organization information and the Nonprofit Board Builder fundraising framework. It produces one coherent strategy for the organization.",
      "Review the strategy carefully. Edit anything that needs strengthening or correction. When you are satisfied, approve it as the Board Review Version.",
    ],
    complete: [],
    outro: [
      "Completed Board Planning Responses → Generate Fundraising Strategy → Review → Edit if needed → Save → Approve for Board Review.",
    ],
  },
  "activation-4": {
    doing: [
      "The Fundraising Strategy has now been built from the organization's direction and the ideas contributed through the Board Fundraising Planning process.",
      "The next step is to bring the Board together to review the complete strategy, strengthen anything that needs strengthening, agree on the fundraising priorities and adopt the strategy as the organization's working fundraising document.",
      "Enter the actual meeting details and prepare the Fundraising Strategy Review & Adoption Meeting Invitation. The invitation gives the Board access to the strategy before the meeting so they can come prepared.",
      "Then generate the Fundraising Plan Adoption Facilitation Guide. Read the guide before the meeting and use it to facilitate the conversation.",
      "During the meeting, the Board should discuss the strategy together, agree any necessary changes, confirm the priorities, adopt the plan and discuss how the Board will participate in execution.",
      "After the meeting, record what actually happened.",
    ],
    complete: [
      "Confirm the Board Review Version is ready.",
      "Enter the Review & Adoption Meeting details.",
      "Prepare and send the Meeting Invitation with the strategy link.",
      "Generate and review the Facilitation Guide.",
      "Hold the Board meeting.",
      "Record the Plan Adoption Conclusion.",
      "Record any agreed changes.",
      "Record the fundraising priorities confirmed.",
      "Record what the Board agreed to help carry.",
      "Record each Board Member's actual agreed fundraising responsibility where an agreement was reached.",
    ],
    outro: [
      "If the strategy was adopted with changes, apply the agreed changes to the existing strategy before confirming the final adopted version.",
    ],
  },
  "activation-5": {
    doing: [
      "Your Board has now adopted the Fundraising Strategy and agreed how it will participate. This final step turns that agreement into something each Board Member can actually use.",
      "For every Board Member whose fundraising responsibility was genuinely agreed, generate their Individual Fundraising Portfolio. Their Portfolio shows them what they agreed to help carry, why it matters, how it connects to the adopted strategy and what they should focus on next. Do not create a Portfolio for somebody whose fundraising responsibility has not actually been agreed.",
      "At the organization level, you can then prepare the execution resources.",
      "Case for Support: the supporter-facing document that explains why the organization's work matters, what you are raising money for and why someone should support the mission.",
      "Board Fundraising Communication System: tells Board Members what to say as they move a relationship through Introduce Impact → Case for Support → Follow Up & Ask.",
      "Board Fundraising Execution Toolkit: gives the Board the practical preparation, tracking, report-back, follow-up and stewardship tools needed to execute responsibly.",
    ],
    complete: [
      "Generate individual Fundraising Portfolios for Board Members with an agreed responsibility.",
      "Review, edit, approve and deliver those Portfolios.",
      "Generate, review and approve the Case for Support.",
      "Once the Case for Support is approved, generate the Board Fundraising Communication System.",
      "Generate the Execution Toolkit.",
      "Begin executing the adopted Fundraising Strategy with the Board.",
    ],
    outro: [
      "Remember: your Board is not an unpaid fundraising staff team. The Board helps provide direction, relationships, leadership, introductions, oversight and agreed participation. The organization still needs the people and capacity required to carry the day-to-day fundraising work.",
    ],
  },
};
