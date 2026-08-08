export const CALENDLY_URL = "https://calendly.com/boardbuilder/recruitboard";

export const funnelConfigs = {
  recruitment: {
    slug: "recruit", eyebrow: "Board Recruitment",
    heading: "Recruit the Board Members Your Nonprofit Needs to Move Forward",
    supporting: "Stop filling board seats simply because someone is willing to serve. Build your recruitment process around the skills, experience, fundraising capacity and relationships your organization actually needs.",
    formHeading: "Build Your Board Recruitment Starting Point",
    heroCta: "Build My Board Recruitment Starting Point",
    submit: "Show Me My Recruitment Starting Point",
    resultHeading: "Your Board Recruitment Starting Point",
    resultCta: "I’m Ready to Recruit My Board",
    option97: "Learn the Board Recruitment Process and Execute It Yourself",
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
    resultHeading: "Your Board Reactivation Starting Point",
    resultCta: "I’m Ready to Reactivate My Board",
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
    resultHeading: "Your Board Fundraising Activation Starting Point",
    resultCta: "I’m Ready to Activate My Board",
    option97: "Learn the Board Fundraising Activation Process and Execute It Yourself",
    option497: "Follow the Self-Guided Board Fundraising Activation System",
    option3497: "Activate My Board With Me",
  },
};

export const sourceFromSlug = (slug) => Object.keys(funnelConfigs).find((key) => funnelConfigs[key].slug === slug);