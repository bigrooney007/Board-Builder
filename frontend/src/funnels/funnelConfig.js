export const CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard";

const contactFields = [
  { type: "text", name: "name", label: "Your name", scope: "contact" },
  { type: "text", name: "email", label: "Email address", inputType: "email", scope: "contact" },
  { type: "text", name: "phone", label: "Phone number", inputType: "tel", scope: "contact" },
  { type: "text", name: "organization", label: "Organization name", scope: "contact" },
  { type: "text", name: "website", label: "Website", inputType: "url", required: false, scope: "contact" },
  { type: "text", name: "city", label: "City", scope: "contact" },
  { type: "text", name: "state_region", label: "State or region", scope: "contact" },
  { type: "select", name: "country", label: "Country", options: ["United States", "United Kingdom", "Other"], scope: "contact" },
];

const accomplishAreas = ["Raise money", "Build corporate partnerships", "Connect with major donors", "Strengthen grant development", "Strengthen finance and financial oversight", "Strengthen governance", "Improve strategic planning", "Strengthen marketing and communications", "Build community relationships", "Provide legal expertise", "Strengthen technology", "Strengthen programs", "Strengthen operations", "Make professional introductions and connections", "Bring important lived experience or community perspective", "Help the organization grow", "Expand programs or services", "Increase visibility", "Other"]; // eslint-disable-line no-unused-vars
const strategicOptions = ["Yes", "We have a strategic plan, but the board was not meaningfully involved", "We started but did not complete it", "No", "We do not currently have a strategic plan", "I am not sure"];

