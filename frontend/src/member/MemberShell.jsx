import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMemberAuth } from "./MemberAuthContext";
import { ReviewModeBanner } from "@/reviewMode";
import { AdminPreviewBanner } from "@/adminPreview";
import { memberShellText } from "../content/appContent";


export const MemberShell = ({ children }) => {
  const { member, logout } = useMemberAuth();
  const navigate = useNavigate();
  const handleLogout = async () => { await logout(); navigate("/login"); };
  return (
    <div className="member-shell">
      <AdminPreviewBanner />
      <ReviewModeBanner />
      <nav className="site-nav member-nav" data-testid="member-navigation" style={{ justifyContent: "flex-end" }}>
        {member ? (
          <div className="member-nav-right">
            <span className="member-nav-name" data-testid="member-nav-name">{member.first_name}</span>
            <button className="button button-small" onClick={handleLogout} data-testid="member-logout-button">{memberShellText.t_logOut}</button>
          </div>
        ) : (
          <Link className="button button-small" to="/login" data-testid="member-login-link">{memberShellText.t_logIn}</Link>
        )}
      </nav>
      {children}
    </div>
  );
};
