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

// Shared generated-resource card copy (Recruitment workspace + shared resource surfaces).
export const materialCardContent = {
  edit: "Edit", regenerate: "Regenerate", generating: "Generating…", copy: "Copy",
  downloadPdf: "Download PDF", approve: "Approve",
  publish: "Publish — Live Secure Link", editDesign: "Edit Design",
  applyDesign: "Apply Design Change", applyingDesign: "Applying…", closeDesign: "Close",
  saveChanges: "Save Changes", cancel: "Cancel", tryAgain: "Try Again",
  liveLinkLabel: "Live secure link:",
  publishSuccess: "Published. Your live secure link is ready (and copied) — anyone with it sees the current version.",
  publishError: "Could not publish this resource.",
  designPrompt: "Tell us exactly what you want changed about the design of the published page — in your own words. For example: “Make the heading smaller”, “Move the organization logo to the top right”, “Add more spacing between sections”, “Make this page look more formal”. The content never changes.",
  designEmptyError: "Describe what you want changed — for example: “Make the heading smaller” or “Move the logo to the top right”.",
  designSuccess: "Design updated — your published page now uses the new design. The content itself is unchanged.",
  designError: "The design change could not be applied. Please try again.",
  approveNote: "Read it, edit anything you want changed, then approve it before use. Editing an approved resource returns it to Draft for re-approval.",
  generationError: "Generation failed. Your information is preserved — you can try again.",
  saveError: "We could not save your changes.",
  approveError: "Could not approve.",
  statusApproved: "Approved", statusGenerated: "Generated", statusNotGenerated: "Not Generated",
};

// Strategic Planning — public Board Member form + public plan pages.
export const strategicPlanningPublicContent = {
  form: {
    title: "Strategic Planning Form",
    nameLabel: "Your Name", emailLabel: "Your Email",
    back: "Back", next: "Next",
    submit: "SUBMIT MY STRATEGIC PLANNING RESPONSES", submitting: "Submitting…",
    thanksHeading: "Thank You",
    thanks: (org) => `Your response has been recorded and will be combined with the ideas of the other Board Members as ${org} builds its strategic plan.`,
    nameRequired: "Please enter your name.", emailRequired: "Please enter your email.",
    answerRequired: (prompt) => `Please answer: ${prompt}`,
    submitFailed: "Submission failed. Please try again.",
    invalidLink: "This link is not valid.", loading: "Loading…",
    stepLabel: (step, total) => `Step ${step} of ${total}`,
  },
  planPage: {
    printButton: "Download / Print PDF",
    notAvailableHeading: "Not Available",
    footer: (issuedBy) => `Prepared with ${issuedBy} · The Nonprofit Board Builder`,
  },
};


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

// ---- Migrated static copy (headings, descriptions, notes) ----

