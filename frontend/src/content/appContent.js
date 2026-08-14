// Single source of truth for authenticated-app customer-facing copy.
// Public marketing copy lives in ./siteContent.js. Module titles are canonical
// in backend/course_content.py and arrive via the course API.
// Static email templates are canonical in backend/content_templates.py.

// Copy shared by every course experience (Recruitment, Reactivation, Activation).
export const sharedCourseContent = {
  forbidden: {
    heading: "This Program Is Not Included in Your Account",
    body: "Your account does not include access to this program. If you believe this is a mistake, please contact us.",
    backButton: "Back to My Board Builder",
  },
  nav: {
    previousStep: "Previous Step", nextStep: "Next Step",
    previousModule: "Previous Module", nextModule: "Next Module",
    markStepComplete: "Mark This Step Complete", stepCompleted: "Step Completed",
    markModuleComplete: "Mark This Module Complete", moduleCompleted: "Module Completed",
  },
  loadError: "We could not load this course.",
};

export const recruitmentContent = {
  module1: {
    heading: "Start Here: Recruiting Board Members the Right Way",
    body: "This training shows you how the whole recruitment process works before you begin executing it. Watch the training above, then continue to Step 2 to identify the board members your organization needs.",
    continueButton: "Continue to Step 2 — Identify the Board Members Your Organization Needs",
  },
  module2: {
    generateBoardButton: "Generate the Board We Need",
  },
};

export const activationContent = {
  overview: {
    previewEyebrow: "After Module 5",
    previewHeading: "My Fundraising Board",
    previewBody: "Your permanent fundraising dashboard — your adopted fundraising strategy, each Board Member's fundraising responsibilities and their individual Fundraising Portfolios live here once your plan is adopted.",
    previewButton: "OPEN MY FUNDRAISING BOARD",
  },
  module1: {
    heading: "Prepare to Build a Fundraising Board",
    body: "This module is training only. Watch the video above to understand how fundraising Board ownership is created, then mark this module complete and continue to Module 2 to begin initiating the fundraising planning process with your Board.",
  },
  videoPlaceholder: "Board Fundraising Activation Training Video Coming Soon",
  moduleNotFound: { heading: "Module Not Found", backButton: "Back to Board Fundraising Activation" },
};

// Admin-facing Strategic Planning workspace copy (operator context — never shown to customers).
export const strategicPlanningAdminContent = {
  sections: {
    form: "1. Strategic Planning Form",
    responses: "2. Board Member Responses",
    draft: "3. Draft Plan & Board Review",
    areas: "4. Strategic Areas, Owners & Development Packs",
    actionPlan: "5. One-Page Action Plan",
    finalPlan: "6. Final Strategic Plan",
  },
  buttons: {
    generateProject: "Generate",
    generateDraft: "Generate Draft Plan",
    emailDraftToBoard: "Email Draft Plan to Board",
    synchronize: "Synchronize Foundational Plan",
    finalize: "Finalize Foundational Plan",
    suggestOwners: "AI: Recommend Area Owners (you make every final assignment)",
    generateActionPlan: "Generate Action Plan",
    buildFinalPlan: "Build Final Strategic Plan",
    generateMeetingGuide: "Generate Adoption Meeting Guide",
  },
  leaveUnassigned: "— Leave Unassigned —",
};

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
