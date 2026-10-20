import { Link } from "react-router-dom";
import { SiteBrand } from "@/components/SiteBrand";
import { ReviewModeBanner } from "@/reviewMode";
import { AdminPreviewBanner } from "@/adminPreview";


export const MemberShell = ({ children }) => {
  return (
    <div className="member-shell">
      <AdminPreviewBanner />
      <ReviewModeBanner />
      <nav className="site-nav member-nav" data-testid="member-navigation"><SiteBrand/><Link to="/">Our Services</Link></nav>
      {children}
    </div>
  );
};
