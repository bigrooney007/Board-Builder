import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { FunnelChoices, FunnelRadioCards, FunnelSelect, FunnelText, FunnelTextarea } from "./FunnelFormControls";
import { funnelConfigs } from "./funnelConfig";
import { useReviewMode } from "@/reviewMode";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const emptyContact = { name: "", email: "", phone: "", organization: "", website: "", city: "", state_region: "", country: "" };

const emptyAnswers = (config) => {
  const answers = {};
  config.steps.forEach((step) => step.fields.forEach((field) => {
    if (field.scope === "answers") answers[field.name] = field.type === "choices" ? [] : "";
  }));
  return answers;
};

export const FunnelStepForm = ({ offerSource }) => {
  const config = funnelConfigs[offerSource];
  const navigate = useNavigate();
  const reviewMode = useReviewMode();
  const reviewBypass = reviewMode && offerSource === "recruitment";
  const totalSteps = config.steps.length;
  const [stepIndex, setStepIndex] = useState(0);
  const [contact, setContact] = useState(emptyContact);
  const [answers, setAnswers] = useState(() => emptyAnswers(config));
  const [errors, setErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const valueFor = (field) => (field.scope === "contact" ? contact[field.name] : answers[field.name]);
  const update = (name, value, scope) => {
    if (scope === "contact") setContact((current) => ({ ...current, [name]: value }));
    else setAnswers((current) => ({ ...current, [name]: value }));
    setErrors((current) => ({ ...current, [name]: undefined }));
  };

  const visibleFields = (step) => step.fields.filter((field) => !field.showIf || field.showIf(answers));

  const validateStep = () => {
    const step = config.steps[stepIndex];
    const found = {};
    visibleFields(step).forEach((field) => {
      const value = valueFor(field);
      const required = field.required !== false;
      if (required && (value === "" || (Array.isArray(value) && !value.length))) {
        found[field.name] = field.type === "choices" || field.type === "select" || field.type === "textarea" ? "This question is required." : "This field is required.";
      }
    });
    if (step.fields.some((field) => field.name === "email") && contact.email && !/^\S+@\S+\.\S+$/.test(contact.email)) found.email = "Enter a valid email address.";
    if (step.fields.some((field) => field.name === "active_board") && answers.present_board !== "" && answers.active_board !== "" && Number(answers.active_board) > Number(answers.present_board)) {
      found.active_board = "Active board members cannot exceed the present board size.";
    }
    setErrors(found);
    return Object.keys(found).length === 0;
  };

  const goBack = () => { setSubmitError(""); setStepIndex((current) => Math.max(0, current - 1)); window.scrollTo({ top: document.getElementById("offer-form")?.offsetTop - 90 || 0, behavior: "smooth" }); };
  const goForward = async () => {
    if (!reviewBypass && !validateStep()) return;
    if (stepIndex < totalSteps - 1) {
      setStepIndex((current) => current + 1);
      window.scrollTo({ top: document.getElementById("offer-form")?.offsetTop - 90 || 0, behavior: "smooth" });
      return;
    }
    if (reviewBypass) {
      navigate("/recruit-with-rooney");
      return;
    }
    setSubmitting(true); setSubmitError("");
    try {
      const response = await axios.post(`${API}/funnel-leads/${offerSource}`, { ...contact, answers });
      sessionStorage.setItem("funnelLeadContext", JSON.stringify({ lead_id: response.data.lead_id, result_token: response.data.result_token, offer_source: offerSource, organization: contact.organization, support_preference: answers.support_preference || "" }));
      if (config.redirectAfterSubmit === "options") navigate(`/${config.slug}/options`);
      else if (config.redirectAfterSubmit === "rooney") navigate("/recruit-with-rooney");
      else if (config.redirectAfterSubmit === "reactivate-rooney") navigate("/reactivate-with-rooney");
      else if (config.redirectAfterSubmit === "process") navigate(`/${config.slug}/process`);
      else navigate(`/${config.slug}/result/${response.data.result_token}`);
    } catch (error) {
      setSubmitError(error.response?.data?.detail || "We could not save your submission. Please try again.");
      setSubmitting(false);
    }
  };

  const step = config.steps[stepIndex];
  const isLast = stepIndex === totalSteps - 1;

  return (
    <section id="offer-form" className="funnel-form-section" data-testid={`${offerSource}-lead-form-section`}>
      <div className="funnel-lead-form step-form">
        <div className="form-title">
          <p className="eyebrow">{config.formHeading}</p>
          <div className="step-progress" data-testid={`${offerSource}-step-progress`}>
            <span className="step-count" data-testid={`${offerSource}-step-count`}>Step {stepIndex + 1} of {totalSteps}</span>
            <div className="step-progress-bar" role="progressbar" aria-valuenow={stepIndex + 1} aria-valuemin={1} aria-valuemax={totalSteps}>
              <i style={{ width: `${((stepIndex + 1) / totalSteps) * 100}%` }} />
            </div>
          </div>
          <h2 data-testid={`${offerSource}-form-heading`}>{step.heading}</h2>
        </div>
        <div className="step-fields" key={stepIndex} data-testid={`${offerSource}-step-${stepIndex + 1}`}>
          {visibleFields(step).map((field) => {
            const shared = { name: field.name, label: field.label, value: valueFor(field), error: errors[field.name], update: (name, value) => update(name, value, field.scope) };
            if (field.type === "select") return <FunnelSelect key={field.name} {...shared} options={field.options} />;
            if (field.type === "textarea") return <FunnelTextarea key={field.name} {...shared} helper={field.helper} required={field.required !== false} />;
            if (field.type === "choices") return <FunnelChoices key={field.name} {...shared} options={field.options} helper={field.helper} />;
            if (field.type === "radio_cards") return <FunnelRadioCards key={field.name} {...shared} options={field.options} />;
            return <FunnelText key={field.name} {...shared} type={field.inputType || "text"} required={field.required !== false} />;
          })}
        </div>
        {submitError && <p className="submit-error" data-testid={`${offerSource}-submit-error`}>{submitError}</p>}
        <div className="step-actions">
          {stepIndex > 0 ? (
            <button type="button" className="button button-back step-back" onClick={goBack} data-testid={`${offerSource}-back-button`}><ArrowLeft size={16} /> Back</button>
          ) : <span />}
          <button type="button" className="button funnel-submit" disabled={submitting} onClick={goForward} data-testid={isLast ? `${offerSource}-submit-button` : `${offerSource}-continue-button`}>
            {submitting ? "Saving…" : isLast ? config.submit : <>Continue <ArrowRight size={16} /></>}
          </button>
        </div>
      </div>
    </section>
  );
};
