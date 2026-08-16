import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { CheckCircle2 } from "lucide-react";
import { FunnelLayout } from "./FunnelLayout";
import { usePageMeta } from "@/seo";
import { strategyReviewText } from "../content/appContent";
import { strategyReviewPageText } from "../content/siteContent";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function StrategyReviewPage() {
  usePageMeta("Fundraising Strategy Plan Review | Nonprofit Board Builder", "Review your organization's Fundraising Strategy Plan and share your input.", true);
  const { token } = useParams();
  const [context, setContext] = useState(null);
  const [state, setState] = useState("loading");
  const [identity, setIdentity] = useState({ full_name: "", email: "", role: "" });
  const [ideaReviews, setIdeaReviews] = useState({});
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
  const ideas = context?.ideas || [];

  const setIdea = (key, patch) => setIdeaReviews((current) => ({ ...current, [key]: { ...(current[key] || {}), ...patch } }));

  const submit = async () => {
    const found = {};
    if (context.requires_identity) {
      if (!identity.full_name.trim()) found.full_name = "Required.";
      if (!/^\S+@\S+\.\S+$/.test(identity.email.trim())) found.email = "Enter a valid email address.";
    }
    ideas.forEach((idea) => {
      const entry = ideaReviews[idea.key] || {};
      if (!entry.decision) found[`idea-${idea.key}`] = "Please approve or disapprove this idea.";
      else if (entry.decision === "Disapprove" && !(entry.reason || "").trim()) found[`idea-${idea.key}`] = "Please share your reason for disapproving.";
    });
    if (!position) found.position = "Please choose the option that best reflects your position.";
    if (needsDiscussion && !discussion.trim()) found.discussion = "Please share what you would like the Board to discuss.";
    if (!contribution.trim()) found.contribution = "This question is required.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    setSubmitError("");
    try {
      await axios.post(`${API}/strategy-review/${token}`, {
        ...identity,
        position, discussion_points: discussion, contribution, support_needs: support,
        idea_reviews: ideas.map((idea) => ({
          key: idea.key, title: idea.title,
          decision: ideaReviews[idea.key].decision,
          reason: ideaReviews[idea.key].reason || "",
        })),
      });
      setState("done");
      window.scrollTo(0, 0);
    } catch (err) {
      setSubmitError(err.response?.data?.detail || "We could not submit your review. Please try again.");
      setBusy(false);
    }
  };

  if (state === "loading") return <FunnelLayout restrained><main><div className="intake-card" data-testid="sr-loading"><h2>{strategyReviewText.h_loading}</h2></div></main></FunnelLayout>;
  if (state === "invalid") {
    return <FunnelLayout restrained><main><div className="intake-card" data-testid="sr-invalid"><h2>{strategyReviewText.h_thisReviewLinkIsNot}</h2><p>{strategyReviewPageText.pleaseContactThePersonWho}</p></div></main></FunnelLayout>;
  }
  if (state === "done") {
    return (
      <FunnelLayout restrained>
        <main>
          <div className="intake-card" data-testid="sr-thank-you">
            <p className="purchase-confirmed"><CheckCircle2 size={20} /> Review submitted</p>
            <h2>{strategyReviewText.h_thankYou}</h2>
            <p>Your review of the Fundraising Strategy Plan has been submitted to {context.organization_name}.</p>
            <p>{strategyReviewPageText.yourInputWillHelpThe}</p>
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
          {context.requires_identity && (
            <>
              <h2 className="intake-step-title" data-testid="sr-about-you-heading">{strategyReviewText.h_aboutYou}</h2>
              <div className="two-col-fields">
                <label className="field"><span>Full Name <b>*</b></span><input value={identity.full_name} onChange={(e) => setIdentity({ ...identity, full_name: e.target.value })} data-testid="sr-full-name" />{errors.full_name && <p className="field-error">{errors.full_name}</p>}</label>
                <label className="field"><span>Email <b>*</b></span><input type="email" value={identity.email} onChange={(e) => setIdentity({ ...identity, email: e.target.value })} data-testid="sr-email" />{errors.email && <p className="field-error">{errors.email}</p>}</label>
              </div>
              <label className="field"><span>Current Board Role</span><input value={identity.role} onChange={(e) => setIdentity({ ...identity, role: e.target.value })} data-testid="sr-role" /></label>
            </>
          )}

          <h2 className="intake-step-title" data-testid="sr-ideas-heading">{strategyReviewText.h_reviewEachIdea}</h2>
          <p data-testid="sr-ideas-instruction">{strategyReviewText.d_reviewEachIdea}</p>
          {ideas.map((idea) => {
            const entry = ideaReviews[idea.key] || {};
            return (
              <div key={idea.key} style={{ border: "1px solid #ddd", borderRadius: 8, padding: 18, marginBottom: 18, background: "#fff" }} data-testid={`sr-idea-${idea.key}`}>
                <h3 style={{ marginTop: 0 }}>{idea.title}</h3>
                <p style={{ whiteSpace: "pre-wrap" }}>{idea.content}</p>
                <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                  <label className={`choice ${entry.decision === "Approve" ? "selected" : ""}`}>
                    <input type="radio" name={`idea-${idea.key}`} checked={entry.decision === "Approve"} onChange={() => setIdea(idea.key, { decision: "Approve" })} data-testid={`sr-approve-${idea.key}`} />
                    <span>Approve</span>
                  </label>
                  <label className={`choice ${entry.decision === "Disapprove" ? "selected" : ""}`}>
                    <input type="radio" name={`idea-${idea.key}`} checked={entry.decision === "Disapprove"} onChange={() => setIdea(idea.key, { decision: "Disapprove" })} data-testid={`sr-disapprove-${idea.key}`} />
                    <span>Disapprove</span>
                  </label>
                </div>
                {entry.decision === "Disapprove" && (
                  <label className="field" style={{ marginTop: 10 }}><span>{strategyReviewPageText.whyDoYouDisapproveOf}<b>*</b></span>
                    <textarea rows={3} value={entry.reason || ""} onChange={(e) => setIdea(idea.key, { reason: e.target.value })} data-testid={`sr-reason-${idea.key}`} />
                  </label>
                )}
                {errors[`idea-${idea.key}`] && <p className="field-error" data-testid={`sr-idea-error-${idea.key}`}>{errors[`idea-${idea.key}`]}</p>}
              </div>
            );
          })}

          <h2 className="intake-step-title" data-testid="sr-your-review-heading">{strategyReviewText.h_yourReview}</h2>
          <fieldset className="field choice-field" data-testid="sr-position-field">
            <legend>{strategyReviewPageText.afterReviewingTheFundraisingStrategy}<b>*</b></legend>
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

          <label className="field"><span>{strategyReviewPageText.basedOnThisPlanWhere}<b>*</b></span>
            <textarea rows={5} value={contribution} onChange={(e) => setContribution(e.target.value)} data-testid="sr-contribution" />
            {errors.contribution && <p className="field-error">{errors.contribution}</p>}
          </label>

          <label className="field"><span>{strategyReviewPageText.whatSupportOrResourcesWould}</span>
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