export const funnelConfigs = {
  recruitment: {
    slug: "recruit", eyebrow: "Board Recruitment",
    heading: "Start the Process of Recruiting the Board Your Nonprofit Needs",
    supporting: "Enter your organization details below and we will show you the 6-step process to build a board that commits, helps raise money and works with you to build the organization your mission deserves.",
    formHeading: "Tell Us About the Board You Want to Recruit",
    submit: "Show Me How You Can Help",
    redirectAfterSubmit: "rooney",
    steps: [
      {
        heading: "Tell Us About You and Your Organization",
        fields: [
          { type: "text", name: "name", label: "Your name", scope: "contact" },
          { type: "text", name: "email", label: "Email address", inputType: "email", scope: "contact" },
          { type: "text", name: "organization", label: "Organization name", scope: "contact" },
          { type: "text", name: "phone", label: "Phone number", inputType: "tel", scope: "contact" },
          { type: "select", name: "new_members_needed", label: "How Many Board Members Do You Want to Recruit?", options: ["1", "2", "3", "4", "5", "6+", "Not Sure"], scope: "answers" },
        ],
      },
    ],
    optionsHeading: "Choose the Level of Support You Want Recruiting Your Board",
    optionsSupporting: "Whether you want to do it yourself, have the system guide you, or have us work directly with you, choose the level of support that works for you.",
    option97: "Get the Instructions and Execute It Yourself",
    option497: "Follow the Self-Guided Board Recruitment System",
    option3497: "Recruit My Board With Me",
  },
  reactivation: {
    slug: "reactivate", eyebrow: "Board Reactivation",
    heading: "Get Your Present Board to Step Up or Step Down Without Destroying Relationships",
    supporting: "Give each present board member a clear opportunity to recommit, accept meaningful responsibility and contribute. Those who can no longer serve should have a respectful way to step down.",
    formHeading: "Build Your Board Reactivation Starting Point",
    heroCta: "Build My Board Reactivation Starting Point",
    submit: "Show Me My Reactivation Starting Point",
    redirectAfterSubmit: "result",
    resultHeading: "Your Board Reactivation Starting Point",
    resultCta: "I’m Ready to Reactivate My Board",
    steps: [
      { heading: "Tell Us About You and Your Organization", fields: contactFields },
      {
        heading: "Tell Us About Your Present Board",
        fields: [
          { type: "text", name: "present_board", label: "How many people are presently on your board?", inputType: "number", scope: "answers" },
          { type: "text", name: "active_board", label: "How many are consistently active?", inputType: "number", scope: "answers" },
          { type: "choices", name: "inactive_situations", label: "What is happening with the board members who are not consistently active?", options: ["They do not attend meetings", "They attend but do not accept responsibility", "They do not respond to emails, calls or texts", "They say they are committed but rarely follow through", "They are supportive but do not know what to do", "They are too busy", "Some may be ready to step down", "Other"], scope: "answers" },
          { type: "select", name: "recommitment_conversations", label: "Have you individually asked these board members whether they are still willing and able to serve?", options: ["Yes, all of them", "Some of them", "No", "I am not sure"], scope: "answers" },
        ],
      },
      {
        heading: "Tell Us What You Want to Change",
        fields: [
          { type: "select", name: "strategic_planning", label: "Has your present board participated in strategic planning together?", options: strategicOptions, scope: "answers" },
          { type: "textarea", name: "priorities", label: "What are the three most important priorities your organization needs to accomplish during the next 12 months?", scope: "answers" },
          { type: "choices", name: "desired_changes", label: "What would you most like to change about the present board?", options: ["More participation", "Better meeting attendance", "Clearer responsibilities", "More fundraising involvement", "Better accountability", "Allow inactive members to step down", "Rebuild most of the board", "Other"], scope: "answers" },
        ],
      },
    ],
    optionsHeading: "Board Reactivation Options",
    optionsSupporting: "Choose the level of training, technology and execution support that fits your organization.",
    option97: "Learn the Board Reactivation Process and Execute It Yourself",
    option497: "Follow the Self-Guided Board Reactivation System",
    option3497: "Reactivate My Board With Me",
  },
  fundraising_activation: {
    slug: "activate", eyebrow: "Board Fundraising Activation",
    heading: "Activate Your Board to Start Raising Money",
    supporting: "Your board members do not all need to become professional fundraisers. They need a clear way to contribute based on their strengths, experience, relationships and willingness to execute.",
    formHeading: "Build Your Board Fundraising Starting Point",
    heroCta: "Build My Board Fundraising Starting Point",
    submit: "Show Me My Fundraising Starting Point",
    redirectAfterSubmit: "result",
    resultHeading: "Your Board Fundraising Activation Starting Point",
    resultCta: "I’m Ready to Activate My Board",
    steps: [
      { heading: "Tell Us About You and Your Organization", fields: contactFields },
      {
        heading: "Tell Us About Your Board Today",
        fields: [
          { type: "text", name: "present_board", label: "How many people are presently on your board?", inputType: "number", scope: "answers" },
          { type: "text", name: "active_board", label: "How many are consistently active?", inputType: "number", scope: "answers" },
          { type: "select", name: "fundraising_involvement", label: "How involved is your board in fundraising today?", options: ["Most board members are involved", "Some board members are involved", "One person does most of it", "No board members are actively involved"], scope: "answers" },
          { type: "select", name: "strategic_planning", label: "Has your board participated in strategic planning together?", options: strategicOptions, scope: "answers" },
        ],
      },
      {
        heading: "Tell Us About Your Fundraising",
        fields: [
          { type: "select", name: "fundraising_strategy", label: "Does your organization have a written fundraising strategy?", options: ["Yes", "Yes, but the board is not meaningfully involved", "Yes, but it needs updating", "No", "I am not sure"], scope: "answers" },
          { type: "select", name: "individual_responsibilities", label: "Does each board member have a defined fundraising responsibility?", options: ["Yes", "Some do", "No", "I am not sure"], scope: "answers" },
          { type: "textarea", name: "fundraising_need", label: "What does your organization most need to raise money for during the next 12 months?", scope: "answers" },
          { type: "choices", name: "fundraising_areas", label: "Which fundraising areas would you most like your board to help with?", options: ["Corporate partnerships", "Major donors", "Donor introductions", "Grants", "Events", "Sponsorship", "Community relationships", "Fundraising committee", "Volunteer fundraising team", "Donor stewardship", "Other"], scope: "answers" },
        ],
      },
    ],
    optionsHeading: "Board Fundraising Activation Options",
    optionsSupporting: "Choose the level of training, technology and execution support that fits your organization.",
    option97: "Learn the Board Fundraising Activation Process and Execute It Yourself",
    option497: "Follow the Self-Guided Board Fundraising Activation System",
    option3497: "Activate My Board With Me",
  },
};

export const sourceFromSlug = (slug) => Object.keys(funnelConfigs).find((key) => funnelConfigs[key].slug === slug);
