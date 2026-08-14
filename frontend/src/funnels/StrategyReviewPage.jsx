import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { usePageMeta } from "@/seo";
import { strategyReviewText } from "../content/appContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategyReviewPage() {
  usePageMeta("Fundraising Strategy Plan Review | Nonprofit Board Builder", "Review your organization's Fundraising Strategy Plan and share your input.", true);
  const { token } = useParams();
  const [context, setContext] = useState(null);
  const [state, setState] = useState("loading");
  const [position, setPosition] = useState("");
  const [discussion, setDiscussion] = useState("");
  const [contribution, setContribution] = useState("");
  const [support, setSupport] = useState("");
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const [submitError, setSubmitError] = useState("");

  useEffect(() => {
    axios.get(`${API}/strategy-review/${token}`).then((res) => {
      setContext(res.data);
      setState(res.data.submitted ? "done" : "ready");
    }).catch(() => setState("invalid"));
  }, [token]);

  const needsDiscussion = position && position !== "I support the plan as written";

  const submit = async () => {
    const found = {};
    if (!position) found.position = "Please choose the option that best reflects your position.";
    if (needsDiscussion && !discussion.trim()) found.discussion = "Please share what you would like the Board to discuss.";
    if (!contribution.trim()) found.contribution = "This question is required.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setSubmitError("");
    try {
      await axios.post(`${API}/strategy-review/${token}`, { position, discussion_points: discussion, contribution, support_needs: support });
      setState("done");
      window.scrollTo(0, 0);
    } catch (err) {
      setSubmitError(err.response?.data?.detail || "We could not submit your review. Please try again.");
      setBusy(false);
    }
  };

  if (state === "loading") return <FunnelLayout restrained><main><div className="intake-card" data-testid="sr-loading"><h2>{strategyReviewText.h_loading}</h2></div></main></FunnelLayout>;
  if (state === "invalid") {
    return <FunnelLayout restrained><main><div className="intake-card" data-testid="sr-invalid"><h2>{strategyReviewText.h_thisReviewLinkIsNot}</h2><p>Please contact the person who sent you this link and ask them to resend your personal review link.</p></div></main></FunnelLayout>;
  }
  if (state === "done") {
    return (
      <FunnelLayout restrained>
        <main>
          <div className="intake-card" data-testid="sr-thank-you">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Review submitted</p>
            <h2>{strategyReviewText.h_thankYou}</h2>
            <p>Your review of the Fundraising Strategy Plan has been submitted to {context.organization_name}.</p>
            <p>Your input will help the Board work through the strategy and agree on the way forward together.</p>
          </div>
        </main>
      </FunnelLayout>
    );
  }

  return (
    <FunnelLayout restrained>
      <main data-testid="sr-page">
        <section className="funnel-hero-banner brp-hero intake-hero" data-testid="sr-hero">
          <h1 data-testid="sr-title">{strategyReviewText.h_fundraisingStrategyPlan}</h1>
          <p className="funnel-hero-banner-supporting" data-testid="sr-organization">{context.organization_name}</p>
          <i aria-hidden="true" />
        </section>

        <section className="intake-shell" data-testid="sr-body">
          <div style={{ whiteSpace: "pre-wrap", border: "1px solid #ddd", borderRadius: 8, padding: 20, marginBottom: 24, background: "#fff" }} data-testid="sr-strategy-text">{context.strategy_text}</div>

          <h2 className="intake-step-title" data-testid="sr-your-review-heading">{strategyReviewText.h_yourReview}</h2>
          <fieldset className="field choice-field" data-testid="sr-position-field">
            <legend>After reviewing the Fundraising Strategy Plan, which best reflects your position? <b>*</b></legend>
            <div className="choice-grid" style={{ gridTemplateColumns: "1fr" }}>
              {context.options.map((option) => (
                <label className={`choice ${position === option ? "selected" : ""}`} key={option}>
                  <input type="radio" name="position" checked={position === option} onChange={() => setPosition(option)} data-testid={`sr-position-${context.options.indexOf(option) + 1}`} />
                  <span>{option}</span>
                </label>
              ))}
            </div>
            {errors.position && <p className="field-error">{errors.position}</p>}
          </fieldset>

          <label className="field"><span>What suggestions, concerns or changes would you like the Board to discuss before the plan is adopted? {needsDiscussion ? <b>*</b> : "(optional)"}</span>
            <textarea rows={5} value={discussion} onChange={(e) => setDiscussion(e.target.value)} data-testid="sr-discussion" />
            {errors.discussion && <p className="field-error">{errors.discussion}</p>}
          </label>

          <label className="field"><span>Based on this plan, where do you see yourself being able to contribute? <b>*</b></span>
            <textarea rows={5} value={contribution} onChange={(e) => setContribution(e.target.value)} data-testid="sr-contribution" />
            {errors.contribution && <p className="field-error">{errors.contribution}</p>}
          </label>

          <label className="field"><span>What support or resources would help you contribute effectively? (optional)</span>
            <textarea rows={4} value={support} onChange={(e) => setSupport(e.target.value)} data-testid="sr-support" />
          </label>

          {submitError && <p className="submit-error" data-testid="sr-submit-error">{submitError}</p>}
          <div className="intake-nav">
            <span />
            <button type="button" className="button" onClick={submit} disabled={busy} data-testid="sr-submit-button">{busy ? "Submitting…" : "SUBMIT MY PLAN REVIEW"}</button>
          </div>
        </section>
      </main>
    </FunnelLayout>
  );
}
