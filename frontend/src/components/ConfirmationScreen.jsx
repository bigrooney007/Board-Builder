import { Check } from "lucide-react";
import { confirmationScreenText } from "../content/siteContent";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

export const ConfirmationScreen = ({ confirmation, onHome }) => (
  <main className="confirmation-page" data-testid="confirmation-screen">
    <div className="confirmation-brand" data-testid="confirmation-brand"><img src={logoUrl} alt={confirmationScreenText.nonprofitBoardBuilder} data-testid="confirmation-brand-logo-image" /></div>
    <section className="confirmation-card">
      <div className="confirmation-icon" data-testid="confirmation-success-icon"><Check size={34} /></div>
      <p className="eyebrow" data-testid="confirmation-eyebrow">Assessment successfully submitted</p>
      <h1 data-testid="confirmation-heading">{confirmationScreenText.thankYouWeHaveReceived}</h1>
      <p data-testid="confirmation-review-text">{confirmationScreenText.weWillPersonallyReviewYour}</p>
      <p data-testid="confirmation-follow-up-text">{confirmationScreenText.pleaseLookOutForAn}</p>
      <div className="confirmation-details" data-testid="confirmation-details">
        <div><span>Organization</span><strong data-testid="confirmation-organization-name">{confirmation?.organization_name}</strong></div>
        <div><span>Assessment number</span><strong data-testid="confirmation-assessment-number">{confirmation?.assessment_number}</strong></div>
        <div><span>Submitted email</span><strong data-testid="confirmation-submitted-email">{confirmation?.submitted_email}</strong></div>
      </div>
      <p className="phone-note" data-testid="confirmation-phone-note">{confirmationScreenText.weMayAlsoContactYou}</p>
      <button className="button" onClick={onHome} data-testid="return-homepage-button">Return to Homepage</button>
    </section>
  </main>
);