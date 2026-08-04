import { useState } from "react";
import axios from "axios";
import { ApplicantStepFour, ApplicantStepOne, ApplicantStepThree, ApplicantStepTwo } from "./ApplicantFormSteps";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const initialData = {
  first_name: "", last_name: "", email: "", phone: "", linkedin_url: "", country: "", city: "", state_region: "", postal_code: "",
  job_title: "", employer: "", professional_field: "", years_experience: "", skills: [], other_skill: "", professional_summary: "", resume: null,
  causes: [], other_cause: "", board_types: [], participation_preferences: [], geographic_preferences: "", availability: "", monthly_commitment: "",
  previous_board_experience: "", board_experience_details: "", fundraising_activities: [], professional_relationships: "", reason_for_joining: "", commitment_answer: "", understands_unpaid: "",
  profile_sharing_permission: false, board_opportunity_consent: false, other_offers_consent: false, privacy_accepted: false,
};

const required = [
  ["first_name", "last_name", "email", "phone", "country", "city", "state_region"],
  ["job_title", "professional_field", "years_experience", "skills", "professional_summary"],
  ["causes", "board_types", "participation_preferences", "geographic_preferences", "availability", "monthly_commitment"],
  ["previous_board_experience", "fundraising_activities", "professional_relationships", "reason_for_joining", "commitment_answer", "understands_unpaid", "profile_sharing_permission", "board_opportunity_consent", "privacy_accepted"],
];

export const ApplicantForm = ({ onComplete }) => {
  const [step, setStep] = useState(1);
  const [data, setData] = useState(initialData);
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const update = (name, value) => {
    setData((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  };

  const validate = () => {
    const found = {};
    required[step - 1].forEach((name) => {
      const value = data[name];
      if (!value || (Array.isArray(value) && value.length === 0)) found[name] = "This question is required.";
    });
    if (step === 1 && data.email && !/^\S+@\S+\.\S+$/.test(data.email)) found.email = "Enter a valid email address.";
    if (step === 1 && !["United States", "United Kingdom"].includes(data.country)) found.country = "Select United States or United Kingdom.";
    if (step === 2 && data.skills.includes("Something else") && !data.other_skill) found.other_skill = "Describe your other skill.";
    if (step === 2 && data.resume && data.resume.size > 8 * 1024 * 1024) found.resume = "Résumé must be 8 MB or smaller.";
    if (step === 3 && data.causes.includes("Other") && !data.other_cause) found.other_cause = "Describe your other cause.";
    if (step === 4 && data.previous_board_experience.startsWith("Yes") && !data.board_experience_details) found.board_experience_details = "Tell us briefly about your board experience.";
    setErrors(found);
    return Object.keys(found).length === 0;
  };

  const next = () => {
    if (!validate()) return;
    setStep((current) => current + 1);
    document.getElementById("applicant-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const back = () => {
    setStep((current) => current - 1);
    setErrors({});
    document.getElementById("applicant-form")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const submit = async () => {
    if (!validate()) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      const form = new FormData();
      const payload = { ...data };
      delete payload.resume;
      form.append("payload", JSON.stringify(payload));
      if (data.resume) form.append("resume", data.resume);
      const response = await axios.post(`${API}/applicants`, form);
      onComplete(response.data);
    } catch (error) {
      const detail = error.response?.data?.detail;
      setSubmitError(typeof detail === "string" ? detail : "We could not save your profile. Please try again.");
      setSubmitting(false);
    }
  };
  const shared = { data, update, errors };
  return <section id="applicant-form" className="join-form-section" data-testid="board-applicant-form"><div className="form-shell applicant-form-shell"><div className="progress-copy"><span data-testid="applicant-progress-text">Step {step} of 4</span><span>{step * 25}% complete</span></div><div className="progress-track" data-testid="applicant-progress-indicator"><div style={{ width: `${step * 25}%` }} /></div>{step === 1 && <ApplicantStepOne {...shared} next={next} />}{step === 2 && <ApplicantStepTwo {...shared} back={back} next={next} />}{step === 3 && <ApplicantStepThree {...shared} back={back} next={next} />}{step === 4 && <ApplicantStepFour {...shared} back={back} submit={submit} submitting={submitting} submitError={submitError} />}</div></section>;
};