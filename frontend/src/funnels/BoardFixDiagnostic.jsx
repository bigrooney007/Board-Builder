import { useState } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const QUESTIONS = [
  { key: "has_board", label: "Do you currently have Board Members serving the organization?", options: ["Yes", "No"], always: true },
  { key: "active_participation", label: "Are most of your current Board Members actively participating and carrying meaningful responsibility?", options: ["Yes", "No", "Some are, some are not"] },
  { key: "right_people", label: "Do you believe your current Board has the people, skills, experience and relationships the organization needs to move forward?", options: ["Yes", "No", "Not sure"] },
  { key: "fundraising_working", label: "Is your Board currently working with you to raise money and build the organization's fundraising system?", options: ["Yes", "No", "Only a little"] },
];

export const RESULTS = {
  recruitment: {
    heading: "Your Immediate Priority: Build Your Board",
    explanation: "You have already built the organization. Your immediate limitation is that you do not have the Board Members around you that the organization now needs. Your next step is to build the right Board around your mission.",
    offerName: "Board Recruitment", regular: "$1,997", price: "$997", cta: "BUILD MY BOARD",
    what: "I will work with you to identify the Board Members your organization needs, launch your recruitment campaign, interview and select the right candidates, and move them through appointment and onboarding.",
  },
  reactivation: {
    heading: "Your Immediate Priority: Reactivate Your Board",
    explanation: "You already have Board Members, but some are inactive, disengaged or not carrying meaningful responsibility. Your first priority is to get the people already on your Board to step up or step down before doing anything else.",
    offerName: "Board Reactivation", regular: "$1,997", price: "$997", cta: "REACTIVATE MY BOARD",
    what: "I will work with you to determine who on your current Board is ready to step up, who may need to step down, and how to rebuild an active Board around the people who are ready to serve.",
  },
  activation: {
    heading: "Your Immediate Priority: Activate Your Board for Fundraising",
    explanation: "You already have a reasonably active Board. Your immediate opportunity is to work with them to build your fundraising strategy, determine how each Board Member can participate in fundraising, and build the fundraising system your organization needs.",
    offerName: "Board Fundraising Activation", regular: "$1,997", price: "$997", cta: "ACTIVATE MY BOARD",
    what: "I will work with you and your Board to build your Fundraising Strategy, adopt it together, agree how each Board Member will participate, and equip your Board to begin executing the plan.",
  },
  complete_transformation: {
    heading: "Your Board Needs a Complete Transformation",
    explanation: "Your Board is dealing with more than one significant problem. Fixing only one part will leave the others unresolved. Your Board needs the complete Reactivate → Recruit → Activate process.",
    offerName: "Complete Board Transformation", regular: "$3,997", price: "$1,997", cta: "TRANSFORM MY BOARD",
    what: "We will reactivate your present Board, recruit the people you are missing, and activate the complete Board to raise money and work with you to build your organization's fundraising system.",
  },
};

const resultToken = () => {
  try { return JSON.parse(sessionStorage.getItem("funnelLeadContext") || "{}").result_token || ""; } catch { return ""; }
};

export const startOfferCheckout = async (recommendation, leadToken = "") => {
  const endpoint = recommendation === "complete_transformation" ? "complete-transformation-checkout" : "dfy-checkout";
  const body = { origin_url: window.location.origin, result_token: leadToken };
  if (recommendation !== "complete_transformation") body.pathway = recommendation;
  else body.cancel_path = "/offer/board-fix";
  const response = await axios.post(`${API}/payments/${endpoint}`, body);
  window.location.href = response.data.checkout_url;
};

export const OfferPurchaseBlock = ({ recommendation, showDiagnosis = false, leadToken = "" }) => {
  const result = RESULTS[recommendation];
  const [checkingOut, setCheckingOut] = useState(false);
  const [error, setError] = useState("");

  const buy = async () => {
    setCheckingOut(true); setError("");
    try {
      await startOfferCheckout(recommendation, leadToken);
    } catch {
      setError("We could not start your checkout. Please try again.");
      setCheckingOut(false);
    }
  };

  return (
    <section className="offer-sales-offers" data-testid={showDiagnosis ? "bfd-result" : `direct-offer-${recommendation}`}>
      <div className="offer-sales-grid" style={{ gridTemplateColumns: "1fr" }}>
        <section className="offer-sales-card" data-testid={`bfd-result-${recommendation}`}>
          {showDiagnosis && (
            <>
              <h2 data-testid="bfd-result-heading">{result.heading}</h2>
              <p data-testid="bfd-result-explanation">{result.explanation}</p>
            </>
          )}
          <h3 style={{ marginBottom: 0 }} data-testid="bfd-result-offer-name">{result.offerName}</h3>
          <p className="offer-regular-price" data-testid="bfd-regular-price">Regular Investment: <s>{result.regular}</s></p>
          <p className="offer-sales-price" data-testid="bfd-price">Get Started Now: {result.price}</p>
          <p className="offer-discount-note" data-testid="bfd-discount-note">50% Immediate-Action Discount</p>
          <p data-testid="bfd-what">{result.what}</p>
          <button type="button" className="button" onClick={buy} disabled={checkingOut} data-testid="bfd-buy-button">{checkingOut ? "Starting secure checkout…" : result.cta}</button>
          {error && <p className="submit-error" data-testid="bfd-checkout-error">{error}</p>}
        </section>
      </div>
    </section>
  );
};

export const BoardFixDiagnostic = () => {
  const [answers, setAnswers] = useState({ has_board: "", active_participation: "", right_people: "", fundraising_working: "" });
  const [recommendation, setRecommendation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const visible = QUESTIONS.filter((q) => q.always || answers.has_board === "Yes");
  const complete = visible.every((q) => answers[q.key]);

  const diagnose = async () => {
    if (!complete) { setError("Please answer every question so we can show you where to start."); return; }
    setBusy(true); setError("");
    try {
      const response = await axios.post(`${API}/funnel-leads/board-fix/diagnostic`, { result_token: resultToken(), ...answers });
      setRecommendation(response.data.recommended_pathway);
    } catch (err) {
      setError(err.response?.data?.detail || "We could not process your answers. Please try again.");
    }
    setBusy(false);
  };

  if (recommendation) {
    return <OfferPurchaseBlock recommendation={recommendation} showDiagnosis leadToken={resultToken()} />;
  }

  return (
    <section className="offer-sales-offers" data-testid="bfd-diagnostic">
      <h2 style={{ textAlign: "center", fontWeight: 800, fontSize: "1.8rem" }} data-testid="bfd-heading">Tell Us What Is Happening With Your Board</h2>
      <p style={{ textAlign: "center" }} data-testid="bfd-supporting"><strong>Answer four short questions and we will show you where your Board needs to start.</strong></p>
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
        <button type="button" className="button" onClick={diagnose} disabled={busy} data-testid="bfd-submit-button">{busy ? "One moment…" : "SHOW ME WHERE MY BOARD NEEDS TO START"}</button>
      </div>
    </section>
  );
};
