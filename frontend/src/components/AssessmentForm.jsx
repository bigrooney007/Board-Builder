import { useState } from "react";
import axios from "axios";
import { ArrowLeft } from "lucide-react";
import { StepOne } from "@/components/form/StepOne";
import { StepTwo } from "@/components/form/StepTwo";
import { StepThree } from "@/components/form/StepThree";
import { StepFour } from "@/components/form/StepFour";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

const initialData = {
  name: "", email: "", phone: "", organization_name: "", website: "", mission: "", city: "", state_region: "", country: "", annual_budget: "", most_important_board_result: "",
  bylaws_board_size: "", current_board_size: "", active_board_members: "", inactive_board_members: "", present_board_condition: [], board_type: "", commitment_conversations: "", willing_to_allow_step_down: "", bylaw_clarity: "",
  new_board_members_needed: "", recruitment_timeline: "", areas_carried_alone: [], missing_skills_networks: "", expected_new_member_benefit: "", people_already_identified: "", benefits_of_joining: "", previous_recruitment_experience: "",
  present_fundraising_involvement: "", board_support_areas: [], written_fundraising_strategy: "", individual_responsibilities: "", board_participation_in_planning: "", missing_fundraising_elements: [], desired_result: "", support_required: "", additional_information: "", confirmation_accepted: false, marketing_consent: false,
};

const requiredByStep = [
  ["name", "email", "phone", "organization_name", "mission", "city", "state_region", "country", "annual_budget", "most_important_board_result"],
  ["bylaws_board_size", "current_board_size", "active_board_members", "inactive_board_members", "present_board_condition", "board_type", "commitment_conversations", "willing_to_allow_step_down", "bylaw_clarity"],
  ["new_board_members_needed", "recruitment_timeline", "areas_carried_alone", "missing_skills_networks", "expected_new_member_benefit", "people_already_identified", "benefits_of_joining", "previous_recruitment_experience"],
  ["present_fundraising_involvement", "board_support_areas", "written_fundraising_strategy", "individual_responsibilities", "board_participation_in_planning", "missing_fundraising_elements", "desired_result", "support_required", "confirmation_accepted"],
];

export const AssessmentForm = ({ onComplete, onHome }) => {
  const [step, setStep] = useState(1);
  const [data, setData] = useState(initialData);
  const [errors, setErrors] = useState({});
  const [submitError, setSubmitError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const update = (name, value) => {
    setData((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  };

  const validate = () => {
    const nextErrors = {};
    requiredByStep[step - 1].forEach((field) => {
      const value = data[field];
      if (!value || (Array.isArray(value) && !value.length)) nextErrors[field] = "This question is required.";
    });
    if (step === 1 && data.email && !/^\S+@\S+\.\S+$/.test(data.email)) nextErrors.email = "Enter a valid email address.";
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const next = () => {
    if (!validate()) return;
    setStep((current) => current + 1);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const back = () => {
    setStep((current) => current - 1);
    setErrors({});
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const submit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const response = await axios.post(`${API}/assessments`, data);
      onComplete(response.data);
    } catch (error) {
      setSubmitError(error.response?.data?.detail?.[0]?.msg || "We could not submit your assessment. Please try again.");
      setSubmitting(false);
    }
  };

  const shared = { data, update, errors };
  return (
    <main className="form-page" data-testid="board-assessment-form-page">
      <header className="form-header">
        <button onClick={onHome} className="back-home" data-testid="assessment-back-home-button"><ArrowLeft size={17} /> Homepage</button>
        <div className="form-brand" data-testid="assessment-brand"><img src={logoUrl} alt="Nonprofit Board Builder" data-testid="assessment-brand-logo-image" /></div>
        <span className="secure-note" data-testid="assessment-private-note">Private assessment</span>
      </header>
      <section className="form-shell">
        <div className="progress-copy"><span data-testid="assessment-progress-text">Step {step} of 4</span><span data-testid="assessment-progress-percent">{step * 25}% complete</span></div>
        <div className="progress-track" data-testid="assessment-progress-indicator"><div style={{ width: `${step * 25}%` }} /></div>
        {step === 1 && <StepOne {...shared} onNext={next} />}
        {step === 2 && <StepTwo {...shared} onBack={back} onNext={next} />}
        {step === 3 && <StepThree {...shared} onBack={back} onNext={next} />}
        {step === 4 && <StepFour {...shared} onBack={back} onSubmit={submit} submitting={submitting} submitError={submitError} />}
      </section>
    </main>
  );
};