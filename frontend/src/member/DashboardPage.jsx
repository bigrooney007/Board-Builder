import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";
import { dashboardText, dashboardPageText } from "../content/appContent";

export const DashboardPage = () => {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [qualifying, setQualifying] = useState([]);

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login"); return; }
    memberApi.get("/members/dashboard").then((response) => {
      setData(response.data);
      if (response.data.fbb) return;
      const hasRecruitment = response.data.products.some((p) => !p.entitlement.startsWith("reactivation_") && !p.entitlement.startsWith("activation_"));
      if (hasRecruitment) {
        memberApi.get("/workspace/applications").then((r) => {
          setQualifying((r.data.applications || []).filter((a) =>
            ["Moving Forward", "Selected", "Conditional Appointment"].includes(a.status) || a.final_outcome === "Joined Board"));
        }).catch(() => {});
      }
    }).catch(() => setError("We could not load your dashboard."));
  }, [loading, member, navigate]);

  return (
    <MemberShell>
      <main className="member-page" data-testid="member-dashboard-page">
        <header className="member-page-heading">
          <p className="eyebrow">Member area</p>
          <h1 data-testid="dashboard-heading">{dashboardText.h_myBoardBuilder}</h1>
          {member && <p>Welcome back, {member.first_name}.</p>}
        </header>
        {error && <p className="submit-error">{error}</p>}
        {data && data.products.length === 0 && (
          <div className="member-card" data-testid="dashboard-empty">
            <h2>{dashboardText.h_noProgramsYet}</h2>
            <p>{dashboardPageText.yourAccountDoesNotInclude}</p>
          </div>
        )}
        {data && data.fbb && data.products.map((product) => (
          <section className="member-card dashboard-product" key={product.entitlement} data-testid={`dashboard-product-${product.entitlement}`}>
            <p className="eyebrow">Fundraising Board Builder</p>
            <h2>{product.name}</h2>
            <p>{product.description}</p>
            <button className="button" onClick={() => navigate(product.route)} data-testid={`dashboard-open-${product.entitlement}`}>Open {product.name} <ArrowRight size={16} /></button>
          </section>
        ))}
        {data && !data.fbb && data.products.map((product) => {
          const productLabel = product.entitlement === "reactivation_self_guided" ? "Board Reactivation" : product.entitlement === "activation_self_guided" ? "Board Fundraising Activation" : "Board Recruitment";
          const emailLed = product.route === "/app/activation/start";
          return (
          <section className="member-card dashboard-product" key={product.entitlement} data-testid={`dashboard-product-${product.entitlement}`}>
            <p className="eyebrow">{productLabel}</p>
            <h2>{product.name}</h2>
            {emailLed ? (
              <p data-testid="dashboard-activation-email-led">Set up your Board Fundraising Planning process once — after that, we track your Board's responses and keep you updated by email.</p>
            ) : (
              <>
                <div className="dashboard-product-stats">
                  <div><span>Purchased tier</span><strong data-testid={`dashboard-tier-${product.entitlement}`}>{product.entitlement === "recruitment_basic" ? "$97 Basic" : "Self-Guided System"}</strong></div>
                  <div><span>Course progress</span><strong data-testid={`dashboard-progress-${product.entitlement}`}>{product.percent_complete}% · {product.modules_completed} of {product.modules_total} modules</strong></div>
                  <div><span>Last module visited</span><strong data-testid={`dashboard-last-module-${product.entitlement}`}>{product.last_module ? `Module ${product.last_module.number}: ${product.last_module.title}` : "Not started yet"}</strong></div>
                </div>
                <div className="dashboard-progress-bar"><i style={{ width: `${product.percent_complete}%` }} /></div>
              </>
            )}
            <button className="button" onClick={() => navigate(product.route)} data-testid={`dashboard-continue-${product.entitlement}`}>Continue {productLabel} <ArrowRight size={16} /></button>
          </section>
          );
        })}
        {qualifying.length > 0 && (
          <section className="member-card dashboard-product" data-testid="dashboard-candidate-actions">
            <p className="eyebrow">{dashboardPageText.boardRecruitmentYourCandidates}</p>
            <h2>{dashboardText.h_boardMemberPortfolioAmpFinal}</h2>
            <p>{qualifying.map((a) => a.profile_snapshot?.full_name || a.applicant_email).filter(Boolean).join(", ")} {qualifying.length === 1 ? "has" : "have"} reached the candidate stage.</p>
            <div className="material-actions">
              <button className="button" onClick={() => navigate("/app/recruitment/self-guided/results")} data-testid="dashboard-portfolio-button">Board Member Portfolio <ArrowRight size={16} /></button>
              <button className="button button-back" onClick={() => navigate("/app/recruitment/self-guided/module/6")} data-testid="dashboard-final-offer-button">{dashboardPageText.generateFinalBoardOfferEmail}<ArrowRight size={16} /></button>
            </div>
          </section>
        )}
      </main>
    </MemberShell>
  );
};
