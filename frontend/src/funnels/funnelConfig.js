export const CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard";

const contactFields = [ // eslint-disable-line no-unused-vars
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
const strategicOptions = ["Yes", "We have a strategic plan, but the board was not meaningfully involved", "We started but did not complete it", "No", "We do not currently have a strategic plan", "I am not sure"]; // eslint-disable-line no-unused-vars

export const funnelConfigs = {
  board_fix: {
    slug: "board-fix", eyebrow: "BOARD FIX",
    heading: "Tell Us About Your Board",
    supporting: "Enter your information below, and we will show you the three mistakes you are making with your board that are limiting your organization's ability to raise money exponentially and grow.",
    formHeading: "Tell Us About You and Your Organization",
    submit: "Show Me How You Can Help",
    redirectAfterSubmit: "offer-board-fix",
    steps: [
      {
        heading: "Tell Us About You and Your Organization",
        fields: [
          { type: "text", name: "first_name", label: "First name", scope: "contact" },
          { type: "text", name: "last_name", label: "Last name", scope: "contact" },
          { type: "text", name: "organization", label: "Organization name", scope: "contact" },
          { type: "text", name: "email", label: "Email address", inputType: "email", scope: "contact" },
          { type: "text", name: "phone", label: "Phone number", inputType: "tel", scope: "contact" },
          { type: "text", name: "website", label: "Website (optional)", inputType: "url", required: false, scope: "contact" },
        ],
      },
    ],
  },
  recruitment: {
    slug: "recruit", eyebrow: "Board Recruitment",
    heading: "Start the Process of Recruiting the Board Your Nonprofit Needs",
    supporting: "Enter your organization details below, and we will show you the 2 ways to launch your board recruitment campaign and start building a board that commits, helps raise money, and works with you to build the organization your mission deserves in just 30 minutes.",
    formHeading: "Tell Us About the Board You Want to Recruit",
    submit: "Show Me How You Can Help",
    redirectAfterSubmit: "offer-recruitment",
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
    heading: "Stop Carrying Dead Weight on Your Board",
    supporting: "Your Board should help carry the organization — not become more weight for you to carry. Find out who is ready to stand up, give them clear responsibility, and help those who are no longer prepared to serve step down or transition without destroying relationships.",
    formHeading: "Tell Us About You and Your Board",
    submit: "SHOW ME HOW TO REACTIVATE MY BOARD",
    redirectAfterSubmit: "reactivate-rooney",
    resultHeading: "Your Board Reactivation Starting Point",
    resultCta: "I’m Ready to Reactivate My Board",
    steps: [
      {
        heading: "Tell Us About You and Your Organization",
        fields: [
          { type: "text", name: "name", label: "Your name", scope: "contact" },
          { type: "text", name: "email", label: "Email address", inputType: "email", scope: "contact" },
          { type: "text", name: "organization", label: "Organization name", scope: "contact" },
          { type: "text", name: "phone", label: "Phone number", inputType: "tel", scope: "contact" },
          { type: "select", name: "disengaged_count", label: "How Many of Your Board Members Are Currently Disengaged?", options: ["1", "2", "3", "4", "5", "6+", "Most of the Board", "Not Sure"], scope: "answers" },
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
    heading: "Turn Your Board Into Fundraising Champions for Your Mission",
    supporting: "Your Board should not sit on the sidelines while you carry fundraising alone. Get your Board involved in building the fundraising plan, taking ownership of the strategy, accepting clear responsibility and helping your organization raise the money it needs to move the mission forward.",
    formHeading: "Tell Us About You and Your Organization",
    submit: "SHOW ME HOW TO ACTIVATE MY BOARD",
    redirectAfterSubmit: "activate-rooney",
    resultHeading: "Your Board Fundraising Activation Starting Point",
    resultCta: "I’m Ready to Activate My Board",
    steps: [
      {
        heading: "Tell Us About You and Your Organization",
        fields: [
          { type: "text", name: "name", label: "Your name", scope: "contact" },
          { type: "text", name: "email", label: "Email address", inputType: "email", scope: "contact" },
          { type: "text", name: "organization", label: "Organization name", scope: "contact" },
          { type: "text", name: "phone", label: "Phone number", inputType: "tel", scope: "contact" },
          { type: "select", name: "board_member_count", label: "How Many Board Members Do You Currently Have?", options: ["0", "1", "2", "3", "4", "5", "6", "7+", "Not Sure"], scope: "answers" },
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
