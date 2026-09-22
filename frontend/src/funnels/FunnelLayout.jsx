import { Link, useLocation, useNavigate } from "react-router-dom";
import { ReviewModeBanner } from "@/reviewMode";
import { AdminPreviewBanner } from "@/adminPreview";
import { useMemberAuth } from "@/member/MemberAuthContext";
import { funnelLayoutText } from "../content/appContent";

const PUBLIC_TASK_PREFIXES = [
  "/board-opportunities/",
  "/apply/",
  "/reference-form/",
  "/referee-form/",
  "/board-profile/",
  "/sign/",
  "/shared/",
];

export const FunnelLayout = ({ children, restrained = false, isolated = false }) => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { member, loading, logout } = useMemberAuth();
  const publicTask = PUBLIC_TASK_PREFIXES.some((prefix) => pathname.startsWith(prefix));

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className={`funnel-page-shell${restrained ? " funnel-restrained" : ""}`}>
      <AdminPreviewBanner />
      <ReviewModeBanner />

      {!publicTask && !isolated && (
        <nav className="site-nav funnel-nav" data-testid="funnel-navigation" style={{ justifyContent: "flex-end" }}>
          {!loading && (
            member ? (
              <button className="button button-small" onClick={handleLogout} data-testid="funnel-logout-button">
                {funnelLayoutText.t_logOut || "Log Out"}
              </button>
            ) : (
              <Link className="button button-small" to="/login" data-testid="funnel-login-link">
                {funnelLayoutText.t_logIn}
              </Link>
            )
          )}
        </nav>
      )}

      {children}

      <footer className="footer" data-testid="funnel-footer">
        {!isolated && <p>{funnelLayoutText.nonprofitBoardBuilderHelpsNonprofits}</p>}
        <div className="footer-links">
          <Link to="/privacy-policy">{funnelLayoutText.t_privacyPolicy}</Link>
          <Link to="/terms">Terms</Link>
        </div>
      </footer>
    </div>
  );
};
