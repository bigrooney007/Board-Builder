import { Link } from "react-router-dom";
import { FunnelLayout } from "./FunnelLayout";
import { TestimonialCarousel } from "@/components/TestimonialCarousel";
import { SITE_CONTENT } from "@/content/siteContent";

const ROUTES = {
  recruitment: { diy: "/recruit-your-board-yourself", dwy: "/board-recruitment-proposal" },
  reactivation: { diy: "/reactivate-your-board-yourself", dwy: "/board-reactivation-proposal" },
  activation: { diy: "/activate-your-board-yourself", dwy: "/board-activation-proposal" },
};

export default function OfferVideoPage({ offer }) {
  const content = SITE_CONTENT.offerVideos[offer];
  const routes = ROUTES[offer];
  return (
    <FunnelLayout restrained>
      <main data-testid={`offer-video-page-${offer}`} style={{ maxWidth: 900, margin: "0 auto", padding: "48px 20px" }}>
        <header style={{ marginBottom: 26, textAlign: "center" }}>
          <h1 className="video-page-title" data-testid={`offer-headline-${offer}`}>{content.headline}</h1>
        </header>

        <div className="video-stage" data-testid={`offer-video-${offer}`}>
          <span data-testid={`offer-video-placeholder-${offer}`}>{content.videoPlaceholder}</span>
        </div>

        <section data-testid={`offer-payment-choices-${offer}`}>
          <div className="offer-choice-grid">
            <Link className="button" to={routes.diy} data-testid={`offer-diy-button-${offer}`}>{content.diyLabel}</Link>
            <Link className="button button-outline" to={routes.dwy} data-testid={`offer-dwy-button-${offer}`}>{content.dwyLabel}</Link>
          </div>
        </section>

        <div style={{ marginTop: 40 }}>
          <TestimonialCarousel idPrefix={`offer-${offer}`} />
        </div>
      </main>
    </FunnelLayout>
  );
}
