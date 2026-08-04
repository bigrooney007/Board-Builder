import { Link } from "react-router-dom";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

const privacySections = [
  ["Information We Collect", "We collect information submitted through the nonprofit board assessment and Board Applicant Network, including contact information, organization or professional details, board preferences, consent choices and uploaded résumés or CVs."],
  ["Board Applicant Profiles", "Applicant profiles are stored to review and identify possible board-opportunity matches. Profiles may be shared with nonprofit organizations only when the applicant gives profile-sharing permission."],
  ["Email Preferences", "We store email preferences and exact consent timestamps. Applicants and nonprofit leaders are subscribed only to the email categories they explicitly select and may unsubscribe at any time."],
  ["Weekly Email Reports", "Consenting nonprofit leaders may receive weekly Board Applicant Network reports and relevant board-building emails. Consenting applicants may receive weekly Board Applicant Network reports, nonprofit board opportunities and information directly connected to finding and serving on boards."],
  ["Aggregate Reporting", "Weekly reports contain aggregate numbers only. Applicant names, contact details, employers, résumés, LinkedIn profiles and personal application answers are not disclosed in nonprofit reports. Confidential nonprofit assessment details, organization identities and contact information are not disclosed in applicant reports."],
  ["Email Engagement and Tracked Actions", "We may record email engagement and clicks on secure Text I Am Ready or Confirm I Am Available links. A tracked click records that the contact opened the text-message action; it does not confirm that a text message was sent."],
  ["Profile Updates and Removal", "Applicants may ask Nonprofit Board Builder to update, pause, withdraw or remove their profile and associated contact information."],
  ["How Information Is Used", "Nonprofit board assessment information and board applicant information are stored to review board needs, manage applicant profiles, communicate relevant opportunities, fulfil requested services and maintain consent records. Personal information is not sold."],
  ["Résumés and Contact Details", "Résumés, CVs and contact details are protected in persistent storage and are available only through the private administrator area, except when an applicant has permitted profile sharing with nonprofits."],
  ["Email Processing", "Resend processes email contact details, audience segments, topic subscriptions, delivery information and unsubscribe preferences for Nonprofit Board Builder."],
  ["Network Availability", "The Board Applicant Network is currently limited to professionals living in the United States and United Kingdom."],
  ["Contact", "Privacy or profile requests may be sent to boardapplicants@nonprofitboardbuilder.com. Postal address: 651 N Broad Street, Middletown, Delaware 19709."],
];
const termsSections = [
  ["Service Scope", "Nonprofit Board Builder provides board assessment, consulting, applicant-network and board-opportunity communication services. Submitting information does not guarantee placement, recruitment, engagement or a specific result."],
  ["Applicant Responsibilities", "Applicants must provide accurate information, maintain appropriate professional conduct and independently evaluate any organization or board opportunity before accepting a position."],
  ["Volunteer Board Service", "Most nonprofit board positions are unpaid volunteer leadership roles. Specific responsibilities, fiduciary duties, insurance and expectations are determined by each nonprofit."],
  ["Nonprofit Responsibilities", "Nonprofits remain responsible for candidate review, references, background checks, legal compliance, appointment decisions and board governance."],
  ["Communications", "Users may receive emails only according to the consent choices they make and may unsubscribe from optional communications at any time."],
  ["Contact", "Questions about these terms may be sent to rooney@nonprofitboardbuilder.com. Postal address: 651 N Broad Street, Middletown, Delaware 19709."],
];

export default function LegalPage({ type }) {
  const privacy = type === "privacy";
  const sections = privacy ? privacySections : termsSections;
  return <main className="legal-page" data-testid={privacy ? "privacy-policy-page" : "terms-page"}><header className="legal-header"><Link to="/"><img src={logoUrl} alt="Nonprofit Board Builder" /></Link><Link className="button button-small" to="/">Return Home</Link></header><article><p className="eyebrow">Nonprofit Board Builder</p><h1>{privacy ? "Privacy Policy" : "Terms"}</h1><p className="legal-updated">Last updated August 4, 2026</p>{sections.map(([heading, text]) => <section key={heading}><h2>{heading}</h2><p>{text}</p></section>)}</article></main>;
}