export const recruitmentWorkspaceText = {
  h_addExternalApplicant: "Add External Applicant",
  h_yourBoardApplicants: "Your Board Applicants",
  h_backgroundCheck: "Background Check",
  h_decideWhoMovesForward: "Decide Who Moves Forward",
  h_prepareYourNewBoardMember: "Prepare Your New Board Member Materials",
  h_scheduleTheBoardOnboardingSession: "Schedule the Board Onboarding Session",
  h_yourFirstBoardMeeting: "Your First Board Meeting",
  h_onboardYourNewBoardMembers: "Onboard Your New Board Members",
  h_onboardingResourcesPreparedInStep: "Onboarding Resources Prepared in Step 5",
  h_prepareForYourBoardOnboarding: "Prepare for Your Board Onboarding Session",
  h_yourBoard: "Your Board",
  h_applicantProfile: "Applicant Profile",
  h_applicationAnswers: "Application Answers",
  h_privateNotesNeverShownTo: "Private Notes (never shown to the applicant)",
  h_backgroundCheckRecord: "Background Check Record",
  h_boardMemberProfileForm: "Board Member Profile Form",
  h_recipientsFormallyAppointedBoardMembers: "Recipients (formally appointed board members only)",
  d_applicantsMayAlsoComeTo: "Applicants may also come to you through LinkedIn, email, referrals or your personal network. Add their name, CV and any relevant details you have \u2014 nothing is ever invented. They then enter the exact same interview workflow as your hosted applicants.",
  d_everyoneWhoAppliesThroughYour: "Everyone who applies through your Board Application appears here automatically \u2014 nothing is re-entered. Review each candidate, view their application and CV, then use the actions to invite them to interview, prepare their candidate-specific interview guide, and follow up after the interview. You decide who moves forward \u2014 never the AI.",
  d_collectTheProfessionalInformationSkills: "Collect the professional information, skills, experience and interests you need to understand how each new board member can contribute. One standard hosted form \u2014 candidate-specific secure links with prefilled information are created automatically with each Conditional Appointment.",
  d_nonprofitBoardBuilderDoesNot: "Nonprofit Board Builder does not perform background checks and does not endorse, rank or select any provider. Use a provider your organization trusts \u2014 then record the result on each applicant below.",
  d_reviewTheApplicantsYouInterviewed: "Review the applicants you interviewed and select the people you would like to move forward in your board recruitment process. Your organization decides \u2014 never the AI. Marking a decision sends nothing automatically; it only prepares the right next steps for your review.",
  d_prepareTheDocumentsAndInformation: "Prepare the documents and information your selected board members will need before onboarding. Generate each resource, review it, make any changes you want, and approve the final version. These are generated once for your organization \u2014 candidate-specific links are created automatically later.",
  d_chooseWhenYouWouldLike: "Choose when you would like to meet with your new board members for onboarding. This information will automatically be included in their Conditional Appointment email, along with each candidate's secure links \u2014 nothing is ever pasted manually.",
  d_thisMeetingIsTheTransition: "This meeting is the transition from recruitment into active board participation. We only need the meeting details \u2014 your organization information is already stored, and the details are saved once for every board member.",
  d_completeTheFinalStepsFor: "Complete the final steps for the people you have selected, formally welcome them to your board, and prepare them to begin serving. Completion of every item never appoints anyone automatically \u2014 your organization confirms each appointment.",
  d_seeEveryPersonWhoHas: "See every person who has joined your board, their professional profiles, and the engagement guide for working with each of them.",
  n_weFoundThisEmailAddress: "We found this email address in the applicant's CV \u2014 please confirm it before anything is sent:",
  n_weCouldNotConfidentlyFind: "We could not confidently find an email address for this applicant \u2014 we never guess. Enter it below:",
  n_nonprofitBoardBuilderDoesNot: "Nonprofit Board Builder does not perform background checks and does not endorse, rank or select any provider. No applicant information is shared. The nonprofit remains responsible for its selection decision.",
  n_chooseACandidateAboveTo: "Choose a candidate above to prepare their Conditional Appointment email.",
};

export const recruitmentModulesText = {
  h_yourBoardApplication: "Your Board Application",
  h_yourRecruitmentCampaignMaterials: "Your Recruitment Campaign Materials",
  h_launchMyRecruitmentCampaign: "Launch My Recruitment Campaign",
  h_yourRecruitmentCampaignIsLive: "Your Recruitment Campaign Is Live",
  d_yourHostedBoardApplicationIs: "Your hosted Board Application is created automatically using your organization's information and the proven standard board application structure \u2014 you do not need to configure anything. Every recruitment material below automatically uses this exact link.",
  d_eachResourceIsCreatedFrom: "Each resource is created from the information you have already provided and the board members you identified in Step 2 \u2014 your Board Application link is inserted automatically. Generate each one, read it, edit anything you want changed, then approve it. Nothing is sent or published until you launch below.",
  d_launchingIsTheOnlyAction: "Launching is the only action that makes your Board Application public and triggers the one-time Board Applicant Network announcement. Generating materials above never sends emails or publishes anything.",
  n_thisCampaignIsClosedApplications: "This campaign is closed. Applications show \u201cApplications Closed\u201d. All data remains.",
};

