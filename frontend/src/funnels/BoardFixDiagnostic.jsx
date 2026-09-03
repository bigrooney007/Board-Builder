import { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const QUESTIONS = [
  { key: "has_board", label: "Do you currently have Board Members serving the organization?", options: ["Yes", "No"], always: true },
  { key: "active_participation", label: "Are most of your current Board Members actively participating and carrying meaningful responsibility?", options: ["Yes", "No", "Some are, some are not"] },
  { key: "right_people", label: "Do you believe your current Board has the people, skills, experience and relationships the organization needs to move forward?", options: ["Yes", "No", "Not sure"] },
  { key: "fundraising_working", label: "Is your Board currently working with you to raise money and build the organization's fundraising system?", options: ["Yes", "No", "Only a little"] },
];

const PATHWAY_ROUTES = {
  reactivation: "/board-reactivation",
  recruitment: "/board-recruitment",
  activation: "/board-fundraising-activation",
  complete_transformation: "/complete-board-transformation",
};

const storedToken = () => {
  try { return JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}").result_token || ""; } catch { return ""; }
};

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 80, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px 16px" };

export const BoardFixDiagnostic = () => {
  const navigate = useNavigate();
  const [answers, setAnswers] = useState({ has_board: "", active_participation: "", right_people: "", fundraising_working: "" });
  const [showContact, setShowContact] = useState(false);
  const [contact, setContact] = useState({ name: "", email: "", organization: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [contactError, setContactError] = useState("");

  const visible = QUESTIONS.filter((q) => q.always || answers.has_board === "Yes");
  const complete = visible.every((q) => answers[q.key]);

  const openContact = () => {
    if (!complete) { setError("Please answer every question so we can show you where to start."); return; }
    setError("");
    setShowContact(true);
  };

  const seeRecommendation = async () => {
    if (!contact.name.trim() || !contact.email.trim() || !contact.organization.trim()) {
      setContactError("Please enter your name, email and organization name.");
      return;
    }
    setBusy(true); setContactError("");
    try {
      const response = await axios.post(`${API}/funnel-leads/board-fix/diagnostic`, {
        result_token: storedToken(), ...answers,
        name: contact.name, email: contact.email, organization: contact.organization,
      });
      if (response.data.result_token) {
        try { sessionStorage.setItem("funnelLeadContext", JSON.stringify({ result_token: response.data.result_token })); } catch { /* best-effort */ }
      }
      navigate(PATHWAY_ROUTES[response.data.recommended_pathway] || "/complete-board-transformation");
    } catch (err) {
      setContactError(err.response?.data?.detail || "We could not process your answers. Please try again.");
      setBusy(false);
    }
  };

  return (
    <section className="offer-sales-offers" data-testid="bfd-diagnostic">
      <h2 style={{ textAlign: "center", fontWeight: 800, fontSize: "1.8rem" }} data-testid="bfd-heading">Tell Us What Is Happening With Your Board</h2>
      <p style={{ textAlign: "center" }} data-testid="bfd-supporting"><strong>Answer the four questions below about your board. Based on your answers, I'll show you where I believe you should begin and exactly how to fix it.</strong></p>
      {visible.map((question) => (
        <div key={question.key} style={{ margin: "18px 0" }} data-testid={`bfd-question-${question.key}`}>
          <p style={{ fontWeight: 700, marginBottom: 8 }}>{question.label}</p>
          <div className="bt-options">
            {question.options.map((option) => (
              <label key={option} className={`bt-option ${answers[question.key] === option ? "selected" : ""}`} data-testid={`bfd-option-${question.key}-${option.replace(/[^a-zA-Z0-9]+/g, "-").toLowerCase()}`}>
                <input type="radio" name={question.key} value={option} checked={answers[question.key] === option} onChange={() => setAnswers((prev) => ({ ...prev, [question.key]: option }))} />
                <span>{option}</span>
              </label>
            ))}
          </div>
        </div>
      ))}
      {error && <p className="submit-error" data-testid="bfd-error">{error}</p>}
      <div style={{ textAlign: "center", marginTop: 14 }}>
        <button type="button" className="button" onClick={openContact} data-testid="bfd-submit-button">SHOW ME WHERE MY BOARD NEEDS TO START</button>
      </div>
      {showContact && (
        <div style={overlayStyle} data-testid="bfd-contact-modal">
          <div style={{ background: "#fff", maxWidth: 460, width: "100%", padding: 28, borderRadius: 10 }}>
            <h2 style={{ marginTop: 0, fontWeight: 800 }} data-testid="bfd-contact-title">See My Recommendation</h2>
            <label className="intake-field">Name
              <input value={contact.name} onChange={(e) => setContact({ ...contact, name: e.target.value })} data-testid="bfd-contact-name" />
            </label>
            <label className="intake-field">Email
              <input type="email" value={contact.email} onChange={(e) => setContact({ ...contact, email: e.target.value })} data-testid="bfd-contact-email" />
            </label>
            <label className="intake-field">Organization Name
              <input value={contact.organization} onChange={(e) => setContact({ ...contact, organization: e.target.value })} data-testid="bfd-contact-organization" />
            </label>
            {contactError && <p className="submit-error" data-testid="bfd-contact-error">{contactError}</p>}
            <div style={{ display: "flex", gap: 10, marginTop: 12, flexWrap: "wrap" }}>
              <button type="button" className="button" onClick={seeRecommendation} disabled={busy} data-testid="bfd-contact-submit">{busy ? "One moment…" : "See My Recommendation"}</button>
              <button type="button" className="button button-outline" onClick={() => setShowContact(false)} disabled={busy} data-testid="bfd-contact-cancel">Back</button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
};
