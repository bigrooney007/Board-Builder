// Single source of truth for authenticated-app customer-facing copy.
// Public marketing copy lives in ./siteContent.js. Module titles are canonical
// in backend/course_content.py and arrive via the course API.

export const reactivationContent = {
  step1: {
    heading: "Understand the Situation",
    body: [
      "This step is training only. Watch the video above to understand why Boards disengage and what reactivating a Board actually requires.",
      "When you are ready, mark this step complete and continue to Step 2 to generate your Board Recommitment Form.",
    ],
  },
  step2: {
    heading: "Find Out Who Is Ready to Stand Up",
    intro: [
      "Before you start having difficult conversations, give every current Board Member an opportunity to tell you where they are, what they can realistically contribute, and whether they are willing and able to continue serving actively.",
      "Generate your Recommitment Form below. You get one secure link — send it to your Board Members from your own email. Everyone who completes it appears automatically in Step 3.",
    ],
    generateFormButton: "GENERATE RECOMMITMENT FORM",
    formReadyNote: "Review the form introduction below. Edit anything you want changed, save it, then approve it to make your secure form link live.",
    saveButton: "SAVE",
    approveButton: "APPROVE FORM",
    editButton: "EDIT FORM",
    approvedNote: "Your Recommitment Form is live. Copy the link or the prepared email below and send it to your Board Members from your own email.",
    formLinkLabel: "Form Link",
    generateEmailButton: "GENERATE EMAIL",
    emailLabel: "Email to Send",
    copyEmailButton: "COPY EMAIL",
    copyLinkButton: "COPY FORM LINK",
    copiedLabel: "Copied!",
    responsesLabel: (count) => `${count} response${count === 1 ? "" : "s"} received so far — responses appear in Step 3: Understand Their Response.`,
    frameworkNote: "The form itself uses the established Recommitment Form framework: professional profile, expertise, networks, Board experience, areas of contribution, fundraising participation, availability, support needed and the recommitment decision.",
    errors: { load: "We could not load this step.", action: "That did not work. Please try again." },
  },
  step3: {
    heading: "Understand What Each Board Member Told You",
    intro: [
      "Every Board Member who completes the Recommitment Form appears here automatically — you never add anyone manually.",
      "For each person, generate an interpretation of what they communicated: their commitment, their concerns, their willingness to continue or step up, and the recommended direction for your conversation — so you enter the conversation prepared.",
    ],
    understandButton: "UNDERSTAND THEIR RESPONSE",
    regenerateButton: "RE-ANALYZE THEIR RESPONSE",
    viewUnderstandingButton: "VIEW UNDERSTANDING",
    viewResponseButton: "VIEW FULL RESPONSE",
    analyzingLabel: "Understanding their response…",
    failedLabel: "The analysis did not complete. Your information is preserved — try again.",
    emptyState: "No responses yet. Once a Board Member completes the Recommitment Form from Step 2, they appear here automatically.",
    waitingBadge: "Waiting for Recommitment Form",
    progress: (p) => `${p.total} Board Member${p.total === 1 ? "" : "s"} · ${p.responded} Responded · ${p.analyzed} Understood`,
  },
  step4: {
    heading: "Have the Conversations That Need to Happen",
    intro: [
      "You now understand what each Board Member communicated. The next step is to talk with each person.",
      "Choose the direction for each conversation — remain and step up, step down, or move to the Advisory Board — and generate a call script written specifically for that person and that direction.",
    ],
    directionLabel: "Conversation Direction",
    directionPlaceholder: "Choose the direction for this conversation…",
    directionHint: "The recommended direction is in their Understanding from Step 3. You decide.",
    generateScript: "GENERATE CALL SCRIPT",
    regenerateScript: "REGENERATE SCRIPT",
    conclusionHeading: "After the Conversation — What Happened",
    conclusionHint: "Record what happened during the call: what the Board Member ultimately decided, important information from the conversation, any commitments made, any follow-up required, and the final direction. This becomes the source of truth for the next stage.",
    conclusionPlaceholder: "What happened · what they decided · important information · commitments made · follow-up required · final direction",
    saveConclusion: "SAVE POST-CALL NOTES",
    conclusionSaved: "Notes Saved",
    outcomeHeading: "Final Outcome",
  },
  dashboard: {
    heading: "Your Reactivated Board",
    intro: [
      "This is your operating center. Every Board Member is grouped by their outcome, with the exact resources each one needs next.",
    ],
    pipelineLabels: {
      responded: "Responded", analyzed: "Understood", conversations: "Conversations Done",
      steppedUp: "Stepped Up", advisory: "Advisory", steppedDown: "Stepped Down", portfolios: "Portfolios Ready",
    },
    steppedUpActions: "Board Member Portfolio",
    followUpEmailButton: "GENERATE FOLLOW-UP EMAIL",
    advisoryEmailButton: "GENERATE ADVISORY BOARD CONFIRMATION EMAIL",
    regenerateEmailButton: "REGENERATE EMAIL",
    viewEmailButton: "VIEW / EDIT EMAIL",
    copyEmailButton: "COPY EMAIL",
    emailReadyLabel: "Email ready — copy it and send it from your own email.",
  },
};