export const activationM2Text = {
  h_buildThePlanWithYour: "Build the Plan With Your Board",
  h_boardFundraisingPlanningProgress: "Board Fundraising Planning Progress",
  h_boardMembersAlreadyInYour: "Board Members Already in Your Account",
  h_addCurrentBoardMember: "Add Current Board Member",
  h_editBoardFundraisingPlanningForm: "Edit Board Fundraising Planning Form",
  h_reminderCallScript: "Reminder Call Script",
  h_questions: "Questions",
  h_sendThePlanningFormToYourBoard: "Send the Planning Form to Your Board",
  d_sendThePlanningFormToYourBoard: "Generate the email you will send to your Board Members. It automatically contains the secure link to your approved planning form. Copy the email and send it from your own email \u2014 Board Members identify themselves when they complete the form.",
  n_approveFormToUnlockEmail: "Approve your planning form above to unlock the email.",
  h_responsesReceived: "Responses Received",
  d_responsesReceived: "Board Members who complete the planning form appear here automatically.",
};

export const activationM3Text = {
  h_turnTheBoardsIdeasInto: "Turn the Board's Ideas Into One Fundraising Strategy",
  h_boardPlanningResponses: "Board Planning Responses",
  h_boardFundraisingStrategyReview: "Board Fundraising Strategy Review",
  h_editFundraisingStrategyPlan: "Edit Fundraising Strategy Plan",
  h_sendThePlanForBoardReview: "Send the Plan to Your Board for Review",
  d_sendThePlanForBoardReview: "Generate the email you will send to your Board Members. It automatically contains the secure link to the Fundraising Strategy Plan review. Copy the email and send it from your own email. Board Members review each idea, approve or disapprove it with their reason, and submit their review \u2014 without logging in.",
  n_approvePlanToUnlockEmail: "Approve the plan for Board review above to unlock the email.",
  n_reviewsAppearInModule4: "Submitted Board reviews become visible in Module 4, where you facilitate plan adoption.",
};

export const activationM4Text = {
  h_turnTheFundraisingStrategyInto: "Turn the Fundraising Strategy Into a Board-Owned Plan",
  h_whereThingsStand: "Where Things Stand",
  h_planAdoptionConclusion: "Plan Adoption Conclusion",
  d_planAdoptionConclusion: "After the adoption meeting, record what happened \u2014 paste the meeting transcript or your notes, describe what was agreed, what changed and what still needs attention. This record becomes the basis for the Board's execution responsibilities and Module 5 follow-up.",
  h_planStatus: "Plan Status",
  h_boardMemberResponsibilities: "Board Member Responsibilities",
  h_editFacilitationGuide: "Edit Facilitation Guide",
  h_boardReviewParticipants: "Board Review Participants",
  d_boardReviewParticipants: "The Board Members who completed the planning form and submitted their strategy review appear here with their positions and idea decisions.",
  n_noReviewsYet: "No Board reviews have been submitted yet. Reviews appear here automatically as Board Members complete the secure review sent in Module 3.",
  h_revisedFundraisingStrategyPlan: "Revised Fundraising Strategy Plan",
  d_revisedFundraisingStrategyPlan: "Generate the revised Fundraising Strategy Plan. It synthesizes the original plan and the Board's planning responses with each member's review \u2014 approvals, disapprovals and their reasons \u2014 into the plan that is ready for adoption.",
  h_adoptionMeetingDetails: "Adoption Meeting Details",
  d_adoptionMeetingDetails: "Enter the details of the meeting where the Board will work through the feedback and adopt the plan. These saved details are used in the invitation email.",
  h_adoptionMeetingInvitation: "Adoption Meeting Invitation Email",
  d_adoptionMeetingInvitation: "Generate the invitation email for your Board. It automatically contains the secure link to the current Fundraising Strategy Plan and your saved meeting details. Copy it and send it from your own email.",
  n_saveMeetingToUnlockEmail: "Save your adoption meeting details above to unlock the invitation email.",
};

