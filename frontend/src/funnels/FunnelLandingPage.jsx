import { ArrowRight } from "lucide-react";
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
  const scrollToForm = () => document.getElementById("offer-form")?.scrollIntoView({ behavior: "smooth" });
  return (
    <FunnelLayout>
      <main data-testid={`${offerSource}-landing-page`}>
        <section className={`funnel-hero ${offerSource}`}>
          <div>
            <p className="eyebrow" data-testid={`${offerSource}-eyebrow`}>{config.eyebrow}</p>
            <h1 data-testid={`${offerSource}-headline`}>{config.heading}</h1>
            <p className="funnel-supporting" data-testid={`${offerSource}-supporting`}>{config.supporting}</p>
            {!isRecruitment && config.supportingParagraph && <p data-testid={`${offerSource}-supporting-paragraph`}>{config.supportingParagraph}</p>}
            {!isRecruitment && <button className="button" onClick={scrollToForm} data-testid={`${offerSource}-hero-button`}>{config.heroCta} <ArrowRight size={18} /></button>}
          </div>
          <div className="funnel-hero-mark" aria-hidden="true">
            <span>{offerSource === "recruitment" ? "RECRUIT" : offerSource === "reactivation" ? "REACTIVATE" : "ACTIVATE"}</span>
            <strong>{offerSource === "recruitment" ? "Find the right people" : offerSource === "reactivation" ? "Reset expectations" : "Turn strengths into action"}</strong>
            <i />
          </div>
        </section>
        {isRecruitment ? (
          <>
            <FunnelStepForm offerSource={offerSource} />
            <TestimonialCarousel heading="See What Other Nonprofit Leaders Have Accomplished" idPrefix="recruit-landing" />
          </>
        ) : (
          <>
            <TestimonialCarousel heading="Nonprofit Leaders We Have Helped Build Stronger Boards" idPrefix={`${config.slug}-landing`} />
            <FunnelStepForm offerSource={offerSource} />
          </>
        )}
      </main>
    </FunnelLayout>
  );
}
