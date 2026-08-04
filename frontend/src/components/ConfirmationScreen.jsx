import { Check } from "lucide-react";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

export const ConfirmationScreen = ({ confirmation, onHome }) => (
  <main className="confirmation-page" data-testid="confirmation-screen">
    <div className="confirmation-brand" data-testid="confirmation-brand"><img src={logoUrl} alt="Nonprofit Board Builder" data-testid="confirmation-brand-logo-image" /></div>
    <section className="confirmation-card">
      <div className="confirmation-icon" data-testid="confirmation-success-icon"><Check size={34} /></div>
      <p className="eyebrow" data-testid="confirmation-eyebrow">Assessment successfully submitted</p>
      <h1 data-testid="confirmation-heading">Thank You — We Have Received Your Board Assessment</h1>
      <p data-testid="confirmation-review-text">We will personally review your present board, identify which board members can be reactivated, determine the exact type of board members you may need to recruit, and assess what must happen to activate your board around fundraising.</p>
      <p data-testid="confirmation-follow-up-text">Please look out for an email from Nonprofit Board Builder shortly. We will explain what you need to do to begin transforming your present board into a powerhouse fundraising board and the available options for us to help you execute.</p>
      <div className="confirmation-details" data-testid="confirmation-details">
        <div><span>Organization</span><strong data-testid="confirmation-organization-name">{confirmation?.organization_name}</strong></div>
        <div><span>Assessment number</span><strong data-testid="confirmation-assessment-number">{confirmation?.assessment_number}</strong></div>
        <div><span>Submitted email</span><strong data-testid="confirmation-submitted-email">{confirmation?.submitted_email}</strong></div>
      </div>
      <p className="phone-note" data-testid="confirmation-phone-note">We may also contact you using the phone number provided if we are unable to reach you by email.</p>
      <button className="button" onClick={onHome} data-testid="return-homepage-button">Return to Homepage</button>
    </section>
  </main>
);