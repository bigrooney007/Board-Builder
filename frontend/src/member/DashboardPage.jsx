import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { memberApi } from "./api";
import { useMemberAuth } from "./MemberAuthContext";
import { MemberShell } from "./MemberShell";

export const DashboardPage = () => {
  const { member, loading } = useMemberAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (loading) return;
    if (!member) { navigate("/login"); return; }
    memberApi.get("/members/dashboard").then((response) => setData(response.data)).catch(() => setError("We could not load your dashboard."));
  }, [loading, member, navigate]);

  return (
    <MemberShell>
      <main className="member-page" data-testid="member-dashboard-page">
        <header className="member-page-heading">
          <p className="eyebrow">Member area</p>
          <h1 data-testid="dashboard-heading">My Board Builder</h1>
          {member && <p>Welcome back, {member.first_name}.</p>}
        </header>
        {error && <p className="submit-error">{error}</p>}
        {data && data.products.length === 0 && (
          <div className="member-card" data-testid="dashboard-empty">
            <h2>No Programs Yet</h2>
            <p>Your account does not include a program yet. When you purchase a Recruitment program, it will appear here.</p>
          </div>
        )}
        {data && data.products.map((product) => {
          const isReactivation = product.entitlement === "reactivation_self_guided";
          return (
          <section className="member-card dashboard-product" key={product.entitlement} data-testid={`dashboard-product-${product.entitlement}`}>
            <p className="eyebrow">{isReactivation ? "Board Reactivation" : "Board Recruitment"}</p>
            <h2>{product.name}</h2>
            <div className="dashboard-product-stats">
              <div><span>Purchased tier</span><strong data-testid={`dashboard-tier-${product.entitlement}`}>{product.entitlement === "recruitment_basic" ? "$97 Basic" : "Self-Guided System"}</strong></div>
              <div><span>Course progress</span><strong data-testid={`dashboard-progress-${product.entitlement}`}>{product.percent_complete}% · {product.modules_completed} of {product.modules_total} modules</strong></div>
              <div><span>Last module visited</span><strong data-testid={`dashboard-last-module-${product.entitlement}`}>{product.last_module ? `Module ${product.last_module.number}: ${product.last_module.title}` : "Not started yet"}</strong></div>
            </div>
            <div className="dashboard-progress-bar"><i style={{ width: `${product.percent_complete}%` }} /></div>
            <button className="button" onClick={() => navigate(product.route)} data-testid={`dashboard-continue-${product.entitlement}`}>{isReactivation ? "Continue Board Reactivation" : "Continue Board Recruitment"} <ArrowRight size={16} /></button>
          </section>
          );
        })}
      </main>
    </MemberShell>
  );
};
