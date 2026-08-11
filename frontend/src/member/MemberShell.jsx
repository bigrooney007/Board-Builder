import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "./MemberAuthContext";
import { ReviewModeBanner } from "@/reviewMode";

const logoUrl = "https://customer-assets-jt897jd0.emergentagent.net/job_board-assessment/artifacts/2qaqmobl_Minimalist%20nonprofit%20logo%20design.png";

export const MemberShell = ({ children }) => {
  const { member, logout } = useMemberAuth();
  const navigate = useNavigate();
  const handleLogout = async () => { await logout(); navigate("/login"); };
  return (
    <div className="member-shell">
      <ReviewModeBanner />
      <nav className="site-nav member-nav" data-testid="member-navigation">
        <Link className="brand" to="/" data-testid="member-home-logo"><img src={logoUrl} alt="Nonprofit Board Builder" /></Link>
        <div className="nav-links">
          <Link to="/app" data-testid="member-dashboard-link">My Board Builder</Link>
        </div>
        {member ? (
          <div className="member-nav-right">
            <span className="member-nav-name" data-testid="member-nav-name">{member.first_name}</span>
            <button className="button button-small" onClick={handleLogout} data-testid="member-logout-button">Log Out</button>
          </div>
        ) : (
          <Link className="button button-small" to="/login" data-testid="member-login-link">Log In</Link>
        )}
      </nav>
      {children}
    </div>
  );
};