export const activationM5Text = {
  h_giveYourBoardTheTools: "Give Your Board the Tools to Start Taking Action",
  h_thePlanMustBeAdopted: "The Plan Must Be Adopted First",
  h_yourBoardIsReadyTo: "Your Board Is Ready to Start Executing",
  h_editExecutionToolkit: "Edit Execution Toolkit",
  h_equipEachBoardMember: "Equip Each Board Member",
  d_equipEachBoardMember: "Record what each Board Member agreed to carry during the adoption discussion, then generate their individual follow-up email based on the adopted strategy and the meeting conclusions. Copy each email and send it from your own email.",
  h_editFollowUpEmail: "Edit Follow-Up Email",
};

export const myFundraisingBoardText = {
  h_yourFundraisingDirection: "Your Fundraising Direction",
  h_yourFundraisingBoardIsReady: "Your Fundraising Board Is Ready to Execute",
  h_stillMissingTheRightPeople: "Still Missing the Right People Around the Table?",
  h_editFundraisingPortfolio: "Edit Fundraising Portfolio",
  h_portfolioEmail: "Portfolio Email",
};

export const adminClientDeliveryText = {
  m_walkThroughEachRealProduct: "Walk through each real product as a customer would, inside your isolated TEST MODE workspace. No payment is required, no emails are sent automatically, and nothing touches real client data.",
  m_everyVerifiedDowithyouCustomerAcross: "Every verified Do-With-You customer across Recruitment, Reactivation and Activation. Open a client workspace to operate their actual product workflow on their behalf \u2014 everything you generate belongs to that client's project.",
};

export const adminPageText = {
  h_recruitmentExperienceReview: "Recruitment Experience Review",
  h_importExistingBoardApplicants: "Import Existing Board Applicants",
  m_privateFounderonlyExamplesClaudeUses: "Private founder-only examples Claude uses for structure and methodology when generating customer materials. Client-specific details are never copied into customer outputs. A material is only used once you mark it Approved.",
};

export const authText = {
  h_logInToBoardBuilder: "Log In to Board Builder",
  h_forgotYourPassword: "Forgot Your Password?",
  h_chooseANewPassword: "Choose a New Password",
};

export const dashboardText = {
  h_myBoardBuilder: "My Board Builder",
  h_noProgramsYet: "No Programs Yet",
  h_boardMemberPortfolioAmpFinal: "Board Member Portfolio &amp; Final Board Offer",
};

export const purchaseSuccessText = {
  h_confirmingYourPayment: "Confirming Your Payment\u2026",
  h_missingPurchaseDetails: "Missing Purchase Details",
  h_weCouldNotConfirmYour: "We Could Not Confirm Your Payment Yet",
  h_yourPurchaseIsLinkedTo: "Your Purchase Is Linked to Your Account",
};

export const myBoardText = {
  h_myBoard: "My Board",
  h_weCouldNotLoadYour: "We Could Not Load Your Results",
  h_yourRecruitmentResults: "Your Recruitment Results",
  h_recruitmentSummary: "Recruitment Summary",
  h_stillInProgress: "Still In Progress",
  h_notSelected: "Not Selected",
  h_needHelpMovingForward: "Need Help Moving Forward?",
  n_loadingYourRecruitmentResults: "Loading your recruitment results\u2026",
  n_boardMembersAppearHereAs: "Board members appear here as soon as they are formally confirmed in Step 5.",
};

export const materialsLibraryText = {
  h_myRecruitmentMaterials: "My Recruitment Materials",
};

export const sharedPagesText = {
  h_thankYou: "Thank you",
};

