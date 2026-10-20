import { Link, useLocation } from "react-router-dom";
import { ReviewModeBanner } from "@/reviewMode";
import { AdminPreviewBanner } from "@/adminPreview";
import { SiteBrand } from "@/components/SiteBrand";
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
  const publicTask = PUBLIC_TASK_PREFIXES.some((prefix) => pathname.startsWith(prefix));

  return (
    <div className={`funnel-page-shell${restrained ? " funnel-restrained" : ""}`}>
      <AdminPreviewBanner />
      <ReviewModeBanner />

      {!publicTask && !isolated && (
        <nav className="site-nav funnel-nav" data-testid="funnel-navigation"><SiteBrand/><Link to="/">Our Services</Link></nav>
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
