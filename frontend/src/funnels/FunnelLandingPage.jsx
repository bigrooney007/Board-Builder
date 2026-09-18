import RecruitmentHomePage from "./RecruitmentHomePage";
import { FunnelLayout } from "./FunnelLayout";
import { FunnelStepForm } from "./FunnelStepForm";
import { funnelConfigs } from "./funnelConfig";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { PAGE_META, usePageMeta } from "@/seo";

export default function FunnelLandingPage({ offerSource }) {
  const config = funnelConfigs[offerSource];
  const meta = PAGE_META[offerSource] || PAGE_META.recruitment;
  usePageMeta(meta[0], meta[1]);
  const isRecruitment = offerSource === "recruitment";
  if (isRecruitment) return <RecruitmentHomePage form={<FunnelStepForm offerSource={offerSource} />} />;
  return (
    <FunnelLayout>
      <main data-testid={`${offerSource}-landing-page`}>
        <section className={`funnel-hero-banner ${offerSource}`} data-testid={`${offerSource}-hero-banner`}>
          <p className="eyebrow" data-testid={`${offerSource}-eyebrow`}>{config.eyebrow}</p>
          <h1 data-testid={`${offerSource}-headline`}>{config.heading}</h1>
          <p className="funnel-hero-banner-supporting" data-testid={`${offerSource}-supporting`}>{config.supporting}</p>
          {config.supportingParagraph && <p className="funnel-hero-banner-secondary" data-testid={`${offerSource}-supporting-paragraph`}>{config.supportingParagraph}</p>}
          <i aria-hidden="true" />
        </section>
        <FunnelStepForm offerSource={offerSource} />
        <TestimonialCarousel heading={isRecruitment ? "See What Other Nonprofit Leaders Have Accomplished" : "Nonprofit Leaders We Have Helped Build Stronger Boards"} idPrefix={`${config.slug}-landing`} />
      </main>
    </FunnelLayout>
  );
}