export const joinBoardText = {
  h_joinANonprofitBoardWhere: "Join a Nonprofit Board Where Your Skills, Experience and Network Can Make a Difference",
  h_findTheRightNonprofitBoard: "Find the Right Nonprofit Board Opportunity in Four Steps",
  h_nonprofitsNeedMoreThanNames: "Nonprofits Need More Than Names on Their Boards",
};

export const portfolioPageText = {
  h_thisPortfolioIsNotAvailable: "This Portfolio Is Not Available",
};

export const recruitIntakeText = {
  h_tellMeAboutYourOrganization: "Tell Me About Your Organization and Board",
  h_confirmingYourPayment: "Confirming Your Payment\u2026",
  h_thisFormIsForCustomers: "This Form Is for Customers Who Have Completed Payment",
  h_youreReadyToStart: "You're Ready to Start",
  h_letsScheduleYourCallWith: "Let's Schedule Your Call With Rooney",
  h_aboutYouAndYourOrganization: "About You and Your Organization",
  h_linkedin: "LinkedIn",
  h_yourPresentBoard: "Your Present Board",
  h_theBoardYouNeed: "The Board You Need",
  h_boardLogistics: "Board Logistics",
  s_giveMeTheInformationI: "Give me the information I need to start your board recruitment.",
};

export const reactivationIntakeText = {
  h_tellMeAboutYourBoard: "Tell Me About Your Board",
  h_confirmingYourPayment: "Confirming Your Payment\u2026",
  h_thisFormIsForCustomers: "This Form Is for Customers Who Have Completed Payment",
  h_youreReadyToStart: "You're Ready to Start",
  h_letsScheduleYourCallWith: "Let's Schedule Your Call With Rooney",
  h_yourOrganizationsDirection: "Your Organization's Direction",
  h_yourCurrentBoard: "Your Current Board",
  h_howYourBoardWasBuilt: "How Your Board Was Built",
  h_disengagement: "Disengagement",
  h_meetingsTransitions: "Meetings & Transitions",
  s_giveMeTheInformationI: "Give me the information I need to start reactivating your Board. Ask once \u2014 remembered throughout your Reactivation journey.",
};

export const activationIntakeText = {
  h_tellMeAboutYourFundraising: "Tell Me About Your Fundraising",
  h_confirmingYourPayment: "Confirming Your Payment\u2026",
  h_thisFormIsForCustomers: "This Form Is for Customers Who Have Completed Payment",
  h_youreReadyToStart: "You're Ready to Start",
  h_letsScheduleYourCallWith: "Let's Schedule Your Call With Rooney",
  h_yourOrganizationsDirection: "Your Organization's Direction",
  h_yourFundraisingToday: "Your Fundraising Today",
  h_whoCarriesFundraising: "Who Carries Fundraising",
  h_yourBoardFundraising: "Your Board & Fundraising",
  h_whatYouWantToChange: "What You Want to Change",
  s_giveMeTheInformationI: "Give me the information I need to start activating your Board around fundraising. Ask once \u2014 remembered throughout your Activation journey.",
};

export const recommitFormText = {
  h_boardMemberProfileAmpRecommitment: "Board Member Profile &amp; Recommitment Form",
  h_thisLinkIsNotValid: "This Link Is Not Valid",
  h_thankYou: "Thank You",
  h_aboutYou: "About You",
  h_yourExperienceOnTheBoard: "Your Experience on the Board",
  h_recommitment: "Recommitment",
  h_howYouWantToContribute: "How You Want to Contribute",
  h_yourCapacity: "Your Capacity",
  h_finalQuestions: "Final Questions",
  h_confirmation: "Confirmation",
  s_pleaseCompleteThisFormHonestly: "Please complete this form honestly. Your responses will help guide a conversation about how you would like to continue contributing to the organization.",
};

