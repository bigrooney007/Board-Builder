import { DashboardPreviewSection } from "@/admin/DashboardPreviewSection";

export { PlatformVideosSection } from "@/admin/PlatformVideosSection";
export { HomepageTextSection } from "@/admin/HomepageTextSection";
export { PlatformAnalyticsSection } from "@/admin/PlatformAnalyticsSection";

export const BoardBuilderPathwaysSection = () => (
  <section data-testid="clean-board-builder-pathways">
    <div className="admin-funnel-numbers-head">
      <div>
        <h2>The 4 Board Builder Pathways</h2>
        <p>Open the real customer dashboard for each product. These are the four paid product houses preserved in the clean rebuild.</p>
      </div>
    </div>
    <DashboardPreviewSection />
  </section>
);
