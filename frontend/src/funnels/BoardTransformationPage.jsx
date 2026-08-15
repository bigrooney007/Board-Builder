import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { FunnelLayout } from "./FunnelLayout";
import { SITE_CONTENT } from "@/content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const RECRUIT_OPTIONS = ["Yes", "No", "Not Sure"];
const REACTIVATE_OPTIONS = ["Yes — all of them if possible", "Yes — some of them", "No", "Not Sure"];
const FUNDRAISING_NOW_OPTIONS = ["Yes — most do", "Some do", "Very little", "No", "Not Sure"];
const WANT_FUNDRAISING_OPTIONS = ["Yes", "No", "Not Sure"];

const RadioGroup = ({ name, options, value, onChange }) => (
  <div className="bt-options" data-testid={`bt-options-${name}`}>
    {options.map((option) => (
      <label key={option} className={`bt-option ${value === option ? "selected" : ""}`} data-testid={`bt-option-${name}-${option.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase()}`}>
        <input type="radio" name={name} value={option} checked={value === option} onChange={() => onChange(option)} />
        <span>{option}</span>
      </label>
    ))}
  </div>
);

export default function BoardTransformationPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [contact, setContact] = useState({ name: "", email: "", organization: "", phone: "" });
  const [answers, setAnswers] = useState({
    present_board: "", active_board: "", need_recruit: "", reactivate_inactive: "",
    board_fundraising_now: "", want_fundraising: "",
  });

  const setAnswer = (key, value) => setAnswers((prev) => ({ ...prev, [key]: value }));

  const validateStep = () => {
    setError("");
    if (step === 0) {
      if (!contact.name || !contact.email || !contact.organization || !contact.phone) { setError("Please complete your contact details."); return false; }
    }
    if (step === 1) {
      const total = Number(answers.present_board), active = Number(answers.active_board);
      if (answers.present_board === "" || answers.active_board === "" || Number.isNaN(total) || Number.isNaN(active) || total < 0 || active < 0) { setError("Please enter your board numbers."); return false; }
      if (active > total) { setError("Active Board Members cannot exceed your total Board Members."); return false; }
    }
    if (step === 2 && !answers.need_recruit) { setError("Please choose an answer."); return false; }
    if (step === 3 && !answers.reactivate_inactive) { setError("Please choose an answer."); return false; }
    if (step === 4 && (!answers.board_fundraising_now || !answers.want_fundraising)) { setError("Please answer both questions."); return false; }
    return true;
  };

  const next = () => { if (validateStep()) setStep((s) => s + 1); };

  const submit = async () => {
    if (!validateStep()) return;
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/funnel-leads/board_transformation`, {
        name: contact.name, email: contact.email, phone: contact.phone, organization: contact.organization,
        answers,
      });
      navigate(`/board-transformation/result/${response.data.result_token}`);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not submit your answers. Please try again.");
    }
    setBusy(false);
  };

  return (
    <FunnelLayout restrained>
      <main className="bt-page" data-testid="board-transformation-page" style={{ maxWidth: 720, margin: "0 auto", padding: "48px 20px" }}>
        <header style={{ marginBottom: 28 }}>
          <p className="eyebrow" data-testid="bt-eyebrow">Board Transformation</p>
          <h1 data-testid="bt-headline">{SITE_CONTENT.boardTransformation.headline}</h1>
          <p data-testid="bt-intro">{SITE_CONTENT.boardTransformation.intro}</p>
        </header>

        {step === 0 && (
          <section className="member-card" data-testid="bt-step-contact">
            <h2>Tell Us Where to Send Your Results</h2>
            {[["name", "Name"], ["email", "Email"], ["organization", "Organization Name"], ["phone", "Phone Number"]].map(([key, label]) => (
              <label className="field" key={key} style={{ display: "block", marginBottom: 12 }}>
                <span>{label} <b>*</b></span>
                <input type={key === "email" ? "email" : "text"} value={contact[key]} onChange={(e) => setContact({ ...contact, [key]: e.target.value })} style={{ width: "100%" }} data-testid={`bt-contact-${key}`} />
              </label>
            ))}
          </section>
        )}

        {step === 1 && (
          <section className="member-card" data-testid="bt-step-1">
            <h2>What Does Your Board Look Like Today?</h2>
            <label className="field" style={{ display: "block", marginBottom: 12 }}>
              <span>How many Board Members do you currently have? <b>*</b></span>
              <input type="number" min="0" value={answers.present_board} onChange={(e) => setAnswer("present_board", e.target.value)} data-testid="bt-total-members" />
            </label>
            <label className="field" style={{ display: "block" }}>
              <span>How many of those Board Members are currently active? <b>*</b></span>
              <input type="number" min="0" value={answers.active_board} onChange={(e) => setAnswer("active_board", e.target.value)} data-testid="bt-active-members" />
            </label>
          </section>
        )}

        {step === 2 && (
          <section className="member-card" data-testid="bt-step-2">
            <h2>Do You Need More People Around the Table?</h2>
            <p>Do you think you need to recruit new Board Members?</p>
            <RadioGroup name="need_recruit" options={RECRUIT_OPTIONS} value={answers.need_recruit} onChange={(v) => setAnswer("need_recruit", v)} />
          </section>
        )}

        {step === 3 && (
          <section className="member-card" data-testid="bt-step-3">
            <h2>What Do You Want to Do About Your Inactive Board Members?</h2>
            <p>Would you like to reactivate the Board Members who are currently inactive?</p>
            <RadioGroup name="reactivate_inactive" options={REACTIVATE_OPTIONS} value={answers.reactivate_inactive} onChange={(v) => setAnswer("reactivate_inactive", v)} />
          </section>
        )}

        {step === 4 && (
          <section className="member-card" data-testid="bt-step-4">
            <h2>What About Fundraising?</h2>
            <p>Do your Board Members currently help raise money?</p>
            <RadioGroup name="board_fundraising_now" options={FUNDRAISING_NOW_OPTIONS} value={answers.board_fundraising_now} onChange={(v) => setAnswer("board_fundraising_now", v)} />
            <p style={{ marginTop: 18 }}>Would you like your Board Members to actively help raise money for the organization?</p>
            <RadioGroup name="want_fundraising" options={WANT_FUNDRAISING_OPTIONS} value={answers.want_fundraising} onChange={(v) => setAnswer("want_fundraising", v)} />
          </section>
        )}

        {error && <p className="submit-error" data-testid="bt-error">{error}</p>}
        <div style={{ display: "flex", gap: 10, marginTop: 20 }}>
          {step > 0 && <button className="button button-back" onClick={() => setStep((s) => s - 1)} data-testid="bt-back-button">Back</button>}
          {step < 4 && <button className="button" onClick={next} data-testid="bt-next-button">Continue</button>}
          {step === 4 && <button className="button" disabled={busy} onClick={submit} data-testid="bt-submit-button">{busy ? "Submitting…" : "TELL ME WHAT MY BOARD NEEDS"}</button>}
        </div>
      </main>
    </FunnelLayout>
  );
}