export const planningFormText = {
  h_loading: "Loading\u2026",
  h_thisFormLinkIsNot: "This Form Link Is Not Valid",
  h_thankYou: "Thank You",
  h_aboutYou: "About You",
};

export const spReviewText = {
  h_foundationalPlanReview: "Foundational Plan Review",
  h_thankYou: "Thank You",
  h_foundationalStrategicPlanBoardReview: "Foundational Strategic Plan \u2014 Board Review & Refinement",
};

export const areaPackText = {
  h_strategicAreaDevelopmentPack: "Strategic Area Development Pack",
  h_detailedPlanSubmitted: "Detailed Plan Submitted",
};

export const fundraisingPortfolioText = {
  h_thisPortfolioLinkIsNot: "This Portfolio Link Is Not Valid",
  h_fundraisingPortfolio: "FUNDRAISING PORTFOLIO",
};

export const strategyReviewText = {
  h_fundraisingStrategyPlan: "Fundraising Strategy Plan",
  h_loading: "Loading\u2026",
  h_thisReviewLinkIsNot: "This Review Link Is Not Valid",
  h_thankYou: "Thank You",
  h_yourReview: "Your Review",
  h_aboutYou: "About You",
  h_reviewEachIdea: "Review Each Part of the Plan",
  d_reviewEachIdea: "Review each part of the plan below. Approve the ideas you support. Disapprove the ones you do not, and share your reason so the Board can work through it together.",
};

export const strategyPlanText = {
  h_loading: "Loading\u2026",
  h_thisPlanLinkIsNot: "This Plan Link Is Not Valid",
  h_fundraisingStrategyPlan: "Fundraising Strategy Plan",
};

export const recruitProcessText = {
  h_yourPathToBuildingThe: "Your Path to Building the Board Your Nonprofit Needs",
  h_buildTheBoardYourMission: "Build the Board Your Mission Deserves",
};

export const recruitCheckoutText = {
  h_buildTheStrongerBoardYour: "Build the Stronger Board Your Nonprofit Has Been Missing",
  h_recruitmentGuarantee: "Recruitment Guarantee",
  h_whatYouWalkAwayWith: "What You Walk Away With",
  h_startRecruitingInLessThan: "Start Recruiting in Less Than 30 Minutes",
  h_buildTheBoardYourOrganization: "Build the Board Your Organization Needs",
};

export const funnelOptionsText = {
  h_doItYourself: "Do It Yourself",
  h_selfguidedRecruitment: "Self-Guided Recruitment",
  h_doneWithYou: "Done With You",
};

export const funnelResultText = {
  h_yourBoardToday: "Your Board Today",
  h_whatYourOrganizationNeedsTo: "What Your Organization Needs to Accomplish",
  h_areasYourRecruitmentShouldStrengthen: "Areas Your Recruitment Should Strengthen",
  h_howYourPresentBoardWas: "How Your Present Board Was Built",
  h_yourOrganizationalPriorities: "Your Organizational Priorities",
  h_whatYouWantToChange: "What You Want to Change",
  h_whatYouNeedToRaise: "What You Need to Raise Money For",
  h_fundraisingAreasForTheBoard: "Fundraising Areas for the Board",
};

export const memberShellText = {
  t_myBoardBuilder: "My Board Builder",
  t_logOut: "Log Out",
  t_logIn: "Log In",
};

export const funnelLayoutText = {
  t_reactivate: "Reactivate",
  t_recruit: "Recruit",
  t_fundraisingActivation: "Fundraising Activation",
  t_joinABoard: "Join a Board",
  t_logIn: "Log In",
  t_chooseYourBoardSolution: "Choose Your Board Solution",
  t_privacyPolicy: "Privacy Policy",
};

export const funnelFormText = {
  t_yourStartingPoint: "Your starting point",
};

export const funnelControlsText = {
  t_selectOne: "Select one",
};

export const funnelStepText = {
  t_continue: "Continue ",
};
